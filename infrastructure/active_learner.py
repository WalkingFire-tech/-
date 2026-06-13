"""
主动学习器 - 事件驱动的持续学习单元
实现"主动求知"能力，遵循安全第一原则
"""
import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
from collections import defaultdict


class LearningTrigger(Enum):
    """学习触发事件"""
    INTENT_FAILURE = "intent_failure"
    CAPABILITY_LOW = "capability_low"
    USER_QUESTION = "user_question"
    APHI_DECLINE = "aphi_decline"
    MANUAL = "manual"


class LearningStatus(Enum):
    """学习状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class LearningActivity:
    """学习活动"""
    id: Optional[int] = None
    trigger: LearningTrigger = LearningTrigger.MANUAL
    query: str = ""
    source: str = ""
    knowledge: str = ""
    status: LearningStatus = LearningStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    impact_score: float = 0.0
    user_approved: Optional[bool] = None
    metadata: Dict = field(default_factory=dict)


class ActiveLearner:
    """主动学习器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._activities_db = Path("data/learning_activities.db")
        self._knowledge_db = Path("data/knowledge_base.db")
        self._is_learning = False
        self._paused = False
        self._event_counts = defaultdict(int)
        self._failure_threshold = 3
        self._low_capability_threshold = 0.3
        self._aphi_decline_threshold = 0.1
        
        self._init_databases()
        logger.info("主动学习器已初始化")
    
    def _init_databases(self):
        """初始化数据库"""
        self._activities_db.parent.mkdir(parents=True, exist_ok=True)
        self._knowledge_db.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self._activities_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger TEXT,
                    query TEXT,
                    source TEXT,
                    knowledge TEXT,
                    status TEXT,
                    created_at TEXT,
                    completed_at TEXT,
                    impact_score REAL,
                    user_approved INTEGER,
                    metadata TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_trigger ON learning_activities(trigger)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_status ON learning_activities(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_created ON learning_activities(created_at)')
        
        with sqlite3.connect(self._knowledge_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    content TEXT,
                    source TEXT,
                    learning_activity_id INTEGER,
                    created_at TEXT,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT,
                    usefulness_score REAL DEFAULT 0.5,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_topic ON knowledge_base(topic)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_active ON knowledge_base(is_active)')
    
    def record_event(self, event_type: str, details: Dict = None):
        """记录事件（用于触发学习）"""
        self._event_counts[event_type] += 1
        
        if event_type == "intent_failure":
            if self._event_counts[event_type] >= self._failure_threshold:
                logger.info(f"意图失败次数达到阈值({self._failure_threshold})，触发学习")
                asyncio.create_task(self.trigger_learning(
                    LearningTrigger.INTENT_FAILURE,
                    details.get("intent", "unknown"),
                    details
                ))
                self._event_counts[event_type] = 0
        
        elif event_type == "capability_low":
            capability = details.get("capability", "unknown")
            score = details.get("score", 0)
            if score < self._low_capability_threshold:
                logger.info(f"能力维度低迷({capability}: {score:.2f})，触发学习")
                asyncio.create_task(self.trigger_learning(
                    LearningTrigger.CAPABILITY_LOW,
                    f"如何提升{capability}能力",
                    details
                ))
        
        elif event_type == "user_question":
            question = details.get("question", "")
            logger.info(f"用户提问，触发学习: {question[:50]}")
            asyncio.create_task(self.trigger_learning(
                LearningTrigger.USER_QUESTION,
                question,
                details
            ))
        
        elif event_type == "aphi_decline":
            decline_rate = details.get("decline_rate", 0)
            if decline_rate > self._aphi_decline_threshold:
                logger.info(f"APHI连续下降({decline_rate:.2%})，触发学习")
                asyncio.create_task(self.trigger_learning(
                    LearningTrigger.APHI_DECLINE,
                    "系统性能优化策略",
                    details
                ))
    
    async def trigger_learning(self, trigger: LearningTrigger, query: str, 
                               context: Dict = None) -> LearningActivity:
        """触发学习"""
        if self._paused:
            logger.warning("学习器已暂停，跳过学习")
            return LearningActivity(
                trigger=trigger,
                query=query,
                status=LearningStatus.FAILED,
                metadata={"error": "学习器已暂停"}
            )
        
        activity = LearningActivity(
            trigger=trigger,
            query=query,
            status=LearningStatus.RUNNING,
            metadata=context or {}
        )
        
        activity_id = self._save_activity(activity)
        activity.id = activity_id
        
        try:
            knowledge = await self._search_and_learn(query, context)
            
            activity.knowledge = knowledge
            activity.status = LearningStatus.COMPLETED
            activity.completed_at = datetime.now().isoformat()
            activity.impact_score = self._calculate_impact(knowledge)
            
            self._update_activity(activity)
            self._save_knowledge(query, knowledge, activity_id)
            
            logger.info(f"学习完成: {query[:50]} (影响分: {activity.impact_score:.2f})")
            
        except Exception as e:
            activity.status = LearningStatus.FAILED
            activity.metadata["error"] = str(e)
            self._update_activity(activity)
            logger.error(f"学习失败: {e}")
        
        return activity
    
    async def _search_and_learn(self, query: str, context: Dict = None) -> str:
        """搜索并学习"""
        from tools.web_search import QuickSearchTool
        
        search_tool = QuickSearchTool()
        result = await asyncio.to_thread(
            search_tool.execute,
            query=query
        )
        
        if not result.success:
            raise Exception(f"搜索失败: {result.error}")
        
        output = result.output
        knowledge = f"【查询】{query}\n\n"
        knowledge += f"【来源】{', '.join(output.get('sources', []))}\n\n"
        knowledge += f"【摘要】\n{output.get('summary', '无摘要')}"
        
        return knowledge
    
    def _calculate_impact(self, knowledge: str) -> float:
        """计算影响分数"""
        score = 0.5
        
        if len(knowledge) > 500:
            score += 0.1
        if "来源" in knowledge and "http" in knowledge:
            score += 0.2
        if "摘要" in knowledge:
            score += 0.1
        
        return min(1.0, score)
    
    def _save_activity(self, activity: LearningActivity) -> int:
        """保存学习活动"""
        import json
        
        with sqlite3.connect(self._activities_db) as conn:
            cur = conn.execute('''
                INSERT INTO learning_activities 
                (trigger, query, source, knowledge, status, created_at, completed_at, 
                 impact_score, user_approved, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                activity.trigger.value,
                activity.query,
                activity.source,
                activity.knowledge,
                activity.status.value,
                activity.created_at,
                activity.completed_at,
                activity.impact_score,
                activity.user_approved,
                json.dumps(activity.metadata, ensure_ascii=False)
            ))
            return cur.lastrowid
    
    def _update_activity(self, activity: LearningActivity):
        """更新学习活动"""
        import json
        
        with sqlite3.connect(self._activities_db) as conn:
            conn.execute('''
                UPDATE learning_activities
                SET knowledge=?, status=?, completed_at=?, impact_score=?, 
                    user_approved=?, metadata=?
                WHERE id=?
            ''', (
                activity.knowledge,
                activity.status.value,
                activity.completed_at,
                activity.impact_score,
                activity.user_approved,
                json.dumps(activity.metadata, ensure_ascii=False),
                activity.id
            ))
    
    def _save_knowledge(self, topic: str, content: str, activity_id: int):
        """保存知识到知识库"""
        with sqlite3.connect(self._knowledge_db) as conn:
            conn.execute('''
                INSERT INTO knowledge_base
                (topic, content, source, learning_activity_id, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                topic,
                content,
                "web_search",
                activity_id,
                datetime.now().isoformat()
            ))
    
    def get_activities(self, limit: int = 20, status: LearningStatus = None) -> List[Dict]:
        """获取学习活动"""
        with sqlite3.connect(self._activities_db) as conn:
            if status:
                cur = conn.execute('''
                    SELECT * FROM learning_activities
                    WHERE status=?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (status.value, limit))
            else:
                cur = conn.execute('''
                    SELECT * FROM learning_activities
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))
            
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    def get_knowledge(self, topic: str = None, limit: int = 20) -> List[Dict]:
        """获取知识"""
        with sqlite3.connect(self._knowledge_db) as conn:
            if topic:
                cur = conn.execute('''
                    SELECT * FROM knowledge_base
                    WHERE topic LIKE ? AND is_active=1
                    ORDER BY usefulness_score DESC, created_at DESC
                    LIMIT ?
                ''', (f"%{topic}%", limit))
            else:
                cur = conn.execute('''
                    SELECT * FROM knowledge_base
                    WHERE is_active=1
                    ORDER BY usefulness_score DESC, created_at DESC
                    LIMIT ?
                ''', (limit,))
            
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    
    def rollback_learning(self, activity_id: int) -> bool:
        """回滚学习"""
        with sqlite3.connect(self._activities_db) as conn:
            conn.execute('''
                UPDATE learning_activities
                SET status=?
                WHERE id=?
            ''', (LearningStatus.ROLLED_BACK.value, activity_id))
            
            with sqlite3.connect(self._knowledge_db) as conn2:
                conn2.execute('''
                    UPDATE knowledge_base
                    SET is_active=0
                    WHERE learning_activity_id=?
                ''', (activity_id,))
        
        logger.info(f"已回滚学习活动: {activity_id}")
        return True
    
    def delete_knowledge(self, knowledge_id: int) -> bool:
        """删除知识"""
        with sqlite3.connect(self._knowledge_db) as conn:
            conn.execute('''
                UPDATE knowledge_base
                SET is_active=0
                WHERE id=?
            ''', (knowledge_id,))
        
        logger.info(f"已删除知识: {knowledge_id}")
        return True
    
    def pause(self):
        """暂停学习"""
        self._paused = True
        logger.info("学习器已暂停")
    
    def resume(self):
        """恢复学习"""
        self._paused = False
        logger.info("学习器已恢复")
    
    def is_paused(self) -> bool:
        return self._paused
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self._activities_db) as conn:
            cur = conn.execute('SELECT COUNT(*) FROM learning_activities')
            total_activities = cur.fetchone()[0]
            
            cur = conn.execute('''
                SELECT status, COUNT(*) 
                FROM learning_activities 
                GROUP BY status
            ''')
            by_status = {row[0]: row[1] for row in cur.fetchall()}
        
        with sqlite3.connect(self._knowledge_db) as conn:
            cur = conn.execute('SELECT COUNT(*) FROM knowledge_base WHERE is_active=1')
            total_knowledge = cur.fetchone()[0]
        
        return {
            "total_activities": total_activities,
            "by_status": by_status,
            "total_knowledge": total_knowledge,
            "is_paused": self._paused
        }


active_learner = ActiveLearner()