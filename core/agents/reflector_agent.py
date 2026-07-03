"""
反思者Agent - 评估执行结果、反馈给规划者、形成闭环
"""
from typing import Dict, List
from loguru import logger

from core.agents.base_agent import BaseAgent, AgentState, ReflectionFeedback
from core.agents.agent_events import AgentEventTypes


class ReflectorAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id="reflector", role="reflector")
        self._quality_threshold_replan = 40
        self._quality_threshold_accept = 60

    def evaluate(self, plan_id: str, execution_result,
                 query: str = "") -> ReflectionFeedback:
        self.state = AgentState.REFLECTING
        try:
            quality = execution_result.quality if hasattr(execution_result, 'quality') else execution_result.get("quality", 0)
            success = execution_result.success if hasattr(execution_result, 'success') else execution_result.get("success", False)

            needs_replan = quality < self._quality_threshold_replan and not success

            lessons = self._extract_lessons(execution_result, quality)
            suggestions = self._generate_suggestions(execution_result, quality)

            feedback = ReflectionFeedback(
                plan_id=plan_id,
                execution_id="",
                quality_score=quality,
                needs_replan=needs_replan,
                lessons=lessons,
                suggestions=suggestions,
            )

            self.send_message(
                AgentEventTypes.ReflectionFeedback,
                {
                    "plan_id": plan_id,
                    "quality_score": quality,
                    "needs_replan": needs_replan,
                    "lessons": lessons,
                    "suggestions": suggestions,
                    "success": success,
                },
                recipient="planner",
                correlation_id=plan_id,
            )

            self._save_lessons_to_spirit(lessons, query, quality)

            logger.info(f"ReflectorAgent: 评估完成 plan={plan_id} "
                         f"quality={quality:.1f} needs_replan={needs_replan} "
                         f"lessons={len(lessons)}")
            self.state = AgentState.IDLE
            return feedback

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"ReflectorAgent: 评估失败: {e}")
            return ReflectionFeedback(
                plan_id=plan_id, execution_id="",
                quality_score=0, needs_replan=False,
            )

    def _extract_lessons(self, execution_result, quality: float) -> List[str]:
        lessons = []
        source = execution_result.source if hasattr(execution_result, 'source') else execution_result.get("source", "")

        if quality < 30:
            lessons.append(f"来源{source}质量极低({quality:.0f})，需要更深度推理")
        elif quality < 50:
            lessons.append(f"来源{source}质量不足({quality:.0f})，需要补充验证")

        if "error" in source.lower() or "fail" in source.lower():
            lessons.append(f"执行失败来源: {source}，建议切换策略")

        return lessons

    def _generate_suggestions(self, execution_result, quality: float) -> List[str]:
        suggestions = []

        if quality < self._quality_threshold_replan:
            suggestions.append("补充外部信息")
            suggestions.append("交叉验证")

        if quality < 30:
            suggestions.append("深度模型推理")

        source = execution_result.source if hasattr(execution_result, 'source') else execution_result.get("source", "")
        if "experience_pool" in source and quality < 50:
            suggestions.append("经验池命中质量低，尝试模型推理")
        if "ollama" in source and quality < 40:
            suggestions.append("模型输出质量低，尝试外部搜索补充")

        return suggestions

    def _save_lessons_to_spirit(self, lessons: List[str], query: str, quality: float):
        if not lessons:
            return
        try:
            import sqlite3
            from datetime import datetime
            with sqlite3.connect("data/spirit_lessons.db") as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS lessons (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lesson TEXT,
                        context TEXT,
                        quality_score REAL,
                        created_at TEXT
                    )
                ''')
                for lesson in lessons:
                    conn.execute(
                        "INSERT INTO lessons (lesson, context, quality_score, created_at) VALUES (?, ?, ?, ?)",
                        (lesson, query[:100], quality, datetime.now().isoformat()),
                    )
                conn.commit()
        except Exception as e:
            logger.debug(f"ReflectorAgent: 教训保存失败: {e}")


reflector_agent = ReflectorAgent()