"""
元学习层 - 观察学习模式，调整学习策略

对应六层架构的 L6 内省层扩展
职责：从"报告状态"升级为"驱动调整"
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from core.ports.adapters import get_storage_port
import json
import hashlib
import threading
import time
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class LearningObservation:
    """学习观察记录"""
    observation_id: str
    layer_name: str
    metric_name: str
    old_value: float
    new_value: float
    delta: float
    strategy_used: str
    effectiveness: float
    timestamp: str


@dataclass
class LearningPattern:
    """学习模式"""
    pattern_id: str
    pattern_type: str
    description: str
    confidence: float
    affected_metrics: List[str]
    recommendation: str
    detected_at: str
    status: str


class MetaLearner:
    """
    元学习器
    
    观察各层的学习模式，识别趋势，提出优化建议。
    """
    
    def __init__(self, db_path: str = "data/meta_learning.db"):
        self.db_path = db_path
        self._init_database()
        
        self._running = False
        self._thread = None
        self._last_pattern_detection: Optional[datetime] = None
        self._pattern_detection_interval = 3600
        
        logger.info("🧠 元学习器已初始化")
    
    def _init_database(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        db = get_storage_port(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS learning_observations (
                id TEXT PRIMARY KEY,
                layer_name TEXT,
                metric_name TEXT,
                old_value REAL,
                new_value REAL,
                delta REAL,
                strategy_used TEXT,
                effectiveness REAL,
                timestamp TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_layer_metric ON learning_observations(layer_name, metric_name);
            CREATE INDEX IF NOT EXISTS idx_observation_time ON learning_observations(timestamp);
            CREATE TABLE IF NOT EXISTS learning_patterns (
                id TEXT PRIMARY KEY,
                pattern_type TEXT,
                description TEXT,
                confidence REAL,
                affected_metrics TEXT,
                recommendation TEXT,
                detected_at TEXT,
                status TEXT
            );
            CREATE TABLE IF NOT EXISTS learning_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adjustment_type TEXT,
                target_layer TEXT,
                parameter_name TEXT,
                old_value REAL,
                new_value REAL,
                reason TEXT,
                effectiveness REAL,
                applied_at TEXT
            );
            CREATE TABLE IF NOT EXISTS layer_metrics (
                layer_name TEXT,
                metric_name TEXT,
                current_value REAL,
                trend TEXT,
                last_updated TEXT,
                PRIMARY KEY (layer_name, metric_name)
            );
            CREATE TABLE IF NOT EXISTS learning_sessions (
                session_id TEXT PRIMARY KEY,
                start_time TEXT,
                end_time TEXT,
                observations_count INTEGER,
                patterns_detected INTEGER,
                adjustments_applied INTEGER,
                status TEXT
            )
        ''')
    
    def observe(self, layer_name: str, metric_name: str, 
                old_value: float, new_value: float, 
                strategy_used: str = "unknown") -> str:
        """
        记录一次学习观察
        
        Args:
            layer_name: 层名称 (behavior_evolution, knowledge_evolution, strategy_evolution)
            metric_name: 指标名称
            old_value: 旧值
            new_value: 新值
            strategy_used: 使用的策略
        
        Returns:
            observation_id
        """
        delta = new_value - old_value
        effectiveness = self._calculate_effectiveness(delta, metric_name)
        
        observation_id = hashlib.md5(
            f"{layer_name}{metric_name}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        db = get_storage_port(self.db_path)
        db.execute('''
            INSERT INTO learning_observations
            (id, layer_name, metric_name, old_value, new_value,
             delta, strategy_used, effectiveness, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            observation_id,
            layer_name,
            metric_name,
            old_value,
            new_value,
            delta,
            strategy_used,
            effectiveness,
            datetime.now().isoformat()
        ), commit=True)
        
        trend = self._calculate_trend(db, layer_name, metric_name, delta)
        
        db.execute('''
            INSERT OR REPLACE INTO layer_metrics
            (layer_name, metric_name, current_value, trend, last_updated)
            VALUES (?, ?, ?, ?, ?)
        ''', (layer_name, metric_name, new_value, trend, datetime.now().isoformat()), commit=True)
        
        logger.warning(f"学习观察: {layer_name}.{metric_name} = {new_value:.2f} (Δ={delta:+.2f})")
        return observation_id
    
    def _calculate_effectiveness(self, delta: float, metric_name: str) -> float:
        """计算策略有效性"""
        positive_indicators = ["score", "quality", "rate", "confidence", "success", "effectiveness"]
        negative_indicators = ["time", "length", "count", "error", "failure", "conflict"]
        
        metric_lower = metric_name.lower()
        
        if any(kw in metric_lower for kw in positive_indicators):
            return min(1.0, max(0.0, 0.5 + delta * 2))
        elif any(kw in metric_lower for kw in negative_indicators):
            return min(1.0, max(0.0, 0.5 - delta * 2))
        
        return min(1.0, max(0.0, 0.5 + delta))
    
    def _calculate_trend(self, db, layer_name: str, metric_name: str, current_delta: float) -> str:
        """计算趋势"""
        rows = db.query('''
            SELECT delta FROM learning_observations
            WHERE layer_name = ? AND metric_name = ?
            ORDER BY timestamp DESC
            LIMIT 5
        ''', (layer_name, metric_name))
        
        recent_deltas = [row[0] for row in rows if row[0] is not None]
        recent_deltas.append(current_delta)
        
        if len(recent_deltas) < 3:
            return "insufficient_data"
        
        avg_delta = sum(recent_deltas) / len(recent_deltas)
        
        if avg_delta > 0.02:
            return "improving"
        elif avg_delta < -0.02:
            return "declining"
        
        variance = sum((d - avg_delta) ** 2 for d in recent_deltas) / len(recent_deltas)
        if variance > 0.01:
            return "volatile"
        
        return "stable"
    
    def detect_patterns(self) -> List[LearningPattern]:
        """
        检测学习模式
        
        分析各指标的变化趋势，识别模式。
        """
        patterns = []
        
        db = get_storage_port(self.db_path)
        
        rows = db.query('''
            SELECT metric_name, 
                   AVG(delta) as avg_delta,
                   COUNT(*) as sample_count,
                   MAX(delta) as max_delta,
                   MIN(delta) as min_delta
            FROM learning_observations
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY metric_name
            HAVING sample_count >= 3
        ''')
        
        for row in rows:
            metric_name = row['metric_name']
            avg_delta = row['avg_delta'] if row['avg_delta'] is not None else 0.0
            sample_count = row['sample_count']
            max_delta = row['max_delta'] if row['max_delta'] is not None else 0.0
            min_delta = row['min_delta'] if row['min_delta'] is not None else 0.0
            
            recent_rows = db.query('''
                SELECT delta FROM learning_observations
                WHERE metric_name = ?
                ORDER BY timestamp DESC
                LIMIT 10
            ''', (metric_name,))
            recent_deltas = [r2[0] for r2 in recent_rows if r2[0] is not None]
            
            std_dev = 0.0
            if len(recent_deltas) > 1:
                mean = sum(recent_deltas) / len(recent_deltas)
                std_dev = (sum((d - mean) ** 2 for d in recent_deltas) / len(recent_deltas)) ** 0.5
            
            pattern_type = "stable"
            confidence = 0.6
            description = f"指标 {metric_name} 保持稳定"
            recommendation = "继续当前策略"
            
            if avg_delta > 0.03:
                pattern_type = "improving"
                confidence = min(1.0, 0.6 + sample_count * 0.02)
                description = f"指标 {metric_name} 持续改善 (平均变化: {avg_delta:.3f})"
                recommendation = "保持当前学习方向"
            elif avg_delta < -0.03:
                pattern_type = "declining"
                confidence = min(1.0, 0.6 + sample_count * 0.02)
                description = f"指标 {metric_name} 持续下降 (平均变化: {avg_delta:.3f})"
                recommendation = "需要调整当前学习策略"
            
            if std_dev > 0.15 and sample_count > 3:
                pattern_type = "volatile"
                confidence = 0.7
                description = f"指标 {metric_name} 波动较大 (标准差: {std_dev:.3f})"
                recommendation = "建议增加学习样本量，减少波动"
            
            if len(recent_deltas) >= 4:
                sign_changes = 0
                for i in range(1, len(recent_deltas)):
                    if (recent_deltas[i] > 0) != (recent_deltas[i-1] > 0):
                        sign_changes += 1
                
                if sign_changes >= 2:
                    pattern_type = "cyclical"
                    confidence = 0.65
                    description = f"指标 {metric_name} 呈现周期性波动"
                    recommendation = "建议调整学习策略以平滑波动"
            
            if max_delta > 0.3 and min_delta < -0.3:
                pattern_type = "extreme_variance"
                confidence = 0.75
                description = f"指标 {metric_name} 存在极端变化"
                recommendation = "检查异常情况，可能需要干预"
            
            pattern_id = hashlib.md5(
                f"{metric_name}{datetime.now().isoformat()}".encode()
            ).hexdigest()[:12]
            
            pattern = LearningPattern(
                pattern_id=pattern_id,
                pattern_type=pattern_type,
                description=description,
                confidence=confidence,
                affected_metrics=[metric_name],
                recommendation=recommendation,
                detected_at=datetime.now().isoformat(),
                status='active'
            )
            patterns.append(pattern)
        
        for pattern in patterns:
            db.execute('''
                INSERT OR REPLACE INTO learning_patterns
                (id, pattern_type, description, confidence,
                 affected_metrics, recommendation, detected_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pattern.pattern_id,
                pattern.pattern_type,
                pattern.description,
                pattern.confidence,
                json.dumps(pattern.affected_metrics),
                pattern.recommendation,
                pattern.detected_at,
                pattern.status
            ), commit=True)
        
        self._last_pattern_detection = datetime.now()
        logger.warning(f"检测到 {len(patterns)} 个学习模式")
        return patterns
    
    def get_active_patterns(self) -> List[LearningPattern]:
        """获取活跃的学习模式"""
        db = get_storage_port(self.db_path)
        rows = db.query('''
            SELECT * FROM learning_patterns
            WHERE status = 'active'
            ORDER BY confidence DESC
        ''')
        
        patterns = []
        for row in rows:
            patterns.append(LearningPattern(
                pattern_id=row['id'],
                pattern_type=row['pattern_type'],
                description=row['description'],
                confidence=row['confidence'],
                affected_metrics=json.loads(row['affected_metrics']) if row['affected_metrics'] else [],
                recommendation=row['recommendation'],
                detected_at=row['detected_at'],
                status=row['status']
            ))
        return patterns
    
    def apply_adjustment(self, adjustment_type: str, target_layer: str,
                         parameter_name: str, old_value: float, new_value: float,
                         reason: str) -> int:
        """
        应用一次策略调整
        
        Returns:
            adjustment_id
        """
        db = get_storage_port(self.db_path)
        cur = db.execute('''
            INSERT INTO learning_adjustments
            (adjustment_type, target_layer, parameter_name,
             old_value, new_value, reason, effectiveness, applied_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            adjustment_type,
            target_layer,
            parameter_name,
            old_value,
            new_value,
            reason,
            0.0,
            datetime.now().isoformat()
        ), commit=True)
        
        logger.info(f"策略调整: {target_layer}.{parameter_name} {old_value:.2f} -> {new_value:.2f} ({reason})")
        return cur.lastrowid
    
    def evaluate_adjustment(self, adjustment_id: int, effectiveness: float):
        """评估调整效果"""
        db = get_storage_port(self.db_path)
        db.execute('''
            UPDATE learning_adjustments
            SET effectiveness = ?
            WHERE id = ?
        ''', (effectiveness, adjustment_id), commit=True)
    
    def get_layer_metrics(self) -> List[Dict]:
        """获取各层指标"""
        db = get_storage_port(self.db_path)
        rows = db.query('''
            SELECT * FROM layer_metrics
            ORDER BY layer_name, metric_name
        ''')
        return [dict(row) for row in rows]
    
    def get_learning_report(self) -> Dict:
        """获取学习报告"""
        db = get_storage_port(self.db_path)
        
        total_observations = db.query_one("SELECT COUNT(*) as total FROM learning_observations")['total']
        
        active_patterns = self.get_active_patterns()
        
        recent_adjustments = [dict(row) for row in db.query('''
            SELECT * FROM learning_adjustments
            ORDER BY applied_at DESC
            LIMIT 10
        ''')]
        
        layer_summary = [dict(row) for row in db.query('''
            SELECT layer_name, 
                   AVG(effectiveness) as avg_effectiveness,
                   COUNT(*) as count
            FROM learning_observations
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY layer_name
        ''')]
        
        adjustment_effectiveness = [dict(row) for row in db.query('''
            SELECT adjustment_type,
                   AVG(effectiveness) as avg_effectiveness,
                   COUNT(*) as count
            FROM learning_adjustments
            WHERE effectiveness > 0
            GROUP BY adjustment_type
        ''')]
        
        return {
            "total_observations": total_observations,
            "active_patterns": [
                {
                    "type": p.pattern_type,
                    "description": p.description,
                    "confidence": p.confidence,
                    "recommendation": p.recommendation
                }
                for p in active_patterns
            ],
            "recent_adjustments": recent_adjustments,
            "layer_summary": layer_summary,
            "adjustment_effectiveness": adjustment_effectiveness,
            "timestamp": datetime.now().isoformat()
        }
    
    def start_auto_learning(self, interval_hours: int = 6):
        """
        启动自动学习模式
        
        Args:
            interval_hours: 检测间隔（小时）
        """
        if self._running:
            logger.warning("元学习自动模式已在运行")
            return
        
        self._running = True
        self._pattern_detection_interval = interval_hours * 3600
        self._thread = threading.Thread(target=self._auto_learning_loop, daemon=True)
        self._thread.start()
        logger.info(f"🔄 元学习自动模式已启动 (间隔: {interval_hours}小时)")
    
    def stop_auto_learning(self):
        """停止自动学习模式"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("🛑 元学习自动模式已停止")
    
    def _auto_learning_loop(self):
        """自动学习循环"""
        while self._running:
            try:
                patterns = self.detect_patterns()
                
                for pattern in patterns:
                    if pattern.pattern_type in ['declining', 'volatile', 'extreme_variance']:
                        self._handle_pattern(pattern)
                
                self._cleanup_old_data()
                
                time.sleep(self._pattern_detection_interval)
                
            except Exception as e:
                logger.error(f"自动学习循环异常: {e}")
                time.sleep(60)
    
    def _handle_pattern(self, pattern: LearningPattern):
        """处理检测到的模式"""
        if pattern.pattern_type == 'declining':
            self.apply_adjustment(
                adjustment_type="slow_down",
                target_layer="evolution",
                parameter_name="learning_rate",
                old_value=0.3,
                new_value=0.15,
                reason=f"检测到下降趋势: {pattern.description}"
            )
        
        elif pattern.pattern_type == 'volatile':
            self.apply_adjustment(
                adjustment_type="stabilize",
                target_layer="evolution",
                parameter_name="smoothing_factor",
                old_value=0.3,
                new_value=0.5,
                reason=f"检测到波动模式: {pattern.description}"
            )
        
        elif pattern.pattern_type == 'extreme_variance':
            self.apply_adjustment(
                adjustment_type="investigate",
                target_layer="evolution",
                parameter_name="anomaly_threshold",
                old_value=0.3,
                new_value=0.2,
                reason=f"检测到极端变化: {pattern.description}"
            )
    
    def _cleanup_old_data(self):
        """清理旧数据"""
        try:
            db = get_storage_port(self.db_path)
            cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
            
            db.execute('''
                DELETE FROM learning_observations
                WHERE timestamp < ?
            ''', (cutoff_date,), commit=True)
            
            db.execute('''
                UPDATE learning_patterns
                SET status = 'archived'
                WHERE detected_at < ? AND status = 'active'
            ''', (cutoff_date,), commit=True)
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        db = get_storage_port(self.db_path)
        
        total_observations = db.query_one("SELECT COUNT(*) as total FROM learning_observations")['total']
        
        total_adjustments = db.query_one("SELECT COUNT(*) as total FROM learning_adjustments")['total']
        
        patterns_by_type = [dict(row) for row in db.query('''
            SELECT pattern_type, COUNT(*) as count
            FROM learning_patterns
            WHERE status = 'active'
            GROUP BY pattern_type
        ''')]
        
        observations_by_layer = [dict(row) for row in db.query('''
            SELECT layer_name, COUNT(*) as count
            FROM learning_observations
            GROUP BY layer_name
        ''')]
        
        return {
            "total_observations": total_observations,
            "total_adjustments": total_adjustments,
            "patterns_by_type": patterns_by_type,
            "observations_by_layer": observations_by_layer
        }


_meta_learner: Optional[MetaLearner] = None


def get_meta_learner() -> MetaLearner:
    """获取元学习器单例"""
    global _meta_learner
    if _meta_learner is None:
        _meta_learner = MetaLearner()
    return _meta_learner
