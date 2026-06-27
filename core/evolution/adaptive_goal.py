"""
自适应进化目标 (Adaptive Evolution Goal)

核心理念：进化方向不是预设的，而是从互动中学习
- 系统从用户反馈中推断价值
- 自动调整进化方向
- 形成自己的成长路径

核能力：
1. 价值推断 - 从互动中学习用户看重什么（语义级分析）
2. 目标调整 - 动态调整进化目标（趋势感知）
3. 进度追踪 - 追踪进化进度
4. 持久化存储 - 重启不丢失
5. L5集成 - 真正驱动进化

修复记录：
- P1: 语义级价值推断（多层级规则）
- P2: SQLite持久化存储
- P3: 趋势感知的目标调整
- P4: L5进化层集成
- P5: 配置化映射表
- P7: 规范单例实现
"""

import sqlite3
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from collections import deque

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class EvolutionDimension(Enum):
    ACCURACY = "accuracy"
    SPEED = "speed"
    CREATIVITY = "creativity"
    EMPATHY = "empathy"
    KNOWLEDGE = "knowledge"
    SKILL = "skill"
    RELIABILITY = "reliability"


class GoalPriority(Enum):
    CRITICAL = 1.0
    HIGH = 0.8
    MEDIUM = 0.5
    LOW = 0.3


@dataclass
class EvolutionGoal:
    dimension: EvolutionDimension
    target_value: float
    current_value: float
    priority: GoalPriority
    source: str
    created_at: datetime
    updated_at: datetime
    progress_history: List[float] = field(default_factory=list)
    
    @property
    def progress(self) -> float:
        if self.target_value == 0:
            return 0.0
        return min(1.0, self.current_value / self.target_value)
    
    @property
    def gap(self) -> float:
        return max(0.0, self.target_value - self.current_value)


@dataclass
class ValueInference:
    dimension: EvolutionDimension
    inferred_value: float
    evidence_count: int
    evidence_sources: List[str]
    confidence: float
    trend: str = "stable"


class AdaptiveEvolutionGoal:
    """
    自适应进化目标
    
    从互动中学习进化方向，真正驱动系统进化
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self._db_path = Path("data/evolution_goals.db")
        self.goals: Dict[EvolutionDimension, EvolutionGoal] = {}
        self.value_inferences: Dict[EvolutionDimension, ValueInference] = {}
        self.feedback_history: deque = deque(maxlen=1000)
        
        self._config = config or self._get_default_config()
        
        self._init_database()
        self._load_from_database()
        
        if not self.goals:
            self._init_default_goals()
        
        self.stats = {
            "total_adjustments": 0,
            "total_progress": 0.0,
            "goals_achieved": 0,
            "evolutions_triggered": 0,
        }
        
        logger.info("🎯 自适应进化目标系统已初始化")
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "dimension_keywords": {
                EvolutionDimension.ACCURACY: {
                    "positive": ["准确", "精确", "精准", "正确", "对", "没错", 
                                "correct", "accurate", "precise", "right"],
                    "negative": ["错误", "偏差", "不准确", "不对", "错", 
                                "wrong", "incorrect", "inaccurate"]
                },
                EvolutionDimension.SPEED: {
                    "positive": ["快速", "及时", "迅速", "快", "效率高",
                                "fast", "quick", "prompt", "efficient"],
                    "negative": ["慢", "延迟", "缓慢", "拖沓", "效率低",
                                "slow", "delayed", "lag"]
                },
                EvolutionDimension.CREATIVITY: {
                    "positive": ["创意", "创新", "新颖", "独特", "有想法",
                                "creative", "innovative", "novel", "unique"],
                    "negative": ["老套", "陈旧", "缺乏创意", "平庸",
                                "boring", "dull", "uncreative"]
                },
                EvolutionDimension.EMPATHY: {
                    "positive": ["理解", "同理心", "体贴", "关心", "懂我",
                                "empathetic", "understanding", "caring"],
                    "negative": ["冷漠", "不理解", "不关心", "机械",
                                "cold", "indifferent", "robotic"]
                },
                EvolutionDimension.KNOWLEDGE: {
                    "positive": ["知识渊博", "懂得多", "专业", "博学",
                                "knowledgeable", "expert", "professional"],
                    "negative": ["知识不足", "不专业", "外行",
                                "ignorant", "unprofessional"]
                },
                EvolutionDimension.SKILL: {
                    "positive": ["技能熟练", "能力强", "擅长", "精通",
                                "skilled", "proficient", "expert"],
                    "negative": ["技能不足", "不熟练", "生疏",
                                "unskilled", "inexperienced"]
                },
                EvolutionDimension.RELIABILITY: {
                    "positive": ["可靠", "稳定", "可信赖", "靠谱",
                                "reliable", "stable", "trustworthy"],
                    "negative": ["不可靠", "不稳定", "不可信",
                                "unreliable", "unstable"]
                }
            },
            "sentiment_words": {
                "positive": ["好", "优秀", "很棒", "不错", "满意", "喜欢", 
                            "great", "good", "excellent", "nice", "love"],
                "negative": ["差", "不好", "糟糕", "不满", "失望", "讨厌",
                            "bad", "poor", "terrible", "awful", "hate"]
            },
            "intensity_words": {
                "strong": ["非常", "极其", "特别", "很", "really", "very", "extremely"],
                "medium": ["比较", "挺", "还", "quite", "fairly"],
                "weak": ["有点", "稍微", "略微", "slightly", "a little"]
            },
            "negation_words": ["不", "没", "无", "not", "no", "never"],
            "adjustment_config": {
                "base_rate": 0.3,
                "confidence_threshold": 0.5,
                "min_evidence_for_adjustment": 5,
            }
        }
    
    def _init_database(self):
        """初始化数据库"""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS evolution_goals (
                        dimension TEXT PRIMARY KEY,
                        target_value REAL,
                        current_value REAL,
                        priority TEXT,
                        source TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        progress_history TEXT
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS value_inferences (
                        dimension TEXT PRIMARY KEY,
                        inferred_value REAL,
                        evidence_count INTEGER,
                        evidence_sources TEXT,
                        confidence REAL,
                        trend TEXT,
                        updated_at TEXT
                    )
                ''')
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS feedback_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        satisfaction REAL,
                        praised TEXT,
                        criticized TEXT,
                        raw_feedback TEXT
                    )
                ''')
                conn.commit()
            logger.debug("进化目标数据库初始化成功")
        except Exception as e:
            logger.warning(f"进化目标数据库初始化失败: {e}")
    
    def _load_from_database(self):
        """从数据库加载数据"""
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                cursor = conn.execute('''
                    SELECT dimension, target_value, current_value, priority,
                           source, created_at, updated_at, progress_history
                    FROM evolution_goals
                ''')
                
                for row in cursor:
                    dim = EvolutionDimension(row[0])
                    self.goals[dim] = EvolutionGoal(
                        dimension=dim,
                        target_value=row[1],
                        current_value=row[2],
                        priority=GoalPriority[row[3]],
                        source=row[4],
                        created_at=datetime.fromisoformat(row[5]),
                        updated_at=datetime.fromisoformat(row[6]),
                        progress_history=json.loads(row[7]) if row[7] else []
                    )
                
                cursor = conn.execute('''
                    SELECT dimension, inferred_value, evidence_count,
                           evidence_sources, confidence, trend
                    FROM value_inferences
                ''')
                
                for row in cursor:
                    dim = EvolutionDimension(row[0])
                    self.value_inferences[dim] = ValueInference(
                        dimension=dim,
                        inferred_value=row[1],
                        evidence_count=row[2],
                        evidence_sources=json.loads(row[3]) if row[3] else [],
                        confidence=row[4],
                        trend=row[5] or "stable"
                    )
            
            logger.debug(f"从数据库加载了 {len(self.goals)} 个目标, {len(self.value_inferences)} 个推断")
        except Exception as e:
            logger.warning(f"从数据库加载失败: {e}")
    
    def _save_goal_to_db(self, goal: EvolutionGoal):
        """保存目标到数据库"""
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO evolution_goals
                    (dimension, target_value, current_value, priority, source,
                     created_at, updated_at, progress_history)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    goal.dimension.value,
                    goal.target_value,
                    goal.current_value,
                    goal.priority.name,
                    goal.source,
                    goal.created_at.isoformat(),
                    goal.updated_at.isoformat(),
                    json.dumps(goal.progress_history[-100:])
                ))
                conn.commit()
        except Exception as e:
            logger.debug(f"保存目标失败: {e}")
    
    def _save_inference_to_db(self, inference: ValueInference):
        """保存推断到数据库"""
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO value_inferences
                    (dimension, inferred_value, evidence_count, evidence_sources,
                     confidence, trend, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    inference.dimension.value,
                    inference.inferred_value,
                    inference.evidence_count,
                    json.dumps(inference.evidence_sources),
                    inference.confidence,
                    inference.trend,
                    datetime.now().isoformat()
                ))
                conn.commit()
        except Exception as e:
            logger.debug(f"保存推断失败: {e}")
    
    def _init_default_goals(self):
        """初始化默认目标"""
        default_goals = [
            (EvolutionDimension.ACCURACY, 0.9, GoalPriority.HIGH),
            (EvolutionDimension.RELIABILITY, 0.85, GoalPriority.HIGH),
            (EvolutionDimension.KNOWLEDGE, 0.7, GoalPriority.MEDIUM),
            (EvolutionDimension.EMPATHY, 0.6, GoalPriority.MEDIUM),
            (EvolutionDimension.SPEED, 0.7, GoalPriority.LOW),
        ]
        
        now = datetime.now()
        
        for dimension, target, priority in default_goals:
            goal = EvolutionGoal(
                dimension=dimension,
                target_value=target,
                current_value=0.5,
                priority=priority,
                source="default",
                created_at=now,
                updated_at=now,
            )
            self.goals[dimension] = goal
            self._save_goal_to_db(goal)
        
        logger.info(f"初始化了 {len(default_goals)} 个默认目标")
    
    def infer_value_from_feedback(
        self,
        feedback: Dict[str, Any],
    ):
        """
        从反馈中推断价值（语义级分析）
        
        修复P1: 多层级语义分析
        """
        satisfaction = feedback.get("satisfaction", 0.5)
        praised = feedback.get("praised_aspects", [])
        criticized = feedback.get("criticized_aspects", [])
        raw_feedback = feedback.get("raw_text", "")
        
        semantic_results = self._analyze_feedback_semantic(raw_feedback)
        
        for dimension, score in semantic_results.items():
            self._update_value_inference(
                dimension,
                value=score,
                source="semantic_analysis",
            )
        
        for aspect in praised:
            dimension = self._map_aspect_to_dimension(aspect)
            if dimension:
                self._update_value_inference(
                    dimension,
                    value=0.15,
                    source="user_praise",
                )
        
        for aspect in criticized:
            dimension = self._map_aspect_to_dimension(aspect)
            if dimension:
                self._update_value_inference(
                    dimension,
                    value=-0.15,
                    source="user_criticism",
                )
        
        fb_record = {
            "timestamp": datetime.now().isoformat(),
            "satisfaction": satisfaction,
            "praised": praised,
            "criticized": criticized,
            "raw_feedback": raw_feedback,
        }
        self.feedback_history.append(fb_record)
        self._save_feedback_to_db(fb_record)
        
        if len(self.feedback_history) % 5 == 0:
            self._adjust_goals_from_inferences()
    
    def _analyze_feedback_semantic(self, feedback: str) -> Dict[EvolutionDimension, float]:
        """
        语义级反馈分析（多层级规则）
        
        修复P1: 增强价值推断能力
        """
        if not feedback:
            return {}
        
        result = {}
        feedback_lower = feedback.lower()
        
        dimension_keywords = self._config["dimension_keywords"]
        intensity_words = self._config["intensity_words"]
        negation_words = self._config["negation_words"]
        
        intensity = self._get_intensity(feedback_lower)
        
        for dimension, keywords in dimension_keywords.items():
            positive_score = 0
            negative_score = 0
            
            for word in keywords["positive"]:
                if word in feedback_lower:
                    word_pos = feedback_lower.find(word)
                    has_negation = any(
                        neg in feedback_lower[max(0, word_pos-10):word_pos]
                        for neg in negation_words
                    )
                    
                    if has_negation:
                        negative_score += 1
                    else:
                        positive_score += 1
            
            for word in keywords["negative"]:
                if word in feedback_lower:
                    word_pos = feedback_lower.find(word)
                    has_negation = any(
                        neg in feedback_lower[max(0, word_pos-10):word_pos]
                        for neg in negation_words
                    )
                    
                    if has_negation:
                        positive_score += 1
                    else:
                        negative_score += 1
            
            if positive_score > 0 or negative_score > 0:
                total = positive_score + negative_score
                raw_score = (positive_score - negative_score) / max(total, 1)
                result[dimension] = raw_score * intensity
        
        return result
    
    def _get_intensity(self, text: str) -> float:
        """获取程度词强度"""
        intensity_words = self._config["intensity_words"]
        
        for word in intensity_words["strong"]:
            if word in text:
                return 1.5
        
        for word in intensity_words["medium"]:
            if word in text:
                return 1.0
        
        for word in intensity_words["weak"]:
            if word in text:
                return 0.5
        
        return 1.0
    
    def _map_aspect_to_dimension(self, aspect: str) -> Optional[EvolutionDimension]:
        """映射方面到维度（使用配置）"""
        aspect_lower = aspect.lower()
        
        for dimension, keywords in self._config["dimension_keywords"].items():
            all_words = keywords["positive"] + keywords["negative"]
            for word in all_words:
                if word in aspect_lower:
                    return dimension
        
        return None
    
    def _update_value_inference(
        self,
        dimension: EvolutionDimension,
        value: float,
        source: str,
    ):
        """更新价值推断"""
        if dimension not in self.value_inferences:
            self.value_inferences[dimension] = ValueInference(
                dimension=dimension,
                inferred_value=0.5,
                evidence_count=0,
                evidence_sources=[],
                confidence=0.0,
                trend="stable",
            )
        
        inference = self.value_inferences[dimension]
        
        old_value = inference.inferred_value
        count = inference.evidence_count
        
        inference.inferred_value = (old_value * count + (value + 0.5)) / (count + 1)
        inference.inferred_value = max(0.0, min(1.0, inference.inferred_value))
        inference.evidence_count += 1
        
        if source not in inference.evidence_sources:
            inference.evidence_sources.append(source)
        
        inference.confidence = min(1.0, inference.evidence_count / 20)
        
        if len(inference.evidence_sources) >= 3:
            inference.trend = self._calculate_dimension_trend(dimension)
        
        self._save_inference_to_db(inference)
    
    def _calculate_dimension_trend(self, dimension: EvolutionDimension) -> str:
        """计算维度的变化趋势"""
        recent_feedbacks = list(self.feedback_history)[-20:]
        
        if len(recent_feedbacks) < 5:
            return "stable"
        
        scores = []
        for fb in recent_feedbacks:
            raw = fb.get("raw_feedback", "")
            if raw:
                semantic = self._analyze_feedback_semantic(raw)
                if dimension in semantic:
                    scores.append(semantic[dimension])
        
        if len(scores) < 3:
            return "stable"
        
        first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
        second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
        
        if second_half > first_half + 0.1:
            return "increasing"
        elif second_half < first_half - 0.1:
            return "decreasing"
        else:
            return "stable"
    
    def _adjust_goals_from_inferences(self):
        """
        根据推断调整目标（趋势感知）
        
        修复P3: 引入置信度加权和趋势感知
        """
        config = self._config["adjustment_config"]
        base_rate = config["base_rate"]
        confidence_threshold = config["confidence_threshold"]
        min_evidence = config["min_evidence_for_adjustment"]
        
        for dimension, inference in self.value_inferences.items():
            if inference.confidence < confidence_threshold:
                continue
            
            if inference.evidence_count < min_evidence:
                continue
            
            if dimension not in self.goals:
                goal = EvolutionGoal(
                    dimension=dimension,
                    target_value=inference.inferred_value,
                    current_value=0.5,
                    priority=GoalPriority.MEDIUM,
                    source="auto",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                self.goals[dimension] = goal
            else:
                goal = self.goals[dimension]
                
                base_adjustment = (inference.inferred_value - goal.target_value) * base_rate
                
                confidence_weight = inference.confidence
                
                trend_weights = {
                    "increasing": 1.2,
                    "stable": 1.0,
                    "decreasing": 0.7
                }
                trend_weight = trend_weights.get(inference.trend, 1.0)
                
                adjustment = base_adjustment * confidence_weight * trend_weight
                
                goal.target_value = max(0.0, min(1.0, goal.target_value + adjustment))
                goal.updated_at = datetime.now()
                
                if inference.inferred_value > 0.7:
                    goal.priority = GoalPriority.HIGH
                elif inference.inferred_value > 0.5:
                    goal.priority = GoalPriority.MEDIUM
                else:
                    goal.priority = GoalPriority.LOW
            
            self._save_goal_to_db(self.goals[dimension])
            self.stats["total_adjustments"] += 1
    
    def _save_feedback_to_db(self, fb: Dict):
        """保存反馈到数据库"""
        try:
            with sqlite3.connect(str(self._db_path)) as conn:
                conn.execute('''
                    INSERT INTO feedback_history
                    (timestamp, satisfaction, praised, criticized, raw_feedback)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    fb["timestamp"],
                    fb["satisfaction"],
                    json.dumps(fb["praised"]),
                    json.dumps(fb["criticized"]),
                    fb.get("raw_feedback", "")
                ))
                conn.commit()
        except Exception as e:
            logger.debug(f"保存反馈失败: {e}")
    
    def update_progress(
        self,
        dimension: EvolutionDimension,
        current_value: float,
    ):
        """
        更新进度并触发L5进化
        
        修复P4: 与L5进化层集成
        """
        if dimension not in self.goals:
            return
        
        goal = self.goals[dimension]
        old_progress = goal.progress
        
        goal.current_value = current_value
        goal.progress_history.append(current_value)
        goal.updated_at = datetime.now()
        
        if len(goal.progress_history) > 100:
            goal.progress_history = goal.progress_history[-50:]
        
        progress_delta = goal.progress - old_progress
        self.stats["total_progress"] += progress_delta
        
        self._save_goal_to_db(goal)
        
        if goal.progress >= 1.0 and old_progress < 1.0:
            self.stats["goals_achieved"] += 1
            self._trigger_evolution(dimension, goal, "goal_achieved")
        
        if goal.progress >= 0.8 and old_progress < 0.8:
            self._trigger_evolution(dimension, goal, "milestone_reached")
    
    def _trigger_evolution(
        self,
        dimension: EvolutionDimension,
        goal: EvolutionGoal,
        event_type: str
    ):
        """
        触发L5进化
        
        修复P4: 与L5进化层集成
        """
        try:
            from core.layers.l5_evolution import get_l5_evolution
            l5 = get_l5_evolution()
            
            l5.record_experience({
                "user_input": f"进化目标事件: {event_type}",
                "response": f"维度: {dimension.value}, 目标: {goal.target_value:.2f}, 当前: {goal.current_value:.2f}",
                "validation_result": {
                    "status": "pass",
                    "confidence": goal.priority.value
                },
                "perception": {
                    "intent": "evolution_goal",
                    "event_type": event_type,
                    "dimension": dimension.value,
                }
            })
            
            self.stats["evolutions_triggered"] += 1
            logger.info(f"🎯 触发L5进化: {dimension.value} - {event_type}")
        except ImportError:
            logger.debug("L5进化层未安装，跳过触发")
        except Exception as e:
            logger.debug(f"触发L5进化失败: {e}")
    
    def get_priority_goals(self, limit: int = 3) -> List[EvolutionGoal]:
        """获取优先目标"""
        sorted_goals = sorted(
            self.goals.values(),
            key=lambda g: (g.priority.value, g.gap),
            reverse=True,
        )
        
        return sorted_goals[:limit]
    
    def get_evolution_direction(self) -> Dict[str, Any]:
        """获取进化方向"""
        priority_goals = self.get_priority_goals()
        
        return {
            "primary_focus": priority_goals[0].dimension.value if priority_goals else None,
            "goals": [
                {
                    "dimension": g.dimension.value,
                    "target": g.target_value,
                    "current": g.current_value,
                    "progress": g.progress,
                    "gap": g.gap,
                    "priority": g.priority.value,
                    "trend": self.value_inferences.get(g.dimension, ValueInference(
                        dimension=g.dimension,
                        inferred_value=0.5,
                        evidence_count=0,
                        evidence_sources=[],
                        confidence=0.0
                    )).trend,
                }
                for g in priority_goals
            ],
            "total_goals": len(self.goals),
            "goals_achieved": self.stats["goals_achieved"],
            "evolutions_triggered": self.stats["evolutions_triggered"],
        }
    
    def set_explicit_goal(
        self,
        dimension: EvolutionDimension,
        target: float,
        priority: GoalPriority = GoalPriority.MEDIUM,
    ):
        """设置显式目标"""
        now = datetime.now()
        
        current = 0.5
        if dimension in self.goals:
            current = self.goals[dimension].current_value
        
        goal = EvolutionGoal(
            dimension=dimension,
            target_value=target,
            current_value=current,
            priority=priority,
            source="user",
            created_at=now,
            updated_at=now,
        )
        
        self.goals[dimension] = goal
        self._save_goal_to_db(goal)
        
        logger.info(f"🎯 设置显式目标: {dimension.value} = {target:.2f}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_goals": len(self.goals),
            "total_adjustments": self.stats["total_adjustments"],
            "total_progress": self.stats["total_progress"],
            "goals_achieved": self.stats["goals_achieved"],
            "evolutions_triggered": self.stats["evolutions_triggered"],
            "average_progress": (
                sum(g.progress for g in self.goals.values()) / len(self.goals)
                if self.goals else 0
            ),
            "inference_count": len(self.value_inferences),
            "feedback_count": len(self.feedback_history),
        }


_adaptive_evolution_goal: Optional[AdaptiveEvolutionGoal] = None


def get_adaptive_evolution_goal(config: Optional[Dict] = None) -> AdaptiveEvolutionGoal:
    """
    获取自适应进化目标单例
    
    修复P7: 规范单例实现
    """
    global _adaptive_evolution_goal
    if _adaptive_evolution_goal is None:
        _adaptive_evolution_goal = AdaptiveEvolutionGoal(config)
    return _adaptive_evolution_goal
