"""
冲突协调器 - 解决多个进化机制之间的冲突
核心思想：建立仲裁机制，确保进化方向一致
"""

import json
import sqlite3
import hashlib
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ConflictSeverity(Enum):
    """冲突严重程度"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2


class ConflictType(Enum):
    """冲突类型"""
    GENE_RULE = "gene_vs_rule"
    GENE_FEEDBACK = "gene_vs_feedback"
    RULE_FEEDBACK = "rule_vs_feedback"
    MEMORY_CLEANUP = "memory_vs_cleanup"
    SCHEDULER_OVERLAP = "scheduler_overlap"
    PRIORITY_DEADLOCK = "priority_deadlock"


@dataclass
class Conflict:
    """冲突记录"""
    id: str
    type: ConflictType
    severity: ConflictSeverity
    description: str
    source1: Dict
    source2: Dict
    detected_at: str
    resolved_at: Optional[str] = None
    resolution: Optional[str] = None


@dataclass
class EvolutionRule:
    """进化规则（优先级）"""
    rule_id: str
    source_type: str
    parameter: str
    value: any
    priority: int
    applied_at: str
    evidence: Dict


class ConflictCoordinator:
    """
    冲突协调器
    
    职责：
    1. 检测不同进化机制之间的冲突
    2. 根据优先级仲裁
    3. 记录冲突解决过程
    4. 防止未来同类冲突
    """
    
    PRIORITY_TABLE = {
        'user_feedback': 100,
        'safe_guard': 90,
        'philosophy_rule': 85,
        'critical_goal': 80,
        'evolution_result': 70,
        'learning_rule': 60,
        'statistical_pattern': 50,
        'default_config': 40,
        'experimental': 20,
    }
    
    def __init__(self, db_path: str = "data/conflict_coordinator.db"):
        self.db_path = db_path
        self.conflict_history: List[Conflict] = []
        self.active_conflicts: Dict[str, Conflict] = {}
        self.applied_rules: Dict[str, EvolutionRule] = {}
        
        self._init_database()
        self._load_state()
        
        logger.info("⚖️ 冲突协调器已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conflicts (
                    id TEXT PRIMARY KEY,
                    type TEXT,
                    severity TEXT,
                    description TEXT,
                    source1 TEXT,
                    source2 TEXT,
                    detected_at TEXT,
                    resolved_at TEXT,
                    resolution TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS applied_rules (
                    rule_id TEXT PRIMARY KEY,
                    source_type TEXT,
                    parameter TEXT,
                    value TEXT,
                    priority INTEGER,
                    applied_at TEXT,
                    evidence TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS arbitration_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    conflict_id TEXT,
                    decision TEXT,
                    reasoning TEXT,
                    applied_rule_id TEXT
                )
            ''')
            
            conn.commit()
    
    def detect_conflicts(self, rule1: Dict, rule2: Dict) -> Optional[Conflict]:
        """检测两个规则之间是否存在冲突"""
        
        if rule1.get('parameter') == rule2.get('parameter'):
            if rule1.get('value') != rule2.get('value'):
                return self._create_conflict(
                    type=ConflictType.GENE_RULE,
                    severity=ConflictSeverity.HIGH,
                    description=f"参数 {rule1['parameter']} 冲突: {rule1['value']} vs {rule2['value']}",
                    source1=rule1,
                    source2=rule2
                )
        
        if self._has_goal_conflict(rule1, rule2):
            return self._create_conflict(
                type=ConflictType.PRIORITY_DEADLOCK,
                severity=ConflictSeverity.MEDIUM,
                description=f"目标冲突: {rule1.get('goal')} vs {rule2.get('goal')}",
                source1=rule1,
                source2=rule2
            )
        
        return None
    
    def _has_goal_conflict(self, rule1: Dict, rule2: Dict) -> bool:
        """检查是否有目标冲突"""
        goals1 = rule1.get('goals', [])
        goals2 = rule2.get('goals', [])
        
        exclusive_pairs = [
            ('maximize_accuracy', 'maximize_speed'),
            ('maximize_learning', 'minimize_resource'),
        ]
        
        for g1 in goals1:
            for g2 in goals2:
                if (g1, g2) in exclusive_pairs or (g2, g1) in exclusive_pairs:
                    return True
        
        return False
    
    def _create_conflict(self, type: ConflictType, severity: ConflictSeverity,
                         description: str, source1: Dict, source2: Dict) -> Conflict:
        """创建冲突记录"""
        import time
        
        conflict_id = hashlib.md5(
            f"{type.value}{time.time()}".encode()
        ).hexdigest()[:12]
        
        return Conflict(
            id=conflict_id,
            type=type,
            severity=severity,
            description=description,
            source1=source1,
            source2=source2,
            detected_at=datetime.now().isoformat()
        )
    
    def arbitrate(self, conflict: Conflict) -> Dict:
        """仲裁冲突"""
        
        priority1 = self._get_priority(conflict.source1)
        priority2 = self._get_priority(conflict.source2)
        
        decision = {}
        
        if priority1 > priority2:
            decision = {
                'winner': 'source1',
                'rule': conflict.source1,
                'reason': f"源1优先级更高 ({priority1} > {priority2})"
            }
        elif priority2 > priority1:
            decision = {
                'winner': 'source2',
                'rule': conflict.source2,
                'reason': f"源2优先级更高 ({priority2} > {priority1})"
            }
        else:
            evidence1 = self._evaluate_evidence(conflict.source1)
            evidence2 = self._evaluate_evidence(conflict.source2)
            
            if evidence1 > evidence2:
                decision = {
                    'winner': 'source1',
                    'rule': conflict.source1,
                    'reason': f"证据更充分 ({evidence1:.2f} > {evidence2:.2f})"
                }
            elif evidence2 > evidence1:
                decision = {
                    'winner': 'source2',
                    'rule': conflict.source2,
                    'reason': f"证据更充分 ({evidence2:.2f} > {evidence1:.2f})"
                }
            else:
                decision = {
                    'winner': 'none',
                    'rule': None,
                    'reason': "无法自动仲裁，需要人工介入",
                    'needs_human': True
                }
        
        self._record_arbitration(conflict, decision)
        
        conflict.resolved_at = datetime.now().isoformat()
        conflict.resolution = decision.get('reason', '')
        
        return decision
    
    def _get_priority(self, source: Dict) -> int:
        """获取源优先级"""
        source_type = source.get('source_type', 'default_config')
        return self.PRIORITY_TABLE.get(source_type, 30)
    
    def _evaluate_evidence(self, source: Dict) -> float:
        """评估证据充分性"""
        evidence = source.get('evidence', {})
        
        score = 0.0
        
        if evidence.get('user_feedback_count', 0) > 0:
            score += 0.5 * min(evidence['user_feedback_count'], 5)
        
        if evidence.get('success_count', 0) > 0:
            score += 0.3 * min(evidence['success_count'], 3)
        
        if evidence.get('data_points', 0) > 0:
            score += 0.2 * min(evidence['data_points'] / 10, 1)
        
        return min(score, 1.0)
    
    def _record_arbitration(self, conflict: Conflict, decision: Dict):
        """记录仲裁"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO arbitration_log
                (timestamp, conflict_id, decision, reasoning, applied_rule_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                conflict.id,
                decision.get('winner', 'none'),
                decision.get('reason', ''),
                decision.get('rule', {}).get('rule_id', '') if decision.get('rule') else ''
            ))
            
            cursor.execute('''
                UPDATE conflicts
                SET resolved_at = ?, resolution = ?
                WHERE id = ?
            ''', (
                conflict.resolved_at,
                conflict.resolution,
                conflict.id
            ))
            
            conn.commit()
    
    def _load_state(self):
        """加载状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cursor = conn.execute('''
                    SELECT * FROM conflicts ORDER BY detected_at DESC LIMIT 50
                ''')
                for row in cursor:
                    self.conflict_history.append(Conflict(
                        id=row['id'],
                        type=ConflictType(row['type']),
                        severity=ConflictSeverity(row['severity']),
                        description=row['description'],
                        source1=json.loads(row['source1']),
                        source2=json.loads(row['source2']),
                        detected_at=row['detected_at'],
                        resolved_at=row['resolved_at'],
                        resolution=row['resolution']
                    ))
                
                cursor = conn.execute('SELECT * FROM applied_rules')
                for row in cursor:
                    self.applied_rules[row['rule_id']] = EvolutionRule(
                        rule_id=row['rule_id'],
                        source_type=row['source_type'],
                        parameter=row['parameter'],
                        value=json.loads(row['value']),
                        priority=row['priority'],
                        applied_at=row['applied_at'],
                        evidence=json.loads(row['evidence'])
                    )
                    
        except Exception as e:
            logger.warning(f"加载冲突协调状态失败: {e}")
    
    def get_conflict_stats(self) -> Dict:
        """获取冲突统计"""
        return {
            'total_conflicts': len(self.conflict_history),
            'active_conflicts': len([c for c in self.conflict_history if c.resolved_at is None]),
            'resolved_conflicts': len([c for c in self.conflict_history if c.resolved_at is not None]),
            'by_type': {
                ctype.value: len([c for c in self.conflict_history if c.type == ctype])
                for ctype in ConflictType
            },
            'applied_rules_count': len(self.applied_rules)
        }
    
    def register_rule(self, rule: EvolutionRule):
        """注册规则"""
        self.applied_rules[rule.rule_id] = rule
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO applied_rules
                (rule_id, source_type, parameter, value, priority, applied_at, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                rule.rule_id,
                rule.source_type,
                rule.parameter,
                json.dumps(rule.value),
                rule.priority,
                rule.applied_at,
                json.dumps(rule.evidence)
            ))
            
            conn.commit()
    
    def save_conflict(self, conflict: Conflict):
        """保存冲突记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO conflicts
                (id, type, severity, description, source1, source2, detected_at, resolved_at, resolution)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                conflict.id,
                conflict.type.value,
                conflict.severity.value,
                conflict.description,
                json.dumps(conflict.source1),
                json.dumps(conflict.source2),
                conflict.detected_at,
                conflict.resolved_at,
                conflict.resolution
            ))
            
            conn.commit()


conflict_coordinator = ConflictCoordinator()