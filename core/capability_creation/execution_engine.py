import asyncio
import re
import subprocess
from typing import Optional, Tuple

from loguru import logger

from core.capability_creation.constants import (
    _DANGEROUS_PATTERNS, _PIP_PACKAGE_MAP, _INSTALLED_IN_SESSION,
    _MAX_ATTEMPTS, _EXECUTION_TIMEOUT,
)
from core.capability_creation.models import ExecutionResult


def is_dangerous(code: str) -> bool:
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return True
    return False


def extract_missing_module(error_str: str) -> Optional[str]:
    m = re.search(r"No module named ['\"]?(\w+)['\"]?", error_str)
    if m:
        return m.group(1)
    m = re.search(r"cannot import name.*from ['\"]?(\w+)['\"]?", error_str)
    if m:
        return m.group(1)
    return None


def auto_install(module_name: str) -> bool:
    if module_name in _INSTALLED_IN_SESSION:
        return True
    pip_name = _PIP_PACKAGE_MAP.get(module_name, module_name)
    if pip_name is None:
        return False
    try:
        logger.info(f"CapabilityLoop: 自动安装 {pip_name}")
        result = subprocess.run(
            ["pip", "install", pip_name, "--quiet"],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
        )
        if result.returncode == 0:
            _INSTALLED_IN_SESSION.add(module_name)
            logger.info(f"CapabilityLoop: {pip_name} 安装成功")
            return True
        logger.warning(f"CapabilityLoop: {pip_name} 安装失败: {result.stderr[:200]}")
        return False
    except Exception as e:
        logger.warning(f"CapabilityLoop: {pip_name} 安装异常: {e}")
        return False


def execute_python_code(code: str, timeout: int = _EXECUTION_TIMEOUT) -> Tuple[bool, str, str]:
    try:
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
        )
        output = result.stdout.strip() if result.stdout else ""
        error = result.stderr.strip() if result.stderr else ""
        return result.returncode == 0, output, error
    except subprocess.TimeoutExpired:
        return False, "", f"执行超时({timeout}s)"
    except Exception as e:
        return False, "", str(e)


def validate_output(output: str, expected_type: str = "") -> bool:
    if not output or len(output.strip()) < 2:
        return False
    if expected_type == "gps":
        return bool(re.search(r'\d+\.\d+.*[°]?\s*[NS]', output)) or bool(re.search(r'经度|纬度|latitude|longitude', output, re.IGNORECASE))
    if expected_type == "map":
        return "html" in output.lower() or "folium" in output.lower() or "map" in output.lower()
    if expected_type == "serial":
        return bool(re.search(r'COM\d+|serial|串口|数据', output, re.IGNORECASE))
    return True


def diagnose_and_fix(error: str, output: str, code: str, attempt: int) -> Optional[str]:
    missing = extract_missing_module(error)
    if missing:
        if auto_install(missing):
            return code

    if "Permission" in error or "拒绝" in error:
        port_match = re.search(r'COM(\d+)', code)
        if port_match and attempt < 2:
            new_port = f"COM{int(port_match.group(1)) + 1}"
            code = code.replace(f"COM{port_match.group(1)}", new_port)
            logger.info(f"CapabilityLoop: 端口被占用，尝试 {new_port}")
            return code

    if "not found" in error or "找不到" in error:
        port_matches = re.findall(r'COM\d+', error)
        if port_matches and attempt < 2:
            for pm in port_matches:
                code = code.replace(pm, "COM_AUTO")
            return code

    if "timeout" in error.lower() or "超时" in error:
        timeout_match = re.search(r'timeout\s*=\s*(\d+)', code)
        if timeout_match:
            old_t = int(timeout_match.group(1))
            new_t = min(old_t * 2, 30)
            code = code.replace(f"timeout={old_t}", f"timeout={new_t}")
            logger.info(f"CapabilityLoop: 超时，增加timeout {old_t}→{new_t}")
            return code

    return None


async def execute_with_retry(goal: str, expected_type: str = "",
                              context: dict = None,
                              generate_code_fn=None,
                              regenerate_code_fn=None,
                              fallback_code_fn=None,
                              record_fn=None) -> ExecutionResult:
    import time
    start = time.time()
    context = context or {}

    code = None
    if generate_code_fn:
        code = await generate_code_fn(goal, context)
    if not code and fallback_code_fn:
        code = fallback_code_fn(goal)
    if not code:
        return ExecutionResult(
            success=False, error="无法生成执行代码",
            attempts=1, duration_ms=(time.time() - start) * 1000,
        )

    code_history = [code]
    auto_installed = []

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        logger.info(f"CapabilityLoop: 第{attempt}次执行 (目标: {goal[:50]})")

        if is_dangerous(code):
            return ExecutionResult(
                success=False, error="代码包含危险操作，拒绝执行",
                attempts=attempt, code_history=code_history,
                duration_ms=(time.time() - start) * 1000,
            )

        success, output, error = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                None, lambda: execute_python_code(code, _EXECUTION_TIMEOUT)
            ),
            timeout=_EXECUTION_TIMEOUT + 5,
        )

        if success and validate_output(output, expected_type):
            if record_fn:
                record_fn(goal, True, output, attempt, code)
            return ExecutionResult(
                success=True, output=output, attempts=attempt,
                code_history=code_history, auto_installed=auto_installed,
                duration_ms=(time.time() - start) * 1000,
            )

        logger.warning(f"CapabilityLoop: 第{attempt}次失败 - error={error[:100]}, output={output[:100]}")

        missing = extract_missing_module(error)
        if missing and missing not in auto_installed:
            if auto_install(missing):
                auto_installed.append(missing)
                code_history.append(code)
                continue

        fixed_code = diagnose_and_fix(error, output, code, attempt)
        if fixed_code:
            code = fixed_code
            code_history.append(code)
        else:
            new_code = None
            if regenerate_code_fn:
                new_code = await regenerate_code_fn(goal, error, output, attempt, context)
            if new_code:
                code = new_code
                code_history.append(code)
            else:
                if record_fn:
                    record_fn(goal, False, error, attempt, code)
                return ExecutionResult(
                    success=False, error=f"自主执行{attempt}次后仍失败: {error[:200]}",
                    output=output, attempts=attempt, code_history=code_history,
                    auto_installed=auto_installed,
                    duration_ms=(time.time() - start) * 1000,
                )

    if record_fn:
        record_fn(goal, False, "达到最大重试次数", _MAX_ATTEMPTS, code)
    return ExecutionResult(
        success=False, error=f"自主执行{_MAX_ATTEMPTS}次后仍失败",
        attempts=_MAX_ATTEMPTS, code_history=code_history,
        auto_installed=auto_installed,
        duration_ms=(time.time() - start) * 1000,
    )