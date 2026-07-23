import re
import time
from typing import Dict, List, Optional, Any

from loguru import logger
from datetime import datetime

from core.capability_creation.constants import _SHELL_KEYWORDS
from core.capability_creation.models import CapabilityGap, CreationAttempt, ExecutionResult
from core.capability_creation.execution_engine import (
    is_dangerous, execute_with_retry, auto_install,
)
from core.capability_creation.shell_executor import (
    try_shell_execution, solve_serial_read,
)


class CapabilityCreationLoop:
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
            "天气": self._solve_weather_query,
            "weather": self._solve_weather_query,
            "气温": self._solve_weather_query,
        }

    async def _solve_serial_read(self, query: str) -> Dict:
        return await solve_serial_read(query)

    async def _solve_map_render(self, query: str) -> Dict:
        from core.capability_creation.solvers.map_render import solve_map_render
        return await solve_map_render(query, serial_solve_fn=solve_serial_read)

    async def _solve_system_management(self, query: str) -> Dict:
        from core.capability_creation.solvers.system_management import solve_system_management
        return await solve_system_management(query)

    async def _solve_system_diagnosis(self, query: str) -> Dict:
        from core.capability_creation.solvers.system_diagnosis import solve_system_diagnosis
        return await solve_system_diagnosis(query)

    async def _solve_auto_repair(self, query: str) -> Dict:
        from core.capability_creation.solvers.auto_repair import solve_auto_repair
        return await solve_auto_repair(query)

    async def _solve_weather_query(self, query: str) -> Dict:
        from core.capability_creation.solvers.weather import solve_weather_query
        return await solve_weather_query(query)

    async def handle(self, query: str, context: Dict = None) -> Dict:
        context = context or {}
        logger.info(f"🧠 能力创造回路启动: {query[:80]}")

        gap = CapabilityGap(query, "no_tool", "主链路无工具匹配")
        self.gaps.append(gap)
        self._persist_gap_to_db(query, "no_tool", "主链路无工具匹配")

        q_lower = query.lower()

        for pattern, solver in self._pattern_solutions.items():
            if pattern in q_lower:
                logger.info(f"🔍 匹配到问题模式: {pattern}")
                try:
                    gap.gap_type = "tool_failed"
                    result = await solver(query)
                    if result and isinstance(result, dict) and result.get("success"):
                        gap.resolved = True
                        gap.solution = str(result.get("data", ""))[:200]

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

        _looks_like_command = any(kw in q_lower for kw in _SHELL_KEYWORDS) or (
            not any('\u4e00' <= c <= '\u9fff' for c in query[:10])
        )
        if _looks_like_command:
            logger.info("🔄 尝试通用shell方案")
            attempt = CreationAttempt(query, "shell_fallback")
            try:
                result = await try_shell_execution(query)
                attempt.finish(result["success"], result.get("data", ""), result.get("error", ""))
                self.attempts.append(attempt)

                if result["success"]:
                    gap.resolved = True
                    gap.solution = str(result.get("data", ""))[:200]
                    await self._register_tool(query, result.get("data", ""), "shell_fallback")
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
        else:
            logger.info("🔄 跳过shell方案（非命令式查询）")

        return {
            "handled": False,
            "data": "",
            "source": "capability_creation_loop",
            "method": "all_failed",
            "confidence": 0.0,
        }

    async def _register_tool(self, query: str, result_data: str, pattern: str):
        try:
            from core.tool_registry import tool_registry

            pattern_tool_map = {
                "serial": "serial_port",
                "地图": "map_render",
                "天气": "weather_query",
                "系统": "system_management",
                "诊断": "system_diagnosis",
                "修复": "auto_repair",
            }
            tool_name = None
            for key, name in pattern_tool_map.items():
                if key in pattern:
                    tool_name = name
                    break
            if not tool_name:
                tool_name = f"capability_{pattern[:20]}"

            existing = tool_registry.get(tool_name)
            if not existing:
                if tool_name == "serial_port":
                    try:
                        from core.tools.serial_port_tool import SerialPortTool
                        tool_registry.register(SerialPortTool())
                        logger.info(f"✅ 能力创造回路: 注册 {tool_name} 工具")
                    except Exception as e:
                        logger.debug(f"SerialPortTool注册跳过: {e}")
                else:
                    self._tools_created[tool_name] = {
                        "pattern": pattern,
                        "query_sample": query[:100],
                        "created_at": datetime.now().isoformat(),
                    }
                    logger.info(f"✅ 能力创造回路: 记录能力 {tool_name} (pattern={pattern})")

            try:
                from core.ports.adapters import get_storage_port
                get_storage_port("data/experience_pool.db").execute(
                    "INSERT INTO experiences (timestamp, query, result, success) VALUES (?, ?, ?, 1)",
                    (datetime.now().isoformat(), query[:200], result_data[:500]),
                    commit=True
                )
            except Exception as e:
                logger.error(f"经验写入失败: {e}")

            try:
                from core.learning.tool_builder import ToolSelfBuilder
                builder = ToolSelfBuilder()
                builder.record_success("capability_creation_loop", query, result_data[:100])
            except Exception as e:
                logger.error(f"ToolBuilder通知失败: {e}")

        except Exception as e:
            logger.warning(f"工具注册失败: {e}")

    def _persist_gap_to_db(self, query: str, gap_type: str, description: str):
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/capability_gaps.db")
            db.execute(
                "CREATE TABLE IF NOT EXISTS capability_gaps "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT, failed_paths TEXT, "
                "gap_type TEXT, resolution TEXT, resolved INTEGER DEFAULT 0, "
                "attempts INTEGER DEFAULT 1, first_seen TEXT, last_seen TEXT)"
            )
            existing = db.query_one(
                "SELECT id, attempts FROM capability_gaps WHERE query LIKE ? AND gap_type=?",
                (query[:200], gap_type)
            )
            now = datetime.now().isoformat()
            if existing:
                db.execute(
                    "UPDATE capability_gaps SET attempts=?, last_seen=? WHERE id=?",
                    (existing[1] + 1, now, existing[0]),
                    commit=True,
                )
            else:
                db.execute(
                    "INSERT INTO capability_gaps (query, failed_paths, gap_type, resolution, resolved, attempts, first_seen, last_seen) "
                    "VALUES (?, ?, ?, '', 0, 1, ?, ?)",
                    (query[:200], description[:200], gap_type, now, now),
                    commit=True,
                )
        except Exception as e:
            logger.debug(f"缺口持久化跳过: {e}")

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

    def get_status(self) -> Dict:
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


capability_creation_loop = CapabilityCreationLoop()