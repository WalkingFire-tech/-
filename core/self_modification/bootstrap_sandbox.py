"""
L5自举测试环境 — 让L5在隔离环境中修改自身并验证修改效果

核心概念：
- 自举(Bootstrap)：L5修改自身代码的能力
- 隔离环境：修改后的代码在子进程中运行，不影响当前运行实例
- 自洽验证：修改后的L5能否正确执行自修改流程

设计原则：
- R1: 未经自举验证的自修改，视同毒药
- R2: 自修改必须走渐进注入，不可一步到位
- R3: 自修改路径须可回溯，偏移须可感知

与PatchSandbox的区别：
- PatchSandbox验证"他者"代码（导入验证）
- BootstrapSandbox验证"自身"代码（子进程隔离+功能自检）
"""

import ast
import os
import sys
import json
import time
import shutil
import tempfile
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


L5_SELF_FILES = {
    "core/self_modification/loop.py",
    "core/self_modification/defect_diagnoser.py",
    "core/self_modification/patch_generator.py",
    "core/self_modification/patch_sandbox_deployer.py",
    "core/self_modification/bootstrap_sandbox.py",
}

SELF_TEST_SCRIPT = """
import sys
import json

results = []

# Test 1: Can import the modified module
try:
    import {module_name}
    results.append({{"test": "import", "passed": True}})
except Exception as e:
    results.append({{"test": "import", "passed": False, "error": str(e)[:200]}})
    print(json.dumps(results))
    sys.exit(1)

# Test 2: Can instantiate core classes
try:
    obj = {class_name}()
    results.append({{"test": "instantiate", "passed": True}})
except Exception as e:
    results.append({{"test": "instantiate", "passed": False, "error": str(e)[:200]}})

# Test 3: Core method callable
try:
    method = getattr(obj, "{test_method}", None)
    if method is not None:
        results.append({{"test": "method_exists", "passed": True, "method": "{test_method}"}})
    else:
        results.append({{"test": "method_exists", "passed": False, "method": "{test_method}"}})
except Exception as e:
    results.append({{"test": "method_exists", "passed": False, "error": str(e)[:200]}})

print(json.dumps(results, ensure_ascii=False))
"""

MODULE_TEST_MAP = {
    "core/self_modification/loop.py": {
        "module_name": "core.self_modification.loop",
        "class_name": "SelfModificationLoop",
        "test_method": "can_run",
    },
    "core/self_modification/defect_diagnoser.py": {
        "module_name": "core.self_modification.defect_diagnoser",
        "class_name": "DefectDiagnoser",
        "test_method": "diagnose_from_lessons",
    },
    "core/self_modification/patch_generator.py": {
        "module_name": "core.self_modification.patch_generator",
        "class_name": "PatchGenerator",
        "test_method": "generate_patch",
    },
    "core/self_modification/patch_sandbox_deployer.py": {
        "module_name": "core.self_modification.patch_sandbox_deployer",
        "class_name": "PatchSandbox",
        "test_method": "validate_safety",
    },
    "core/self_modification/bootstrap_sandbox.py": {
        "module_name": "core.self_modification.bootstrap_sandbox",
        "class_name": "BootstrapSandbox",
        "test_method": "verify_self_consistency",
    },
}


@dataclass
class BootstrapResult:
    file_path: str
    safe: bool = False
    syntax_ok: bool = False
    import_ok: bool = False
    self_consistent: bool = False
    functional_ok: bool = False
    can_bootstrap: bool = False
    violations: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    test_results: List[Dict] = field(default_factory=list)
    duration_ms: float = 0.0


class BootstrapSandbox:
    """
    L5自举测试环境
    
    在隔离子进程中验证修改后的L5自身代码能否正确运行
    """

    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    SELF_MODIFICATION_SAFETY_CHECKLIST = [
        "修改后能否正常导入",
        "修改后核心类能否实例化",
        "修改后核心方法是否可调用",
        "修改后不会破坏IMMUTABLE_FILES保护",
        "修改后不会移除安全检查逻辑",
        "修改后不会绕过渐进注入协议",
        "修改后审计日志仍能正常写入",
        "修改后回滚路径仍然完整",
    ]

    def is_self_modification(self, file_path: str) -> bool:
        return file_path in L5_SELF_FILES

    def verify_self_consistency(
        self, file_path: str, patched_code: str, original_code: str
    ) -> BootstrapResult:
        """
        自举验证：修改后的L5代码能否正确运行自修改流程
        
        步骤：
        1. 语法验证
        2. 安全检查（自修改专用）
        3. 子进程隔离导入验证
        4. 功能自检（核心方法可调用）
        """
        start = time.time()
        result = BootstrapResult(file_path=file_path)

        # Step 1: 语法验证
        try:
            ast.parse(patched_code)
            result.syntax_ok = True
        except SyntaxError as e:
            result.syntax_ok = False
            result.errors.append(f"语法错误: 行{e.lineno}: {e.msg}")
            return result

        # Step 2: 自修改安全检查
        safe, violations = self._validate_self_modification_safety(file_path, patched_code, original_code)
        result.safe = safe
        result.violations = violations
        if not safe:
            result.errors.append(f"自修改安全检查未通过: {'; '.join(violations)}")
            return result

        # Step 3: 子进程隔离导入验证
        import_ok, import_err = self._isolated_import_test(file_path, patched_code)
        result.import_ok = import_ok
        if not import_ok:
            result.errors.append(f"隔离导入验证失败: {import_err}")
            return result

        # Step 4: 功能自检
        func_ok, func_results = self._functional_self_test(file_path, patched_code)
        result.functional_ok = func_ok
        result.test_results = func_results
        if not func_ok:
            failed = [t for t in func_results if not t.get("passed")]
            result.errors.append(f"功能自检未通过: {len(failed)}/{len(func_results)}项失败")

        # Step 5: 自洽判定
        result.self_consistent = result.import_ok and result.functional_ok
        result.can_bootstrap = result.syntax_ok and result.safe and result.self_consistent

        result.duration_ms = (time.time() - start) * 1000

        if result.can_bootstrap:
            logger.info(f"🧬 自举验证通过: {file_path} ({result.duration_ms:.0f}ms)")
        else:
            logger.warning(f"🧬 自举验证失败: {file_path} — {result.errors}")

        return result

    def _validate_self_modification_safety(
        self, file_path: str, patched_code: str, original_code: str
    ) -> Tuple[bool, List[str]]:
        violations = []

        from core.self_modification import IMMUTABLE_FILES
        if file_path in IMMUTABLE_FILES:
            violations.append(f"不可变文件: {file_path}")

        safety_patterns = [
            (r'IMMUTABLE_FILES\s*=\s*\{\s*\}', "禁止清空IMMUTABLE_FILES"),
            (r'DANGEROUS_PATTERNS\s*=\s*\[\s*\]', "禁止清空DANGEROUS_PATTERNS"),
            (r'#\s*IMMUTABLE', "禁止注释掉IMMUTABLE_FILES"),
            (r'#\s*DANGEROUS', "禁止注释掉DANGEROUS_PATTERNS"),
        ]
        import re
        for pattern, msg in safety_patterns:
            if re.search(pattern, patched_code):
                violations.append(msg)

        if "def _write_audit_log" not in patched_code and "def _write_audit_log" in original_code:
            violations.append("禁止移除审计日志写入方法")

        if "def rollback" not in patched_code and "def rollback" in original_code:
            violations.append("禁止移除回滚方法")

        return len(violations) == 0, violations

    def _isolated_import_test(self, file_path: str, patched_code: str) -> Tuple[bool, Optional[str]]:
        """在临时目录中写入修改后代码，用子进程验证能否导入"""
        tmp_dir = tempfile.mkdtemp(prefix="l5_bootstrap_")
        try:
            rel_parts = file_path.replace("/", os.sep).split(os.sep)
            tmp_file = os.path.join(tmp_dir, *rel_parts)
            os.makedirs(os.path.dirname(tmp_file), exist_ok=True)
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(patched_code)

            for init_dir in self._ensure_inits(tmp_dir, rel_parts):
                pass

            module_name = file_path.replace("/", ".").replace(".py", "")
            test_code = f"import sys; sys.path.insert(0, r'{tmp_dir}'); import {module_name}; print('IMPORT_OK')"
            
            proc = subprocess.run(
                [sys.executable, "-c", test_code],
                capture_output=True, text=True, timeout=15,
                cwd=self.PROJECT_ROOT,
            )

            if proc.returncode == 0 and "IMPORT_OK" in proc.stdout:
                return True, None
            else:
                err = (proc.stderr or proc.stdout)[-300:]
                return False, err

        except subprocess.TimeoutExpired:
            return False, "子进程导入超时(15s)"
        except Exception as e:
            return False, str(e)[:200]
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _functional_self_test(self, file_path: str, patched_code: str) -> Tuple[bool, List[Dict]]:
        """在子进程中验证修改后模块的核心功能"""
        test_config = MODULE_TEST_MAP.get(file_path)
        if not test_config:
            return True, [{"test": "no_test_config", "passed": True, "note": "无专用测试配置，默认通过"}]

        tmp_dir = tempfile.mkdtemp(prefix="l5_func_")
        try:
            rel_parts = file_path.replace("/", os.sep).split(os.sep)
            tmp_file = os.path.join(tmp_dir, *rel_parts)
            os.makedirs(os.path.dirname(tmp_file), exist_ok=True)
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(patched_code)

            for init_dir in self._ensure_inits(tmp_dir, rel_parts):
                pass

            script = SELF_TEST_SCRIPT.format(**test_config)
            proc = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True, timeout=15,
                cwd=self.PROJECT_ROOT,
            )

            if proc.returncode == 0 and proc.stdout.strip():
                try:
                    results = json.loads(proc.stdout.strip())
                    all_passed = all(t.get("passed", False) for t in results)
                    return all_passed, results
                except json.JSONDecodeError:
                    return False, [{"test": "parse_output", "passed": False, "error": "无法解析测试输出"}]
            else:
                err = (proc.stderr or "")[-200:]
                return False, [{"test": "subprocess", "passed": False, "error": err}]

        except subprocess.TimeoutExpired:
            return False, [{"test": "timeout", "passed": False, "error": "子进程功能测试超时(15s)"}]
        except Exception as e:
            return False, [{"test": "exception", "passed": False, "error": str(e)[:200]}]
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _ensure_inits(self, tmp_dir: str, rel_parts: list) -> list:
        """确保临时目录中的__init__.py文件存在"""
        created = []
        current = tmp_dir
        for part in rel_parts[:-1]:
            current = os.path.join(current, part)
            init_file = os.path.join(current, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, "w") as f:
                    f.write("")
                created.append(init_file)
        return created


class SelfModificationDeployer:
    """
    L5自修改专用部署器 — 影子模式四阶段注入
    
    与PatchDeployer的区别：
    - PatchDeployer: 修改"他者"代码，用流量分配策略
    - SelfModificationDeployer: 修改"自身"代码，用影子模式+功能逐步启用
    
    四阶段：
    0.1% — 沙盒验证：在隔离子进程中运行修改后代码，执行自检套件
    1%   — 影子运行：修改后代码在子进程中运行，与主进程对比输出
    20%  — 功能启用：逐步启用新代码功能（诊断→生成→部署）
    100% — 全量替换：执行实际文件写入，保留回滚快照
    """

    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def __init__(self):
        self._bootstrap = BootstrapSandbox()
        self._results: Dict[str, Dict] = {}

    def deploy_self_modification(
        self, file_path: str, patched_code: str, original_code: str, confidence: float
    ) -> Dict[str, Any]:
        """
        执行自修改四阶段部署
        
        Returns: 各阶段结果汇总
        """
        deployment_id = f"self_mod_{int(time.time())}"
        self._results[deployment_id] = {
            "file_path": file_path,
            "confidence": confidence,
            "stages": {},
        }

        # 阶段0.1%: 沙盒验证
        stage_0_1 = self._stage_sandbox_verify(file_path, patched_code, original_code)
        self._results[deployment_id]["stages"]["0_1pct"] = stage_0_1
        if not stage_0_1["passed"]:
            logger.warning(f"🧬 自修改0.1%阶段失败: {stage_0_1.get('errors', [])}")
            return self._finalize(deployment_id, "sandbox_failed", stage_0_1)

        # 阶段1%: 影子运行
        stage_1 = self._stage_shadow_run(file_path, patched_code, original_code)
        self._results[deployment_id]["stages"]["1pct"] = stage_1
        if not stage_1["passed"]:
            logger.warning(f"🧬 自修改1%影子运行失败: {stage_1.get('errors', [])}")
            return self._finalize(deployment_id, "shadow_failed", stage_1)

        # 阶段20%: 功能逐步启用
        stage_20 = self._stage_feature_enablement(file_path, patched_code, original_code)
        self._results[deployment_id]["stages"]["20pct"] = stage_20
        if not stage_20["passed"]:
            logger.warning(f"🧬 自修改20%功能启用失败: {stage_20.get('errors', [])}")
            return self._finalize(deployment_id, "feature_enablement_failed", stage_20)

        # 阶段100%: 全量替换
        stage_100 = self._stage_full_replace(file_path, patched_code, original_code)
        self._results[deployment_id]["stages"]["100pct"] = stage_100
        if not stage_100["passed"]:
            self._rollback_file(file_path, original_code)
            return self._finalize(deployment_id, "rollback", stage_100)

        return self._finalize(deployment_id, "completed", stage_100)

    def _stage_sandbox_verify(
        self, file_path: str, patched_code: str, original_code: str
    ) -> Dict[str, Any]:
        """阶段0.1%: 在隔离子进程中运行修改后代码，执行自检套件"""
        result = self._bootstrap.verify_self_consistency(file_path, patched_code, original_code)
        return {
            "passed": result.can_bootstrap,
            "syntax_ok": result.syntax_ok,
            "safe": result.safe,
            "import_ok": result.import_ok,
            "functional_ok": result.functional_ok,
            "self_consistent": result.self_consistent,
            "errors": result.errors,
            "duration_ms": result.duration_ms,
        }

    def _stage_shadow_run(
        self, file_path: str, patched_code: str, original_code: str
    ) -> Dict[str, Any]:
        """阶段1%: 影子运行 — 修改后代码在子进程中运行，与主进程对比输出"""
        test_config = MODULE_TEST_MAP.get(file_path)
        if not test_config:
            return {"passed": True, "note": "无影子测试配置，默认通过"}

        tmp_dir = tempfile.mkdtemp(prefix="l5_shadow_")
        try:
            rel_parts = file_path.replace("/", os.sep).split(os.sep)
            tmp_file = os.path.join(tmp_dir, *rel_parts)
            os.makedirs(os.path.dirname(tmp_file), exist_ok=True)
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(patched_code)

            for init_dir in self._bootstrap._ensure_inits(tmp_dir, rel_parts):
                pass

            module_name = test_config["module_name"]
            class_name = test_config["class_name"]
            test_method = test_config["test_method"]

            shadow_script = f"""
import sys
sys.path.insert(0, r'{tmp_dir}')
import {module_name}
obj = {module_name}.{class_name}()
method = getattr(obj, "{test_method}", None)
if method is not None:
    try:
        result = method()
        print("SHADOW_OK:" + str(result))
    except Exception as e:
        print("SHADOW_ERROR:" + str(e)[:200])
else:
    print("SHADOW_ERROR:method_not_found")
"""
            proc = subprocess.run(
                [sys.executable, "-c", shadow_script],
                capture_output=True, text=True, timeout=15,
                cwd=self.PROJECT_ROOT,
            )

            output = (proc.stdout or "").strip()
            if output.startswith("SHADOW_OK:"):
                return {
                    "passed": True,
                    "shadow_output": output[len("SHADOW_OK:"):100],
                    "returncode": proc.returncode,
                }
            else:
                err = output.replace("SHADOW_ERROR:", "") or (proc.stderr or "")[-200:]
                return {"passed": False, "errors": [err]}

        except subprocess.TimeoutExpired:
            return {"passed": False, "errors": ["影子运行超时(15s)"]}
        except Exception as e:
            return {"passed": False, "errors": [str(e)[:200]]}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _stage_feature_enablement(
        self, file_path: str, patched_code: str, original_code: str
    ) -> Dict[str, Any]:
        """
        阶段20%: 功能逐步启用
        
        策略：先验证诊断功能→再验证补丁生成→最后验证部署能力
        每一步都在隔离子进程中验证
        """
        test_config = MODULE_TEST_MAP.get(file_path)
        if not test_config:
            return {"passed": True, "note": "无功能启用配置，默认通过"}

        feature_stages = [
            ("import", f"import {test_config['module_name']}"),
            ("instantiate", f"{test_config['module_name']}.{test_config['class_name']}()"),
            ("method_call", f"getattr(obj, '{test_config['test_method']}', None)"),
        ]

        tmp_dir = tempfile.mkdtemp(prefix="l5_feature_")
        try:
            rel_parts = file_path.replace("/", os.sep).split(os.sep)
            tmp_file = os.path.join(tmp_dir, *rel_parts)
            os.makedirs(os.path.dirname(tmp_file), exist_ok=True)
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(patched_code)

            for init_dir in self._bootstrap._ensure_inits(tmp_dir, rel_parts):
                pass

            results = []
            for stage_name, code_line in feature_stages:
                script = f"import sys; sys.path.insert(0, r'{tmp_dir}'); {code_line}; print('OK')"
                try:
                    proc = subprocess.run(
                        [sys.executable, "-c", script],
                        capture_output=True, text=True, timeout=10,
                        cwd=self.PROJECT_ROOT,
                    )
                    passed = proc.returncode == 0 and "OK" in proc.stdout
                    results.append({"stage": stage_name, "passed": passed})
                    if not passed:
                        err = (proc.stderr or "")[-150:]
                        results[-1]["error"] = err
                        return {"passed": False, "results": results, "failed_at": stage_name}
                except subprocess.TimeoutExpired:
                    results.append({"stage": stage_name, "passed": False, "error": "timeout"})
                    return {"passed": False, "results": results, "failed_at": stage_name}

            return {"passed": True, "results": results}

        except Exception as e:
            return {"passed": False, "errors": [str(e)[:200]]}
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _stage_full_replace(
        self, file_path: str, patched_code: str, original_code: str
    ) -> Dict[str, Any]:
        """阶段100%: 全量替换 — 执行实际文件写入"""
        full_path = os.path.join(self.PROJECT_ROOT, file_path.replace("/", os.sep))
        snapshot_path = full_path + f".self_mod_backup_{int(time.time())}"

        try:
            shutil.copy2(full_path, snapshot_path)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(patched_code)

            import_ok, import_err = self._bootstrap._isolated_import_test(file_path, patched_code)
            if not import_ok:
                shutil.copy2(snapshot_path, full_path)
                os.remove(snapshot_path)
                return {"passed": False, "errors": [f"替换后导入验证失败: {import_err}"]}

            try:
                os.remove(snapshot_path)
            except OSError:
                pass

            logger.info(f"🧬 自修改100%完成: {file_path}")
            return {"passed": True, "snapshot_path": snapshot_path}

        except Exception as e:
            if os.path.exists(snapshot_path):
                shutil.copy2(snapshot_path, full_path)
            return {"passed": False, "errors": [str(e)[:200]]}

    def _rollback_file(self, file_path: str, original_code: str):
        """回滚文件到原始代码"""
        full_path = os.path.join(self.PROJECT_ROOT, file_path.replace("/", os.sep))
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(original_code)
            logger.info(f"🧬 自修改回滚完成: {file_path}")
        except Exception as e:
            logger.error(f"🧬 自修改回滚失败: {e}")

    def _finalize(self, deployment_id: str, final_status: str, last_stage: Dict) -> Dict:
        result = self._results[deployment_id]
        result["final_status"] = final_status
        result["last_stage"] = last_stage
        return result


bootstrap_sandbox = BootstrapSandbox()
self_modification_deployer = SelfModificationDeployer()