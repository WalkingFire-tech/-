"""
学习反思引擎
让系统能够审视自己的学习行为，回答"我为什么学、学得好不好、下次怎么改进"
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import sqlite3
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class LearningEvent:
    """学习事件"""
    event_id: str
    event_type: str
    timestamp: str
    question: str
    action_taken: str
    result: str
    knowledge_gained: int
    confidence_before: float
    confidence_after: float
    improvement: float
    metadata: Dict = field(default_factory=dict)


@dataclass
class ReflectionResult:
    """反思结果"""
    period: str
    total_events: int
    success_rate: float
    avg_improvement: float
    knowledge_absorbed: int
    knowledge_rejected: int
    knowledge_pending: int
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    generated_at: str


class LearningReflector:
    """
    学习反思引擎
    
    让系统能够：
    1. 反思单次学习事件
    2. 生成学习报告
    3. 识别行为模式
    4. 提出改进建议
    """
    
    def __init__(self, db_path: str = "data/learning_reflection.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS learning_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT UNIQUE NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    question TEXT,
                    action_taken TEXT,
                    result TEXT,
                    knowledge_gained INTEGER DEFAULT 0,
                    confidence_before REAL DEFAULT 0,
                    confidence_after REAL DEFAULT 0,
                    improvement REAL DEFAULT 0,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    total_events INTEGER,
                    success_rate REAL,
                    avg_improvement REAL,
                    knowledge_absorbed INTEGER,
                    knowledge_rejected INTEGER,
                    knowledge_pending INTEGER,
                    strengths TEXT,
                    weaknesses TEXT,
                    recommendations TEXT
                )
            ''')
            
            conn.commit()
        logger.info(f"🪞 学习反思引擎已初始化: {self.db_path}")
    
    def record_learning_event(
        self,
        event_type: str,
        question: str,
        action_taken: str,
        result: str,
        knowledge_gained: int = 0,
        confidence_before: float = 0.0,
        confidence_after: float = 0.0,
        metadata: Dict = None
    ) -> str:
        """记录学习事件"""
        event_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        improvement = confidence_after - confidence_before
        timestamp = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO learning_events
                (event_id, event_type, timestamp, question, action_taken, result,
                 knowledge_gained, confidence_before, confidence_after, improvement, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_id, event_type, timestamp, question, action_taken, result,
                knowledge_gained, confidence_before, confidence_after, improvement,
                json.dumps(metadata or {}, ensure_ascii=False)
            ))
            conn.commit()
        
        logger.info(f"📝 学习事件已记录: {event_type} - {result}")
        return event_id
    
    def reflect_on_learning(self, event_id: str) -> Dict:
        """对一次学习事件进行反思"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                'SELECT * FROM learning_events WHERE event_id = ?',
                (event_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return {'error': '事件不存在'}
            
            event = dict(row)
        
        effectiveness = self._evaluate_effectiveness(event)
        improvement_suggestions = self._generate_improvement_suggestions(event)
        strategy_adjustments = self._suggest_strategy_adjustments(event)
        
        reflection = {
            'event_id': event_id,
            'event_type': event['event_type'],
            'effectiveness': effectiveness,
            'improvement_suggestions': improvement_suggestions,
            'strategy_adjustments': strategy_adjustments,
            'reflected_at': datetime.now().isoformat()
        }
        
        logger.info(f"🪞 学习事件反思完成: {event_id}")
        return reflection
    
    def _evaluate_effectiveness(self, event: Dict) -> Dict:
        """评估学习效果"""
        if event['result'] == 'success':
            return {'rating': 'high', 'score': 0.9, 'reason': '学习成功，知识已吸收'}
        elif event['result'] == 'partial':
            return {'rating': 'medium', 'score': 0.5, 'reason': '部分成功，需要进一步验证'}
        else:
            return {'rating': 'low', 'score': 0.1, 'reason': '学习失败，需要调整策略'}
    
    def _generate_improvement_suggestions(self, event: Dict) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if event['result'] == 'failed':
            suggestions.extend(["尝试其他知识源", "调整查询策略", "检查知识相关性"])
        
        if event['improvement'] < 5.0:
            suggestions.extend(["增加注入知识数量", "提高知识质量阈值"])
        
        if event['knowledge_gained'] == 0:
            suggestions.extend(["扩展搜索范围", "使用不同的关键词"])
        
        return suggestions
    
    def _suggest_strategy_adjustments(self, event: Dict) -> Dict:
        """建议策略调整"""
        adjustments = {}
        
        if event['event_type'] == 'external_learn' and event['result'] == 'failed':
            adjustments['source_priority'] = '尝试其他学习源'
            adjustments['query_strategy'] = '优化查询关键词'
        
        if event['event_type'] == 'injection' and event['improvement'] < 5.0:
            adjustments['injection_threshold'] = '降低注入阈值'
            adjustments['verification_criteria'] = '调整验证标准'
        
        return adjustments
    
    def generate_learning_report(self, period: str = "week") -> ReflectionResult:
        """生成学习报告"""
        now = datetime.now()
        if period == "day":
            start_time = now - timedelta(days=1)
        elif period == "week":
            start_time = now - timedelta(weeks=1)
        elif period == "month":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(weeks=1)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM learning_events WHERE timestamp >= ? ORDER BY timestamp DESC
            ''', (start_time.isoformat(),))
            events = [dict(row) for row in cursor.fetchall()]
        
        total_events = len(events)
        if total_events == 0:
            return ReflectionResult(
                period=period, total_events=0, success_rate=0, avg_improvement=0,
                knowledge_absorbed=0, knowledge_rejected=0, knowledge_pending=0,
                strengths=[], weaknesses=[], recommendations=["暂无学习事件"],
                generated_at=datetime.now().isoformat()
            )
        
        success_count = sum(1 for e in events if e['result'] == 'success')
        partial_count = sum(1 for e in events if e['result'] == 'partial')
        failed_count = sum(1 for e in events if e['result'] == 'failed')
        
        success_rate = success_count / total_events
        avg_improvement = sum(e['improvement'] for e in events) / total_events
        
        strengths = self._identify_strengths(events)
        weaknesses = self._identify_weaknesses(events)
        recommendations = self._generate_recommendations(events, success_rate, avg_improvement)
        
        result = ReflectionResult(
            period=period, total_events=total_events, success_rate=success_rate,
            avg_improvement=avg_improvement, knowledge_absorbed=success_count,
            knowledge_rejected=failed_count, knowledge_pending=partial_count,
            strengths=strengths, weaknesses=weaknesses, recommendations=recommendations,
            generated_at=datetime.now().isoformat()
        )
        
        self._save_reflection(result)
        logger.info(f"📊 学习报告已生成: {period} - {total_events}个事件")
        return result
    
    def _identify_strengths(self, events: List[Dict]) -> List[str]:
        """识别优势"""
        strengths = []
        type_stats = {}
        for event in events:
            etype = event['event_type']
            if etype not in type_stats:
                type_stats[etype] = {'success': 0, 'total': 0}
            type_stats[etype]['total'] += 1
            if event['result'] == 'success':
                type_stats[etype]['success'] += 1
        
        for etype, stats in type_stats.items():
            rate = stats['success'] / stats['total']
            if rate > 0.7:
                strengths.append(f"{etype}成功率高({rate:.0%})")
        
        avg_improvement = sum(e['improvement'] for e in events) / len(events)
        if avg_improvement > 10:
            strengths.append(f"平均改进幅度大({avg_improvement:.1f}分)")
        
        return strengths
    
    def _identify_weaknesses(self, events: List[Dict]) -> List[str]:
        """识别劣势"""
        weaknesses = []
        type_stats = {}
        for event in events:
            etype = event['event_type']
            if etype not in type_stats:
                type_stats[etype] = {'failed': 0, 'total': 0}
            type_stats[etype]['total'] += 1
            if event['result'] == 'failed':
                type_stats[etype]['failed'] += 1
        
        for etype, stats in type_stats.items():
            rate = stats['failed'] / stats['total']
            if rate > 0.3:
                weaknesses.append(f"{etype}失败率高({rate:.0%})")
        
        zero_knowledge = sum(1 for e in events if e['knowledge_gained'] == 0)
        if zero_knowledge > len(events) * 0.3:
            weaknesses.append(f"零知识事件多({zero_knowledge}个)")
        
        return weaknesses
    
    def _generate_recommendations(self, events: List[Dict], success_rate: float, avg_improvement: float) -> List[str]:
        """生成总体建议"""
        recommendations = []
        
        if success_rate < 0.5:
            recommendations.append("整体成功率偏低，建议优化学习策略")
        
        if avg_improvement < 5.0:
            recommendations.append("平均改进幅度不足，建议提高知识质量")
        
        type_counts = {}
        for event in events:
            etype = event['event_type']
            type_counts[etype] = type_counts.get(etype, 0) + 1
        
        if type_counts.get('correction', 0) > len(events) * 0.3:
            recommendations.append("纠错事件较多，建议改进初始回答质量")
        
        if not recommendations:
            recommendations.append("学习状态良好，继续保持")
        
        return recommendations
    
    def _save_reflection(self, result: ReflectionResult):
        """保存反思记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO reflections
                (period, generated_at, total_events, success_rate, avg_improvement,
                 knowledge_absorbed, knowledge_rejected, knowledge_pending,
                 strengths, weaknesses, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.period, result.generated_at, result.total_events, result.success_rate,
                result.avg_improvement, result.knowledge_absorbed, result.knowledge_rejected,
                result.knowledge_pending,
                json.dumps(result.strengths, ensure_ascii=False),
                json.dumps(result.weaknesses, ensure_ascii=False),
                json.dumps(result.recommendations, ensure_ascii=False)
            ))
            conn.commit()
    
    def format_report(self, result: ReflectionResult) -> str:
        """格式化报告为可读文本"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"  学习反思报告 ({result.period})")
        lines.append(f"  生成时间: {result.generated_at}")
        lines.append("=" * 70)
        
        lines.append(f"\n【总体统计】")
        lines.append(f"  总学习事件: {result.total_events}")
        lines.append(f"  成功率: {result.success_rate:.1%}")
        lines.append(f"  平均改进: {result.avg_improvement:.1f} 分")
        
        lines.append(f"\n【知识状态】")
        lines.append(f"  ✅ 已吸收: {result.knowledge_absorbed}")
        lines.append(f"  ⏳ 待验证: {result.knowledge_pending}")
        lines.append(f"  ❌ 已拒绝: {result.knowledge_rejected}")
        
        if result.strengths:
            lines.append(f"\n【优势】")
            for s in result.strengths:
                lines.append(f"  💪 {s}")
        
        if result.weaknesses:
            lines.append(f"\n【劣势】")
            for w in result.weaknesses:
                lines.append(f"  ⚠️ {w}")
        
        if result.recommendations:
            lines.append(f"\n【建议】")
            for i, r in enumerate(result.recommendations, 1):
                lines.append(f"  {i}. {r}")
        
        lines.append("\n" + "=" * 70)
        return "\n".join(lines)


learning_reflector = LearningReflector()