"""
关系积累系统 (Relationship Accumulation System)

实现用户信任度演化和关系深度积累
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
import threading

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.ports.adapters import get_storage_port


class RelationshipStage(Enum):
    STRANGER = "stranger"          # 陌生人：首次接触
    ACQUAINTANCE = "acquaintance"  # 熟人：多次交互
    FRIEND = "friend"              # 朋友：建立信任
    COMPANION = "companion"        # 同行：深度理解
    CONFIDANT = "confidant"        # 知己：完全信任


class InteractionType(Enum):
    QUESTION = "question"          # 提问
    FEEDBACK = "feedback"          # 反馈
    CORRECTION = "correction"      # 纠正
    PRAISE = "praise"              # 赞扬
    CRITICISM = "criticism"        # 批评
    COLLABORATION = "collaboration"  # 协作
    SHARING = "sharing"            # 分享
    CONFLICT = "conflict"          # 冲突


@dataclass
class Interaction:
    """交互记录"""
    interaction_id: str
    user_id: str
    type: InteractionType
    timestamp: datetime
    content: str
    sentiment: float  # -1.0 到 1.0
    impact: float     # 对关系的影响 -1.0 到 1.0
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationshipProfile:
    """关系档案"""
    user_id: str
    stage: RelationshipStage
    trust_score: float          # 0.0 到 1.0
    depth: float                # 0.0 到 1.0 关系深度
    understanding: float        # 0.0 到 1.0 理解程度
    satisfaction_history: List[float] = field(default_factory=list)
    interaction_count: int = 0
    positive_interactions: int = 0
    negative_interactions: int = 0
    first_interaction: datetime = None
    last_interaction: datetime = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    topics_of_interest: List[str] = field(default_factory=list)
    communication_style: Dict[str, float] = field(default_factory=dict)


class RelationshipManager:
    """
    关系积累管理器
    
    职责：
    1. 追踪用户交互历史
    2. 计算信任度演化
    3. 评估关系深度
    4. 识别关系阶段
    5. 个性化适配
    """
    
    def __init__(self, db_path: str = "data/relationships.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._lock = threading.Lock()
        self._init_database()
        
        self.relationships: Dict[str, RelationshipProfile] = {}
        
        self.trust_decay_rate = 0.01
        self.trust_gain_rate = 0.05
        self.trust_loss_rate = 0.15
        
        self.stage_thresholds = {
            RelationshipStage.STRANGER: 0.0,
            RelationshipStage.ACQUAINTANCE: 0.2,
            RelationshipStage.FRIEND: 0.4,
            RelationshipStage.COMPANION: 0.6,
            RelationshipStage.CONFIDANT: 0.8,
        }
        
        logger.info("🤝 关系积累系统已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        db = get_storage_port(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS relationships (
                user_id TEXT PRIMARY KEY,
                stage TEXT NOT NULL,
                trust_score REAL NOT NULL,
                depth REAL NOT NULL,
                understanding REAL NOT NULL,
                satisfaction_history TEXT,
                interaction_count INTEGER DEFAULT 0,
                positive_interactions INTEGER DEFAULT 0,
                negative_interactions INTEGER DEFAULT 0,
                first_interaction TEXT,
                last_interaction TEXT,
                preferences TEXT,
                topics_of_interest TEXT,
                communication_style TEXT
            );

            CREATE TABLE IF NOT EXISTS interactions (
                interaction_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                content TEXT,
                sentiment REAL,
                impact REAL,
                context TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_interactions_time ON interactions(timestamp)
        ''')
    
    def record_interaction(
        self,
        user_id: str,
        interaction_type: InteractionType,
        content: str,
        sentiment: float = 0.0,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """记录交互"""
        import uuid
        interaction_id = f"int_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        impact = self._calculate_impact(interaction_type, sentiment)
        
        interaction = Interaction(
            interaction_id=interaction_id,
            user_id=user_id,
            type=interaction_type,
            timestamp=datetime.now(),
            content=content,
            sentiment=sentiment,
            impact=impact,
            context=context or {},
        )
        
        with self._lock:
            db = get_storage_port(self.db_path)
            db.execute('''
                INSERT INTO interactions
                (interaction_id, user_id, type, timestamp, content, sentiment, impact, context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                interaction_id,
                user_id,
                interaction_type.value,
                interaction.timestamp.isoformat(),
                content,
                sentiment,
                impact,
                json.dumps(context or {}, ensure_ascii=False),
            ), commit=True)
            
            self._update_relationship(user_id, interaction)
        
        logger.debug(f"记录交互: {interaction_id} (用户: {user_id}, 类型: {interaction_type.value})")
        return interaction_id
    
    def _calculate_impact(self, interaction_type: InteractionType, sentiment: float) -> float:
        """计算交互影响"""
        type_impacts = {
            InteractionType.PRAISE: 0.3,
            InteractionType.COLLABORATION: 0.2,
            InteractionType.SHARING: 0.15,
            InteractionType.QUESTION: 0.05,
            InteractionType.FEEDBACK: 0.1,
            InteractionType.CORRECTION: -0.1,
            InteractionType.CRITICISM: -0.2,
            InteractionType.CONFLICT: -0.3,
        }
        
        base_impact = type_impacts.get(interaction_type, 0.0)
        sentiment_factor = 1.0 + sentiment * 0.5
        
        return base_impact * sentiment_factor
    
    def _update_relationship(self, user_id: str, interaction: Interaction):
        """更新关系状态"""
        profile = self.get_relationship(user_id)
        
        if profile.first_interaction is None:
            profile.first_interaction = interaction.timestamp
        profile.last_interaction = interaction.timestamp
        
        profile.interaction_count += 1
        
        if interaction.impact > 0:
            profile.positive_interactions += 1
            trust_delta = self.trust_gain_rate * interaction.impact
        else:
            profile.negative_interactions += 1
            trust_delta = self.trust_loss_rate * interaction.impact
        
        profile.trust_score = max(0.0, min(1.0, profile.trust_score + trust_delta))
        
        profile.depth = min(1.0, profile.depth + 0.01)
        
        if interaction.sentiment != 0:
            profile.satisfaction_history.append(interaction.sentiment)
            if len(profile.satisfaction_history) > 100:
                profile.satisfaction_history = profile.satisfaction_history[-100:]
        
        profile.stage = self._determine_stage(profile)
        
        self._save_relationship(profile)
        self.relationships[user_id] = profile
    
    def _determine_stage(self, profile: RelationshipProfile) -> RelationshipStage:
        """确定关系阶段"""
        combined_score = (
            profile.trust_score * 0.4 +
            profile.depth * 0.3 +
            profile.understanding * 0.3
        )
        
        for stage, threshold in sorted(
            self.stage_thresholds.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if combined_score >= threshold:
                return stage
        
        return RelationshipStage.STRANGER
    
    def get_relationship(self, user_id: str) -> RelationshipProfile:
        """获取关系档案"""
        if user_id in self.relationships:
            return self.relationships[user_id]
        
        db = get_storage_port(self.db_path)
        row = db.query_one(
            'SELECT * FROM relationships WHERE user_id = ?',
            (user_id,)
        )
        
        if row:
            profile = RelationshipProfile(
                user_id=row[0],
                stage=RelationshipStage(row[1]),
                trust_score=row[2],
                depth=row[3],
                understanding=row[4],
                satisfaction_history=json.loads(row[5]) if row[5] else [],
                interaction_count=row[6],
                positive_interactions=row[7],
                negative_interactions=row[8],
                first_interaction=datetime.fromisoformat(row[9]) if row[9] else None,
                last_interaction=datetime.fromisoformat(row[10]) if row[10] else None,
                preferences=json.loads(row[11]) if row[11] else {},
                topics_of_interest=json.loads(row[12]) if row[12] else [],
                communication_style=json.loads(row[13]) if row[13] else {},
            )
            self.relationships[user_id] = profile
            return profile
        
        profile = RelationshipProfile(
            user_id=user_id,
            stage=RelationshipStage.STRANGER,
            trust_score=0.5,
            depth=0.0,
            understanding=0.0,
        )
        self.relationships[user_id] = profile
        return profile
    
    def _save_relationship(self, profile: RelationshipProfile):
        """保存关系档案"""
        db = get_storage_port(self.db_path)
        db.execute('''
            INSERT OR REPLACE INTO relationships
            (user_id, stage, trust_score, depth, understanding,
             satisfaction_history, interaction_count, positive_interactions,
             negative_interactions, first_interaction, last_interaction,
             preferences, topics_of_interest, communication_style)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            profile.user_id,
            profile.stage.value,
            profile.trust_score,
            profile.depth,
            profile.understanding,
            json.dumps(profile.satisfaction_history),
            profile.interaction_count,
            profile.positive_interactions,
            profile.negative_interactions,
            profile.first_interaction.isoformat() if profile.first_interaction else None,
            profile.last_interaction.isoformat() if profile.last_interaction else None,
            json.dumps(profile.preferences, ensure_ascii=False),
            json.dumps(profile.topics_of_interest, ensure_ascii=False),
            json.dumps(profile.communication_style),
        ), commit=True)
    
    def update_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
        topics: Optional[List[str]] = None,
    ):
        """更新用户偏好"""
        profile = self.get_relationship(user_id)
        
        for key, value in preferences.items():
            profile.preferences[key] = value
        
        if topics:
            for topic in topics:
                if topic not in profile.topics_of_interest:
                    profile.topics_of_interest.append(topic)
        
        self._save_relationship(profile)
        self.relationships[user_id] = profile
    
    def get_personalized_context(self, user_id: str) -> Dict[str, Any]:
        """获取个性化上下文"""
        profile = self.get_relationship(user_id)
        
        return {
            "trust_level": profile.trust_score,
            "relationship_stage": profile.stage.value,
            "depth": profile.depth,
            "understanding": profile.understanding,
            "preferences": profile.preferences,
            "topics": profile.topics_of_interest,
            "communication_style": profile.communication_style,
            "interaction_count": profile.interaction_count,
            "positive_ratio": (
                profile.positive_interactions / profile.interaction_count
                if profile.interaction_count > 0 else 0.5
            ),
        }
    
    def should_be_proactive(self, user_id: str) -> bool:
        """判断是否应该主动"""
        profile = self.get_relationship(user_id)
        
        if profile.stage in [RelationshipStage.COMPANION, RelationshipStage.CONFIDANT]:
            return True
        
        if profile.trust_score > 0.6 and profile.interaction_count > 10:
            return True
        
        if profile.last_interaction:
            days_since = (datetime.now() - profile.last_interaction).days
            if days_since > 7 and profile.trust_score > 0.4:
                return True
        
        return False
    
    def get_relationship_summary(self, user_id: str) -> str:
        """获取关系摘要"""
        profile = self.get_relationship(user_id)
        
        stage_names = {
            RelationshipStage.STRANGER: "陌生人",
            RelationshipStage.ACQUAINTANCE: "熟人",
            RelationshipStage.FRIEND: "朋友",
            RelationshipStage.COMPANION: "同行者",
            RelationshipStage.CONFIDANT: "知己",
        }
        
        summary = f"关系阶段: {stage_names[profile.stage]}\n"
        summary += f"信任度: {profile.trust_score:.2f}\n"
        summary += f"深度: {profile.depth:.2f}\n"
        summary += f"交互次数: {profile.interaction_count}\n"
        
        if profile.interaction_count > 0:
            positive_ratio = profile.positive_interactions / profile.interaction_count
            summary += f"正面交互比例: {positive_ratio:.1%}\n"
        
        return summary
    
    def get_all_relationships(self) -> List[Dict[str, Any]]:
        """获取所有关系"""
        db = get_storage_port(self.db_path)
        rows = db.query('''
            SELECT user_id, stage, trust_score, depth, interaction_count, last_interaction
            FROM relationships
            ORDER BY trust_score DESC
        ''')
        
        relationships = []
        for row in rows:
            relationships.append({
                "user_id": row[0],
                "stage": row[1],
                "trust_score": row[2],
                "depth": row[3],
                "interaction_count": row[4],
                "last_interaction": row[5],
            })
        
        return relationships
    
    def decay_trust(self):
        """信任度衰减（时间因素）"""
        with self._lock:
            db = get_storage_port(self.db_path)
            rows = db.query('SELECT user_id, trust_score FROM relationships')
            
            for row in rows:
                user_id, trust = row
                new_trust = max(0.5, trust - self.trust_decay_rate)
                
                db.execute(
                    'UPDATE relationships SET trust_score = ? WHERE user_id = ?',
                    (new_trust, user_id),
                    commit=True
                )
        
        logger.debug("信任度衰减完成")


relationship_manager = RelationshipManager()
