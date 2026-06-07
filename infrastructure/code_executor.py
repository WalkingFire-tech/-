import subprocess
import tempfile
import os
import re
from loguru import logger

class CodeExecutor:
    @staticmethod
    def execute(code: str, timeout: int = 10) -> dict:
        # 禁止危险模块
        dangerous = ['os', 'subprocess', 'shutil', 'sys', '__import__', 'eval', 'exec', 'compile']
        for mod in dangerous:
            if re.search(rf'\b{mod}\b', code):
                return {"success": False, "output": "", "error": f"禁止使用模块: {mod}"}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            tmp = f.name
        try:
            result = subprocess.run(['python', tmp], capture_output=True, text=True, timeout=timeout, env={})
            return {"success": result.returncode == 0, "output": result.stdout, "error": result.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": f"超时({timeout}s)"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}
        finally:
            os.unlink(tmp)
