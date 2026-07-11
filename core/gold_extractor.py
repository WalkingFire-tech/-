# -*- coding: utf-8 -*-
"""
黄金数据提取器 - 识别值得学习的对话

基于神经科学的记忆固化机制：
- 识别高价值对话（纠错、点赞）
- 提取正确的知识
- 标记为"待固化"状态

这是"白天记忆"阶段。
"""
import json
from infrastructure.database_manager import DatabaseManager
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class GoldExtractor:
    """
    从对话记录中提取高价值训练样本
    
    识别标准：
    1. 明确的纠错（包含"不对"、"应该是"等）
    2. 用户点赞或正面反馈
    3. 深度对话（回答长度 > 200字）
    """
    
    def __init__(self, 
                 db_path: str = "data/alliance.db",
                 pending_file: str = "data/pending_training.jsonl"):
        self.db_path = Path(db_path)
        self.pending_file = Path(pending_file)
        self.pending_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 纠错关键词
        self.correction_keywords = [
            "不对", "错了", "应该是", "实际上是", 
            "纠正", "更正", "不是", "错误",
            "不完整", "缺少", "遗漏"
        ]
        
        # 正面反馈关键词
        self.positive_keywords = [
            "👍", "点赞", "好的", "正确", 
            "很好", "完美", "谢谢", "有用"
        ]
        
        logger.info("🔍 黄金数据提取器已初始化")
    
    def extract_from_interactions(self, limit: int = 30) -> List[Dict]:
        """
        从对话记录中提取黄金数据
        
        Args:
            limit: 最大提取数量
        
        Returns:
            黄金样本列表
        """
        gold_samples = []
        
        # 从数据库获取最近的交互记录
        interactions = self._get_recent_interactions(limit)
        
        for interaction in interactions:
            question = interaction.get('question', '')
            response = interaction.get('response', '')
            feedback = interaction.get('feedback', '')
            
            # 识别纠错
            if self._is_correction(feedback):
                correct_answer = self._extract_correct_answer(feedback, response)
                if correct_answer:
                    gold_samples.append({
                        "instruction": question,
                        "output": correct_answer,
                        "source": "user_correction",
                        "timestamp": datetime.now().isoformat(),
                        "is_gold": True,
                        "quality": "high"
                    })
                    logger.info(f"✅ 提取纠错样本: {question[:30]}...")
            
            # 识别正面反馈
            elif self._is_positive_feedback(feedback):
                gold_samples.append({
                    "instruction": question,
                    "output": response,
                    "source": "user_approval",
                    "timestamp": datetime.now().isoformat(),
                    "is_gold": True,
                    "quality": "medium"
                })
                logger.info(f"✅ 提取正面样本: {question[:30]}...")
            
            # 识别深度对话
            elif len(response) > 200 and interaction.get('objective_score', 0) > 70:
                gold_samples.append({
                    "instruction": question,
                    "output": response,
                    "source": "deep_conversation",
                    "timestamp": datetime.now().isoformat(),
                    "is_gold": True,
                    "quality": "low"
                })
        
        return gold_samples
    
    def extract_from_correction_file(self, 
                                    correction_file: str = "data/corrections/correction_2026-06-27.json") -> List[Dict]:
        """
        从纠错文件中提取黄金数据
        
        Args:
            correction_file: 纠错文件路径
        
        Returns:
            黄金样本列表
        """
        gold_samples = []
        
        correction_path = Path(correction_file)
        if not correction_path.exists():
            logger.warning(f"纠错文件不存在: {correction_file}")
            return gold_samples
        
        with open(correction_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        corrections = data.get('corrections', [])
        
        for corr in corrections:
            question = corr.get('question', '')
            correct_answer = corr.get('correct_answer', '')
            
            if question and correct_answer:
                gold_samples.append({
                    "instruction": question,
                    "output": correct_answer,
                    "source": "correction_file",
                    "timestamp": datetime.now().isoformat(),
                    "is_gold": True,
                    "quality": "high",
                    "category": corr.get('category', 'general')
                })
        
        logger.info(f"✅ 从纠错文件提取 {len(gold_samples)} 条黄金样本")
        
        return gold_samples
    
    def append_to_pending(self, samples: List[Dict]) -> int:
        """
        将黄金样本追加到待训练池
        
        Args:
            samples: 黄金样本列表
        
        Returns:
            追加的数量
        """
        if not samples:
            return 0
        
        # 过滤只保留高质量样本
        high_quality = [s for s in samples if s.get('quality') in ['high', 'medium']]
        
        with open(self.pending_file, 'a', encoding='utf-8') as f:
            for sample in high_quality:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        
        logger.info(f"🔥 提炼 {len(high_quality)} 条黄金样本，存入待学习池")
        
        return len(high_quality)
    
    def get_pending_count(self) -> int:
        """获取待训练样本数量"""
        if not self.pending_file.exists():
            return 0
        
        with open(self.pending_file, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)
    
    def _get_recent_interactions(self, limit: int = 30) -> List[Dict]:
        """从数据库获取最近的交互记录"""
        interactions = []
        
        if not self.db_path.exists():
            logger.warning(f"数据库不存在: {self.db_path}")
            return interactions
        
        try:
            rows = DatabaseManager.get(str(self.db_path)).query("""
                SELECT question, response, feedback, objective_score, timestamp 
                FROM interactions 
                WHERE feedback IS NOT NULL 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            interactions = [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"读取数据库失败: {e}")
        
        return interactions
    
    def _is_correction(self, text: str) -> bool:
        """判断是否为纠错"""
        if not text:
            return False
        return any(kw in text for kw in self.correction_keywords)
    
    def _is_positive_feedback(self, text: str) -> bool:
        """判断是否为正面反馈"""
        if not text:
            return False
        return any(kw in text for kw in self.positive_keywords)
    
    def _extract_correct_answer(self, feedback: str, original_response: str) -> Optional[str]:
        """
        从纠错文本中提取正确答案
        
        Args:
            feedback: 纠错文本
            original_response: 原始回答
        
        Returns:
            正确答案
        """
        # 尝试提取"应该是"之后的内容
        match = re.search(r'应该是[：:]\s*(.+)', feedback, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 尝试提取"更正"后的内容
        match = re.search(r'更正[：:]\s*(.+)', feedback, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 尝试提取"正确答案"后的内容
        match = re.search(r'正确答案[：:]\s*(.+)', feedback, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 如果无法提取，返回整个反馈
        if len(feedback) > 50:
            return feedback
        
        return None


def test_gold_extractor():
    """测试黄金数据提取器"""
    print("="*60)
    print("测试黄金数据提取器")
    print("="*60)
    print()
    
    extractor = GoldExtractor()
    
    # 1. 从纠错文件提取
    print("\n1. 从纠错文件提取黄金数据")
    samples = extractor.extract_from_correction_file()
    print(f"   提取数量: {len(samples)}")
    
    if samples:
        print(f"   示例: {samples[0]['instruction'][:30]}...")
    
    # 2. 追加到待训练池
    print("\n2. 追加到待训练池")
    count = extractor.append_to_pending(samples)
    print(f"   追加数量: {count}")
    
    # 3. 查看待训练池
    print("\n3. 待训练池状态")
    pending_count = extractor.get_pending_count()
    print(f"   待训练样本: {pending_count} 条")
    
    print("\n✅ 测试完成")


if __name__ == "__main__":
    test_gold_extractor()