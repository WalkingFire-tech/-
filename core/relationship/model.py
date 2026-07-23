"""
关系模型 (Relationship Model)

核心理念：系统与用户的关系是动态演化的
- 信任度：用户对系统的信任
- 亲密度：关系的亲密程度
- 理解度：系统对用户的理解
- 互动模式：典型的互动方式

核心能力：
1. 关系状态追踪
2. 信任度演化
3. 互动模式识别
4. 关系预测
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import os
import json
from core.ports.adapters import get_storage_port

try:
    from core.memory.stereo_memory import MemoryImportance
    MEMORY_IMPORTANCE_AVAILABLE = True
except ImportError:
    MEMORY_IMPORTANCE_AVAILABLE = False


class TrustLevel(Enum):
    NONE = 0.0           # 无信任
    LOW = 0.2            # 低信任
    MODERATE = 0.5       # 中等信任
    HIGH = 0.8           # 高信任
    COMPLETE = 1.0       # 完全信任


class InteractionType(Enum):
    QUESTION = "question"        # 提问
    COMMAND = "command"          # 命令
    CONVERSATION = "conversation" # 对话
    FEEDBACK = "feedback"        # 反馈
    CORRECTION = "correction"    # 纠正
    EXPLORATION = "exploration"  # 探索
    COLLABORATION = "collaboration"  # 协作


@dataclass
class InteractionRecord:
    """互动记录"""
    timestamp: datetime
    interaction_type: InteractionType
    user_input: str
    system_response: str
    user_satisfaction: Optional[float] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrustEvolution:
    """信任演化"""
    timestamp: datetime
    old_trust: float
    new_trust: float
    delta: float
    reason: str
    interaction_type: InteractionType


@dataclass
class RelationshipState:
    """关系状态"""
    # 基础维度
    trust_level: float              # 信任度 0-1
    intimacy_level: float           # 亲密度 0-1
    understanding_level: float      # 理解度 0-1
    
    # 互动统计
    total_interactions: int
    positive_interactions: int
    negative_interactions: int
    
    # 模式识别
    preferred_interaction_types: List[InteractionType]
    typical_topics: List[str]
    communication_style: str        # formal, casual, mixed
    
    # 时间维度
    relationship_age_days: float
    last_interaction: datetime
    interaction_frequency: float    # 每天平均互动次数
    
    # 趋势
    trust_trend: str                # improving, stable, declining
    intimacy_trend: str


class RelationshipModel:
    """
    关系模型
    
    追踪系统与用户关系的动态演化
    """
    
    def __init__(self, db_path: str = "data/relationship.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.user_id = "default"
        
        self.interactions: List[InteractionRecord] = []
        self.trust_history: List[TrustEvolution] = []
        
        self._relationship_start = datetime.now()
        
        self._init_database()
        self._load_relationship()
        
        self.state = RelationshipState(
            trust_level=0.5,
            intimacy_level=0.3,
            understanding_level=0.3,
            total_interactions=0,
            positive_interactions=0,
            negative_interactions=0,
            preferred_interaction_types=[],
            typical_topics=[],
            communication_style="mixed",
            relationship_age_days=0.0,
            last_interaction=datetime.now(),
            interaction_frequency=0.0,
            trust_trend="stable",
            intimacy_trend="stable",
        )
    
    def _init_database(self):
        """初始化数据库"""
        db = get_storage_port(self.db_path)
        db.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                interaction_type TEXT,
                user_input TEXT,
                system_response TEXT,
                user_satisfaction REAL,
                context TEXT
            )
        ''')
        
        db.execute('''
            CREATE TABLE IF NOT EXISTS trust_evolution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                old_trust REAL,
                new_trust REAL,
                delta REAL,
                reason TEXT,
                interaction_type TEXT
            )
        ''')
        
        db.execute('''
            CREATE TABLE IF NOT EXISTS relationship_state (
                user_id TEXT PRIMARY KEY,
                trust_level REAL,
                intimacy_level REAL,
                understanding_level REAL,
                total_interactions INTEGER,
                positive_interactions INTEGER,
                negative_interactions INTEGER,
                preferred_types TEXT,
                typical_topics TEXT,
                communication_style TEXT,
                relationship_start TEXT,
                last_interaction TEXT
            )
        ''', commit=True)
    
    def _load_relationship(self):
        """加载关系状态"""
        try:
            db = get_storage_port(self.db_path)
            row = db.query_one(
                "SELECT * FROM relationship_state WHERE user_id = ?",
                (self.user_id,)
            )
            
            if row:
                trust = row['trust_level']
                intimacy = row['intimacy_level']
                understanding = row['understanding_level']
                total = row['total_interactions']
                positive = row['positive_interactions']
                negative = row['negative_interactions']
                preferred_types = row['preferred_types']
                typical_topics = row['typical_topics']
                style = row['communication_style']
                start = row['relationship_start']
                last = row['last_interaction']
                
                if start:
                    self._relationship_start = datetime.fromisoformat(start)
                else:
                    self._relationship_start = datetime.now()
                
                self.state = RelationshipState(
                    trust_level=trust,
                    intimacy_level=intimacy,
                    understanding_level=understanding,
                    total_interactions=total,
                    positive_interactions=positive,
                    negative_interactions=negative,
                    preferred_interaction_types=[
                        InteractionType(t) for t in json.loads(preferred_types)
                    ] if preferred_types else [],
                    typical_topics=json.loads(typical_topics) if typical_topics else [],
                    communication_style=style or "mixed",
                    relationship_age_days=(datetime.now() - self._relationship_start).days,
                    last_interaction=datetime.fromisoformat(last) if last else datetime.now(),
                    interaction_frequency=total / max(1, (datetime.now() - self._relationship_start).days),
                    trust_trend="stable",
                    intimacy_trend="stable",
                )
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
    
    def record_interaction(
        self,
        user_input: str,
        system_response: str,
        interaction_type: InteractionType = InteractionType.CONVERSATION,
        user_satisfaction: float = None,
        context: Dict[str, Any] = None,
    ):
        """
        记录互动
        
        Args:
            user_input: 用户输入
            system_response: 系统响应
            interaction_type: 互动类型
            user_satisfaction: 用户满意度 (0-1)
            context: 上下文
        """
        now = datetime.now()
        
        record = InteractionRecord(
            timestamp=now,
            interaction_type=interaction_type,
            user_input=user_input,
            system_response=system_response,
            user_satisfaction=user_satisfaction,
            context=context or {},
        )
        
        self.interactions.append(record)
        
        self._save_interaction(record)
        
        self._update_relationship_state(record)
        
        self._evolve_trust(record)
    
    def _save_interaction(self, record: InteractionRecord):
        """保存互动记录"""
        db = get_storage_port(self.db_path)
        db.execute('''
            INSERT INTO interactions (
                timestamp, interaction_type, user_input,
                system_response, user_satisfaction, context
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            record.timestamp.isoformat(),
            record.interaction_type.value,
            record.user_input,
            record.system_response,
            record.user_satisfaction,
            json.dumps(record.context),
        ), commit=True)
    
    def _update_relationship_state(self, record: InteractionRecord):
        """更新关系状态"""
        self.state.total_interactions += 1
        self.state.last_interaction = record.timestamp
        
        if record.user_satisfaction is not None:
            if record.user_satisfaction >= 0.7:
                self.state.positive_interactions += 1
            elif record.user_satisfaction < 0.3:
                self.state.negative_interactions += 1
        
        self._update_interaction_patterns()
        
        self._save_state()
    
    def _update_interaction_patterns(self):
        """更新互动模式"""
        if len(self.interactions) < 5:
            return
        
        recent = self.interactions[-50:]
        
        type_counts = {}
        for interaction in recent:
            t = interaction.interaction_type
            type_counts[t] = type_counts.get(t, 0) + 1
        
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        self.state.preferred_interaction_types = [t for t, _ in sorted_types[:3]]
    
    def _evolve_trust(self, record: InteractionRecord):
        """
        信任度演化
        
        根据互动结果调整信任度
        """
        old_trust = self.state.trust_level
        delta = 0.0
        reason = ""
        
        if record.user_satisfaction is not None:
            if record.user_satisfaction >= 0.8:
                delta = 0.02
                reason = "高满意度互动"
            elif record.user_satisfaction >= 0.5:
                delta = 0.005
                reason = "正面互动"
            elif record.user_satisfaction < 0.3:
                delta = -0.05
                reason = "低满意度互动"
            else:
                delta = -0.01
                reason = "负面互动"
        
        if record.interaction_type == InteractionType.CORRECTION:
            delta -= 0.02
            reason = "用户纠正"
        elif record.interaction_type == InteractionType.FEEDBACK:
            delta += 0.01
            reason = "用户反馈"
        
        new_trust = max(0.0, min(1.0, old_trust + delta))
        self.state.trust_level = new_trust
        
        self._update_trends()
        
        evolution = TrustEvolution(
            timestamp=record.timestamp,
            old_trust=old_trust,
            new_trust=new_trust,
            delta=delta,
            reason=reason,
            interaction_type=record.interaction_type,
        )
        
        self.trust_history.append(evolution)
        self._save_trust_evolution(evolution)
    
    def _update_trends(self):
        """更新趋势"""
        if len(self.trust_history) < 5:
            return
        
        recent = self.trust_history[-10:]
        
        trust_deltas = [e.delta for e in recent]
        avg_delta = sum(trust_deltas) / len(trust_deltas)
        
        if avg_delta > 0.005:
            self.state.trust_trend = "improving"
        elif avg_delta < -0.005:
            self.state.trust_trend = "declining"
        else:
            self.state.trust_trend = "stable"
    
    def _save_state(self):
        """保存关系状态"""
        db = get_storage_port(self.db_path)
        db.execute('''
            INSERT OR REPLACE INTO relationship_state (
                user_id, trust_level, intimacy_level, understanding_level,
                total_interactions, positive_interactions, negative_interactions,
                preferred_types, typical_topics, communication_style,
                relationship_start, last_interaction
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.user_id,
            self.state.trust_level,
            self.state.intimacy_level,
            self.state.understanding_level,
            self.state.total_interactions,
            self.state.positive_interactions,
            self.state.negative_interactions,
            json.dumps([t.value for t in self.state.preferred_interaction_types]),
            json.dumps(self.state.typical_topics),
            self.state.communication_style,
            self._relationship_start.isoformat(),
            self.state.last_interaction.isoformat(),
        ), commit=True)
    
    def _save_trust_evolution(self, evolution: TrustEvolution):
        """保存信任演化"""
        db = get_storage_port(self.db_path)
        db.execute('''
            INSERT INTO trust_evolution (
                timestamp, old_trust, new_trust, delta, reason, interaction_type
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            evolution.timestamp.isoformat(),
            evolution.old_trust,
            evolution.new_trust,
            evolution.delta,
            evolution.reason,
            evolution.interaction_type.value,
        ), commit=True)
    
    def get_trust_level(self) -> TrustLevel:
        """获取信任等级"""
        trust = self.state.trust_level
        
        if trust >= 0.9:
            return TrustLevel.COMPLETE
        elif trust >= 0.7:
            return TrustLevel.HIGH
        elif trust >= 0.4:
            return TrustLevel.MODERATE
        elif trust >= 0.2:
            return TrustLevel.LOW
        else:
            return TrustLevel.NONE
    
    def get_relationship_summary(self) -> Dict[str, Any]:
        """获取关系摘要"""
        return {
            "trust_level": self.state.trust_level,
            "trust_grade": self.get_trust_level().value,
            "trust_trend": self.state.trust_trend,
            "intimacy_level": self.state.intimacy_level,
            "intimacy_trend": self.state.intimacy_trend,
            "understanding_level": self.state.understanding_level,
            "total_interactions": self.state.total_interactions,
            "positive_rate": (
                self.state.positive_interactions / self.state.total_interactions
                if self.state.total_interactions > 0 else 0
            ),
            "relationship_age_days": self.state.relationship_age_days,
            "interaction_frequency": self.state.interaction_frequency,
            "preferred_types": [t.value for t in self.state.preferred_interaction_types],
            "communication_style": self.state.communication_style,
        }
    
    def predict_next_interaction_type(self) -> InteractionType:
        """预测下次互动类型"""
        if not self.state.preferred_interaction_types:
            return InteractionType.CONVERSATION
        
        return self.state.preferred_interaction_types[0]
    
    def should_proactive_engage(self) -> bool:
        """
        判断是否应该主动互动
        
        条件：
        1. 信任度足够高
        2. 关系已建立一段时间
        3. 最近没有互动
        """
        if self.state.trust_level < 0.6:
            return False
        
        if self.state.relationship_age_days < 3:
            return False
        
        silence = (datetime.now() - self.state.last_interaction).total_seconds() / 3600
        
        if silence < 1:
            return False
        
        if silence > 24:
            return True
        
        return False
    
    def update_from_conversation(self, conversation_data: Dict) -> Dict:
        """
        根据一次对话更新关系指标（适配样例代码）
        
        conversation_data 应包含：
        - user_satisfaction: 用户满意度 0-1
        - emotional_intensity: 情绪强度 0-1
        - duration_minutes: 对话时长
        - system_helpfulness: 系统帮助程度 0-1
        """
        satisfaction = conversation_data.get("user_satisfaction", 0.5)
        emotional_intensity = conversation_data.get("emotional_intensity", 0.3)
        duration = conversation_data.get("duration_minutes", 5)
        helpfulness = conversation_data.get("system_helpfulness", 0.5)
        
        old_trust = self.state.trust_level
        old_intimacy = self.state.intimacy_level
        
        self.record_interaction(
            interaction_type=InteractionType.CONVERSATION,
            user_input=conversation_data.get("user_input", ""),
            system_response=conversation_data.get("system_response", ""),
            user_satisfaction=satisfaction
        )
        
        return {
            "trust_change": self.state.trust_level - old_trust,
            "intimacy_change": self.state.intimacy_level - old_intimacy,
            "dependency_change": 0.02,
            "impact": satisfaction * 0.5 + helpfulness * 0.5
        }
    
    def get_metrics(self) -> Dict:
        """获取当前指标（适配样例代码）"""
        return {
            "trust": self.state.trust_level,
            "intimacy": self.state.intimacy_level,
            "dependency": 0.3,
            "stability": 0.7,
            "conversation_count": self.state.total_interactions,
            "last_update": self.state.last_interaction.isoformat() if self.state.last_interaction else ""
        }
    
    def get_relationship_phase(self) -> str:
        """获取关系阶段（适配样例代码）"""
        t = self.state.trust_level
        i = self.state.intimacy_level
        
        if t < 0.3:
            return "initial"
        elif t < 0.5 and i < 0.4:
            return "exploratory"
        elif t >= 0.6 and i >= 0.5:
            return "trusted"
        elif t >= 0.7 and i >= 0.6:
            return "close"
        else:
            return "established"


_relationship_model: Optional[RelationshipModel] = None


def get_relationship_model() -> RelationshipModel:
    """获取关系模型单例"""
    global _relationship_model
    if _relationship_model is None:
        _relationship_model = RelationshipModel()
    return _relationship_model