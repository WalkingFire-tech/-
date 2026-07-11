"""
交互数据收集系统
记录完整的"问题-回答-反馈"三元组，为未来的监督微调（SFT）积累训练数据
"""
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from infrastructure.database_manager import DatabaseManager

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class InteractionRecord:
    """交互记录"""
    session_id: str
    question: str
    response: str
    feedback_type: str          # 'positive', 'negative', 'correction', 'neutral'
    feedback_content: str
    objective_score: float
    subjective_score: float
    total_score: float
    timestamp: str
    metadata: Dict


class InteractionDataCollector:
    """
    交互数据收集器
    
    目标：为未来的监督微调（SFT）积累高质量训练数据
    
    记录内容：
    1. 完整的问题-回答-反馈三元组
    2. 客观分、主观分、总分
    3. 决策链摘要
    4. 使用的知识来源
    """
    
    def __init__(self, db_path: str = "data/interaction_data.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库"""
        db = DatabaseManager.get(self.db_path)
        db.executescript('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                question TEXT NOT NULL,
                response TEXT NOT NULL,
                feedback_type TEXT,
                feedback_content TEXT,
                objective_score REAL,
                subjective_score REAL,
                total_score REAL,
                decision_chain_summary TEXT,
                knowledge_sources TEXT,
                model_version TEXT,
                system_version TEXT,
                timestamp TEXT NOT NULL,
                metadata TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_session ON interactions(session_id);
            CREATE INDEX IF NOT EXISTS idx_feedback ON interactions(feedback_type);
            CREATE INDEX IF NOT EXISTS idx_score ON interactions(total_score);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON interactions(timestamp);
            CREATE TABLE IF NOT EXISTS data_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_id INTEGER NOT NULL,
                quality_score REAL,
                is_high_quality BOOLEAN,
                quality_reasons TEXT,
                assessed_at TEXT
            )
        ''')
        
        logger.info(f"📊 交互数据收集器已初始化: {self.db_path}")
    
    def save_interaction(
        self,
        session_id: str,
        question: str,
        response: str,
        feedback_type: str = "neutral",
        feedback_content: str = "",
        objective_score: float = 0.0,
        subjective_score: float = 0.0,
        total_score: float = 0.0,
        decision_chain_summary: str = "",
        knowledge_sources: List[str] = None,
        model_version: str = "1.0",
        system_version: str = "1.0",
        metadata: Dict = None
    ) -> int:
        """
        保存交互记录
        
        Args:
            session_id: 会话ID
            question: 用户问题
            response: 系统回答
            feedback_type: 反馈类型 ('positive', 'negative', 'correction', 'neutral')
            feedback_content: 反馈内容
            objective_score: 客观分
            subjective_score: 主观分
            total_score: 总分
            decision_chain_summary: 决策链摘要
            knowledge_sources: 知识来源列表
            model_version: 模型版本
            system_version: 系统版本
            metadata: 额外元数据
        
        Returns:
            记录ID
        """
        timestamp = datetime.now().isoformat()
        
        db = DatabaseManager.get(self.db_path)
        cur = db.execute('''
            INSERT INTO interactions
            (session_id, question, response, feedback_type, feedback_content,
             objective_score, subjective_score, total_score, decision_chain_summary,
             knowledge_sources, model_version, system_version, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id, question, response, feedback_type, feedback_content,
            objective_score, subjective_score, total_score, decision_chain_summary,
            json.dumps(knowledge_sources or [], ensure_ascii=False),
            model_version, system_version, timestamp,
            json.dumps(metadata or {}, ensure_ascii=False)
        ), commit=True)
        
        interaction_id = cur.lastrowid
        
        logger.info(f"📝 交互已记录: ID={interaction_id}, 反馈={feedback_type}, 总分={total_score:.1f}")
        
        # 自动评估数据质量
        self._assess_quality(interaction_id, question, response, feedback_type, total_score)
        
        return interaction_id
    
    def _assess_quality(
        self,
        interaction_id: int,
        question: str,
        response: str,
        feedback_type: str,
        total_score: float
    ):
        """评估数据质量"""
        quality_score = 0.0
        reasons = []
        
        # 评分1: 问题长度（太短的问题质量低）
        if len(question) >= 10:
            quality_score += 0.2
        else:
            reasons.append("问题过短")
        
        # 评分2: 回答长度（太短的回答质量低）
        if len(response) >= 20:
            quality_score += 0.2
        else:
            reasons.append("回答过短")
        
        # 评分3: 有明确反馈
        if feedback_type in ['positive', 'negative', 'correction']:
            quality_score += 0.3
        else:
            reasons.append("无明确反馈")
        
        # 评分4: 总分
        if total_score >= 60:
            quality_score += 0.3
        elif total_score >= 40:
            quality_score += 0.15
        else:
            reasons.append("总分偏低")
        
        is_high_quality = quality_score >= 0.7
        
        db = DatabaseManager.get(self.db_path)
        db.execute('''
            INSERT INTO data_quality
            (interaction_id, quality_score, is_high_quality, quality_reasons, assessed_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            interaction_id, quality_score, 1 if is_high_quality else 0,
            json.dumps(reasons, ensure_ascii=False),
            datetime.now().isoformat()
        ), commit=True)
    
    def get_training_data(
        self,
        min_quality_score: float = 0.7,
        feedback_types: List[str] = None,
        limit: int = 1000
    ) -> List[Dict]:
        """
        获取训练数据
        
        Args:
            min_quality_score: 最低质量分数
            feedback_types: 反馈类型过滤
            limit: 最大数量
        
        Returns:
            训练数据列表
        """
        db = DatabaseManager.get(self.db_path)
        
        query = '''
            SELECT i.*, q.quality_score, q.is_high_quality
            FROM interactions i
            JOIN data_quality q ON i.id = q.interaction_id
            WHERE q.quality_score >= ?
        '''
        params = [min_quality_score]
        
        if feedback_types:
            placeholders = ','.join('?' * len(feedback_types))
            query += f" AND i.feedback_type IN ({placeholders})"
            params.extend(feedback_types)
        
        query += " ORDER BY i.timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = db.query(query, params)
        
        return [dict(row) for row in rows]
    
    def export_for_sft(
        self,
        output_path: str,
        format_type: str = "json",
        min_quality_score: float = 0.7,
        include_corrections: bool = True
    ) -> int:
        """
        导出为监督微调（SFT）格式
        
        Args:
            output_path: 输出文件路径
            format_type: 格式类型 ('json', 'jsonl', 'csv')
            min_quality_score: 最低质量分数
            include_corrections: 是否包含纠错数据
        
        Returns:
            导出记录数
        """
        # 获取高质量数据
        feedback_types = ['positive']
        if include_corrections:
            feedback_types.append('correction')
        
        data = self.get_training_data(
            min_quality_score=min_quality_score,
            feedback_types=feedback_types
        )
        
        if not data:
            logger.warning("没有符合条件的数据可导出")
            return 0
        
        # 转换为SFT格式
        sft_data = []
        for record in data:
            # 对于纠错数据，使用纠错内容作为标准输出
            output = record['response']
            if record['feedback_type'] == 'correction' and record['feedback_content']:
                output = record['feedback_content']
            
            sft_item = {
                'instruction': "请回答以下问题",
                'input': record['question'],
                'output': output,
                'metadata': {
                    'session_id': record['session_id'],
                    'quality_score': record['quality_score'],
                    'timestamp': record['timestamp']
                }
            }
            sft_data.append(sft_item)
        
        # 导出
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        if format_type == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(sft_data, f, ensure_ascii=False, indent=2)
        
        elif format_type == "jsonl":
            with open(output_path, 'w', encoding='utf-8') as f:
                for item in sft_data:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        elif format_type == "csv":
            import csv
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['instruction', 'input', 'output'])
                for item in sft_data:
                    writer.writerow([item['instruction'], item['input'], item['output']])
        
        logger.info(f"📤 已导出 {len(sft_data)} 条SFT训练数据到 {output_path}")
        return len(sft_data)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        db = DatabaseManager.get(self.db_path)
        total = db.query_one('SELECT COUNT(*) FROM interactions')[0]
        positive = db.query_one(
            "SELECT COUNT(*) FROM interactions WHERE feedback_type = 'positive'"
        )[0]
        negative = db.query_one(
            "SELECT COUNT(*) FROM interactions WHERE feedback_type = 'negative'"
        )[0]
        correction = db.query_one(
            "SELECT COUNT(*) FROM interactions WHERE feedback_type = 'correction'"
        )[0]
        
        high_quality = db.query_one(
            'SELECT COUNT(*) FROM data_quality WHERE is_high_quality = 1'
        )[0]
        
        avg_score = db.query_one(
            'SELECT AVG(total_score) FROM interactions WHERE total_score > 0'
        )[0] or 0
        
        return {
            'total_interactions': total,
            'positive_feedback': positive,
            'negative_feedback': negative,
            'corrections': correction,
            'high_quality_data': high_quality,
            'avg_score': avg_score,
            'ready_for_sft': high_quality >= 100  # 建议至少100条高质量数据
        }


interaction_collector = InteractionDataCollector()
