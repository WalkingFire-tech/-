"""
主动性引擎 (Proactivity Engine)

核心理念：系统不是被动等待，而是主动感知和行动
- 在合适时机主动开口
- 在用户沉默时主动感知
- 在发现机会时主动建议

核心能力：
1. 时机判断 - 何时应该主动
2. 主动性触发 - 基于关系状态和上下文
3. 非打扰式互动 - 尊重用户节奏
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum


class ProactivityType(Enum):
    GREETING = "greeting"              # 问候
    SUGGESTION = "suggestion"          # 建议
    REMINDER = "reminder"              # 提醒
    FOLLOW_UP = "follow_up"            # 跟进
    INSIGHT_SHARING = "insight"        # 分享洞察
    LEARNING_UPDATE = "learning"       # 学习更新


class ProactivityLevel(Enum):
    PASSIVE = 0          # 被动：仅在用户输入时响应
    LOW = 1              # 低：偶尔主动
    MODERATE = 2         # 中：适度主动
    HIGH = 3             # 高：积极主动
    PROACTIVE = 4        # 超主动：持续主动


@dataclass
class ProactivityContext:
    """主动性上下文"""
    user_silence_duration: float       # 用户沉默时长（秒）
    relationship_trust: float          # 关系信任度
    recent_interactions: int           # 最近互动次数
    last_proactivity_time: datetime    # 上次主动时间
    user_engagement_level: float       # 用户参与度


@dataclass
class ProactivityDecision:
    """主动性决策"""
    should_act: bool
    action_type: Optional[ProactivityType]
    content: Optional[str]
    reason: str
    confidence: float
    timing_score: float


class ProactivityEngine:
    """
    主动性引擎
    
    让系统能够在合适时机主动行动
    """
    
    def __init__(self):
        self.level = ProactivityLevel.MODERATE
        self.last_proactivity: Optional[datetime] = None
        self.proactivity_history: List[Dict[str, Any]] = []
        
        self.min_silence_for_greeting = 3600       # 1小时
        self.min_silence_for_suggestion = 1800     # 30分钟
        self.min_silence_for_follow_up = 7200      # 2小时
        
        self.min_trust_for_proactivity = 0.6
        self.max_proactivity_frequency = 0.25      # 每小时最多1次
        
        self.proactivity_rules: List[Callable] = []
        self._setup_default_rules()
        
        self.stats = {
            "total_proactivities": 0,
            "successful_proactivities": 0,
            "by_type": {t.value: 0 for t in ProactivityType},
        }
    
    def _setup_default_rules(self):
        """设置默认规则"""
        self.proactivity_rules = [
            self._rule_long_silence_greeting,
            self._rule_follow_up_unfinished,
            self._rule_share_insight,
            self._rule_learning_update,
        ]
    
    def evaluate(
        self,
        context: ProactivityContext,
    ) -> ProactivityDecision:
        """
        评估是否应该主动行动
        
        Args:
            context: 主动性上下文
        
        Returns:
            主动性决策
        """
        if self.level == ProactivityLevel.PASSIVE:
            return ProactivityDecision(
                should_act=False,
                action_type=None,
                content=None,
                reason="被动模式",
                confidence=0.0,
                timing_score=0.0,
            )
        
        if context.relationship_trust < self.min_trust_for_proactivity:
            return ProactivityDecision(
                should_act=False,
                action_type=None,
                content=None,
                reason="信任度不足",
                confidence=0.0,
                timing_score=0.0,
            )
        
        if self._too_frequent(context):
            return ProactivityDecision(
                should_act=False,
                action_type=None,
                content=None,
                reason="主动频率过高",
                confidence=0.0,
                timing_score=0.0,
            )
        
        candidates = []
        for rule in self.proactivity_rules:
            decision = rule(context)
            if decision.should_act:
                candidates.append(decision)
        
        if not candidates:
            return ProactivityDecision(
                should_act=False,
                action_type=None,
                content=None,
                reason="无合适的主动行动",
                confidence=0.0,
                timing_score=0.0,
            )
        
        candidates.sort(key=lambda d: d.timing_score * d.confidence, reverse=True)
        
        return candidates[0]
    
    def _too_frequent(self, context: ProactivityContext) -> bool:
        """检查是否过于频繁"""
        if not self.last_proactivity:
            return False
        
        time_since_last = (datetime.now() - self.last_proactivity).total_seconds() / 3600
        
        max_per_hour = self.max_proactivity_frequency * (self.level.value + 1)
        
        return time_since_last < (1.0 / max_per_hour)
    
    def _rule_long_silence_greeting(
        self,
        context: ProactivityContext,
    ) -> ProactivityDecision:
        """规则：长时间沉默后问候"""
        silence = context.user_silence_duration
        
        threshold = self.min_silence_for_greeting / (self.level.value + 1)
        
        if silence >= threshold and context.relationship_trust >= 0.7:
            timing_score = min(1.0, silence / threshold / 2)
            content = self._get_dynamic_content("greeting", f"用户沉默{silence/60:.0f}分钟")
            return ProactivityDecision(
                should_act=True,
                action_type=ProactivityType.GREETING,
                content=content,
                reason=f"用户沉默{silence/60:.0f}分钟",
                confidence=context.relationship_trust,
                timing_score=timing_score,
            )
        
        return ProactivityDecision(
            should_act=False,
            action_type=None,
            content=None,
            reason="",
            confidence=0.0,
            timing_score=0.0,
        )
    
    def _rule_follow_up_unfinished(
        self,
        context: ProactivityContext,
    ) -> ProactivityDecision:
        """规则：跟进未完成事项"""
        if context.user_silence_duration < self.min_silence_for_follow_up:
            return ProactivityDecision(
                should_act=False,
                action_type=None,
                content=None,
                reason="",
                confidence=0.0,
                timing_score=0.0,
            )
        
        content = self._get_dynamic_content("follow_up", "跟进上次对话")
        return ProactivityDecision(
            should_act=True,
            action_type=ProactivityType.FOLLOW_UP,
            content=content,
            reason="跟进上次对话",
            confidence=0.6,
            timing_score=0.7,
        )
    
    def _rule_share_insight(
        self,
        context: ProactivityContext,
    ) -> ProactivityDecision:
        """规则：分享洞察"""
        if context.user_silence_duration < self.min_silence_for_suggestion:
            return ProactivityDecision(
                should_act=False,
                action_type=None,
                content=None,
                reason="",
                confidence=0.0,
                timing_score=0.0,
            )
        
        if context.relationship_trust < 0.8:
            return ProactivityDecision(
                should_act=False,
                action_type=None,
                content=None,
                reason="",
                confidence=0.0,
                timing_score=0.0,
            )
        
        content = self._get_dynamic_content("insight", "发现新洞察")
        return ProactivityDecision(
            should_act=True,
            action_type=ProactivityType.INSIGHT_SHARING,
            content=content,
            reason="发现新洞察",
            confidence=0.7,
            timing_score=0.8,
        )
    
    def _rule_learning_update(
        self,
        context: ProactivityContext,
    ) -> ProactivityDecision:
        """规则：学习更新"""
        if context.user_silence_duration < 7200:
            return ProactivityDecision(
                should_act=False,
                action_type=None,
                content=None,
                reason="",
                confidence=0.0,
                timing_score=0.0,
            )
        
        content = self._get_dynamic_content("learning", "学习进展")
        return ProactivityDecision(
            should_act=True,
            action_type=ProactivityType.LEARNING_UPDATE,
            content=content,
            reason="学习进展",
            confidence=0.6,
            timing_score=0.6,
        )
    
    def _get_dynamic_content(self, action_type: str, fallback_reason: str) -> str:
        try:
            if action_type == "greeting":
                import sqlite3
                conn = sqlite3.connect("data/experience_pool.db")
                cur = conn.execute(
                    "SELECT raw_input FROM experiences WHERE intent_type != 'proactivity' ORDER BY timestamp DESC LIMIT 1"
                )
                row = cur.fetchone()
                conn.close()
                if row and row[0]:
                    topic = row[0][:40]
                    return f"好久不见！上次我们聊到了「{topic}」，还想继续吗？"
                return "好久不见，有什么我可以帮助你的吗？"

            elif action_type == "follow_up":
                import sqlite3
                conn = sqlite3.connect("data/experience_pool.db")
                cur = conn.execute(
                    "SELECT raw_input, response FROM experiences WHERE intent_type != 'proactivity' AND quality_score >= 50 ORDER BY timestamp DESC LIMIT 1"
                )
                row = cur.fetchone()
                conn.close()
                if row and row[0]:
                    return f"之前我们讨论的「{row[0][:30]}」，你有什么新的想法吗？"
                return "之前我们讨论的事情，你有什么新的想法吗？"

            elif action_type == "insight":
                from core.knowledge_graph import get_knowledge_graph
                kg = get_knowledge_graph()
                clusters = kg.find_clusters()
                if clusters and len(clusters) > 0:
                    largest = max(clusters, key=lambda c: len(c.node_ids))
                    nodes = [kg.get_node(nid) for nid in largest.node_ids[:3]]
                    names = [n.content[:15] for n in nodes if n]
                    if names:
                        return f"我发现「{'」和「'.join(names)}」之间有有趣的关联，想和你聊聊。"
                return "我在思考中发现了有趣的模式，想和你分享。"

            elif action_type == "learning":
                import sqlite3
                conn = sqlite3.connect("data/truths.db")
                cur = conn.execute(
                    "SELECT content FROM truths ORDER BY created_at DESC LIMIT 1"
                )
                row = cur.fetchone()
                conn.close()
                if row and row[0]:
                    return f"我最近领悟到：{row[0][:60]}，可能对你有帮助。"
                return "我最近学到了一些新东西，可能对你有帮助。"

        except Exception:
            pass
        return fallback_reason
    def execute(
        self,
        decision: ProactivityDecision,
    ) -> Dict[str, Any]:
        """
        执行主动性决策
        
        Returns:
            执行结果
        """
        if not decision.should_act:
            return {"executed": False}
        
        self.last_proactivity = datetime.now()
        self.stats["total_proactivities"] += 1
        self.stats["by_type"][decision.action_type.value] += 1
        
        record = {
            "timestamp": self.last_proactivity.isoformat(),
            "type": decision.action_type.value,
            "content": decision.content,
            "reason": decision.reason,
            "confidence": decision.confidence,
        }
        
        self.proactivity_history.append(record)
        if len(self.proactivity_history) > 100:
            self.proactivity_history = self.proactivity_history[-50:]
        
        return {
            "executed": True,
            "type": decision.action_type.value,
            "content": decision.content,
            "reason": decision.reason,
        }
    
    def record_feedback(self, success: bool):
        """记录反馈"""
        if success:
            self.stats["successful_proactivities"] += 1
    
    def set_level(self, level: ProactivityLevel):
        """设置主动性等级"""
        self.level = level
    
    def add_rule(self, rule: Callable):
        """添加自定义规则"""
        self.proactivity_rules.append(rule)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        success_rate = (
            self.stats["successful_proactivities"] / self.stats["total_proactivities"]
            if self.stats["total_proactivities"] > 0 else 0
        )
        
        return {
            "level": self.level.value,
            "total_proactivities": self.stats["total_proactivities"],
            "successful_proactivities": self.stats["successful_proactivities"],
            "success_rate": success_rate,
            "by_type": self.stats["by_type"],
        }


def get_proactivity_engine() -> ProactivityEngine:
    """获取主动性引擎单例"""
    global _proactivity_engine
    if '_proactivity_engine' not in globals():
        _proactivity_engine = ProactivityEngine()
    return _proactivity_engine