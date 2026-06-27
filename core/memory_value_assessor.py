"""
记忆价值评估器 - 决定什么应该记住，什么应该遗忘
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class MemoryValue(Enum):
    """记忆价值等级"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    TRANSIENT = 1


@dataclass
class MemoryItem:
    """记忆条目"""
    id: str
    content: str
    memory_type: str
    value_score: float
    value_grade: MemoryValue
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    user_marked_important: bool = False
    correctness_score: float = 0.8
    context_importance: float = 0.5
    created_at: datetime = None
    expires_at: Optional[datetime] = None


class MemoryValueAssessor:
    """
    记忆价值评估器
    
    评估维度：
    1. 访问频率 → 高频记忆价值高
    2. 用户标记 → 用户明确标记为重要
    3. 正确性 → 被验证正确的记忆价值高
    4. 上下文重要性 → 在重要对话中产生的记忆价值高
    5. 时效性 → 近期记忆价值高
    6. 关联性 → 与其他重要记忆关联的价值高
    """
    
    def __init__(self, db_path: str = "data/memory_assessor.db"):
        self.db_path = db_path
        self._init_database()
        
        self.weights = {
            'access_frequency': 0.20,
            'user_marked': 0.25,
            'correctness': 0.15,
            'context_importance': 0.15,
            'recency': 0.10,
            'connectedness': 0.15,
        }
        
        self.thresholds = {
            'critical': 0.85,
            'high': 0.65,
            'medium': 0.40,
            'low': 0.20,
        }
        
        logger.info("💎 记忆价值评估器已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    memory_type TEXT,
                    value_score REAL,
                    value_grade TEXT,
                    access_count INTEGER,
                    last_accessed TEXT,
                    user_marked_important INTEGER,
                    correctness_score REAL,
                    context_importance REAL,
                    created_at TEXT,
                    expires_at TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_graph (
                    memory_id TEXT,
                    related_memory_id TEXT,
                    relation_type TEXT,
                    strength REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memory_verdicts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT,
                    verdict_type TEXT,
                    verdict_value TEXT,
                    created_at TEXT
                )
            ''')
            
            conn.commit()
    
    def evaluate(self, memory: Dict) -> float:
        """
        评估记忆价值
        
        返回: 0-1 价值分数
        """
        
        scores = {
            'access_frequency': self._evaluate_access_frequency(memory),
            'user_marked': self._evaluate_user_marked(memory),
            'correctness': self._evaluate_correctness(memory),
            'context_importance': self._evaluate_context_importance(memory),
            'recency': self._evaluate_recency(memory),
            'connectedness': self._evaluate_connectedness(memory),
        }
        
        total_score = sum(
            scores[key] * self.weights[key]
            for key in self.weights.keys()
        )
        
        return min(total_score, 1.0)
    
    def _evaluate_access_frequency(self, memory: Dict) -> float:
        """评估访问频率"""
        access_count = memory.get('access_count', 0)
        
        if access_count == 0:
            return 0.0
        elif access_count == 1:
            return 0.3
        elif access_count <= 3:
            return 0.5
        elif access_count <= 10:
            return 0.7
        else:
            return 1.0
    
    def _evaluate_user_marked(self, memory: Dict) -> float:
        """评估用户标记"""
        if memory.get('user_marked_important', False):
            return 1.0
        return 0.0
    
    def _evaluate_correctness(self, memory: Dict) -> float:
        """评估正确性"""
        return memory.get('correctness_score', 0.8)
    
    def _evaluate_context_importance(self, memory: Dict) -> float:
        """评估上下文重要性"""
        return memory.get('context_importance', 0.5)
    
    def _evaluate_recency(self, memory: Dict) -> float:
        """评估时效性"""
        created_at = memory.get('created_at')
        if not created_at:
            return 0.5
        
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at)
            except:
                return 0.5
        
        days_old = (datetime.now() - created_at).days
        
        if days_old < 1:
            return 1.0
        elif days_old < 7:
            return 0.8
        elif days_old < 30:
            return 0.5
        elif days_old < 90:
            return 0.3
        else:
            return 0.1
    
    def _evaluate_connectedness(self, memory: Dict) -> float:
        """评估关联性"""
        connections = memory.get('connections', 0)
        
        if connections == 0:
            return 0.2
        elif connections == 1:
            return 0.4
        elif connections <= 3:
            return 0.6
        elif connections <= 10:
            return 0.8
        else:
            return 1.0
    
    def get_value_grade(self, score: float) -> MemoryValue:
        """根据分数获取价值等级"""
        if score >= self.thresholds['critical']:
            return MemoryValue.CRITICAL
        elif score >= self.thresholds['high']:
            return MemoryValue.HIGH
        elif score >= self.thresholds['medium']:
            return MemoryValue.MEDIUM
        elif score >= self.thresholds['low']:
            return MemoryValue.LOW
        else:
            return MemoryValue.TRANSIENT
    
    def should_retain(self, memory: Dict) -> bool:
        """
        判断是否应该保留这条记忆
        
        策略：
        1. 用户标记为重要的 → 永久保留
        2. 价值等级 ≥ MEDIUM → 保留
        3. 价值等级 = LOW → 在清理周期中考虑
        4. 价值等级 = TRANSIENT → 优先遗忘
        """
        
        if memory.get('user_marked_important', False):
            return True
        
        score = self.evaluate(memory)
        grade = self.get_value_grade(score)
        
        if grade in [MemoryValue.CRITICAL, MemoryValue.HIGH, MemoryValue.MEDIUM]:
            return True
        elif grade == MemoryValue.LOW:
            return memory.get('special_retention', False)
        else:
            return False
    
    def get_retention_recommendation(self, memory: Dict) -> Dict:
        """获取保留建议"""
        score = self.evaluate(memory)
        grade = self.get_value_grade(score)
        
        recommendations = {
            MemoryValue.CRITICAL: {
                'action': '永久保留',
                'priority': 5,
                'suggestion': '标记为刻骨铭心记忆，永不遗忘'
            },
            MemoryValue.HIGH: {
                'action': '长期保留',
                'priority': 4,
                'suggestion': '定期回顾，保持活跃'
            },
            MemoryValue.MEDIUM: {
                'action': '标准保留',
                'priority': 3,
                'suggestion': '正常保留，周期性评估'
            },
            MemoryValue.LOW: {
                'action': '考虑清理',
                'priority': 2,
                'suggestion': '在下一次清理周期中评估，如果无新访问则清理'
            },
            MemoryValue.TRANSIENT: {
                'action': '优先清理',
                'priority': 1,
                'suggestion': '可安全遗忘，不会影响系统核心能力'
            }
        }
        
        return {
            'score': score,
            'grade': grade.value,
            'grade_name': grade.name,
            'retain': self.should_retain(memory),
            'action': recommendations[grade]['action'],
            'priority': recommendations[grade]['priority'],
            'suggestion': recommendations[grade]['suggestion']
        }
    
    def update_with_feedback(self, memory_id: str, feedback_type: str, feedback_value: any):
        """根据反馈更新记忆评估"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO memory_verdicts
                (memory_id, verdict_type, verdict_value, created_at)
                VALUES (?, ?, ?, ?)
            ''', (
                memory_id,
                feedback_type,
                str(feedback_value),
                datetime.now().isoformat()
            ))
            
            conn.commit()
        
        if feedback_type == 'user_marked_important' and feedback_value:
            self._mark_important(memory_id)
    
    def _mark_important(self, memory_id: str):
        """标记为重要记忆"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE memories
                SET user_marked_important = 1
                WHERE id = ?
            ''', (memory_id,))
            
            conn.commit()
    
    def get_memory_report(self, limit: int = 20) -> Dict:
        """生成记忆报告"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute('''
                SELECT * FROM memories
                ORDER BY value_score DESC
                LIMIT ?
            ''', (limit,))
            
            memories = [dict(row) for row in cursor.fetchall()]
        
        return {
            'total_memories': len(memories),
            'by_grade': {
                grade.value: len([m for m in memories if m.get('value_grade') == str(grade.value)])
                for grade in MemoryValue
            },
            'top_memories': memories[:10],
            'candidates_for_cleanup': [
                m for m in memories
                if m.get('value_grade') in [str(MemoryValue.LOW.value), str(MemoryValue.TRANSIENT.value)]
            ]
        }
    
    def save_memory(self, memory: Dict):
        """保存记忆"""
        score = self.evaluate(memory)
        grade = self.get_value_grade(score)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO memories
                (id, content, memory_type, value_score, value_grade, 
                 access_count, last_accessed, user_marked_important,
                 correctness_score, context_importance, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                memory.get('id'),
                memory.get('content', ''),
                memory.get('memory_type', 'general'),
                score,
                str(grade.value),
                memory.get('access_count', 0),
                memory.get('last_accessed'),
                1 if memory.get('user_marked_important', False) else 0,
                memory.get('correctness_score', 0.8),
                memory.get('context_importance', 0.5),
                memory.get('created_at', datetime.now().isoformat()),
                memory.get('expires_at')
            ))
            
            conn.commit()


memory_value_assessor = MemoryValueAssessor()