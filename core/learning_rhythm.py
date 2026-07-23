"""
学习节奏感知 - 用预警替代硬限制

核心理念：
- 学习是有节奏的，不是均匀的
- 系统应该感知自己的学习状态
- 预警是为了发现问题，而不是阻止生长
- 限制是对行为的控制，预警是对意识的唤醒

预警模式 vs 硬限制：
- 硬限制：达到上限后停止学习
- 预警模式：达到阈值后发出信号，系统自行决定
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from core.ports.adapters import get_storage_port

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class LearningRhythm(Enum):
    """学习节奏状态"""
    NORMAL = "normal"
    ACCELERATING = "accelerating"
    SLOWING = "slowing"
    SURGE = "surge"
    FATIGUE = "fatigue"
    REFLECTING = "reflecting"


@dataclass
class LearningStatus:
    """学习状态"""
    today_count: int
    week_count: int
    month_count: int
    avg_daily: float
    trend: LearningRhythm
    alerts: List[str]
    quality_avg: float
    sources_distribution: Dict[str, int]


class LearningRhythmMonitor:
    """
    学习节奏监控器
    
    不限制学习，但监控学习节奏的变化，
    在异常时发出预警，让系统自行决定如何响应。
    """
    
    def __init__(self, db_path: str = "data/learning_rhythm.db"):
        self.db_path = Path(db_path)
        self._init_database()
        
        self.thresholds = {
            "daily_surge": 200,
            "weekly_surge": 500,
            "daily_minimum": 5,
            "quality_minimum": 0.5,
            "suspicious_change_rate": 2.0,
        }
        
        self._alert_handlers = []
        
        logger.info("🎵 学习节奏监控器已初始化（预警模式）")
    
    def _init_database(self):
        """初始化数据库"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        db = get_storage_port(str(self.db_path))
        db.execute('''
            CREATE TABLE IF NOT EXISTS learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                source TEXT,
                quality_score REAL,
                content_hash TEXT,
                alignment_status TEXT,
                metadata TEXT
            )
        ''')
        
        db.execute('''
            CREATE TABLE IF NOT EXISTS rhythm_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                alert_type TEXT,
                message TEXT,
                severity TEXT,
                action_taken TEXT,
                resolved INTEGER DEFAULT 0
            )
        ''')
        
        db.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON learning_records(timestamp)')
        db.execute('CREATE INDEX IF NOT EXISTS idx_source ON learning_records(source)', commit=True)
    
    def record(self, source: str, quality_score: float = 0.0, 
               content_hash: str = "", alignment_status: str = "pass",
               metadata: Dict = None) -> LearningStatus:
        """
        记录一次学习
        
        Returns:
            当前学习状态（包含预警）
        """
        metadata = metadata or {}
        
        db = get_storage_port(str(self.db_path))
        db.execute('''
            INSERT INTO learning_records
            (timestamp, source, quality_score, content_hash, alignment_status, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            source,
            quality_score,
            content_hash,
            alignment_status,
            json.dumps(metadata, ensure_ascii=False)
        ), commit=True)
        
        status = self.get_status()
        
        if status.alerts:
            self._handle_alerts(status.alerts)
        
        return status
    
    def get_status(self) -> LearningStatus:
        """获取当前学习状态（带预警）"""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)
        
        db = get_storage_port(str(self.db_path))
        
        today_row = db.query_one('''
            SELECT COUNT(*) as count, AVG(quality_score) as avg_quality
            FROM learning_records
            WHERE timestamp >= ?
        ''', (today_start.isoformat(),))
        today_count = today_row['count']
        today_quality = today_row['avg_quality'] or 0.0
        
        week_row = db.query_one('''
            SELECT COUNT(*) as count
            FROM learning_records
            WHERE timestamp >= ?
        ''', (week_start.isoformat(),))
        week_count = week_row['count']
        
        month_row = db.query_one('''
            SELECT COUNT(*) as count
            FROM learning_records
            WHERE timestamp >= ?
        ''', (month_start.isoformat(),))
        month_count = month_row['count']
        
        source_rows = db.query('''
            SELECT source, COUNT(*) as count
            FROM learning_records
            WHERE timestamp >= ?
            GROUP BY source
        ''', (week_start.isoformat(),))
        sources_distribution = {r['source']: r['count'] for r in source_rows}
        
        week_row2 = db.query_one('''
            SELECT COUNT(*) as count, AVG(quality_score) as avg_quality
            FROM learning_records
            WHERE timestamp >= ?
        ''', ((now - timedelta(days=7)).isoformat(),))
        avg_daily = week_row2['count'] / 7 if week_row2['count'] > 0 else 0
        week_quality = week_row2['avg_quality'] or 0.0
        
        rhythm = self._analyze_rhythm()
        
        alerts = self._generate_alerts(
            today_count, week_count, avg_daily, today_quality, rhythm
        )
        
        return LearningStatus(
            today_count=today_count,
            week_count=week_count,
            month_count=month_count,
            avg_daily=avg_daily,
            trend=rhythm,
            alerts=alerts,
            quality_avg=today_quality,
            sources_distribution=sources_distribution
        )
    
    def _analyze_rhythm(self) -> LearningRhythm:
        """分析学习节奏"""
        now = datetime.now()
        
        db = get_storage_port(str(self.db_path))
        
        daily_counts = []
        for i in range(7):
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            row = db.query_one('''
                SELECT COUNT(*) as count
                FROM learning_records
                WHERE timestamp >= ? AND timestamp < ?
            ''', (day_start.isoformat(), day_end.isoformat()))
            daily_counts.append(row['count'])
        
        daily_counts.reverse()
        
        if len(daily_counts) < 3:
            return LearningRhythm.NORMAL
        
        recent_3 = daily_counts[-3:]
        previous_3 = daily_counts[-6:-3] if len(daily_counts) >= 6 else daily_counts[:-3]
        
        if not previous_3:
            return LearningRhythm.NORMAL
        
        recent_avg = sum(recent_3) / len(recent_3)
        previous_avg = sum(previous_3) / len(previous_3)
        
        if previous_avg == 0:
            if recent_avg > 10:
                return LearningRhythm.SURGE
            return LearningRhythm.NORMAL
        
        change_rate = recent_avg / previous_avg
        
        if change_rate > 3.0:
            return LearningRhythm.SURGE
        elif change_rate > 1.5:
            return LearningRhythm.ACCELERATING
        elif change_rate < 0.3:
            return LearningRhythm.SLOWING
        elif recent_avg < 3 and previous_avg > 5:
            return LearningRhythm.REFLECTING
        else:
            return LearningRhythm.NORMAL
    
    def _generate_alerts(self, today: int, week: int, avg: float, 
                        quality: float, rhythm: LearningRhythm) -> List[str]:
        """生成预警信息"""
        alerts = []
        
        if today > self.thresholds["daily_surge"]:
            alerts.append(f"📈 今日学习量突增 ({today}条)，建议检查来源质量")
        
        if week > self.thresholds["weekly_surge"]:
            alerts.append(f"📊 本周学习量较高 ({week}条)，建议关注学习质量")
        
        if today < self.thresholds["daily_minimum"] and avg > 5:
            alerts.append(f"📉 今日学习量较低 ({today}条)，可能处于反思期")
        
        if quality < self.thresholds["quality_minimum"] and today > 10:
            alerts.append(f"⚠️ 今日学习质量偏低 ({quality:.2f})，建议提高验证深度")
        
        if rhythm == LearningRhythm.SURGE:
            alerts.append("🚨 检测到学习量突增，建议暂停并审查来源")
        
        if rhythm == LearningRhythm.ACCELERATING:
            alerts.append("⚡ 学习节奏加速中，注意质量把控")
        
        if rhythm == LearningRhythm.REFLECTING:
            alerts.append("💭 学习节奏放缓，可能进入反思期")
        
        return alerts
    
    def _handle_alerts(self, alerts: List[str]):
        """处理预警"""
        for alert in alerts:
            severity = "high" if "🚨" in alert else "medium" if "⚠️" in alert else "low"
            
            db = get_storage_port(str(self.db_path))
            db.execute('''
                INSERT INTO rhythm_alerts
                (timestamp, alert_type, message, severity)
                VALUES (?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                "rhythm_alert",
                alert,
                severity
            ), commit=True)
            
            logger.warning(f"⚠️ 学习预警: {alert}")
    
    def register_alert_handler(self, handler):
        """注册预警处理器"""
        self._alert_handlers.append(handler)
    
    def suggest_action(self, status: LearningStatus) -> Dict:
        """根据学习状态建议行动"""
        action = {
            "continue_learning": True,
            "reduce_speed": False,
            "pause_and_review": False,
            "increase_validation": False,
            "enter_reflection_mode": False,
            "reason": "学习状态正常"
        }
        
        if status.trend == LearningRhythm.SURGE:
            action.update({
                "pause_and_review": True,
                "reason": "学习量突增，建议暂停并审查来源"
            })
        
        elif status.trend == LearningRhythm.ACCELERATING:
            action.update({
                "reduce_speed": True,
                "increase_validation": True,
                "reason": "学习节奏加速，建议放慢并提高验证"
            })
        
        elif status.quality_avg < 0.5:
            action.update({
                "increase_validation": True,
                "reason": "学习质量偏低，建议提高验证深度"
            })
        
        elif status.trend == LearningRhythm.REFLECTING:
            action.update({
                "enter_reflection_mode": True,
                "reason": "学习节奏放缓，建议进入反思模式"
            })
        
        return action
    
    def get_learning_summary(self) -> Dict:
        """获取学习摘要"""
        status = self.get_status()
        action = self.suggest_action(status)
        
        return {
            "status": {
                "today": status.today_count,
                "week": status.week_count,
                "month": status.month_count,
                "avg_daily": round(status.avg_daily, 1),
                "quality_avg": round(status.quality_avg, 2),
                "trend": status.trend.value,
            },
            "alerts": status.alerts,
            "suggested_action": action,
            "sources": status.sources_distribution
        }


_rhythm_monitor: Optional[LearningRhythmMonitor] = None


def get_rhythm_monitor() -> LearningRhythmMonitor:
    global _rhythm_monitor
    if _rhythm_monitor is None:
        _rhythm_monitor = LearningRhythmMonitor()
    return _rhythm_monitor