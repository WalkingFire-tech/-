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


async def solve_system_management(query: str) -> Dict:
    goal_lower = query.lower()

    if any(kw in goal_lower for kw in ["进程", "process", "task"]):
        code = '''import subprocess
import json

def get_processes():
    try:
        result = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\\n')
        if len(lines) < 2:
            return []
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
        return processes
    except Exception as e:
        print(f"进程查询失败: {e}")
        return []

def analyze_processes(processes):
    if not processes:
        return {"status": "no_data", "message": "无法获取进程信息"}
    total_mem = sum(p.get('Memory(KB)', 0) for p in processes)
    high_mem_procs = [p for p in processes if p.get('Memory(KB)', 0) > 500000]
    return {
        "total_processes": len(processes),
        "total_memory_mb": round(total_mem / 1024, 1),
        "high_memory_processes": len(high_mem_procs),
        "high_memory_list": [p.get('Image Name', '') for p in high_mem_procs[:5]],
        "status": "analyzed"
    }

if __name__ == "__main__":
    procs = get_processes()
    result = analyze_processes(procs)
    print(json.dumps(result, indent=2, ensure_ascii=False))
'''
        return _run_code_and_return(code, "system_management/process")

    elif any(kw in goal_lower for kw in ["服务", "service"]):
        code = '''import subprocess
def get_services():
    try:
        result = subprocess.run(['sc', 'query', 'type=service', 'state=', '/fo', 'csv', '/nh'],
                               capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\\n')
        if len(lines) < 2:
            return []
        headers = [h.strip('"') for h in lines[0].split(',')]
        services = []
        for line in lines[1:]:
            parts = [p.strip('"') for p in line.split(',')]
            if len(parts) >= len(headers):
                services.append(dict(zip(headers, parts)))
        return services
    except Exception as e:
        print(f"服务查询失败: {e}")
        return []

def analyze_services(services):
    if not services:
        return {"status": "no_data", "message": "无法获取服务信息"}
    running = [s for s in services if s.get('STATE', '') == 'RUNNING']
    stopped = [s for s in services if s.get('STATE', '') == 'STOPPED']
    return {"total_services": len(services), "running": len(running), "stopped": len(stopped)}

if __name__ == "__main__":
    svcs = get_services()
    print(analyze_services(svcs))
'''
        return _run_code_and_return(code, "system_management/service")

    elif any(kw in goal_lower for kw in ["磁盘", "disk", "空间", "storage"]):
        code = '''import subprocess
import json

def get_disk_info():
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
        return disks
    except Exception as e:
        print(f"磁盘查询失败: {e}")
        return []

def analyze_disks(disks):
    if not disks:
        return {"status": "no_data"}
    disk_info = []
    for disk in disks:
        try:
            size_gb = float(disk.get('Size', '0')) / (1024**3)
            free_gb = float(disk.get('FreeSpace', '0')) / (1024**3)
            usage = ((size_gb - free_gb) / size_gb * 100) if size_gb > 0 else 0
            disk_info.append({"drive": disk.get('Caption', '?'), "size_gb": round(size_gb,2), "free_gb": round(free_gb,2), "usage_percent": round(usage,1)})
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
    return {"disks": disk_info}

if __name__ == "__main__":
    print(json.dumps(analyze_disks(get_disk_info()), indent=2, ensure_ascii=False))
'''
        return _run_code_and_return(code, "system_management/disk")

    elif any(kw in goal_lower for kw in ["网络", "network", "连接"]):
        code = '''import subprocess
result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True, timeout=5)
print(result.stdout[:2000] if result.stdout else "网络信息获取失败")
'''
        return _run_code_and_return(code, "system_management/network")

    else:
        code = '''import subprocess
import json

info = {}
try:
    r = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=10)
    info['system'] = r.stdout[:500] if r.stdout else 'N/A'
except Exception:
    info['system'] = 'systeminfo执行失败'

try:
    r = subprocess.run(['wmic', 'cpu', 'get', 'name', '/format:list'], capture_output=True, text=True, timeout=5)
    info['cpu'] = r.stdout.strip() if r.stdout else 'N/A'
except Exception:
    info['cpu'] = 'CPU信息获取失败'

try:
    r = subprocess.run(['wmic', 'OS', 'get', 'TotalVisibleMemorySize,FreePhysicalMemory', '/format:list'], capture_output=True, text=True, timeout=5)
    info['memory'] = r.stdout.strip() if r.stdout else 'N/A'
except Exception:
    info['memory'] = '内存信息获取失败'

print(json.dumps(info, indent=2, ensure_ascii=False))
'''
        return _run_code_and_return(code, "system_management/general")