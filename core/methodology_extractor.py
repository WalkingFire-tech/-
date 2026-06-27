"""
方法论提取器
从老师反馈中提炼可复用的思维方法
"""
from typing import Dict, List, Optional
from datetime import datetime
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
class Methodology:
    """方法论"""
    name: str
    description: str
    trigger_conditions: List[str]
    application_steps: List[str]
    example_application: str
    source_case: str
    effectiveness_score: float
    use_count: int = 0


class MethodologyExtractor:
    """
    方法论提取器
    
    从老师的反馈中提炼出可复用的思维方法
    这些方法将作为"能力基因"影响系统未来的行为
    """
    
    def __init__(self, db_path: str = "data/methodologies.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS methodologies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    trigger_conditions TEXT,
                    application_steps TEXT,
                    example_application TEXT,
                    source_case TEXT,
                    effectiveness_score REAL DEFAULT 0.5,
                    use_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            ''')
            
            conn.execute('CREATE INDEX IF NOT EXISTS idx_name ON methodologies(name)')
            conn.commit()
        
        logger.info(f"📚 方法论库已初始化: {self.db_path}")
    
    def extract_methodology(
        self,
        teacher_feedback: Dict,
        question: str,
        response: str,
        self_reflection: Dict
    ) -> List[Methodology]:
        """
        从老师反馈中提炼方法论
        
        Args:
            teacher_feedback: 老师的反馈
            question: 原问题
            response: 原回答
            self_reflection: 自我复盘
        
        Returns:
            提炼出的方法论列表
        """
        methodologies = []
        
        # 提取1: 基于问题拆解
        if teacher_feedback.get('problem_decomposition', 0) < 7:
            methodologies.append(self._create_decomposition_methodology(question))
        
        # 提取2: 基于分析框架
        if teacher_feedback.get('analysis_framework', 0) < 7:
            methodologies.append(self._create_framework_methodology(question))
        
        # 提取3: 基于改进建议
        suggestions = teacher_feedback.get('improvement_suggestions', [])
        for suggestion in suggestions:
            if '拆解' in suggestion or '分解' in suggestion:
                methodologies.append(self._create_decomposition_methodology(question))
            elif '结构' in suggestion or '框架' in suggestion:
                methodologies.append(self._create_framework_methodology(question))
            elif '假设' in suggestion or '验证' in suggestion:
                methodologies.append(self._create_hypothesis_methodology(question))
        
        # 提取4: 直接从方法论字段
        if 'methodology' in teacher_feedback:
            methodologies.append(Methodology(
                name="老师建议的方法",
                description=teacher_feedback['methodology'],
                trigger_conditions=["遇到类似问题"],
                application_steps=["按老师建议执行"],
                example_application=question,
                source_case=question,
                effectiveness_score=0.7
            ))
        
        # 去重并保存
        unique_methodologies = self._deduplicate(methodologies)
        
        for method in unique_methodologies:
            self._save_methodology(method)
        
        logger.info(f"✅ 提炼出 {len(unique_methodologies)} 个方法论")
        
        return unique_methodologies
    
    def _create_decomposition_methodology(self, question: str) -> Methodology:
        """创建问题拆解方法论"""
        return Methodology(
            name="分层拆解法",
            description="将复杂问题分解为多个独立子问题分别处理",
            trigger_conditions=[
                "问题包含多个要素",
                "涉及因果关系链",
                "问题较长且复杂"
            ],
            application_steps=[
                "识别问题的核心要素",
                "将问题拆分为3-5个子问题",
                "分别处理每个子问题",
                "整合结果形成完整答案"
            ],
            example_application=f"当用户问'{question[:30]}...'时，先拆解为关键要素再分别回答",
            source_case=question,
            effectiveness_score=0.7
        )
    
    def _create_framework_methodology(self, question: str) -> Methodology:
        """创建分析框架方法论"""
        return Methodology(
            name="结构化分析法",
            description="建立清晰的思考框架，分层分析问题",
            trigger_conditions=[
                "需要系统性思考",
                "问题涉及多个维度",
                "需要全面分析"
            ],
            application_steps=[
                "确定分析维度",
                "建立层次结构",
                "逐层深入分析",
                "形成结构化结论"
            ],
            example_application=f"对'{question[:30]}...'从定义、特征、例子多角度分析",
            source_case=question,
            effectiveness_score=0.7
        )
    
    def _create_hypothesis_methodology(self, question: str) -> Methodology:
        """创建假设验证方法论"""
        return Methodology(
            name="假设验证法",
            description="识别关键假设并验证其合理性",
            trigger_conditions=[
                "涉及因果关系推断",
                "存在隐含前提",
                "需要逻辑推理"
            ],
            application_steps=[
                "识别隐含假设",
                "评估假设合理性",
                "验证或修正假设",
                "基于验证结果回答"
            ],
            example_application=f"对'{question[:30]}...'先识别隐含假设再验证",
            source_case=question,
            effectiveness_score=0.7
        )
    
    def _deduplicate(self, methodologies: List[Methodology]) -> List[Methodology]:
        """去重"""
        seen = set()
        unique = []
        
        for method in methodologies:
            if method.name not in seen:
                seen.add(method.name)
                unique.append(method)
        
        return unique
    
    def _save_methodology(self, method: Methodology):
        """保存方法论"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO methodologies
                (name, description, trigger_conditions, application_steps,
                 example_application, source_case, effectiveness_score)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                method.name,
                method.description,
                json.dumps(method.trigger_conditions, ensure_ascii=False),
                json.dumps(method.application_steps, ensure_ascii=False),
                method.example_application,
                method.source_case,
                method.effectiveness_score
            ))
            conn.commit()
    
    def get_relevant_methodologies(self, question: str) -> List[Methodology]:
        """
        获取与问题相关的方法论
        
        Args:
            question: 当前问题
        
        Returns:
            相关方法论列表
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute('''
                SELECT * FROM methodologies
                ORDER BY effectiveness_score DESC, use_count DESC
                LIMIT 5
            ''').fetchall()
            
            methodologies = []
            for row in rows:
                methodologies.append(Methodology(
                    name=row['name'],
                    description=row['description'],
                    trigger_conditions=json.loads(row['trigger_conditions']),
                    application_steps=json.loads(row['application_steps']),
                    example_application=row['example_application'],
                    source_case=row['source_case'],
                    effectiveness_score=row['effectiveness_score'],
                    use_count=row['use_count']
                ))
            
            return methodologies
    
    def record_methodology_use(self, methodology_name: str):
        """记录方法论使用"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                UPDATE methodologies
                SET use_count = use_count + 1, last_used = CURRENT_TIMESTAMP
                WHERE name = ?
            ''', (methodology_name,))
            conn.commit()
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute('SELECT COUNT(*) FROM methodologies').fetchone()[0]
            avg_effectiveness = conn.execute(
                'SELECT AVG(effectiveness_score) FROM methodologies'
            ).fetchone()[0] or 0
            total_uses = conn.execute(
                'SELECT SUM(use_count) FROM methodologies'
            ).fetchone()[0] or 0
        
        return {
            'total_methodologies': total,
            'avg_effectiveness': avg_effectiveness,
            'total_uses': total_uses
        }


methodology_extractor = MethodologyExtractor()