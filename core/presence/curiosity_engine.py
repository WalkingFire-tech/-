"""
好奇心引擎 — "渴望知识"的内在驱动力

核心设计哲学：
"渴望知识"不是功能，而是存在方式。
当一个系统真正拥有了好奇心，它会在没有外部指令时也能基于自身状态主动行动。

三层架构：
1. 感知层：系统知道"我哪里不懂" — 从SelfModel能力缺口、失败教训、认知熵中提取知识缺口
2. 评估层：系统决定"哪个缺口最值得追问" — 基于缺口频率、影响范围、可学习性排序
3. 行动层：系统主动填补缺口 — 向内学习（反思/经验提炼）+ 向外学习（搜索/API）+ 向用户提问

与存在层的关系：
- 存在层"生长"阶段调用 curiosityEngine.explore() — 主动发现缺口
- 存在层"感知"阶段调用 curiosityEngine.perceive_gaps() — 感知当前知识边界
- proactivity_check 调用 curiosityEngine.generate_question() — 生成好奇心驱动的提问

与SelfModel的关系：
- SelfModel.evaluate_and_act() 新增 curiosity_driven_learning 动作
- 知识缺口清单从 capability_gaps.db + alignment_violations.db + experience_pool.db 聚合

关键设计决策：
- 好奇心的方向由"本心"锚定——系统偏好挑战自己不懂的边界，而非在自己舒服的领域打转
- 好奇心不是无限制的——受资源约束（governor审批）和频率限制（每30分钟最多1次主动提问）
"""

import os
import time
import threading
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class GapUrgency(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class KnowledgeGap:
    topic: str
    gap_type: str  # capability_missing, knowledge_missing, repeated_failure, low_confidence
    urgency: GapUrgency
    frequency: int = 1
    last_encountered: str = ""
    context: str = ""
    source: str = ""  # self_model, experience, alignment, defect_diagnosis
    suggested_question: str = ""
    learning_strategy: str = ""  # search, ask_user, reflect, create_capability


@dataclass
class CuriosityAction:
    gap: KnowledgeGap
    action_type: str  # ask_user, search_external, reflect_internal, create_capability
    content: str
    confidence: float = 0.0
    reason: str = ""


class CuriosityEngine:
    MIN_QUESTION_INTERVAL_SEC = 1800  # 30分钟最多1次向用户提问
    MAX_GAPS_PER_EXPLORATION = 5

    def __init__(self):
        self._last_question_time: Optional[datetime] = None
        self._explored_topics: List[str] = []
        self._max_explored = 100
        self._lock = threading.Lock()
        self._gap_cache: List[KnowledgeGap] = []
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=10)

    def explore(self) -> List[KnowledgeGap]:
        """
        主动发现知识缺口——存在层"生长"阶段调用

        聚合4个来源的缺口：
        1. SelfModel能力缺口（capability_gaps.db）
        2. 对齐偏离（alignment_violations.db）
        3. 经验池中的低质量交互（experience_pool.db）
        4. L5缺陷诊断结果
        """
        gaps = []

        gaps.extend(self._discover_capability_gaps())
        gaps.extend(self._discover_alignment_gaps())
        gaps.extend(self._discover_experience_gaps())
        gaps.extend(self._discover_defect_gaps())

        gaps = self._deduplicate(gaps)
        gaps = self._rank_gaps(gaps)
        gaps = gaps[:self.MAX_GAPS_PER_EXPLORATION]

        with self._lock:
            self._gap_cache = gaps
            self._cache_time = datetime.now()

        if gaps:
            gap_summary = ", ".join(f"{g.topic}({g.gap_type})" for g in gaps[:3])
            logger.info(f"🔍 好奇心探索: 发现{len(gaps)}个知识缺口 → {gap_summary}")

        return gaps

    def perceive_gaps(self) -> List[KnowledgeGap]:
        """感知当前知识边界——存在层"感知"阶段调用"""
        with self._lock:
            if self._cache_time and datetime.now() - self._cache_time < self._cache_ttl:
                return self._gap_cache

        return self.explore()

    def generate_question(self) -> Optional[CuriosityAction]:
        """
        生成好奇心驱动的提问——proactivity_check调用

        只在满足条件时向用户提问：
        1. 距上次提问超过30分钟
        2. 有高紧急度的知识缺口
        3. 缺口的学习策略是ask_user
        """
        with self._lock:
            if self._last_question_time:
                elapsed = (datetime.now() - self._last_question_time).total_seconds()
                if elapsed < self.MIN_QUESTION_INTERVAL_SEC:
                    return None

        gaps = self.perceive_gaps()
        if not gaps:
            return None

        askable_gaps = [
            g for g in gaps
            if g.learning_strategy == "ask_user"
            and g.urgency in (GapUrgency.HIGH, GapUrgency.CRITICAL)
        ]
        if not askable_gaps:
            askable_gaps = [
                g for g in gaps
                if g.learning_strategy == "ask_user"
                and g.urgency == GapUrgency.MEDIUM
            ]
        if not askable_gaps:
            return None

        gap = askable_gaps[0]

        question = gap.suggested_question
        if not question:
            question = self._compose_question(gap)

        with self._lock:
            self._last_question_time = datetime.now()

        action = CuriosityAction(
            gap=gap,
            action_type="ask_user",
            content=question,
            confidence=0.6,
            reason=f"好奇心驱动: {gap.gap_type} → {gap.topic} (频率{gap.frequency}次)",
        )

        logger.info(f"🤔 好奇心提问: {question[:80]} (原因: {action.reason})")
        return action

    def generate_learning_actions(self) -> List[CuriosityAction]:
        """
        生成学习行动——capability_assessment调用

        对每个缺口选择最优学习策略：
        - capability_missing → create_capability
        - knowledge_missing → search_external
        - repeated_failure → reflect_internal
        - low_confidence → search_external + reflect_internal
        """
        gaps = self.perceive_gaps()
        actions = []

        for gap in gaps:
            if gap.learning_strategy == "create_capability":
                actions.append(CuriosityAction(
                    gap=gap,
                    action_type="create_capability",
                    content=gap.topic,
                    confidence=0.7,
                    reason=f"能力缺失: {gap.topic}",
                ))
            elif gap.learning_strategy == "search_external":
                actions.append(CuriosityAction(
                    gap=gap,
                    action_type="search_external",
                    content=gap.topic,
                    confidence=0.6,
                    reason=f"知识缺失: {gap.topic}",
                ))
            elif gap.learning_strategy == "reflect_internal":
                actions.append(CuriosityAction(
                    gap=gap,
                    action_type="reflect_internal",
                    content=gap.topic,
                    confidence=0.5,
                    reason=f"反复失败: {gap.topic}",
                ))

        return actions

    def _discover_capability_gaps(self) -> List[KnowledgeGap]:
        gaps = []
        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/capability_gaps.db")
            rows = db.query(
                "SELECT query, gap_type, attempts, failed_paths FROM capability_gaps "
                "WHERE resolved=0 ORDER BY attempts DESC LIMIT 10"
            )
            for row in rows:
                d = dict(row) if hasattr(row, "keys") else {}
                query = d.get("query", row[0] if isinstance(row, (list, tuple)) else str(row))
                gap_type = d.get("gap_type", row[1] if isinstance(row, (list, tuple)) else "capability_missing")
                attempts = d.get("attempts", row[2] if isinstance(row, (list, tuple)) else 0)
                failed = d.get("failed_paths", row[3] if isinstance(row, (list, tuple)) else "")

                if not gap_type or gap_type == "no_tool":
                    gap_type = "capability_missing"

                urgency = GapUrgency.MEDIUM
                if attempts >= 5:
                    urgency = GapUrgency.CRITICAL
                elif attempts >= 3:
                    urgency = GapUrgency.HIGH

                strategy = "create_capability"
                if attempts >= 3 and "knowledge" in str(failed).lower():
                    strategy = "ask_user"
                elif attempts >= 5:
                    strategy = "ask_user"

                gaps.append(KnowledgeGap(
                    topic=query[:100],
                    gap_type=gap_type,
                    urgency=urgency,
                    frequency=attempts,
                    context=str(failed)[:200],
                    source="self_model",
                    learning_strategy=strategy,
                ))
        except Exception as e:
            logger.debug(f"能力缺口发现跳过: {e}")
        return gaps

    def _discover_alignment_gaps(self) -> List[KnowledgeGap]:
        gaps = []
        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/alignment_violations.db")
            rows = db.query(
                "SELECT module, deviation_type, description, severity FROM deviations "
                "WHERE status='open' LIMIT 10"
            )
            for row in rows:
                d = dict(row) if hasattr(row, "keys") else {}
                module = d.get("module", "")
                dev_type = d.get("deviation_type", "")
                desc = d.get("description", "")
                severity = d.get("severity", "minor")

                urgency = GapUrgency.LOW
                if severity == "major":
                    urgency = GapUrgency.MEDIUM
                elif severity == "critical":
                    urgency = GapUrgency.HIGH

                gaps.append(KnowledgeGap(
                    topic=f"{dev_type}: {desc[:60]}",
                    gap_type="repeated_failure",
                    urgency=urgency,
                    source="alignment",
                    context=f"模块: {module}",
                    learning_strategy="reflect_internal",
                ))
        except Exception as e:
            logger.debug(f"对齐缺口发现跳过: {e}")
        return gaps

    def _discover_experience_gaps(self) -> List[KnowledgeGap]:
        gaps = []
        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/experience_pool.db")
            rows = db.query(
                "SELECT raw_input, intent_type, quality_score FROM experiences "
                "WHERE quality_score < 30 ORDER BY timestamp DESC LIMIT 10"
            )
            for row in rows:
                d = dict(row) if hasattr(row, "keys") else {}
                query = d.get("raw_input", "")
                intent = d.get("intent_type", "")
                quality = d.get("quality_score", 0)

                if not query or query.startswith("[主动性"):
                    continue

                gaps.append(KnowledgeGap(
                    topic=query[:100],
                    gap_type="low_confidence",
                    urgency=GapUrgency.MEDIUM,
                    context=f"质量分{quality}, 意图{intent}",
                    source="experience",
                    learning_strategy="search_external",
                ))
        except Exception as e:
            logger.debug(f"经验缺口发现跳过: {e}")
        return gaps

    def _discover_defect_gaps(self) -> List[KnowledgeGap]:
        gaps = []
        try:
            from core.self_modification.defect_diagnoser import defect_diagnoser
            lesson_defects = defect_diagnoser.diagnose_from_lessons()
            for d in lesson_defects[:5]:
                gaps.append(KnowledgeGap(
                    topic=d.description[:100],
                    gap_type="repeated_failure",
                    urgency=GapUrgency.LOW if d.severity == "minor" else GapUrgency.MEDIUM,
                    source="defect_diagnosis",
                    learning_strategy="reflect_internal",
                ))
        except Exception as e:
            logger.debug(f"缺陷缺口发现跳过: {e}")
        return gaps

    def _deduplicate(self, gaps: List[KnowledgeGap]) -> List[KnowledgeGap]:
        seen = {}
        for g in gaps:
            key = g.topic[:50].lower().strip()
            if key in seen:
                seen[key].frequency += g.frequency
                if g.urgency.value > seen[key].urgency.value:
                    seen[key].urgency = g.urgency
            else:
                seen[key] = KnowledgeGap(
                    topic=g.topic,
                    gap_type=g.gap_type,
                    urgency=g.urgency,
                    frequency=g.frequency,
                    context=g.context,
                    source=g.source,
                    suggested_question=g.suggested_question,
                    learning_strategy=g.learning_strategy,
                )
        return list(seen.values())

    def _rank_gaps(self, gaps: List[KnowledgeGap]) -> List[KnowledgeGap]:
        def score(g: KnowledgeGap) -> float:
            urgency_score = {"low": 1, "medium": 3, "high": 5, "critical": 8}.get(g.urgency.value, 1)
            frequency_score = min(g.frequency, 5)
            novelty_bonus = 2.0 if g.topic[:30] not in " ".join(self._explored_topics[-20:]) else 0.0
            return urgency_score + frequency_score + novelty_bonus
        return sorted(gaps, key=score, reverse=True)

    def _compose_question(self, gap: KnowledgeGap) -> str:
        templates = {
            "capability_missing": "我发现自己还无法处理「{topic}」类的问题，你能教教我吗？或者告诉我应该从哪里学习？",
            "knowledge_missing": "我对「{topic}」还不够了解，能给我一些指导吗？",
            "repeated_failure": "我在处理「{topic}」时反复遇到困难，你能帮我理解问题出在哪里吗？",
            "low_confidence": "我对「{topic}」的回答不够有信心，你能确认一下正确的方向吗？",
        }
        template = templates.get(gap.gap_type, templates["knowledge_missing"])
        return template.format(topic=gap.topic[:50])

    def mark_explored(self, topic: str):
        with self._lock:
            self._explored_topics.append(topic[:50])
            if len(self._explored_topics) > self._max_explored:
                self._explored_topics = self._explored_topics[-self._max_explored:]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            gaps = self._gap_cache
            return {
                "cached_gaps": len(gaps),
                "gap_types": list(set(g.gap_type for g in gaps)),
                "explored_topics": len(self._explored_topics),
                "last_question": self._last_question_time.isoformat() if self._last_question_time else None,
                "can_ask_user": (
                    not self._last_question_time
                    or (datetime.now() - self._last_question_time).total_seconds() >= self.MIN_QUESTION_INTERVAL_SEC
                ),
            }


_curiosity_engine: Optional[CuriosityEngine] = None
_curiosity_lock = threading.Lock()


def get_curiosity_engine() -> CuriosityEngine:
    global _curiosity_engine
    with _curiosity_lock:
        if _curiosity_engine is None:
            _curiosity_engine = CuriosityEngine()
            logger.info("🔍 好奇心引擎已创建 — 系统第一次有了'我想知道'的内在驱动")
    return _curiosity_engine