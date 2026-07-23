from typing import Dict

from loguru import logger

from core.capability_creation.execution_engine import execute_python_code


def _run_code_and_return(code: str, label: str = "") -> Dict:
    success, output, error = execute_python_code(code, timeout=30)
    if success and output and len(output.strip()) > 2:
        return {"success": True, "data": output[:2000]}
    logger.warning(f"CapabilityLoop[{label}]: 代码执行失败 - {error[:100]}")
    return {"success": False, "data": output[:500] if output else "", "error": error[:200]}


async def solve_auto_repair(query: str) -> Dict:
    goal_lower = query.lower()

    if any(kw in goal_lower for kw in ["服务", "service", "启动", "start"]):
        code = '''import subprocess
import sys
import time

def manage_service(action, name):
    try:
        if action == "start":
            subprocess.run(['sc', 'start', name], capture_output=True, text=True, timeout=10)
        elif action == "stop":
            subprocess.run(['sc', 'stop', name], capture_output=True, text=True, timeout=10)
        time.sleep(2)
        status = subprocess.run(['sc', 'query', name], capture_output=True, text=True, timeout=5)
        running = "RUNNING" in status.stdout
        return {"service": name, "action": action, "success": running}
    except Exception as e:
        return {"service": name, "action": action, "error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        print(manage_service(sys.argv[1], sys.argv[2]))
    else:
        print("用法: script.py start/stop 服务名")
'''
        return _run_code_and_return(code, "auto_repair/service")

    elif any(kw in goal_lower for kw in ["清理", "clean", "temp", "临时", "cache"]):
        code = '''import os

temp_dirs = []
if os.name == 'nt':
    temp_dirs.append(os.environ.get('TEMP', ''))
    temp_dirs.append(os.environ.get('TMP', ''))
    temp_dirs.append(os.path.join(os.environ.get('SystemDrive', 'C:'), 'Windows', 'Temp'))

cleaned = 0
errors = 0
for temp_dir in [d for d in temp_dirs if d and os.path.exists(d)]:
    for root, dirs, files in os.walk(temp_dir):
        for f in files:
            try:
                os.remove(os.path.join(root, f))
                cleaned += 1
            except Exception:
                errors += 1

print(f"清理完成: 删除{cleaned}个文件, {errors}个失败")
'''
        return _run_code_and_return(code, "auto_repair/clean")

    elif any(kw in goal_lower for kw in ["注册表", "registry", "reg"]):
        code = '''import subprocess
import json

malware_paths = [
    "HKLM\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run",
    "HKCU\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run",
]
checks = []
for path in malware_paths:
    try:
        result = subprocess.run(['reg', 'query', path], capture_output=True, text=True, timeout=5)
        checks.append({"path": path, "exists": result.returncode == 0})
    except Exception:
        checks.append({"path": path, "exists": False})

print(json.dumps({"registry_health": checks}, indent=2, ensure_ascii=False))
'''
        return _run_code_and_return(code, "auto_repair/registry")

    else:
        code = '''import subprocess
import json
from datetime import datetime

health = {}
try:
    r = subprocess.run(['tasklist'], capture_output=True, text=True, timeout=5)
    health['process_count'] = len(r.stdout.split('\\n')) - 1
except Exception:
    health['process_count'] = -1

try:
    r = subprocess.run(['wmic', 'OS', 'get', 'FreePhysicalMemory', '/format:list'],
                       capture_output=True, text=True, timeout=5)
    for line in r.stdout.strip().split('\\n'):
        if '=' in line:
            k, v = line.split('=', 1)
            if k.strip() == 'FreePhysicalMemory' and v.strip():
                health['free_memory_kb'] = int(v.strip())
except Exception:
    health['free_memory_kb'] = -1

health['timestamp'] = datetime.now().isoformat()
print(json.dumps(health, indent=2, ensure_ascii=False))
'''
        return _run_code_and_return(code, "auto_repair/health")