"""
策略进化层 - 优化意图识别和路由策略

对应六层架构的 L5 进化层扩展
职责：从"积累经验"升级为"优化决策方式"
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import sqlite3
import json
import hashlib
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class IntentPattern:
    """意图模式"""
    pattern_id: str
    intent_type: str
    pattern_text: str
    success_rate: float
    sample_count: int
    confidence: float
    created_at: str
    updated_at: str
    status: str


@dataclass
class RouterStrategy:
    """路由策略"""
    strategy_id: str
    strategy_type: str
    configuration: Dict[str, Any]
    success_count: int
    failure_count: int
    avg_confidence: float
    created_at: str
    updated_at: str
    status: str


class StrategyEvolutionEngine:
    """
    策略进化引擎
    
    跟踪策略有效性，优化意图识别和路由策略。
    """
    
    def __init__(self, db_path: str = "data/strategy_evolution.db"):
        self.db_path = db_path
        self._init_database()
        logger.info("🎯 策略进化引擎已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS intent_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    intent_type TEXT,
                    pattern_text TEXT,
                    success_rate REAL,
                    sample_count INTEGER,
                    confidence REAL,
                    created_at TEXT,
                    updated_at TEXT,
                    status TEXT
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_intent_type ON intent_patterns(intent_type)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_pattern_status ON intent_patterns(status)
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS router_strategies (
                    strategy_id TEXT PRIMARY KEY,
                    strategy_type TEXT,
                    configuration TEXT,
                    success_count INTEGER,
                    failure_count INTEGER,
                    avg_confidence REAL,
                    created_at TEXT,
                    updated_at TEXT,
                    status TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT,
                    performance_score REAL,
                    context TEXT,
                    timestamp TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS intent_transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_intent TEXT,
                    to_intent TEXT,
                    transition_count INTEGER,
                    success_count INTEGER,
                    last_seen TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS strategy_recommendations (
                    recommendation_id TEXT PRIMARY KEY,
                    strategy_type TEXT,
                    current_config TEXT,
                    recommended_config TEXT,
                    reason TEXT,
                    expected_improvement REAL,
                    status TEXT,
                    created_at TEXT
                )
            ''')
            
            conn.commit()
    
    def record_intent_result(self, intent_type: str, pattern_text: str, 
                            success: bool, confidence: float = 0.7,
                            context: Dict = None) -> str:
        """
        记录意图识别结果
        
        Args:
            intent_type: 意图类型
            pattern_text: 匹配的模式
            success: 是否成功
            confidence: 置信度
            context: 上下文信息
        
        Returns:
            pattern_id: 模式ID
        """
        pattern_id = hashlib.md5(
            f"{intent_type}{pattern_text}".encode()
        ).hexdigest()[:12]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT success_rate, sample_count, confidence
                FROM intent_patterns
                WHERE pattern_id = ?
            ''', (pattern_id,))
            row = cursor.fetchone()
            
            if row:
                old_rate = row[0]
                sample_count = row[1] + 1
                old_confidence = row[2]
                new_rate = (old_rate * (sample_count - 1) + (1 if success else 0)) / sample_count
                new_confidence = min(1.0, old_confidence + 0.01 if success else max(0.0, old_confidence - 0.01))
                
                conn.execute('''
                    UPDATE intent_patterns
                    SET success_rate = ?, sample_count = ?, confidence = ?, updated_at = ?
                    WHERE pattern_id = ?
                ''', (new_rate, sample_count, new_confidence, datetime.now().isoformat(), pattern_id))
            else:
                conn.execute('''
                    INSERT INTO intent_patterns
                    (pattern_id, intent_type, pattern_text, success_rate,
                     sample_count, confidence, created_at, updated_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pattern_id,
                    intent_type,
                    pattern_text[:100],
                    1.0 if success else 0.0,
                    1,
                    confidence,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    'active'
                ))
            
            conn.commit()
        
        logger.debug(f"意图模式记录: {intent_type} -> {pattern_id} (成功={success})")
        return pattern_id
    
    def record_intent_transition(self, from_intent: str, to_intent: str, success: bool):
        """记录意图转换"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT transition_count, success_count
                FROM intent_transitions
                WHERE from_intent = ? AND to_intent = ?
            ''', (from_intent, to_intent))
            row = cursor.fetchone()
            
            if row:
                new_count = row[0] + 1
                new_success = row[1] + (1 if success else 0)
                conn.execute('''
                    UPDATE intent_transitions
                    SET transition_count = ?, success_count = ?, last_seen = ?
                    WHERE from_intent = ? AND to_intent = ?
                ''', (new_count, new_success, datetime.now().isoformat(), from_intent, to_intent))
            else:
                conn.execute('''
                    INSERT INTO intent_transitions
                    (from_intent, to_intent, transition_count, success_count, last_seen)
                    VALUES (?, ?, ?, ?, ?)
                ''', (from_intent, to_intent, 1, 1 if success else 0, datetime.now().isoformat()))
            
            conn.commit()
    
    def record_router_result(self, strategy_type: str, configuration: Dict,
                            success: bool, confidence: float = 0.7,
                            performance_score: float = None) -> str:
        """
        记录路由结果
        
        Args:
            strategy_type: 策略类型
            configuration: 配置
            success: 是否成功
            confidence: 置信度
            performance_score: 性能分数
        
        Returns:
            strategy_id: 策略ID
        """
        strategy_id = hashlib.md5(
            f"{strategy_type}{json.dumps(configuration)}".encode()
        ).hexdigest()[:12]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT success_count, failure_count, avg_confidence
                FROM router_strategies
                WHERE strategy_id = ?
            ''', (strategy_id,))
            row = cursor.fetchone()
            
            if row:
                success_count = row[0] + (1 if success else 0)
                failure_count = row[1] + (0 if success else 1)
                total = success_count + failure_count
                avg_confidence = (row[2] * (total - 1) + confidence) / total
                
                conn.execute('''
                    UPDATE router_strategies
                    SET success_count = ?, failure_count = ?, avg_confidence = ?, updated_at = ?
                    WHERE strategy_id = ?
                ''', (success_count, failure_count, avg_confidence, datetime.now().isoformat(), strategy_id))
            else:
                conn.execute('''
                    INSERT INTO router_strategies
                    (strategy_id, strategy_type, configuration, success_count,
                     failure_count, avg_confidence, created_at, updated_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    strategy_id,
                    strategy_type,
                    json.dumps(configuration),
                    1 if success else 0,
                    0 if success else 1,
                    confidence,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    'active'
                ))
            
            if performance_score is not None:
                conn.execute('''
                    INSERT INTO strategy_performance
                    (strategy_id, performance_score, context, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (strategy_id, performance_score, json.dumps(configuration), datetime.now().isoformat()))
            
            conn.commit()
        
        logger.debug(f"路由策略记录: {strategy_type} -> {strategy_id} (成功={success})")
        return strategy_id
    
    def get_intent_optimizations(self, limit: int = 10) -> List[Dict]:
        """
        获取意图识别优化建议
        
        返回成功率最低的模式，建议优化
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT pattern_id, intent_type, pattern_text,
                       success_rate, sample_count, confidence
                FROM intent_patterns
                WHERE sample_count >= 3 AND status = 'active'
                ORDER BY success_rate ASC, confidence ASC
                LIMIT ?
            ''', (limit,))
            
            optimizations = []
            for row in cursor.fetchall():
                opt = dict(row)
                
                if opt['success_rate'] < 0.5:
                    opt['recommendation'] = "考虑废弃或重构此模式"
                    opt['priority'] = "high"
                elif opt['success_rate'] < 0.7:
                    opt['recommendation'] = "需要更多样本或调整匹配规则"
                    opt['priority'] = "medium"
                else:
                    opt['recommendation'] = "监控性能变化"
                    opt['priority'] = "low"
                
                optimizations.append(opt)
            
            return optimizations
    
    def get_router_optimizations(self, limit: int = 5) -> List[Dict]:
        """
        获取路由优化建议
        
        返回成功率最低的策略，建议优化
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT strategy_id, strategy_type, configuration,
                       success_count, failure_count, avg_confidence
                FROM router_strategies
                WHERE success_count + failure_count >= 5
                ORDER BY CAST(success_count AS FLOAT) / (success_count + failure_count) ASC
                LIMIT ?
            ''', (limit,))
            
            optimizations = []
            for row in cursor.fetchall():
                opt = dict(row)
                total = opt['success_count'] + opt['failure_count']
                success_rate = opt['success_count'] / total if total > 0 else 0.0
                opt['success_rate'] = success_rate
                
                if success_rate < 0.5:
                    opt['recommendation'] = "考虑更换路由策略"
                    opt['priority'] = "high"
                elif success_rate < 0.7:
                    opt['recommendation'] = "调整配置参数"
                    opt['priority'] = "medium"
                else:
                    opt['recommendation'] = "保持当前配置"
                    opt['priority'] = "low"
                
                optimizations.append(opt)
            
            return optimizations
    
    def generate_strategy_recommendation(self, strategy_type: str) -> Dict:
        """生成策略推荐"""
        optimizations = self.get_router_optimizations(limit=10)
        
        type_opts = [o for o in optimizations if o['strategy_type'] == strategy_type]
        
        if not type_opts:
            return {
                "strategy_type": strategy_type,
                "recommendation": "无足够数据",
                "confidence": 0.0
            }
        
        best = max(type_opts, key=lambda x: x['success_rate'])
        worst = min(type_opts, key=lambda x: x['success_rate'])
        
        recommendation = {
            "strategy_type": strategy_type,
            "best_config": json.loads(best['configuration']) if best['configuration'] else {},
            "best_success_rate": best['success_rate'],
            "worst_config": json.loads(worst['configuration']) if worst['configuration'] else {},
            "worst_success_rate": worst['success_rate'],
            "recommendation": f"推荐使用成功率 {best['success_rate']:.1%} 的配置",
            "confidence": best['avg_confidence']
        }
        
        return recommendation
    
    def deprecate_pattern(self, pattern_id: str, reason: str = "") -> bool:
        """废弃一个模式"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE intent_patterns
                SET status = 'deprecated', updated_at = ?
                WHERE pattern_id = ?
            ''', (datetime.now().isoformat(), pattern_id))
            conn.commit()
        
        logger.info(f"模式已废弃: {pattern_id} - {reason}")
        return True
    
    def activate_pattern(self, pattern_id: str) -> bool:
        """激活一个模式"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE intent_patterns
                SET status = 'active', updated_at = ?
                WHERE pattern_id = ?
            ''', (datetime.now().isoformat(), pattern_id))
            conn.commit()
        
        logger.info(f"模式已激活: {pattern_id}")
        return True
    
    def get_intent_transitions(self) -> List[Dict]:
        """获取意图转换统计"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT from_intent, to_intent, transition_count, success_count,
                       CAST(success_count AS FLOAT) / transition_count as success_rate
                FROM intent_transitions
                WHERE transition_count >= 2
                ORDER BY transition_count DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("SELECT COUNT(*) as total FROM intent_patterns")
            total_patterns = cursor.fetchone()['total']
            
            cursor = conn.execute('''
                SELECT intent_type, 
                       AVG(success_rate) as avg_rate,
                       COUNT(*) as count
                FROM intent_patterns
                WHERE sample_count >= 3
                GROUP BY intent_type
            ''')
            by_type = [dict(row) for row in cursor.fetchall()]
            
            cursor = conn.execute('''
                SELECT strategy_type, 
                       SUM(success_count) as total_success,
                       SUM(failure_count) as total_failure,
                       AVG(avg_confidence) as avg_confidence
                FROM router_strategies
                GROUP BY strategy_type
            ''')
            router_stats = [dict(row) for row in cursor.fetchall()]
            
            cursor = conn.execute('''
                SELECT status, COUNT(*) as count
                FROM intent_patterns
                GROUP BY status
            ''')
            by_status = [dict(row) for row in cursor.fetchall()]
            
            return {
                "total_intent_patterns": total_patterns,
                "intent_by_type": by_type,
                "router_statistics": router_stats,
                "patterns_by_status": by_status
            }
    
    def get_evolution_report(self) -> Dict:
        """获取进化报告"""
        stats = self.get_statistics()
        intent_opts = self.get_intent_optimizations(limit=5)
        router_opts = self.get_router_optimizations(limit=5)
        transitions = self.get_intent_transitions()
        
        recommendations = []
        
        high_priority_intent = [o for o in intent_opts if o.get('priority') == 'high']
        if high_priority_intent:
            recommendations.append({
                "type": "intent_optimization",
                "message": f"有 {len(high_priority_intent)} 个高优先级意图模式需要优化",
                "priority": "high",
                "action": "review_intent_patterns"
            })
        
        high_priority_router = [o for o in router_opts if o.get('priority') == 'high']
        if high_priority_router:
            recommendations.append({
                "type": "router_optimization",
                "message": f"有 {len(high_priority_router)} 个高优先级路由策略需要优化",
                "priority": "high",
                "action": "review_router_strategies"
            })
        
        if transitions:
            low_success_transitions = [
                t for t in transitions
                if t['success_rate'] < 0.5
            ]
            if low_success_transitions:
                recommendations.append({
                    "type": "transition_analysis",
                    "message": f"有 {len(low_success_transitions)} 个低成功率意图转换",
                    "priority": "medium",
                    "action": "analyze_transitions"
                })
        
        return {
            "statistics": stats,
            "intent_optimizations": intent_opts,
            "router_optimizations": router_opts,
            "intent_transitions": transitions[:10],
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }


_strategy_evolution_engine: Optional[StrategyEvolutionEngine] = None


def get_strategy_evolution_engine() -> StrategyEvolutionEngine:
    """获取策略进化引擎单例"""
    global _strategy_evolution_engine
    if _strategy_evolution_engine is None:
        _strategy_evolution_engine = StrategyEvolutionEngine()
    return _strategy_evolution_engine