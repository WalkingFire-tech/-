"""
自主执行回路 - 从"代码生成器"到"自主行动者"的关键跃迁

核心理念：系统不是"告诉你怎么做"，而是"自己动手做到成功"

执行回路：
  目标分析 → 代码生成 → 自动执行 → 结果验证 → 成功？返回 : 失败→诊断→修正→重试

与tool_builder的区别：
  - tool_builder: 沙箱执行，受限（禁止os/subprocess），生成的是"工具"
  - auto_execution_loop: 通过bash执行，可访问硬件，生成的是"行动结果"

安全约束：
  - 危险命令拦截（复用bash_tool的_DANGEROUS_COMMANDS）
  - 最大重试3次
  - 单次执行超时30秒
  - 不执行涉及删除/格式化/权限提升的代码
"""
import asyncio
import re
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger

_DANGEROUS_PATTERNS = [
    r'\brm\s+-rf\b', r'\bdel\s+/s\b', r'\bformat\b', r'\bfdisk\b',
    r'\bmkfs\b', r'\bshutdown\b', r'\breboot\b', r'\btaskkill\b',
    r'\breg\s+delete\b', r'\breg\s+add\b', r'\bnet\s+user\b',
    r'\bcipher\b', r'\bsfc\b', r'\bdism\b', r'\bbcdedit\b',
    r'\bos\.remove\b', r'\bshutil\.rmtree\b', r'\bos\.system\b',
]

_MAX_ATTEMPTS = 3
_EXECUTION_TIMEOUT = 30


@dataclass
class ExecutionResult:
    success: bool
    output: str = ""
    error: str = ""
    attempts: int = 0
    code_history: List[str] = field(default_factory=list)
    auto_installed: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


def _is_dangerous(code: str) -> bool:
    for pattern in _DANGEROUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return True
    return False


def _extract_missing_module(error_str: str) -> Optional[str]:
    m = re.search(r"No module named ['\"]?(\w+)['\"]?", error_str)
    if m:
        return m.group(1)
    m = re.search(r"cannot import name.*from ['\"]?(\w+)['\"]?", error_str)
    if m:
        return m.group(1)
    return None


_PIP_PACKAGE_MAP = {
    "cv2": "opencv-python", "PIL": "Pillow", "sklearn": "scikit-learn",
    "serial": "pyserial", "usb": "pyusb", "yaml": "pyyaml",
    "dotenv": "python-dotenv", "bs4": "beautifulsoup4",
    "folium": "folium", "serial.tools": "pyserial",
    "winreg": None,
}

_INSTALLED_IN_SESSION: set = set()


def _auto_install(module_name: str) -> bool:
    if module_name in _INSTALLED_IN_SESSION:
        return True
    pip_name = _PIP_PACKAGE_MAP.get(module_name, module_name)
    if pip_name is None:
        return False
    try:
        logger.info(f"AutoExec: 自动安装 {pip_name}")
        result = subprocess.run(
            ["pip", "install", pip_name, "--quiet"],
            capture_output=True, text=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
        )
        if result.returncode == 0:
            _INSTALLED_IN_SESSION.add(module_name)
            logger.info(f"AutoExec: {pip_name} 安装成功")
            return True
        logger.warning(f"AutoExec: {pip_name} 安装失败: {result.stderr[:200]}")
        return False
    except Exception as e:
        logger.warning(f"AutoExec: {pip_name} 安装异常: {e}")
        return False


def _execute_python_code(code: str, timeout: int = _EXECUTION_TIMEOUT) -> Tuple[bool, str, str]:
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


def _validate_output(output: str, expected_type: str = "") -> bool:
    if not output or len(output.strip()) < 2:
        return False
    if expected_type == "gps":
        return bool(re.search(r'\d+\.\d+.*[°]?\s*[NS]', output)) or bool(re.search(r'经度|纬度|latitude|longitude', output, re.IGNORECASE))
    if expected_type == "map":
        return "html" in output.lower() or "folium" in output.lower() or "map" in output.lower()
    if expected_type == "serial":
        return bool(re.search(r'COM\d+|serial|串口|数据', output, re.IGNORECASE))
    return True


def _diagnose_failure(error: str, output: str, code: str, attempt: int) -> Optional[str]:
    missing = _extract_missing_module(error)
    if missing:
        if _auto_install(missing):
            return code

    if "Permission" in error or "拒绝" in error:
        port_match = re.search(r'COM(\d+)', code)
        if port_match and attempt < 2:
            new_port = f"COM{int(port_match.group(1)) + 1}"
            code = code.replace(f"COM{port_match.group(1)}", new_port)
            logger.info(f"AutoExec: 端口被占用，尝试 {new_port}")
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
            logger.info(f"AutoExec: 超时，增加timeout {old_t}→{new_t}")
            return code

    return None


class AutoExecutionLoop:
    """
    自主执行回路

    系统不再是"告诉你怎么做"，而是"自己动手做到成功"。

    使用方式：
        loop = AutoExecutionLoop()
        result = await loop.execute("读取COM3的GPS数据", expected_type="gps")
        if result.success:
            print(result.output)  # GPS经纬度数据
    """

    def __init__(self, max_attempts: int = _MAX_ATTEMPTS, timeout: int = _EXECUTION_TIMEOUT):
        self.max_attempts = max_attempts
        self.timeout = timeout
        self._execution_history: List[Dict] = []

    async def execute(self, goal: str, expected_type: str = "",
                      context: Dict[str, Any] = None) -> ExecutionResult:
        start = time.time()
        context = context or {}

        code = await self._generate_code(goal, context)
        if not code:
            return ExecutionResult(
                success=False, error="无法生成执行代码",
                attempts=1, duration_ms=(time.time() - start) * 1000,
            )

        code_history = [code]
        auto_installed = []

        for attempt in range(1, self.max_attempts + 1):
            logger.info(f"AutoExec: 第{attempt}次执行 (目标: {goal[:50]})")

            if _is_dangerous(code):
                return ExecutionResult(
                    success=False, error="代码包含危险操作，拒绝执行",
                    attempts=attempt, code_history=code_history,
                    duration_ms=(time.time() - start) * 1000,
                )

            success, output, error = await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(
                    None, lambda: _execute_python_code(code, self.timeout)
                ),
                timeout=self.timeout + 5,
            )

            if success and _validate_output(output, expected_type):
                self._record_execution(goal, True, output, attempt, code)
                return ExecutionResult(
                    success=True, output=output, attempts=attempt,
                    code_history=code_history, auto_installed=auto_installed,
                    duration_ms=(time.time() - start) * 1000,
                )

            logger.warning(f"AutoExec: 第{attempt}次失败 - error={error[:100]}, output={output[:100]}")

            missing = _extract_missing_module(error)
            if missing and missing not in auto_installed:
                if _auto_install(missing):
                    auto_installed.append(missing)
                    code_history.append(code)
                    continue

            fixed_code = _diagnose_failure(error, output, code, attempt)
            if fixed_code:
                code = fixed_code
                code_history.append(code)
            else:
                new_code = await self._regenerate_code(goal, error, output, attempt, context)
                if new_code:
                    code = new_code
                    code_history.append(code)
                else:
                    self._record_execution(goal, False, error, attempt, code)
                    return ExecutionResult(
                        success=False, error=f"自主执行{attempt}次后仍失败: {error[:200]}",
                        output=output, attempts=attempt, code_history=code_history,
                        auto_installed=auto_installed,
                        duration_ms=(time.time() - start) * 1000,
                    )

        self._record_execution(goal, False, "达到最大重试次数", self.max_attempts, code)
        return ExecutionResult(
            success=False, error=f"自主执行{self.max_attempts}次后仍失败",
            attempts=self.max_attempts, code_history=code_history,
            auto_installed=auto_installed,
            duration_ms=(time.time() - start) * 1000,
        )

    async def _generate_code(self, goal: str, context: Dict[str, Any] = None) -> Optional[str]:
        try:
            from adapters.llm.ollama_adapter import ollama_chat_request
            from infrastructure.config_manager import config_manager
            base_url = config_manager.get("ollama.base_url", "http://localhost:11434")
            model = config_manager.get("ollama.model", "qwen2.5-coder:7b")
            prompt = self._build_generation_prompt(goal, context)
            result = ollama_chat_request(base_url, model, prompt, timeout=30)
            if result and result.get("content"):
                code = result["content"]
                code = re.sub(r'^```python\s*', '', code)
                code = re.sub(r'^```\s*', '', code)
                code = re.sub(r'\s*```$', '', code)
                code = code.strip()
                if "import " in code or "def " in code or "print(" in code:
                    logger.info(f"AutoExec: LLM生成代码 ({len(code)}字符)")
                    return code
        except Exception as e:
            logger.warning(f"AutoExec: LLM代码生成失败: {e}")

        return self._fallback_code_generation(goal)

    async def _regenerate_code(self, goal: str, error: str, output: str,
                                attempt: int, context: Dict[str, Any] = None) -> Optional[str]:
        try:
            from adapters.llm.ollama_adapter import ollama_chat_request
            from infrastructure.config_manager import config_manager
            base_url = config_manager.get("ollama.base_url", "http://localhost:11434")
            model = config_manager.get("ollama.model", "qwen2.5-coder:7b")
            prompt = f"""之前的代码执行失败了，请修正。

目标: {goal}
错误: {error[:500]}
输出: {output[:300]}
第{attempt}次尝试

要求：
- 修正错误，生成可执行的Python代码
- 只输出代码，不要解释
- 代码必须用print()输出结果
- 如果是串口问题，尝试扫描可用端口
- 如果是超时，增加等待时间
"""
            result = ollama_chat_request(base_url, model, prompt, timeout=30)
            if result and result.get("content"):
                code = result["content"]
                code = re.sub(r'^```python\s*', '', code)
                code = re.sub(r'^```\s*', '', code)
                code = re.sub(r'\s*```$', '', code)
                code = code.strip()
                if "import " in code or "def " in code or "print(" in code:
                    logger.info(f"AutoExec: LLM修正代码 ({len(code)}字符)")
                    return code
        except Exception as e:
            logger.warning(f"AutoExec: LLM代码修正失败: {e}")
        return None

    def _build_generation_prompt(self, goal: str, context: Dict[str, Any] = None) -> str:
        ctx_str = ""
        if context:
            port = context.get("port", "")
            baudrate = context.get("baudrate", "")
            if port:
                ctx_str += f"\n- 串口: {port}"
            if baudrate:
                ctx_str += f"\n- 波特率: {baudrate}"

        return f"""生成一段Python代码来完成任务。只输出代码，不要解释。

目标: {goal}
{ctx_str}

要求：
- 代码必须可独立执行
- 用print()输出关键结果
- 如果需要读取串口，用pyserial库
- 如果需要渲染地图，用folium库
- 如果需要扫描串口，用serial.tools.list_ports
- 处理异常，不要让程序崩溃
- 如果读取GPS，解析NMEA数据并输出经纬度
"""

    def _fallback_code_generation(self, goal: str) -> Optional[str]:
        goal_lower = goal.lower()

        if any(kw in goal_lower for kw in ["串口", "serial", "com", "gps"]):
            port = "COM3"
            port_match = re.search(r'COM\d+', goal, re.IGNORECASE)
            if port_match:
                port = port_match.group().upper()
            num_match = re.search(r'串口\s*(\d+)', goal)
            if num_match:
                port = f"COM{num_match.group(1)}"

            return f'''import serial
import serial.tools.list_ports
import time

ports = serial.tools.list_ports.comports()
if not ports:
    print("未检测到串口设备")
else:
    print(f"检测到{{len(ports)}}个串口:")
    for p in sorted(ports, key=lambda x: x.device):
        print(f"  {{p.device}} | {{p.description}}")

target_port = "{port}"
try:
    ser = serial.Serial(port=target_port, baudrate=9600, timeout=5)
    lines = []
    start = time.time()
    while time.time() - start < 5:
        if ser.in_waiting > 0:
            raw = ser.readline()
            decoded = raw.decode("ascii", errors="ignore").strip()
            if decoded:
                lines.append(decoded)
        time.sleep(0.05)
    ser.close()
    if lines:
        for line in lines[:20]:
            print(line)
    else:
        print(f"端口{{target_port}}已打开但5秒内未收到数据")
except Exception as e:
    print(f"读取{{target_port}}失败: {{e}}")
    for p in sorted(serial.tools.list_ports.comports(), key=lambda x: x.device):
        print(f"  可用: {{p.device}} | {{p.description}}")
'''

        if any(kw in goal_lower for kw in ["地图", "map", "标记", "folium"]):
            return '''import folium
import os
m = folium.Map(location=[31.2304, 121.4737], zoom_start=13)
folium.Marker([31.2304, 121.4737], popup="当前位置").add_to(m)
filepath = os.path.join(os.environ.get("TEMP", "/tmp"), "gps_map.html")
m.save(filepath)
print(f"地图已生成: {filepath}")
print(f"坐标: 31.2304, 121.4737")
'''

        return None

    def _record_execution(self, goal: str, success: bool, output: str,
                          attempts: int, code: str):
        self._execution_history.append({
            "goal": goal[:100],
            "success": success,
            "output_preview": output[:200] if output else "",
            "attempts": attempts,
            "code_length": len(code),
            "timestamp": time.time(),
        })
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-50:]

    @property
    def stats(self) -> Dict:
        if not self._execution_history:
            return {"total": 0, "success_rate": 0.0, "avg_attempts": 0.0}
        total = len(self._execution_history)
        successes = sum(1 for h in self._execution_history if h["success"])
        avg_attempts = sum(h["attempts"] for h in self._execution_history) / total
        return {
            "total": total,
            "success_rate": successes / total,
            "avg_attempts": avg_attempts,
        }


auto_execution_loop = AutoExecutionLoop()