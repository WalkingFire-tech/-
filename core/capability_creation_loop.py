"""
能力创造回路 (Capability Creation Loop)

不是分析工具，是行动工具。
当系统遇到"不会的事"时，不再说"不行"，而是开始：
  探测 → 研究 → 尝试 → 验证 → 记住

这是系统"活过来"的起点。
"""

import asyncio
import subprocess
import re
import json
import time
from typing import Dict, List, Optional, Any
from loguru import logger
from datetime import datetime


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
        
        # 已知的问题模式 → 对应的解决方案
        self._pattern_solutions = {
            "serial": self._solve_serial_read,
            "serial_port": self._solve_serial_read,
            "com_port": self._solve_serial_read,
            "uart": self._solve_serial_read,
            "串口": self._solve_serial_read,
        }

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

    async def _solve_serial_read(self, query: str) -> Dict:
        """
        解决串口读取问题
        解析查询中的 COM 口和波特率，用 PowerShell 读取
        """
        # 解析参数
        port_match = re.search(r'COM\d+', query, re.IGNORECASE)
        baud_match = re.search(r'(\d{4,6})', query)
        
        port = port_match.group(0).upper() if port_match else "COM1"
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
        return {
            "gaps_detected": len(self.gaps),
            "gaps_resolved": sum(1 for g in self.gaps if g.resolved),
            "attempts_made": len(self.attempts),
            "attempts_succeeded": sum(1 for a in self.attempts if a.success),
            "tools_created": list(self._tools_created.keys()),
        }


# 全局实例
capability_creation_loop = CapabilityCreationLoop()
