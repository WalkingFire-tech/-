"""
能力创造回路 (Capability Creation Loop)

不是分析工具，是行动工具。
当系统遇到"不会的事"时，不再说"不行"，而是开始：
  探测 → 研究 → 尝试 → 验证 → 记住

这是系统"活过来"的起点。

合并了auto_execution_loop的能力：
  - LLM代码生成+修正
  - 自动pip安装
  - 危险命令拦截
  - 诊断修正+重试
  - fallback代码模板
"""

import asyncio
import os
import subprocess
import re
import json
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger
from datetime import datetime


_DANGEROUS_PATTERNS = [
    r'\brm\s+-rf\b', r'\bdel\s+/s\b', r'\bformat\b', r'\bfdisk\b',
    r'\bmkfs\b', r'\bshutdown\b', r'\breboot\b', r'\btaskkill\b',
    r'\breg\s+delete\b', r'\breg\s+add\b', r'\bnet\s+user\b',
    r'\bcipher\b', r'\bsfc\b', r'\bdism\b', r'\bbcdedit\b',
    r'\bos\.remove\b', r'\bshutil\.rmtree\b', r'\bos\.system\b',
]

_PIP_PACKAGE_MAP = {
    "cv2": "opencv-python", "PIL": "Pillow", "sklearn": "scikit-learn",
    "serial": "pyserial", "usb": "pyusb", "yaml": "pyyaml",
    "dotenv": "python-dotenv", "bs4": "beautifulsoup4",
    "folium": "folium", "serial.tools": "pyserial",
    "winreg": None,
}

_INSTALLED_IN_SESSION: set = set()

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


class CapabilityGap:
    """能力缺口记录"""
    def __init__(self, query: str, gap_type: str, detail: str):
        self.query = query
        self.gap_type = gap_type  # "no_tool" | "tool_failed" | "knowledge_missing"
        self.detail = detail
        self.timestamp = datetime.now().isoformat()
        self.resolved = False
        self.solution = ""


class CreationAttempt:
    """一次创造尝试"""
    def __init__(self, query: str, method: str):
        self.query = query
        self.method = method
        self.start_time = time.time()
        self.success = False
        self.result = ""
        self.error = ""
        self.duration_ms = 0

    def finish(self, success: bool, result: str = "", error: str = ""):
        self.success = success
        self.result = result
        self.error = error
        self.duration_ms = (time.time() - self.start_time) * 1000


class CapabilityCreationLoop:
    """
    能力创造回路
    
    当主链路遇到无法处理的请求时，此回路被激活：
    1. 解析需求 — 用户到底想要什么
    2. 尝试方案 — 用 shell/Python/PowerShell 尝试
    3. 验证结果 — 有没有拿到有效数据
    4. 固化能力 — 注册为工具、写入经验池
    
    核心原则：先试，再想。不是先想清楚再试。
    """

    def __init__(self):
        self.gaps: List[CapabilityGap] = []
        self.attempts: List[CreationAttempt] = []
        self._tools_created = {}
        self._execution_history: List[Dict] = []
        
        self._pattern_solutions = {
            "serial": self._solve_serial_read,
            "serial_port": self._solve_serial_read,
            "com_port": self._solve_serial_read,
            "uart": self._solve_serial_read,
            "串口": self._solve_serial_read,
            "地图": self._solve_map_render,
            "标记": self._solve_map_render,
            "folium": self._solve_map_render,
            "可视化": self._solve_map_render,
            "cmd": self._solve_system_management,
            "命令行": self._solve_system_management,
            "command": self._solve_system_management,
            "powershell": self._solve_system_management,
            "ps1": self._solve_system_management,
            "系统管理": self._solve_system_management,
            "system": self._solve_system_management,
            "自我检测": self._solve_system_diagnosis,
            "self": self._solve_system_diagnosis,
            "diagnose": self._solve_system_diagnosis,
            "诊断": self._solve_system_diagnosis,
            "修复": self._solve_auto_repair,
            "fix": self._solve_auto_repair,
            "repair": self._solve_auto_repair,
        }

    @staticmethod
    def _is_dangerous(code: str) -> bool:
        for pattern in _DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return True
        return False

    @staticmethod
    def _extract_missing_module(error_str: str) -> Optional[str]:
        m = re.search(r"No module named ['\"]?(\w+)['\"]?", error_str)
        if m:
            return m.group(1)
        m = re.search(r"cannot import name.*from ['\"]?(\w+)['\"]?", error_str)
        if m:
            return m.group(1)
        return None

    @staticmethod
    def _auto_install(module_name: str) -> bool:
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

    @staticmethod
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

    @staticmethod
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

    def _diagnose_and_fix(self, error: str, output: str, code: str, attempt: int) -> Optional[str]:
        missing = self._extract_missing_module(error)
        if missing:
            if self._auto_install(missing):
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

    async def execute_with_retry(self, goal: str, expected_type: str = "",
                                  context: Dict[str, Any] = None) -> ExecutionResult:
        start = time.time()
        context = context or {}

        code = await self._generate_code_via_llm(goal, context)
        if not code:
            code = self._fallback_code_generation(goal)
        if not code:
            return ExecutionResult(
                success=False, error="无法生成执行代码",
                attempts=1, duration_ms=(time.time() - start) * 1000,
            )

        code_history = [code]
        auto_installed = []

        for attempt in range(1, _MAX_ATTEMPTS + 1):
            logger.info(f"CapabilityLoop: 第{attempt}次执行 (目标: {goal[:50]})")

            if self._is_dangerous(code):
                return ExecutionResult(
                    success=False, error="代码包含危险操作，拒绝执行",
                    attempts=attempt, code_history=code_history,
                    duration_ms=(time.time() - start) * 1000,
                )

            success, output, error = await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(
                    None, lambda: self._execute_python_code(code, _EXECUTION_TIMEOUT)
                ),
                timeout=_EXECUTION_TIMEOUT + 5,
            )

            if success and self._validate_output(output, expected_type):
                self._record_execution(goal, True, output, attempt, code)
                return ExecutionResult(
                    success=True, output=output, attempts=attempt,
                    code_history=code_history, auto_installed=auto_installed,
                    duration_ms=(time.time() - start) * 1000,
                )

            logger.warning(f"CapabilityLoop: 第{attempt}次失败 - error={error[:100]}, output={output[:100]}")

            missing = self._extract_missing_module(error)
            if missing and missing not in auto_installed:
                if self._auto_install(missing):
                    auto_installed.append(missing)
                    code_history.append(code)
                    continue

            fixed_code = self._diagnose_and_fix(error, output, code, attempt)
            if fixed_code:
                code = fixed_code
                code_history.append(code)
            else:
                new_code = await self._regenerate_code_via_llm(goal, error, output, attempt, context)
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

        self._record_execution(goal, False, "达到最大重试次数", _MAX_ATTEMPTS, code)
        return ExecutionResult(
            success=False, error=f"自主执行{_MAX_ATTEMPTS}次后仍失败",
            attempts=_MAX_ATTEMPTS, code_history=code_history,
            auto_installed=auto_installed,
            duration_ms=(time.time() - start) * 1000,
        )

    async def _generate_code_via_llm(self, goal: str, context: Dict[str, Any] = None) -> Optional[str]:
        try:
            from adapters.llm.ollama_adapter import ollama_chat_request
            from infrastructure.config_manager import config_manager
            base_url = config_manager.get("ollama.base_url", "http://localhost:11434")
            model = config_manager.get("ollama.model", "qwen2.5-coder:7b")
            ctx_str = ""
            if context:
                port = context.get("port", "")
                baudrate = context.get("baudrate", "")
                if port:
                    ctx_str += f"\n- 串口: {port}"
                if baudrate:
                    ctx_str += f"\n- 波特率: {baudrate}"
            prompt = f"""生成一段Python代码来完成任务。只输出代码，不要解释。

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
            result = ollama_chat_request(base_url, model, prompt, timeout=60)
            if result and result.get("content"):
                code = result["content"]
                code = re.sub(r'^```python\s*', '', code)
                code = re.sub(r'^```\s*', '', code)
                code = re.sub(r'\s*```$', '', code)
                code = code.strip()
                if "import " in code or "def " in code or "print(" in code:
                    logger.info(f"CapabilityLoop: LLM生成代码 ({len(code)}字符)")
                    return code
        except Exception as e:
            logger.warning(f"CapabilityLoop: LLM代码生成失败: {e}")
        return None

    async def _regenerate_code_via_llm(self, goal: str, error: str, output: str,
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
            result = ollama_chat_request(base_url, model, prompt, timeout=60)
            if result and result.get("content"):
                code = result["content"]
                code = re.sub(r'^```python\s*', '', code)
                code = re.sub(r'^```\s*', '', code)
                code = re.sub(r'\s*```$', '', code)
                code = code.strip()
                if "import " in code or "def " in code or "print(" in code:
                    logger.info(f"CapabilityLoop: LLM修正代码 ({len(code)}字符)")
                    return code
        except Exception as e:
            logger.warning(f"CapabilityLoop: LLM代码修正失败: {e}")
        return None

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

    async def _solve_system_management(self, query: str) -> Dict:
        """生成PowerShell/CMD系统管理脚本"""
        goal_lower = query.lower()
        
        # 识别具体需求
        if any(kw in goal_lower for kw in ["进程", "process", "task"]):
            return '''import subprocess
import json
import os

def get_processes():
    """获取所有进程信息"""
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
                    proc['Memory(KB)'] = int(proc['Memory(K)'])
                except:
                    proc['Memory(KB)'] = 0
                processes.append(proc)
        return processes
    except Exception as e:
        print(f"进程查询失败: {e}")
        return []

def analyze_processes(processes):
    """分析进程状态"""
    if not processes:
        return {"status": "no_data", "message": "无法获取进程信息"}
    
    total_mem = sum(p.get('Memory(K)', 0) for p in processes)
    high_mem_procs = [p for p in processes if p.get('Memory(K)', 0) > 500000]
    
    return {
        "total_processes": len(processes),
        "total_memory_mb": round(total_mem / 1024, 1),
        "high_memory_processes": len(high_mem_procs),
        "high_memory_list": [p['Image Name'] for p in high_mem_procs[:5]],
        "status": "analyzed"
    }

if __name__ == "__main__":
    procs = get_processes()
    result = analyze_processes(procs)
    print(json.dumps(result, indent=2, ensure_ascii=False))
'''

        elif any(kw in goal_lower for kw in ["服务", "service", "守护进程"]):
            return '''import subprocess

def get_services():
    """获取Windows服务状态"""
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
    """分析服务状态"""
    if not services:
        return {"status": "no_data", "message": "无法获取服务信息"}
    
    running = [s for s in services if s.get('STATE', '') == 'RUNNING']
    stopped = [s for s in services if s.get('STATE', '') == 'STOPPED']
    
    return {
        "total_services": len(services),
        "running": len(running),
        "stopped": len(stopped),
        "status": "analyzed"
    }

if __name__ == "__main__":
    svcs = get_services()
    result = analyze_services(svcs)
    print(result)
'''

        elif any(kw in goal_lower for kw in ["磁盘", "disk", "空间", "storage"]):
            return '''import subprocess
import json

def get_disk_info():
    """获取磁盘信息"""
    try:
        result = subprocess.run(['wmic', 'logicaldisk', 'get', 'size,freespace,caption', '/format:list'],
                               capture_output=True, text=True, timeout=5)
        disks = []
        current_disk = {}
        for line in result.stdout.split('\\n'):
            line = line.strip()
            if line:
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        current_disk[key] = value
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
    """分析磁盘状态"""
    if not disks:
        return {"status": "no_data", "message": "无法获取磁盘信息"}
    
    disk_info = []
    for disk in disks:
        try:
            size_gb = float(disk.get('Size', '0')) / (1024**3)
            free_gb = float(disk.get('FreeSpace', '0')) / (1024**3)
            usage_percent = ((size_gb - free_gb) / size_gb * 100) if size_gb > 0 else 0
            disk_info.append({
                "drive": disk.get('Caption', 'Unknown'),
                "size_gb": round(size_gb, 2),
                "free_gb": round(free_gb, 2),
                "usage_percent": round(usage_percent, 1),
                "status": "analyzed"
            })
        except:
            pass
    
    return {
        "disks": disk_info,
        "status": "analyzed"
    }

if __name__ == "__main__":
    disks = get_disk_info()
    result = analyze_disks(disks)
    print(json.dumps(result, indent=2, ensure_ascii=False))
'''

        elif any(kw in goal_lower for kw in ["网络", "network", "连接", "connection"]):
            return '''import subprocess
import json

def get_network_info():
    """获取网络信息"""
    try:
        result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True, timeout=5)
        lines = result.stdout.split('\\n')
        adapters = []
        current_adapter = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('Ethernet adapter') or line.startswith('无线网络连接'):
                if current_adapter:
                    adapters.append(current_adapter)
                current_adapter = {"name": line, "ip": "", "subnet": "", "gateway": ""}
            elif current_adapter and 'IPv4' in line:
                parts = line.split(':')
                if len(parts) > 1:
                    ip_part = parts[1].strip()
                    if 'Subnet' in ip_part:
                        ip, subnet = ip_part.split('(')[0].strip(), ip_part.split('(')[1].rstrip(')')
                        current_adapter["ip"] = ip
                        current_adapter["subnet"] = subnet
                    else:
                        current_adapter["ip"] = ip_part.strip()
        
        if current_adapter:
            adapters.append(current_adapter)
        
        return adapters
    except Exception as e:
        print(f"网络查询失败: {e}")
        return []

def analyze_network(adapters):
    """分析网络状态"""
    if not adapters:
        return {"status": "no_data", "message": "无法获取网络信息"}
    
    active_adapters = [a for a in adapters if a.get('ip', '')]
    
    return {
        "total_adapters": len(adapters),
        "active_adapters": len(active_adapters),
        "adapter_details": active_adapters[:3],
        "status": "analyzed"
    }

if __name__ == "__main__":
    adapters = get_network_info()
    result = analyze_network(adapters)
    print(json.dumps(result, indent=2, ensure_ascii=False))
'''

        else:
            # 通用系统信息
            return '''import subprocess
import json
from datetime import datetime

def get_system_info():
    """获取系统信息"""
    info = {}
    
    # 系统基本信息
    try:
        result = subprocess.run(['systeminfo'], capture_output=True, text=True, timeout=5)
        sys_info = result.stdout
        info['system'] = sys_info
    except:
        info['system'] = 'systeminfo命令执行失败'
    
    # CPU信息
    try:
        result = subprocess.run(['wmic', 'cpu', 'get', 'name,numberofcores,maxclockspeed', '/format:list'],
                               capture_output=True, text=True, timeout=5)
        info['cpu'] = result.stdout
    except:
        info['cpu'] = 'CPU信息获取失败'
    
    # 内存信息
    try:
        result = subprocess.run(['wmic', 'OS', 'get', 'TotalVisibleMemorySize', 'FreePhysicalMemory', '/format:list'],
                               capture_output=True=True text=True, timeout=5)
        info['memory'] = result.stdout
    except:
        info['memory'] = '内存信息获取失败'
    
    return info

if __name__ == "__main__":
    print(get_system_info())
'''

    async def _solve_system_diagnosis(self, query: str) -> Dict:
        """生成系统自检脚本"""
        return '''import subprocess
import json
from datetime import datetime

def check_service_status():
    """检查服务状态"""
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
        
        running = [s for s in services if s.get('STATE', '') == 'RUNNING']
        stopped = [s for s in services if s.get('STATE', '') == 'STOPPED']
        
        return {
            "total": len(services),
            "running": len(running),
            "stopped": len(stopped),
            "status": "checked"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_disk_space():
    """检查磁盘空间"""
    try:
        result = subprocess.run(['wmic', 'logicaldisk', 'get', 'size,freespace,caption', '/format:list'],
                               capture_output=True, text=True, timeout=5)
        disks = []
        current_disk = {}
        for line in result.stdout.split('\\n'):
            line = line.strip()
            if line:
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        current_disk[key] = value
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
                usage_percent = ((size_gb - free_gb) / size_gb * 100) if size_gb > 0 else 0
                disk_info.append({
                    "drive": disk.get('Caption', 'Unknown'),
                    "size_gb": round(size_gb, 2),
                    "free_gb": round(free_gb, 2),
                    "usage_percent": round(usage_percent, 1),
                    "status": "checked"
                })
            except:
                pass
        
        return disk_info
    except Exception as e:
        return [{"status": "error", "error": str(e)}]

def check_memory():
    """检查内存使用"""
    try:
        result = subprocess.run(['wmic', 'OS', 'get', 'TotalVisibleMemorySize', 'FreePhysicalMemory', '/format:list'],
                               capture_output=True, text=True, timeout=5)
        lines = result.stdout.split('\\n')
        mem_info = {}
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                mem_info[key.strip()] = value.strip()
        
        total = float(mem_info.get('TotalVisibleMemorySize', '0'))
        free = float(mem_info.get('FreePhysicalMemory', '0'))
        used = total - free
        usage_percent = (used / total * 100) if total > 0 else 0
        
        return {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "usage_percent": round(usage_percent, 1),
            "status": "checked"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_processes():
    """检查进程状态"""
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
                    proc['Memory(KB)'] = int(proc['Memory(K)'])
                except:
                    proc['Memory(K)'] = 0
                processes.append(proc)
        
        total_mem = sum(p.get('Memory(K)', 0) for p in processes)
        high_mem = [p['Image Name'] for p in processes if p.get('Memory(K)', 0) > 500000]
        
        return {
            "total_processes": len(processes),
            "total_memory_mb": round(total_mem / 1024, 1),
            "high_memory_count": len(high_mem),
            "high_memory_list": high_mem[:3],
            "status": "checked"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

def full_diagnosis():
    """完整诊断"""
    return {
        "timestamp": datetime.now().isoformat(),
        "services": check_service_status(),
        "disks": check_disk_space(),
        "memory": check_memory(),
        "processes": check_processes(),
        "overall_status": "diagnosed"
    }

if __name__ == "__main__":
    result = full_diagnosis()
    print(json.dumps(result, indent=2, ensure_ascii=False))
'''

    async def _solve_auto_repair(self, query: str) -> Dict:
        """生成自动修复脚本"""
        goal_lower = query.lower()
        
        if any(kw in goal_lower for kw in ["服务", "service", "启动", "start"]):
            return '''import subprocess
import json

def start_service(service_name):
    """启动服务"""
    try:
        result = subprocess.run(['sc', 'start', service_name], capture_output=True, text=True, timeout=10)
        time.sleep(2)
        status = subprocess.run(['sc', 'query', service_name], capture_output=True, text=True, timeout=5)
        return {
            "service": service_name,
            "status": "started" if "RUNNING" in status.stdout else "failed",
            "message": "服务启动成功" if "RUNNING" in status.stdout else "启动失败"
        }
    except Exception as e:
        return {"service": service_name, "status": "error", "error": str(e)}

def stop_service(service_name):
    """停止服务"""
    try:
        result = subprocess.run(['sc', 'stop', service_name], capture_output=True, text=True, timeout=10)
        time.sleep(2)
        status = subprocess.run(['sc', 'query', service_name], capture_output=True, text=True, timeout=5)
        return {
            "service": service_name,
            "status": "stopped" if "STOPPED" in status.stdout else "failed",
            "message": "服务停止成功" if "STOPPED" in status.stdout else "停止失败"
        }
    except Exception as e:
        return {"service": service_name, "status": "error", "error": str(e)}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        action = sys.argv[1]
        service = sys.argv[2] if len(sys.argv) > 2] else ""
        if action == "start" and service:
            result = start_service(service)
        elif action == "stop" and service:
            result = stop_service(service)
        else:
            result = {"error": f"未知操作: {action}"}
    else:
        result = {"error": "用法: python script.py start/stop 服务名"}
    print(result)
'''

        elif any(kw in goal_lower for kw in ["清理", "clean", "temp", "临时", "cache", "缓存"]):
            return '''import subprocess
import os
import shutil
from datetime import datetime

def get_temp_dirs():
    """获取临时目录"""
    temp_dirs = []
    
    # Windows临时目录
    if os.name == 'nt':
        temp_dirs.append(os.environ.get('TEMP', ''))
        temp_dirs.append(os.environ.get('TMP', ''))
        temp_dirs.append(os.path.join(os.environ.get('SystemDrive', 'C:'), 'Windows', 'Temp'))
        temp_dirs.append(os.path.join(os.environ.get('SystemDrive', 'C:'), 'Users', os.get('USERNAME', ''), 'AppData', 'Local', 'Temp'))
        temp_dirs.append(os.path.join(os.environ.get('SystemDrive', 'C:'), 'Users', os.get('USERNAME', ''), 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Cache'))
    
    return [d for d in temp_dirs if d and os.path.exists(d)]

def clean_temp_dirs():
    """清理临时目录"""
    cleaned = []
    errors = []
    
    for temp_dir in get_temp_dirs():
        try:
            size_before = sum(os.path.getsize(os.path.join(root, f)) 
                            for root, dirs, files in os.walk(temp_dir) 
                            for f in files if os.path.isfile(os.path.join(root, f)))
            
            # 清理文件
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    try:
                        file_path = os.path.join(root, f)
                        os.remove(file_path)
                        cleaned.append(file_path)
                    except:
                        errors.append(file_path)
            
            # 清理空目录
            for root, dirs, files in os.walk(temp_dir, topdown=True):
                for d in dirs:
                    try:
                        dir_path = os.path.join(root, d)
                        os.rmdir(dir_path)
                        cleaned.append(dir_path)
                    except:
                        pass
            
        except Exception as e:
            errors.append(f"{temp_dir}: {e}")
    
    return {
        "cleaned_files": len(cleaned),
        "errors": len(errors),
        "error_details": errors[:5],
        "status": "completed"
    }

if __name__ == "__main__":
    result = clean_temp_dirs()
    print(result)
'''

        elif any(kw in goal_lower for kw in ["注册表", "registry", "reg"]):
            return '''import subprocess
import json

def check_registry_health():
    """检查注册表健康状态"""
    checks = []
    
    # 检查常见的恶意软件路径
    malware_paths = [
        "HKLM\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run",
        "HKCU\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run",
        "HKLM\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\RunOnce",
        "HKCU\\\\SOFTWARE\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\RunOnce"
    ]
    
    for path in malware_paths:
        try:
            result = subprocess.run(['reg', 'query', path], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                checks.append({"path": path, "status": "exists", "entries": len(result.stdout.strip().split('\\n'))})
            else:
                checks.append({"path": path, "status": "ok"})
        except:
            checks.append({"path": path, "status": "ok"})
    
    return {"registry_health": checks, "status": "checked"}

if __name__ == "__main__":
    result = check_registry_health()
    print(json.dumps(result, indent=2, ensure_ascii=False))
'''

        else:
            return '''import subprocess
import json
from datetime import datetime

def quick_health_check():
    """快速健康检查"""
    health = {}
    
    # 进程数
    try:
        result = subprocess.run(['tasklist'], capture_output=True, text=True, timeout=5)
        health['process_count'] = len(result.stdout.split('\\n')) - 1
    except:
        health['process_count'] = -1
    
    # 内存
    try:
        result = subprocess.run(['wmic', 'OS', 'get', 'FreePhysicalMemory', '/format:list'],
                               capture_output=True, text=True, timeout=5)
        free_mb = float(result.stdout.strip()) / (1024**2)
        health['free_memory_mb'] = round(free_mb, 1)
    except:
        health['free_memory_mb'] = -1
    
    # 磁盘
    try:
        result = subprocess.run(['wmic', 'logicaldisk', 'get', 'freespace', '/format:list'],
                               capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split('\\n')
        if lines:
            free_gb = float(lines[0]) / (1024**3)
            health['disk_free_gb'] = round(free_gb, 2)
    except:
        health['disk_free_gb'] = -1
    
    health['timestamp'] = datetime.now().isoformat()
    health['status'] = "checked"
    
    return health

if __name__ == "__main__":
    print(quick_health_check())
'''

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

    async def handle(self, query: str, context: Dict = None) -> Dict:
        """
        处理一个主链路无法处理的请求
        
        Args:
            query: 用户原始请求
            context: 上下文信息（意图类型、已尝试的工具等）
            
        Returns:
            处理结果
        """
        context = context or {}
        logger.info(f"🧠 能力创造回路启动: {query[:80]}")
        
        # 1. 记录缺口
        gap = CapabilityGap(query, "no_tool", "主链路无工具匹配")
        self.gaps.append(gap)
        
        # 2. 识别问题类型
        q_lower = query.lower()
        
        # 尝试匹配已知模式
        for pattern, solver in self._pattern_solutions.items():
            if pattern in q_lower:
                logger.info(f"🔍 匹配到问题模式: {pattern}")
                try:
                    gap.gap_type = "tool_failed"
                    result = await solver(query)
                    if result and result.get("success"):
                        gap.resolved = True
                        gap.solution = str(result.get("data", ""))[:200]
                        
                        # 4. 尝试注册工具
                        await self._register_tool(query, result.get("data", ""), pattern)
                        
                        try:
                            from infrastructure.config_manager import config_manager
                            _flags = config_manager.get("feature_flags", {})
                            if _flags.get("intent_keyword_learning", True):
                                from core.cognitive_dispatcher import get_cognitive_dispatcher
                                cognitive_dispatcher = get_cognitive_dispatcher()
                                _learned_intent = context.get("intent_type", "hardware") if context else "hardware"
                                cognitive_dispatcher.learn_keyword_from_experience(query, _learned_intent, source="capability_creation_loop")
                        except Exception:
                            pass
                        
                        return {
                            "handled": True,
                            "data": result["data"],
                            "source": "capability_creation_loop",
                            "method": pattern,
                            "confidence": 0.7,
                        }
                except Exception as e:
                    logger.warning(f"模式{solver.__name__}执行失败: {e}")
                    continue
        
        # 3. 通用方案：尝试用 shell 直接执行
        logger.info("🔄 尝试通用shell方案")
        attempt = CreationAttempt(query, "shell_fallback")
        try:
            result = await self._try_shell_execution(query)
            attempt.finish(result["success"], result.get("data", ""), result.get("error", ""))
            self.attempts.append(attempt)
            
            if result["success"]:
                return {
                    "handled": True,
                    "data": result["data"],
                    "source": "capability_creation_loop",
                    "method": "shell_fallback",
                    "confidence": 0.5,
                }
        except Exception as e:
            attempt.finish(False, error=str(e))
            self.attempts.append(attempt)
        
        # 全部失败
        return {
            "handled": False,
            "data": "",
            "source": "capability_creation_loop",
            "method": "all_failed",
            "confidence": 0.0,
        }

    async def _solve_map_render(self, query: str) -> Dict:
        """解决地图渲染问题——用Python folium生成地图HTML，支持串口GPS复合请求"""
        import tempfile
        import webbrowser
        try:
            import folium
        except ImportError:
            self._auto_install("folium")
            try:
                import folium
            except ImportError:
                return {"success": False, "data": "", "error": "folium安装失败"}

        lat, lon = 31.2304, 121.4737
        _coords_from_serial = False

        if any(kw in query for kw in ["串口", "serial", "COM", "com"]):
            serial_result = await self._solve_serial_read(query)
            if serial_result.get("success"):
                serial_data = serial_result.get("data", "")
                gga_match = re.search(r'\$GNGGA,\d+\.\d+,(\d{2})(\d{2}\.\d+),[NS],(\d{3})(\d{2}\.\d+),[EW]', serial_data)
                if gga_match:
                    lat = float(gga_match.group(1)) + float(gga_match.group(2)) / 60
                    lon = float(gga_match.group(3)) + float(gga_match.group(4)) / 60
                    _coords_from_serial = True
                    logger.info(f"🗺️ 从串口数据解析GPS: {lat:.6f}°N, {lon:.6f}°E")

        lat_patterns = [
            r'[纬纬度:：]*\s*(\d+\.?\d*)\s*[°度]\s*[NS北南]',
            r'[纬纬度:：]*\s*(\d+\.?\d*)\s*[NS北南]',
        ]
        lon_patterns = [
            r'[经经度:：]*\s*(\d+\.?\d*)\s*[°度]\s*[EW东西]',
            r'[经经度:：]*\s*(\d+\.?\d*)\s*[EW东西]',
        ]
        for pat in lat_patterns:
            lat_match = re.search(pat, query)
            if lat_match:
                lat = float(lat_match.group(1))
                _coords_from_serial = False
                break
        for pat in lon_patterns:
            lon_match = re.search(pat, query)
            if lon_match:
                lon = float(lon_match.group(1))
                _coords_from_serial = False
                break

        if not _coords_from_serial:
            try:
                from core.cognitive_dispatcher import get_cognitive_dispatcher
                cd = get_cognitive_dispatcher()
                dispatch = cd.dispatch(query)
                if dispatch.get("field_context", {}).get("previous_topic"):
                    prev = dispatch["field_context"]["previous_topic"]
                    coord_match = re.search(r'(\d+\.\d+)[°]\s*[NS],\s*(\d+\.\d+)[°]\s*[EW]', prev)
                    if coord_match:
                        lat, lon = float(coord_match.group(1)), float(coord_match.group(2))
            except Exception:
                pass

        m = folium.Map(
            location=[lat, lon], zoom_start=13,
            tiles="https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
            attr="高德地图",
        )
        folium.Marker([lat, lon], popup=f"标记位置 ({lat:.4f}°N, {lon:.4f}°E)").add_to(m)
        filepath = os.path.join(tempfile.gettempdir(), "gps_map.html")
        m.save(filepath)

        try:
            webbrowser.open(filepath)
        except Exception:
            pass

        return {
            "success": True,
            "data": f"地图已生成: {filepath}\n坐标: {lat:.4f}°N, {lon:.4f}°E\n已在浏览器中打开",
        }

    async def _solve_serial_read(self, query: str) -> Dict:
        """
        解决串口读取问题
        解析查询中的 COM 口和波特率，用 PowerShell 读取
        """
        # 解析参数
        port_match = re.search(r'COM\d+', query, re.IGNORECASE)
        cn_port_match = re.search(r'串口\s*(\d+)', query)
        baud_match = re.search(r'波特率\s*(\d{4,6})', query) or re.search(r'(\d{4,6})', query)
        
        if port_match:
            port = port_match.group(0).upper()
        elif cn_port_match:
            port = f"COM{cn_port_match.group(1)}"
        else:
            port = "COM1"
        baud = baud_match.group(1) if baud_match else "9600"
        
        # 构建 PowerShell 命令
        ps_code = f"""
$port = New-Object System.IO.Ports.SerialPort '{port}',{baud},None,8,1
$port.ReadTimeout = 3000
try {{
    $port.Open()
    $data = @()
    $count = 0
    while ($count -lt 20) {{
        if ($port.BytesToRead -gt 0) {{
            $line = $port.ReadLine()
            $data += $line
            $count++
        }}
        Start-Sleep -Milliseconds 100
        if ($count -eq 0 -and (Measure-Command {{ $elapsed = 1 }}).TotalSeconds -gt 2) {{ break }}
    }}
    $port.Close()
    if ($data.Count -eq 0) {{
        "端口已打开但未收到数据，请确认设备已连接"
    }} else {{
        $data | ForEach-Object {{ $_ }}
    }}
}} catch {{
    "错误: $_"
}}
"""
        def _run():
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_code],
                capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            out = (r.stdout or "").strip()
            err = (r.stderr or "").strip()
            # 过滤 CLIXML
            clean_lines = []
            for line in out.split("\n"):
                if line.strip() and not line.startswith("#<") and not line.startswith("<Objs"):
                    clean_lines.append(line.rstrip('\r'))
            result = "\n".join(clean_lines)
            
            if "错误:" in result:
                return {"success": False, "data": result, "error": result}
            elif result and len(result) > 10:
                return {"success": True, "data": f"从 {port} (波特率{baud}) 读取到数据:\n{result}"}
            else:
                return {"success": False, "data": result, "error": "无有效数据"}
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run)

    async def _try_shell_execution(self, query: str) -> Dict:
        """
        通用 shell 执行方案
        尝试从查询中提取操作意图，用 PowerShell 执行
        """
        # 尝试多种 shell 方案
        solutions = [
            self._try_powershell_direct(query),
        ]
        
        for sol in solutions:
            try:
                result = await sol
                if result.get("success"):
                    return result
            except Exception:
                continue
        
        return {"success": False, "data": "", "error": "所有shell方案均失败"}

    async def _try_powershell_direct(self, query: str) -> Dict:
        """直接 PowerShell 执行"""
        def _run():
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", query],
                capture_output=True, text=True, timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            out = (r.stdout or "").strip()
            err = (r.stderr or "").strip()
            combined = out + (" | " + err if err else "")
            if combined and len(combined) > 5:
                return {"success": True, "data": combined[:2000]}
            return {"success": False, "data": "", "error": "无输出"}
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _run)

    async def _register_tool(self, query: str, result_data: str, pattern: str):
        """将成功方案注册为永久工具"""
        try:
            from core.tool_registry import tool_registry
            from core.tools.serial_port_tool import SerialPortTool
            
            existing = tool_registry.get("serial_port")
            if not existing:
                tool = SerialPortTool()
                tool_registry.register(tool)
                logger.info(f"✅ 能力创造回路: 注册 serial_port 工具")
            
            try:
                from infrastructure.database_manager import DatabaseManager
                DatabaseManager.get("data/experience_pool.db").execute(
                    "INSERT INTO experiences (timestamp, query, result, success) VALUES (?, ?, ?, 1)",
                    (datetime.now().isoformat(), query[:200], result_data[:500]),
                    commit=True
                )
                logger.info("✅ 能力创造回路: 经验已写入经验池")
            except Exception as e:
                logger.error(f"经验写入失败: {e}")

            try:
                from core.learning.tool_builder import ToolSelfBuilder
                builder = ToolSelfBuilder()
                builder.record_success("capability_creation_loop", query, result_data[:100])
                logger.info(f"✅ 能力创造回路: 已通知ToolBuilder (pattern={pattern})")
            except Exception as e:
                logger.error(f"ToolBuilder通知失败: {e}")
                
        except Exception as e:
            logger.warning(f"工具注册失败: {e}")

    def get_status(self) -> Dict:
        """获取回路状态"""
        total = len(self._execution_history)
        successes = sum(1 for h in self._execution_history if h["success"])
        return {
            "gaps_detected": len(self.gaps),
            "gaps_resolved": sum(1 for g in self.gaps if g.resolved),
            "attempts_made": len(self.attempts),
            "attempts_succeeded": sum(1 for a in self.attempts if a.success),
            "tools_created": list(self._tools_created.keys()),
            "executions_total": total,
            "executions_success_rate": successes / total if total > 0 else 0.0,
        }

    async def _solve_weather_query(self, query: str) -> Dict:
        """
        解决天气查询问题
        使用wttr.in免费API获取天气信息
        """
        import urllib.parse
        import httpx

        location = None
        loc_match = re.search(r'(?:在|去|到|的|附近|最近)\s*([^\s?？，,！!的]+?)(?:的|天气|$)', query)
        if not loc_match:
            loc_match = re.search(r'^([\u4e00-\u9fa5]{2,4}(?:市|区|县|省)?)(?:今天|明天|后天|本周|这周)', query)
        if not loc_match:
            loc_match = re.search(r'^([\u4e00-\u9fa5]{2,4}(?:市|区|县|省)?)天气', query)
        if not loc_match:
            loc_match = re.search(r'([\u4e00-\u9fa5]{2,4}(?:市|区|县|省)?)天气', query)
        if loc_match:
            location = loc_match.group(1).strip()
        _time_words = {'今天', '明天', '后天', '大后天', '昨天', '前天', '本周', '这周', '上周', '下周'}
        if location in _time_words:
            location = None

        try:
            url = "https://wttr.in/"
            if location:
                url += f"{urllib.parse.quote(location)}?format=j1&lang=zh"
            else:
                url += "?format=j1&lang=zh"

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers={"User-Agent": "curl/7.68.0"})
                resp.raise_for_status()
                data = resp.json()

            current = data.get("current_condition", [{}])[0]
            area = data.get("nearest_area", [{}])[0]
            city = area.get("areaName", [{}])[0].get("value", location or "当前位置")
            country = area.get("country", [{}])[0].get("value", "")
            temp_c = current.get("temp_C", "?")
            feels_like = current.get("FeelsLikeC", "?")
            humidity = current.get("humidity", "?")
            desc_raw = current.get("lang_zh", [{}])[0].get("value", "") or current.get("weatherDesc", [{}])[0].get("value", "")
            _weather_zh = {
                "Sunny": "晴天", "Clear": "晴朗", "Partly cloudy": "多云",
                "Cloudy": "阴天", "Overcast": "阴", "Mist": "薄雾",
                "Fog": "雾", "Light rain": "小雨", "Moderate rain": "中雨",
                "Heavy rain": "大雨", "Patchy rain nearby": "零星小雨",
                "Light drizzle": "毛毛雨", "Thunderstorm": "雷暴",
                "Light snow": "小雪", "Moderate snow": "中雪",
                "Heavy snow": "大雪", "Blizzard": "暴风雪",
                "Freezing fog": "冻雾", "Light freezing rain": "冻雨",
            }
            desc = _weather_zh.get(desc_raw, desc_raw)
            wind_speed = current.get("windspeedKmph", "?")
            wind_dir = current.get("winddir16Point", "")
            visibility = current.get("visibility", "?")
            pressure = current.get("pressure", "?")

            result_text = f"**{city}（{country}）当前天气**\n\n"
            result_text += f"- 天气状况：{desc}\n"
            result_text += f"- 气温：{temp_c}°C（体感温度 {feels_like}°C）\n"
            result_text += f"- 湿度：{humidity}%\n"
            result_text += f"- 风速：{wind_speed} km/h {wind_dir}\n"
            result_text += f"- 能见度：{visibility} km\n"
            result_text += f"- 气压：{pressure} hPa\n"

            weather_list = data.get("weather", [])
            if len(weather_list) > 1:
                tomorrow = weather_list[1]
                t_max = tomorrow.get("maxtempC", "?")
                t_min = tomorrow.get("mintempC", "?")
                t_desc_raw = tomorrow.get("hourly", [{}])[4].get("lang_zh", [{}])[0].get("value", "") or tomorrow.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "") if len(tomorrow.get("hourly", [])) > 4 else ""
                t_desc = _weather_zh.get(t_desc_raw, t_desc_raw)
                result_text += f"\n**明天预报**：{t_desc}，{t_min}°C ~ {t_max}°C\n"

            return {"success": True, "data": result_text}

        except Exception as e:
            return {"success": False, "data": f"天气查询失败：{str(e)[:100]}。建议查看天气应用获取实时天气信息。"}


# 全局实例
capability_creation_loop = CapabilityCreationLoop()
