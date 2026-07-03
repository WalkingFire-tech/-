"""
代码执行器 - 安全沙箱实现
使用多层防护：RestrictedPython + Docker + 资源限制
"""
import subprocess
import tempfile
import os
import re
import json
from loguru import logger
from typing import Dict, Any

MAX_CODE_LENGTH = 10000
EXECUTION_TIMEOUT = 10
MEMORY_LIMIT_MB = 256
CPU_QUOTA = 50000

ALLOWED_BUILTINS = {
    'abs', 'all', 'any', 'bin', 'bool', 'chr', 'complex',
    'dict', 'divmod', 'enumerate', 'filter', 'float', 'format',
    'frozenset', 'hex', 'int', 'isinstance', 'issubclass',
    'iter', 'len', 'list', 'map', 'max', 'min', 'next',
    'oct', 'ord', 'pow', 'print', 'range', 'repr', 'reversed',
    'round', 'set', 'slice', 'sorted', 'str', 'sum', 'tuple',
    'type', 'zip'
}

DANGEROUS_PATTERNS = [
    r'__import__',
    r'__builtins__',
    r'__globals__',
    r'__locals__',
    r'__code__',
    r'__dict__',
    r'getattr\s*\(',
    r'setattr\s*\(',
    r'delattr\s*\(',
    r'eval\s*\(',
    r'exec\s*\(',
    r'compile\s*\(',
    r'open\s*\(',
    r'input\s*\(',
    r'breakpoint\s*\(',
    r'os\.',
    r'subprocess\.',
    r'sys\.',
    r'shutil\.',
    r'socket\.',
    r'pickle\.',
    r'marshal\.',
]


class CodeExecutor:
    """安全的代码执行器"""
    
    @staticmethod
    def _validate_code(code: str) -> Dict[str, Any]:
        """验证代码安全性"""
        if len(code) > MAX_CODE_LENGTH:
            return {"valid": False, "error": f"代码过长（最大{MAX_CODE_LENGTH}字符）"}
        
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return {"valid": False, "error": f"检测到危险模式: {pattern}"}
        
        return {"valid": True}
    
    @staticmethod
    def _execute_with_docker(code: str, timeout: int) -> Dict[str, Any]:
        """使用Docker容器执行（最安全）"""
        try:
            import docker
            client = docker.from_env(timeout=timeout)
            
            container = client.containers.run(
                'python:3.10-slim',
                command=['python', '-c', code],
                mem_limit=f'{MEMORY_LIMIT_MB}m',
                cpu_quota=CPU_QUOTA,
                network_disabled=True,
                read_only=True,
                remove=True,
                detach=False,
                stdout=True,
                stderr=True
            )
            
            return {
                "success": True,
                "output": container.decode('utf-8'),
                "error": "",
                "method": "docker"
            }
        
        except ImportError:
            return {"success": False, "error": "Docker不可用", "method": "docker"}
        except Exception as e:
            return {"success": False, "error": f"Docker执行失败: {str(e)}", "method": "docker"}
    
    @staticmethod
    def _execute_with_restricted(code: str, timeout: int) -> Dict[str, Any]:
        """使用RestrictedPython执行"""
        try:
            from RestrictedPython import compile_restricted
            from RestrictedPython.Guards import (
                guarded_iter_unpack_sequence,
                guarded_unpack_sequence,
                safe_builtins
            )
            
            safe_globals = {
                '__builtins__': {
                    **{k: __builtins__[k] for k in ALLOWED_BUILTINS if k in __builtins__},
                    '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
                    '_unpack_sequence_': guarded_unpack_sequence,
                }
            }
            
            compiled = compile_restricted(code, '<sandbox>', 'exec')
            
            import io
            import threading
            output_buffer = io.StringIO()
            _timed_out = [False]
            
            def _timeout_handler():
                _timed_out[0] = True
                import os
                os._exit(2)
            
            safe_globals_with_output = dict(safe_globals)
            safe_globals_with_output['print'] = lambda *args, **kwargs: print(*args, file=output_buffer, **kwargs)
            
            timer = threading.Timer(timeout, _timeout_handler)
            timer.daemon = True
            
            try:
                timer.start()
                exec(compiled, safe_globals_with_output)
                timer.cancel()
                if _timed_out[0]:
                    return {"success": False, "error": f"执行超时（{timeout}秒）", "method": "restricted"}
                output = output_buffer.getvalue()
                return {"success": True, "output": output, "error": "", "method": "restricted"}
            finally:
                timer.cancel()
        
        except ImportError:
            return {"success": False, "error": "RestrictedPython不可用", "method": "restricted"}
        except TimeoutError:
            return {"success": False, "error": f"执行超时（{timeout}秒）", "method": "restricted"}
        except Exception as e:
            return {"success": False, "error": f"执行失败: {str(e)}", "method": "restricted"}
    
    @staticmethod
    def _execute_with_subprocess(code: str, timeout: int) -> Dict[str, Any]:
        """使用子进程执行（受限环境）"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            tmp = f.name
        
        try:
            result = subprocess.run(
                ['python', tmp],
                capture_output=True,
                text=True,
                timeout=timeout,
                env={'PYTHONDONTWRITEBYTECODE': '1'}
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "method": "subprocess"
            }
        
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": f"执行超时（{timeout}秒）", "method": "subprocess"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e), "method": "subprocess"}
        finally:
            try:
                os.unlink(tmp)
            except:
                pass
    
    @staticmethod
    def execute(code: str, timeout: int = EXECUTION_TIMEOUT, method: str = "auto") -> dict:
        """安全执行代码
        
        Args:
            code: Python代码
            timeout: 超时时间（秒）
            method: 执行方法（auto/docker/restricted/subprocess/disabled）
        
        Returns:
            执行结果字典
        """
        validation = CodeExecutor._validate_code(code)
        if not validation["valid"]:
            return {"success": False, "output": "", "error": validation["error"]}
        
        if method == "disabled":
            return {
                "success": False,
                "output": "",
                "error": "代码执行功能已禁用（安全原因）",
                "method": "disabled"
            }
        
        if method == "docker":
            return CodeExecutor._execute_with_docker(code, timeout)
        
        if method == "restricted":
            return CodeExecutor._execute_with_restricted(code, timeout)
        
        if method == "subprocess":
            return CodeExecutor._execute_with_subprocess(code, timeout)
        
        if method == "auto":
            result = CodeExecutor._execute_with_docker(code, timeout)
            if result["success"] or "不可用" not in result.get("error", ""):
                return result
            
            result = CodeExecutor._execute_with_restricted(code, timeout)
            if result["success"] or "不可用" not in result.get("error", ""):
                return result
            
            logger.warning("Docker和RestrictedPython均不可用，使用受限子进程")
            return CodeExecutor._execute_with_subprocess(code, timeout)
        
        return {"success": False, "output": "", "error": f"未知执行方法: {method}"}
    
    @staticmethod
    def is_available() -> Dict[str, bool]:
        """检查可用的执行方法"""
        available = {
            "docker": False,
            "restricted": False,
            "subprocess": True
        }
        
        try:
            import docker
            available["docker"] = True
        except ImportError:
            pass
        
        try:
            from RestrictedPython import compile_restricted
            available["restricted"] = True
        except ImportError:
            pass
        
        return available
