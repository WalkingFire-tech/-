"""
系统自诊断引擎 — 通过安全的CMD/PowerShell命令进行系统级问题发现、修复、验证

设计原则：
1. 白名单制：只允许预定义的安全命令，禁止任意命令执行
2. 只读优先：诊断探针90%是只读的，修复动作需明确标注风险等级
3. 结果可解析：命令输出被结构化解析，而非原始文本堆砌
4. 渐进修复：发现→建议→确认→执行→验证，不跳步

诊断探针分类：
- 硬件健康：GPU温度/风扇、CPU负载、内存使用、磁盘空间
- 系统状态：进程/服务、网络连通、端口占用、事件日志
- 自我检查：Ollama状态、数据库完整性、配置一致性、代码缺陷
- 安全审计：异常进程、可疑端口、权限配置

修复动作分类（需风险等级审批）：
- L0 只读：不修改任何系统状态
- L1 低风险：清理临时文件、刷新DNS缓存
- L2 中风险：重启服务、调整进程优先级
- L3 高风险：修改注册表、安装/卸载软件（需人工确认）
"""

import subprocess
import platform
import re
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    READ_ONLY = "L0"
    LOW = "L1"
    MEDIUM = "L2"
    HIGH = "L3"


class ProbeCategory(Enum):
    HARDWARE = "hardware"
    SYSTEM = "system"
    SELF = "self"
    SECURITY = "security"


@dataclass
class DiagnosticProbe:
    name: str
    command: str
    category: ProbeCategory
    risk: RiskLevel
    timeout: int = 10
    description: str = ""
    parser: str = ""
    fix_suggestion: str = ""


@dataclass
class DiagnosticResult:
    probe_name: str
    category: ProbeCategory
    status: str  # ok, warning, error, unknown
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)
    fix_suggestion: str = ""
    risk: RiskLevel = RiskLevel.READ_ONLY


class SystemDiagnostician:
    PROBES: List[DiagnosticProbe] = [
        # === 硬件健康 ===
        DiagnosticProbe(
            name="gpu_status",
            command="wmic path win32_VideoController get name,AdapterRAM,DriverVersion /format:list",
            category=ProbeCategory.HARDWARE,
            risk=RiskLevel.READ_ONLY,
            description="GPU状态检测",
            parser="key_value",
        ),
        DiagnosticProbe(
            name="cpu_usage",
            command="wmic cpu get LoadPercentage /value",
            category=ProbeCategory.HARDWARE,
            risk=RiskLevel.READ_ONLY,
            description="CPU负载检测",
            parser="key_value",
            fix_suggestion="CPU持续高负载时检查异常进程或降低系统并行度",
        ),
        DiagnosticProbe(
            name="memory_usage",
            command="wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /format:list",
            category=ProbeCategory.HARDWARE,
            risk=RiskLevel.READ_ONLY,
            description="内存使用检测",
            parser="key_value",
            fix_suggestion="可用内存不足时关闭不必要的进程或降低Ollama并发",
        ),
        DiagnosticProbe(
            name="disk_space",
            command="wmic logicaldisk get caption,size,freespace /format:list",
            category=ProbeCategory.HARDWARE,
            risk=RiskLevel.READ_ONLY,
            description="磁盘空间检测",
            parser="disk_list",
            fix_suggestion="磁盘空间不足时清理临时文件和日志",
        ),
        DiagnosticProbe(
            name="disk_health",
            command="wmic diskdrive get status,model,size /format:list",
            category=ProbeCategory.HARDWARE,
            risk=RiskLevel.READ_ONLY,
            description="磁盘健康状态",
            parser="key_value",
        ),
        DiagnosticProbe(
            name="temperature",
            command="powershell -Command \"Get-WmiObject MSAcpi_ThermalZoneTemperature -Namespace root/wmi -ErrorAction SilentlyContinue | Select-Object CurrentTemperature\"",
            category=ProbeCategory.HARDWARE,
            risk=RiskLevel.READ_ONLY,
            timeout=8,
            description="系统温度检测（ACPI）",
            parser="raw",
        ),
        # === 系统状态 ===
        DiagnosticProbe(
            name="high_memory_processes",
            command="tasklist /fo csv /nh",
            category=ProbeCategory.SYSTEM,
            risk=RiskLevel.READ_ONLY,
            description="进程列表",
            parser="raw",
            fix_suggestion="发现异常高内存进程时考虑重启或降低优先级",
        ),
        DiagnosticProbe(
            name="critical_services",
            command="sc.exe query type=service state= all",
            category=ProbeCategory.SYSTEM,
            risk=RiskLevel.READ_ONLY,
            description="关键服务状态",
            parser="raw",
            fix_suggestion="关键服务停止时可尝试 sc start <服务名>",
        ),
        DiagnosticProbe(
            name="network_connectivity",
            command="ping -n 1 127.0.0.1",
            category=ProbeCategory.SYSTEM,
            risk=RiskLevel.READ_ONLY,
            description="网络连通性检测",
            parser="ping",
            fix_suggestion="网络不通时检查ipconfig /all和netsh诊断",
        ),
        DiagnosticProbe(
            name="port_listening",
            command="netstat -ano | findstr LISTENING",
            category=ProbeCategory.SYSTEM,
            risk=RiskLevel.READ_ONLY,
            description="监听端口检测",
            parser="port_list",
        ),
        DiagnosticProbe(
            name="recent_errors",
            command="powershell -Command \"Get-EventLog -LogName System -EntryType Error -Newest 10 -ErrorAction SilentlyContinue | Select-Object TimeGenerated,Source,Message | Format-List\"",
            category=ProbeCategory.SYSTEM,
            risk=RiskLevel.READ_ONLY,
            timeout=15,
            description="最近10条系统错误日志",
            parser="raw",
            fix_suggestion="重复出现的错误需要针对性修复",
        ),
        # === 自我检查 ===
        DiagnosticProbe(
            name="ollama_status",
            command="powershell -Command \"try{Invoke-WebRequest -Uri http://localhost:11434/api/tags -TimeoutSec 3 -UseBasicParsing|Select-Object -ExpandProperty Content}catch{$_.Exception.Message}\"",
            category=ProbeCategory.SELF,
            risk=RiskLevel.READ_ONLY,
            timeout=8,
            description="Ollama服务状态",
            parser="ollama",
            fix_suggestion="Ollama不可用时检查服务是否启动: sc query Ollama",
        ),
        DiagnosticProbe(
            name="python_health",
            command="python --version",
            category=ProbeCategory.SELF,
            risk=RiskLevel.READ_ONLY,
            description="Python版本检测",
            parser="raw",
        ),
        DiagnosticProbe(
            name="db_integrity",
            command="dir data\\*.db",
            category=ProbeCategory.SELF,
            risk=RiskLevel.READ_ONLY,
            description="数据库文件完整性",
            parser="raw",
            fix_suggestion="数据库文件为0KB或不存在时需要重建",
        ),
        # === 安全审计 ===
        DiagnosticProbe(
            name="suspicious_processes",
            command="tasklist /fo csv /nh",
            category=ProbeCategory.SECURITY,
            risk=RiskLevel.READ_ONLY,
            description="运行进程检测",
            parser="raw",
            fix_suggestion="发现可疑进程时检查其数字签名和来源",
        ),
        DiagnosticProbe(
            name="firewall_status",
            command="netsh advfirewall show allprofiles state",
            category=ProbeCategory.SECURITY,
            risk=RiskLevel.READ_ONLY,
            description="防火墙状态",
            parser="key_value",
            fix_suggestion="防火墙关闭时建议启用: netsh advfirewall set allprofiles state on",
        ),
        DiagnosticProbe(
            name="loop_health",
            command="echo ok",
            category=ProbeCategory.SELF,
            risk=RiskLevel.READ_ONLY,
            timeout=5,
            description="闭环健康度看板（规则激活率/策略库/满足感）",
            parser="raw",
        ),
    ]

    SAFE_FIX_COMMANDS = {
        "flush_dns": {
            "command": "ipconfig /flushdns",
            "risk": RiskLevel.LOW,
            "description": "刷新DNS缓存",
            "confirm_required": False,
        },
        "clear_temp": {
            "command": "powershell -Command \"Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue; Write-Output '临时文件已清理'\"",
            "risk": RiskLevel.LOW,
            "description": "清理用户临时文件",
            "confirm_required": False,
        },
        "clear_prefetch": {
            "command": "powershell -Command \"Remove-Item -Path C:\\Windows\\Prefetch\\* -Force -ErrorAction SilentlyContinue; Write-Output '预读缓存已清理'\"",
            "risk": RiskLevel.LOW,
            "description": "清理预读缓存",
            "confirm_required": True,
        },
        "restart_ollama": {
            "command": "powershell -Command \"Get-Process ollama* -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep -Seconds 2; Start-Process 'C:\\Users\\Administrator\\AppData\\Local\\Programs\\Ollama\\ollama app.exe' -WindowStyle Hidden\"",
            "risk": RiskLevel.MEDIUM,
            "description": "重启Ollama服务",
            "confirm_required": True,
        },
    }

    def __init__(self):
        self._last_results: List[DiagnosticResult] = []
        self._last_run_time: float = 0

    def run_probe(self, probe_name: str) -> Optional[DiagnosticResult]:
        probe = next((p for p in self.PROBES if p.name == probe_name), None)
        if not probe:
            logger.warning(f"未知探针: {probe_name}")
            return None
        return self._execute_probe(probe)

    def run_category(self, category: ProbeCategory) -> List[DiagnosticResult]:
        probes = [p for p in self.PROBES if p.category == category]
        results = []
        for probe in probes:
            result = self._execute_probe(probe)
            if result:
                results.append(result)
        return results

    def run_all(self) -> List[DiagnosticResult]:
        self._last_results = []
        self._last_run_time = time.time()
        for probe in self.PROBES:
            result = self._execute_probe(probe)
            if result:
                self._last_results.append(result)
        return self._last_results

    def run_quick(self) -> List[DiagnosticResult]:
        quick_probes = [
            "cpu_usage", "memory_usage", "disk_space",
            "ollama_status", "high_memory_processes",
        ]
        results = []
        for name in quick_probes:
            result = self.run_probe(name)
            if result:
                results.append(result)
        return results

    def execute_fix(self, fix_name: str, auto_confirm: bool = False) -> Dict:
        fix = self.SAFE_FIX_COMMANDS.get(fix_name)
        if not fix:
            return {"success": False, "error": f"未知修复动作: {fix_name}"}

        if fix["confirm_required"] and not auto_confirm:
            return {"success": False, "error": f"修复动作 {fix_name} 需要确认", "risk": fix["risk"].value}

        try:
            is_windows = platform.system() == "Windows"
            cmd_args = ["powershell", "-Command", fix["command"]] if is_windows else ["bash", "-c", fix["command"]]

            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if is_windows else 0,
            )

            output = (result.stdout or "").strip()
            if result.returncode == 0:
                logger.info(f"🔧 修复完成: {fix['description']} → {output[:100]}")
                return {"success": True, "output": output, "fix": fix_name}
            else:
                error = (result.stderr or "").strip()
                logger.warning(f"修复失败: {fix_name} → {error[:100]}")
                return {"success": False, "error": error, "fix": fix_name}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "修复超时", "fix": fix_name}
        except Exception as e:
            return {"success": False, "error": str(e), "fix": fix_name}

    def get_diagnostic_report(self) -> Dict:
        if not self._last_results:
            return {"status": "no_data", "message": "尚未运行诊断"}

        warnings = [r for r in self._last_results if r.status == "warning"]
        errors = [r for r in self._last_results if r.status == "error"]
        ok = [r for r in self._last_results if r.status == "ok"]

        return {
            "status": "error" if errors else ("warning" if warnings else "ok"),
            "total_probes": len(self._last_results),
            "ok_count": len(ok),
            "warning_count": len(warnings),
            "error_count": len(errors),
            "warnings": [{"probe": r.probe_name, "summary": r.summary, "fix": r.fix_suggestion} for r in warnings],
            "errors": [{"probe": r.probe_name, "summary": r.summary, "fix": r.fix_suggestion} for r in errors],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def _execute_probe(self, probe: DiagnosticProbe) -> Optional[DiagnosticResult]:
        try:
            is_windows = platform.system() == "Windows"
            cmd_args = ["powershell", "-Command", probe.command] if is_windows else ["bash", "-c", probe.command]

            result = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=probe.timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if is_windows else 0,
                encoding="utf-8",
                errors="replace",
            )

            output = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()

            if result.returncode != 0 and not output:
                return DiagnosticResult(
                    probe_name=probe.name,
                    category=probe.category,
                    status="error",
                    summary=f"命令执行失败: {stderr[:100]}",
                    details={"exit_code": result.returncode, "stderr": stderr[:200]},
                    fix_suggestion=probe.fix_suggestion,
                    risk=probe.risk,
                )

            parsed = self._parse_output(probe.parser, output)
            status, summary = self._evaluate_probe(probe.name, parsed, output)

            return DiagnosticResult(
                probe_name=probe.name,
                category=probe.category,
                status=status,
                summary=summary,
                details=parsed,
                fix_suggestion=probe.fix_suggestion if status != "ok" else "",
                risk=probe.risk,
            )

        except subprocess.TimeoutExpired:
            return DiagnosticResult(
                probe_name=probe.name,
                category=probe.category,
                status="warning",
                summary=f"探针超时({probe.timeout}s)",
                risk=probe.risk,
            )
        except Exception as e:
            return DiagnosticResult(
                probe_name=probe.name,
                category=probe.category,
                status="error",
                summary=f"探针异常: {str(e)[:80]}",
                risk=probe.risk,
            )

    def _parse_output(self, parser: str, output: str) -> Dict:
        if not output or output == "(无输出)":
            return {"raw": ""}

        if parser == "key_value":
            return self._parse_key_value(output)
        elif parser == "disk_list":
            return self._parse_disk_list(output)
        elif parser == "ping":
            return self._parse_ping(output)
        elif parser == "ollama":
            return self._parse_ollama(output)
        elif parser == "port_list":
            return self._parse_port_list(output)
        elif parser == "service_list":
            return self._parse_service_list(output)
        elif parser == "table":
            return self._parse_table(output)
        else:
            return {"raw": output[:500]}

    def _parse_key_value(self, output: str) -> Dict:
        result = {}
        for line in output.split("\n"):
            line = line.strip()
            if "=" in line:
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()
        return result if result else {"raw": output[:300]}

    def _parse_disk_list(self, output: str) -> Dict:
        disks = {}
        current = {}
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                if current and current.get("Size"):
                    caption = current.get("Caption", "Unknown")
                    disks[caption] = current
                    current = {}
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                current[key.strip()] = value.strip()
        if current and current.get("Size"):
            disks[current.get("Caption", "Unknown")] = current
        return disks if disks else {"raw": output[:300]}

    def _parse_ping(self, output: str) -> Dict:
        times = re.findall(r"时间[=<](\d+)ms|time[=<](\d+)ms|TTL=", output, re.IGNORECASE)
        latency = []
        for t in times:
            val = t[0] or t[1]
            if val:
                latency.append(int(val))
        reachable = len(times) > 0 or "TTL=" in output
        return {
            "reachable": reachable,
            "latency_ms": latency,
            "avg_latency": sum(latency) / len(latency) if latency else 0,
        }

    def _parse_ollama(self, output: str) -> Dict:
        try:
            import json
            data = json.loads(output)
            models = data.get("models", [])
            return {
                "available": True,
                "model_count": len(models),
                "models": [m.get("name", "") for m in models[:5]],
            }
        except Exception:
            return {"available": False, "error": output[:100]}

    def _parse_port_list(self, output: str) -> Dict:
        ports = []
        for line in output.split("\n"):
            line = line.strip()
            if "LISTENING" in line:
                parts = line.split()
                if len(parts) >= 2:
                    addr_port = parts[1]
                    if ":" in addr_port:
                        port = addr_port.rsplit(":", 1)[-1]
                        pid = parts[-1] if parts[-1].isdigit() else ""
                        ports.append({"port": port, "pid": pid})
        return {"listening_ports": ports[:20], "count": len(ports)}

    def _parse_service_list(self, output: str) -> Dict:
        services = {"running": 0, "stopped": 0, "samples": []}
        for line in output.split("\n"):
            line = line.strip()
            if not line or line.startswith('"ServiceName"'):
                continue
            parts = line.strip('"').split('","')
            if len(parts) >= 4:
                state = parts[3] if len(parts) > 3 else ""
                if "RUNNING" in state.upper():
                    services["running"] += 1
                elif "STOPPED" in state.upper():
                    services["stopped"] += 1
                if len(services["samples"]) < 5:
                    services["samples"].append({"name": parts[0], "state": state})
        return services

    def _parse_table(self, output: str) -> Dict:
        lines = [l.strip() for l in output.split("\n") if l.strip()]
        return {"rows": len(lines) - 1, "raw": output[:400]} if lines else {"raw": output[:300]}

    def _evaluate_probe(self, probe_name: str, parsed: Dict, raw: str) -> Tuple[str, str]:
        if probe_name == "cpu_usage":
            load = parsed.get("LoadPercentage", "")
            try:
                val = int(load)
                if val > 90:
                    return "warning", f"CPU负载过高: {val}%"
                elif val > 70:
                    return "warning", f"CPU负载较高: {val}%"
                return "ok", f"CPU负载正常: {val}%"
            except (ValueError, TypeError):
                return "unknown", f"CPU负载: {load or '无法读取'}"

        elif probe_name == "memory_usage":
            try:
                total_kb = int(parsed.get("TotalVisibleMemorySize", "0"))
                free_kb = int(parsed.get("FreePhysicalMemory", "0"))
                if total_kb > 0:
                    used_pct = (1 - free_kb / total_kb) * 100
                    free_gb = free_kb / 1024 / 1024
                    if used_pct > 90:
                        return "error", f"内存严重不足: 可用{free_gb:.1f}GB ({used_pct:.0f}%已用)"
                    elif used_pct > 80:
                        return "warning", f"内存紧张: 可用{free_gb:.1f}GB ({used_pct:.0f}%已用)"
                    return "ok", f"内存正常: 可用{free_gb:.1f}GB ({used_pct:.0f}%已用)"
            except (ValueError, TypeError):
                pass
            return "unknown", "内存信息无法解析"

        elif probe_name == "disk_space":
            warnings = []
            for name, info in parsed.items():
                if name == "raw":
                    continue
                try:
                    size = int(info.get("Size", "0"))
                    free = int(info.get("FreeSpace", "0"))
                    if size > 0:
                        free_gb = free / 1024**3
                        used_pct = (1 - free / size) * 100
                        if free_gb < 5:
                            warnings.append(f"{name} 仅剩{free_gb:.1f}GB")
                        elif used_pct > 95:
                            warnings.append(f"{name} 已用{used_pct:.0f}%")
                except (ValueError, TypeError):
                    continue
            if warnings:
                return "warning", "; ".join(warnings)
            return "ok", "磁盘空间正常"

        elif probe_name == "ollama_status":
            if parsed.get("available"):
                models = parsed.get("models", [])
                return "ok", f"Ollama正常 ({parsed.get('model_count', 0)}个模型: {', '.join(models[:3])})"
            return "error", f"Ollama不可用: {parsed.get('error', '未知')}"

        elif probe_name == "high_memory_processes":
            rows = parsed.get("rows", 0)
            return "ok" if rows > 0 else "unknown", f"检测到{rows}个进程"

        elif probe_name == "network_connectivity":
            if parsed.get("reachable"):
                avg = parsed.get("avg_latency", 0)
                return "ok", f"网络正常 (延迟{avg:.0f}ms)"
            return "error", "网络不可达"

        elif probe_name == "firewall_status":
            raw_lower = raw.lower()
            if "on" in raw_lower:
                return "ok", "防火墙已启用"
            return "warning", "防火墙未启用"

        elif probe_name == "suspicious_processes":
            rows = parsed.get("rows", 0)
            if rows > 5:
                return "warning", f"发现{rows}个非标准路径进程"
            return "ok", f"非标准路径进程{rows}个"

        elif probe_name == "loop_health":
            return self._evaluate_loop_health()

        return "ok", raw[:100] if raw else "无输出"

    def _evaluate_loop_health(self) -> Tuple[str, str]:
        indicators = []
        overall_status = "ok"

        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/learning_rules.db")
            row = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active_rules = row[0] if row else 0
            row2 = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='trial'")
            trial_rules = row2[0] if row2 else 0
            activation_rate = active_rules / max(active_rules + trial_rules, 1) * 100
            if activation_rate < 5:
                indicators.append(f"规则激活率{activation_rate:.1f}%⚠️")
                overall_status = "warning"
            else:
                indicators.append(f"规则激活率{activation_rate:.1f}%✅")
        except Exception:
            indicators.append("规则激活率:无法读取")

        try:
            from core.learning.strategy_library import strategy_library
            stats = strategy_library.get_stats()
            total = stats.get("total_active", 0)
            avg_conf = stats.get("avg_confidence", 0)
            indicators.append(f"策略库{total}条(均值{avg_conf:.1f})")
        except Exception:
            indicators.append("策略库:无法读取")

        try:
            from core.learning.intrinsic_reward import intrinsic_reward
            istats = intrinsic_reward.get_stats()
            satisfaction = istats.get("satisfaction", 0.5)
            if satisfaction < 0.3:
                indicators.append(f"满足感{satisfaction:.1f}⚠️")
                if overall_status != "error":
                    overall_status = "warning"
            else:
                indicators.append(f"满足感{satisfaction:.1f}✅")
        except Exception:
            indicators.append("满足感:无法读取")

        return overall_status, "; ".join(indicators)


system_diagnostician = SystemDiagnostician()