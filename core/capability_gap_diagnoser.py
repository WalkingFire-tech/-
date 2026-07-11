"""
能力缺口诊断器
分析交互历史中的失败模式，识别系统能力缺口
这是通往"主动提案"的桥梁
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import Counter
from infrastructure.database_manager import DatabaseManager
import re
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class CapabilityGap:
    """能力缺口"""
    gap_type: str           # 缺口类型
    category: str           # 类别
    frequency: int          # 频率
    severity: float         # 严重程度 (0-1)
    examples: List[str]     # 示例问题
    suggested_module: str   # 建议的模块
    priority: int           # 优先级 (1-5)


@dataclass
class GapReport:
    """缺口报告"""
    period: str
    total_interactions: int
    failed_interactions: int
    failure_rate: float
    gaps: List[CapabilityGap]
    recommendations: List[str]
    generated_at: str


class CapabilityGapDiagnoser:
    """
    能力缺口诊断器
    
    功能：
    1. 统计未能回答的问题类型
    2. 按类别聚类（视觉类、专业类、事实类等）
    3. 识别用户行为中的隐含需求
    4. 映射到"感官模块库"中的可用模块
    5. 生成"能力缺口报告"
    """
    
    def __init__(self, db_path: str = "data/capability_gaps.db"):
        self.db_path = db_path
        self._init_database()
        
        # 问题类型模式
        self.patterns = {
            'visual': [
                r'图片', r'图像', r'照片', r'看图', r'识别图',
                r'视觉', r'画面', r'截图', r'.*\.png', r'.*\.jpg'
            ],
            'audio': [
                r'音频', r'声音', r'语音', r'听', r'说',
                r'录音', r'音乐', r'.*\.mp3', r'.*\.wav'
            ],
            'code': [
                r'代码', r'编程', r'程序', r'函数', r'算法',
                r'调试', r'运行', r'错误', r'bug'
            ],
            'math': [
                r'计算', r'数学', r'公式', r'方程', r'求解',
                r'数值', r'统计', r'概率'
            ],
            'knowledge': [
                r'什么是', r'解释', r'介绍', r'说明', r'定义',
                r'原理', r'概念', r'理论'
            ],
            'recommendation': [
                r'推荐', r'建议', r'应该', r'如何选择',
                r'哪个好', r'比较'
            ],
            'external_data': [
                r'查询', r'搜索', r'获取', r'最新', r'实时',
                r'当前', r'今天'
            ]
        }
        
        # 模块映射
        self.module_mapping = {
            'visual': '视觉模块 (Vision Module)',
            'audio': '语音模块 (Audio Module)',
            'code': '代码执行模块 (Code Execution)',
            'math': '数学计算模块 (Math Calculator)',
            'knowledge': '知识库扩展 (Knowledge Expansion)',
            'recommendation': '推荐引擎 (Recommendation Engine)',
            'external_data': '实时数据模块 (Real-time Data)'
        }
    
    def _init_database(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                question TEXT NOT NULL,
                response TEXT,
                success INTEGER DEFAULT 0,
                failure_type TEXT,
                confidence REAL DEFAULT 0,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS gap_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                total_interactions INTEGER,
                failed_interactions INTEGER,
                failure_rate REAL,
                gaps TEXT,
                recommendations TEXT
            );
        ''')
        logger.info(f"🔍 能力缺口诊断器已初始化: {self.db_path}")
    
    def record_interaction(
        self,
        question: str,
        response: str,
        success: bool,
        confidence: float = 0.0,
        failure_type: str = None,
        metadata: Dict = None
    ):
        """
        记录一次交互
        
        Args:
            question: 用户问题
            response: 系统回答
            success: 是否成功
            confidence: 置信度
            failure_type: 失败类型
            metadata: 额外信息
        """
        import json
        
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO interactions
            (timestamp, question, response, success, failure_type, confidence, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            question,
            response,
            1 if success else 0,
            failure_type,
            confidence,
            json.dumps(metadata or {}, ensure_ascii=False)
        ), commit=True)
    
    def diagnose(self, period: str = "week") -> GapReport:
        """
        诊断能力缺口
        
        Args:
            period: 时间范围 (day, week, month)
        
        Returns:
            缺口报告
        """
        # 计算时间范围
        now = datetime.now()
        if period == "day":
            start_time = now - timedelta(days=1)
        elif period == "week":
            start_time = now - timedelta(weeks=1)
        elif period == "month":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(weeks=1)
        
        # 查询交互记录
        db = DatabaseManager.get(self.db_path)
        interactions = [dict(row) for row in db.query('''
            SELECT * FROM interactions
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
        ''', (start_time.isoformat(),))]
        
        # 统计
        total = len(interactions)
        failed = [i for i in interactions if i['success'] == 0]
        failure_rate = len(failed) / max(1, total)
        
        # 分类失败问题
        gaps = self._classify_failures(failed)
        
        # 生成建议
        recommendations = self._generate_recommendations(gaps)
        
        report = GapReport(
            period=period,
            total_interactions=total,
            failed_interactions=len(failed),
            failure_rate=failure_rate,
            gaps=gaps,
            recommendations=recommendations,
            generated_at=datetime.now().isoformat()
        )
        
        # 保存报告
        self._save_report(report)
        
        logger.info(f"📊 能力缺口诊断完成: {len(gaps)}个缺口")
        return report
    
    def _classify_failures(self, failures: List[Dict]) -> List[CapabilityGap]:
        """分类失败问题"""
        # 按类型统计
        type_questions = {ptype: [] for ptype in self.patterns.keys()}
        type_questions['other'] = []
        
        for failure in failures:
            question = failure['question']
            classified = False
            
            for ptype, patterns in self.patterns.items():
                for pattern in patterns:
                    if re.search(pattern, question, re.IGNORECASE):
                        type_questions[ptype].append(question)
                        classified = True
                        break
                if classified:
                    break
            
            if not classified:
                type_questions['other'].append(question)
        
        # 构建缺口列表
        gaps = []
        for ptype, questions in type_questions.items():
            if len(questions) > 0:
                severity = min(1.0, len(questions) / 10)  # 最多10次就满严重度
                priority = self._calculate_priority(len(questions), severity)
                
                gap = CapabilityGap(
                    gap_type=ptype,
                    category=self._get_category_name(ptype),
                    frequency=len(questions),
                    severity=severity,
                    examples=questions[:3],  # 最多3个示例
                    suggested_module=self.module_mapping.get(ptype, "通用增强模块"),
                    priority=priority
                )
                gaps.append(gap)
        
        # 按优先级排序
        gaps.sort(key=lambda g: g.priority, reverse=True)
        
        return gaps
    
    def _calculate_priority(self, frequency: int, severity: float) -> int:
        """计算优先级"""
        # 综合频率和严重程度
        score = frequency * 0.4 + severity * 10 * 0.6
        
        if score >= 8:
            return 5  # 最高优先级
        elif score >= 6:
            return 4
        elif score >= 4:
            return 3
        elif score >= 2:
            return 2
        else:
            return 1
    
    def _get_category_name(self, gap_type: str) -> str:
        """获取类别名称"""
        category_names = {
            'visual': '视觉处理',
            'audio': '语音处理',
            'code': '代码执行',
            'math': '数学计算',
            'knowledge': '知识问答',
            'recommendation': '推荐建议',
            'external_data': '外部数据',
            'other': '其他'
        }
        return category_names.get(gap_type, gap_type)
    
    def _generate_recommendations(self, gaps: List[CapabilityGap]) -> List[str]:
        """生成建议"""
        recommendations = []
        
        for gap in gaps:
            if gap.priority >= 4:
                recommendations.append(
                    f"【紧急】添加 {gap.suggested_module} - {gap.category}失败{gap.frequency}次"
                )
            elif gap.priority >= 3:
                recommendations.append(
                    f"【建议】考虑添加 {gap.suggested_module} - {gap.category}失败{gap.frequency}次"
                )
        
        if not recommendations:
            recommendations.append("系统能力良好，无明显缺口")
        
        return recommendations
    
    def _save_report(self, report: GapReport):
        """保存报告"""
        import json
        
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO gap_reports
            (period, generated_at, total_interactions, failed_interactions,
             failure_rate, gaps, recommendations)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            report.period,
            report.generated_at,
            report.total_interactions,
            report.failed_interactions,
            report.failure_rate,
            json.dumps([{
                'type': g.gap_type,
                'category': g.category,
                'frequency': g.frequency,
                'severity': g.severity,
                'module': g.suggested_module,
                'priority': g.priority
            } for g in report.gaps], ensure_ascii=False),
            json.dumps(report.recommendations, ensure_ascii=False)
        ), commit=True)
    
    def format_report(self, report: GapReport) -> str:
        """格式化报告"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"  能力缺口诊断报告 ({report.period})")
        lines.append(f"  生成时间: {report.generated_at}")
        lines.append("=" * 70)
        
        lines.append(f"\n【交互统计】")
        lines.append(f"  总交互数: {report.total_interactions}")
        lines.append(f"  失败交互: {report.failed_interactions}")
        lines.append(f"  失败率: {report.failure_rate:.1%}")
        
        if report.gaps:
            lines.append(f"\n【能力缺口】(按优先级排序)")
            for i, gap in enumerate(report.gaps, 1):
                priority_stars = "★" * gap.priority
                lines.append(f"\n  {i}. {gap.category} [{priority_stars}]")
                lines.append(f"     类型: {gap.gap_type}")
                lines.append(f"     频率: {gap.frequency} 次")
                lines.append(f"     严重度: {gap.severity:.1%}")
                lines.append(f"     建议模块: {gap.suggested_module}")
                
                if gap.examples:
                    lines.append(f"     示例:")
                    for ex in gap.examples[:2]:
                        lines.append(f"       - {ex[:50]}...")
        
        if report.recommendations:
            lines.append(f"\n【改进建议】")
            for rec in report.recommendations:
                lines.append(f"  {rec}")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)


capability_gap_diagnoser = CapabilityGapDiagnoser()