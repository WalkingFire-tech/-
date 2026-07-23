import json
from typing import Dict

from loguru import logger

from core.capability_creation.execution_engine import execute_python_code


def _run_code_and_return(code: str, label: str = "") -> Dict:
    success, output, error = execute_python_code(code, timeout=30)
    if success and output and len(output.strip()) > 2:
        return {"success": True, "data": output[:2000]}
    logger.warning(f"CapabilityLoop[{label}]: 代码执行失败 - {error[:100]}")
    return {"success": False, "data": output[:500] if output else "", "error": error[:200]}


async def solve_system_diagnosis(query: str) -> Dict:
    code = '''import subprocess
import json
from datetime import datetime

def check_service_status():
    try:
        result = subprocess.run(['sc', 'query', 'type=service', 'state=', '/fo', 'csv', '/nh'],
                               capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\\n')
        if len(lines) < 2:
            return {"status": "no_data"}
        headers = [h.strip('"') for h in lines[0].split(',')]
        services = []
        for line in lines[1:]:
            parts = [p.strip('"') for p in line.split(',')]
            if len(parts) >= len(headers):
                services.append(dict(zip(headers, parts)))
        running = [s for s in services if s.get('STATE', '') == 'RUNNING']
        stopped = [s for s in services if s.get('STATE', '') == 'STOPPED']
        return {"total": len(services), "running": len(running), "stopped": len(stopped)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_disk_space():
    try:
        result = subprocess.run(['wmic', 'logicaldisk', 'get', 'size,freespace,caption', '/format:list'],
                               capture_output=True, text=True, timeout=5)
        disks = []
        current_disk = {}
        for line in result.stdout.split('\\n'):
            line = line.strip()
            if line and '=' in line:
                key, value = line.split('=', 1)
                if key.strip() and value.strip():
                    current_disk[key.strip()] = value.strip()
            elif current_disk and 'Caption' in current_disk:
                disks.append(current_disk)
                current_disk = {}
        if current_disk:
            disks.append(current_disk)
        disk_info = []
        for disk in disks:
            try:
                size_gb = float(disk.get('Size', '0')) / (1024**3)
                free_gb = float(disk.get('FreeSpace', '0')) / (1024**3)
                usage = ((size_gb - free_gb) / size_gb * 100) if size_gb > 0 else 0
                disk_info.append({"drive": disk.get('Caption', '?'), "size_gb": round(size_gb,2), "free_gb": round(free_gb,2), "usage_percent": round(usage,1)})
            except Exception:
                pass
        return disk_info
    except Exception as e:
        return [{"status": "error", "error": str(e)}]

def check_memory():
    try:
        result = subprocess.run(['wmic', 'OS', 'get', 'TotalVisibleMemorySize,FreePhysicalMemory', '/format:list'],
                               capture_output=True, text=True, timeout=5)
        mem_info = {}
        for line in result.stdout.split('\\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                mem_info[key.strip()] = value.strip()
        total = float(mem_info.get('TotalVisibleMemorySize', '0'))
        free = float(mem_info.get('FreePhysicalMemory', '0'))
        used = total - free
        usage = (used / total * 100) if total > 0 else 0
        return {"total_gb": round(total/(1024**2),2), "used_gb": round(used/(1024**2),2), "free_gb": round(free/(1024**2),2), "usage_percent": round(usage,1)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_processes():
    try:
        result = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\\n')
        if len(lines) < 2:
            return {"status": "no_data"}
        headers = [h.strip('"') for h in lines[0].split(',')]
        processes = []
        for line in lines[1:]:
            parts = [p.strip('"') for p in line.split(',')]
            if len(parts) >= len(headers):
                proc = dict(zip(headers, parts))
                try:
                    proc['Memory(KB)'] = int(proc.get('Memory(K)', '0').replace(',',''))
                except Exception:
                    proc['Memory(KB)'] = 0
                processes.append(proc)
        total_mem = sum(p.get('Memory(KB)', 0) for p in processes)
        high_mem = [p.get('Image Name', '') for p in processes if p.get('Memory(KB)', 0) > 500000]
        return {"total_processes": len(processes), "total_memory_mb": round(total_mem/1024,1), "high_memory_count": len(high_mem), "high_memory_list": high_mem[:3]}
    except Exception as e:
        return {"status": "error", "error": str(e)}

result = {
    "timestamp": datetime.now().isoformat(),
    "services": check_service_status(),
    "disks": check_disk_space(),
    "memory": check_memory(),
    "processes": check_processes(),
}
print(json.dumps(result, indent=2, ensure_ascii=False))
'''
    return _run_code_and_return(code, "system_diagnosis")