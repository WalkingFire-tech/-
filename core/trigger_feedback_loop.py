"""
触发决策反馈回路 - 让触发系统从错误中学习
"""


import json
import os
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
from dataclasses import dataclass

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.ports.adapters import get_storage_port


@dataclass
class TriggerEvent:
    """触发事件记录"""
    id: str
    user_input: str
    trigger_decision: str
    processing_depth: str
    route_reason: str
    created_at: str
    user_satisfied: Optional[bool] = None
    correction_needed: bool = False
    actual_need: Optional[str] = None


class TriggerFeedbackLoop:
    """
    触发决策反馈回路
    
    核心机制：
    1. 记录每次触发决策
    2. 收集用户反馈
    3. 分析误判模式
    4. 自动调整触发策略
    """
    
    def __init__(self, db_path: str = "data/trigger_feedback.db"):
        self.db_path = db_path
        self._init_database()
        
        self.stats = {
            'total_decisions': 0,
            'true_positives': 0,
            'false_positives': 0,
            'false_negatives': 0,
            'true_negatives': 0,
            'adjustments': 0
        }
        
        self.pattern_weights = defaultdict(lambda: 1.0)
        
        logger.info("🔄 触发决策反馈回路已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        db = get_storage_port(self.db_path)
        
        db.executescript('''
            CREATE TABLE IF NOT EXISTS trigger_events (
                id TEXT PRIMARY KEY,
                user_input TEXT,
                trigger_decision TEXT,
                processing_depth TEXT,
                route_reason TEXT,
                user_satisfied INTEGER,
                correction_needed INTEGER,
                actual_need TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS pattern_weights (
                pattern TEXT PRIMARY KEY,
                weight REAL,
                occurrences INTEGER,
                successes INTEGER,
                failures INTEGER,
                last_updated TEXT
            );
            
            CREATE TABLE IF NOT EXISTS adjustment_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                adjustment_type TEXT,
                previous_value REAL,
                new_value REAL,
                reason TEXT,
                effectiveness REAL
            )
        ''')
    
    def record_decision(self, event: TriggerEvent):
        """记录触发决策"""
        
        db = get_storage_port(self.db_path)
        
        db.execute('''
            INSERT INTO trigger_events
            (id, user_input, trigger_decision, processing_depth, 
             route_reason, user_satisfied, correction_needed, actual_need, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event.id,
            event.user_input[:500],
            event.trigger_decision,
            event.processing_depth,
            event.route_reason,
            1 if event.user_satisfied else 0 if event.user_satisfied is not None else None,
            1 if event.correction_needed else 0,
            event.actual_need,
            event.created_at
        ), commit=True)
        
        self.stats['total_decisions'] += 1
    
    def collect_feedback(self, event_id: str, satisfied: bool, 
                        correction_needed: bool = False,
                        actual_need: str = None):
        """
        收集用户反馈
        
        Args:
            event_id: 触发事件ID
            satisfied: 用户是否满意
            correction_needed: 是否需要纠错
            actual_need: 实际应该如何处理
        """
        
        db = get_storage_port(self.db_path)
        
        db.execute('''
            UPDATE trigger_events
            SET user_satisfied = ?, correction_needed = ?, actual_need = ?
            WHERE id = ?
        ''', (
            1 if satisfied else 0,
            1 if correction_needed else 0,
            actual_need,
            event_id
        ), commit=True)
        
        event = self._get_event(event_id)
        if not event:
            return
        
        if event.trigger_decision == 'triggered':
            if satisfied:
                self.stats['true_positives'] += 1
            else:
                self.stats['false_positives'] += 1
                self._adjust_thresholds('decrease')
        else:
            if satisfied:
                self.stats['true_negatives'] += 1
            else:
                self.stats['false_negatives'] += 1
                self._adjust_thresholds('increase')
    
    def _get_event(self, event_id: str) -> Optional[TriggerEvent]:
        """获取事件"""
        db = get_storage_port(self.db_path)
        row = db.query_one(
            "SELECT * FROM trigger_events WHERE id = ?",
            (event_id,)
        )
        
        if not row:
            return None
        
        return TriggerEvent(
            id=row['id'],
            user_input=row['user_input'],
            trigger_decision=row['trigger_decision'],
            processing_depth=row['processing_depth'],
            route_reason=row['route_reason'],
            user_satisfied=bool(row['user_satisfied']) if row['user_satisfied'] is not None else None,
            correction_needed=bool(row['correction_needed']),
            actual_need=row['actual_need'],
            created_at=row['created_at']
        )
    
    def _adjust_thresholds(self, direction: str):
        """调整触发阈值"""
        
        self.stats['adjustments'] += 1
        
        misclassifications = self._analyze_misclassifications()
        
        if not misclassifications:
            return
        
        for pattern, stats in misclassifications.items():
            current_weight = self.pattern_weights[pattern]
            
            if direction == 'increase':
                new_weight = current_weight * 1.05
            else:
                new_weight = current_weight * 0.95
            
            self.pattern_weights[pattern] = min(max(new_weight, 0.1), 2.0)
            
            logger.info(f"  📌 调整触发权重: {pattern} → {self.pattern_weights[pattern]:.2f}")
            
            self._record_adjustment(pattern, current_weight, self.pattern_weights[pattern])
    
    def _analyze_misclassifications(self) -> Dict:
        """分析误判模式"""
        
        patterns = defaultdict(lambda: {'count': 0, 'false_positives': 0, 'false_negatives': 0})
        
        db = get_storage_port(self.db_path)
        
        rows = db.query('''
            SELECT * FROM trigger_events
            ORDER BY created_at DESC LIMIT 100
        ''')
        
        for row in rows:
            route_reason = row['route_reason']
            pattern = self._extract_pattern(route_reason)
            
            patterns[pattern]['count'] += 1
            
            if row['trigger_decision'] == 'triggered' and row['correction_needed']:
                patterns[pattern]['false_positives'] += 1
            elif row['trigger_decision'] == 'not_triggered' and row['correction_needed']:
                patterns[pattern]['false_negatives'] += 1
        
        return {
            p: s for p, s in patterns.items()
            if s['false_positives'] + s['false_negatives'] > 2
        }
    
    def _extract_pattern(self, reason: str) -> str:
        """提取触发模式"""
        if not reason:
            return 'unknown'
        
        reason_lower = reason.lower()
        
        if 'whitelist' in reason_lower:
            return 'whitelist_match'
        elif 'keyword' in reason_lower:
            return 'keyword_match'
        elif 'semantic' in reason_lower:
            return 'semantic_match'
        elif 'intent' in reason_lower:
            return 'intent_match'
        elif 'state' in reason_lower:
            return 'state_match'
        else:
            return 'unknown'
    
    def _record_adjustment(self, pattern: str, old_value: float, new_value: float):
        """记录调整历史"""
        
        db = get_storage_port(self.db_path)
        
        db.execute('''
            INSERT INTO adjustment_history
            (timestamp, adjustment_type, previous_value, new_value, reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            pattern,
            old_value,
            new_value,
            f"基于误判分析自动调整"
        ), commit=True)
    
    def get_learning_summary(self) -> Dict:
        """获取学习摘要"""
        
        total = self.stats['total_decisions']
        
        if total == 0:
            return {'status': 'no_data'}
        
        tp = self.stats['true_positives']
        fp = self.stats['false_positives']
        fn = self.stats['false_negatives']
        tn = self.stats['true_negatives']
        
        accuracy = (tp + tn) / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        return {
            'total_decisions': total,
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'adjustments': self.stats['adjustments'],
            'pattern_weights': dict(self.pattern_weights),
            'confusion_matrix': {
                'true_positives': tp,
                'false_positives': fp,
                'false_negatives': fn,
                'true_negatives': tn
            }
        }
    
    def create_event_id(self, user_input: str) -> str:
        """创建事件ID"""
        return hashlib.md5(
            f"{user_input}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]


trigger_feedback_loop = TriggerFeedbackLoop()