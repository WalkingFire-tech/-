"""
知识质量评估器 - 系统主动判断是否值得注入

核心理念：
- 知识注入由系统主动判断，而非被动等待用户点赞
- 多维度评估，而非单一反馈
- 有质量门槛，而非来者不拒
"""

from typing import Dict, Tuple, List
from dataclasses import dataclass
import sqlite3
from pathlib import Path
import re

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class KnowledgeQualityAssessment:
    """知识质量评估结果"""
    should_inject: bool
    overall_score: float
    dimensions: Dict[str, float]
    reasons: List[str]
    warnings: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "should_inject": self.should_inject,
            "overall_score": self.overall_score,
            "dimensions": self.dimensions,
            "reasons": self.reasons,
            "warnings": self.warnings
        }


class KnowledgeQualityEvaluator:
    """
    知识质量评估器
    
    系统主动判断知识是否值得注入。
    """
    
    def __init__(self):
        self.quality_threshold = 0.7
        self.min_dimensions = 3
        
        logger.info("🔍 知识质量评估器已初始化")
    
    def evaluate(
        self,
        question: str,
        answer: str,
        intent_type: str = None,
        user_feedback: int = 0,
        confidence: float = 0.0,
        context: Dict = None
    ) -> KnowledgeQualityAssessment:
        """
        评估知识质量
        
        Args:
            question: 用户问题
            answer: 系统回答
            intent_type: 意图类型
            user_feedback: 用户反馈（1=点赞，-1=踩，0=无）
            confidence: 系统置信度
            context: 额外上下文
        
        Returns:
            KnowledgeQualityAssessment: 评估结果
        """
        dimensions = {}
        reasons = []
        warnings = []
        
        # 1. 准确性评估（基于置信度和不确定性）
        accuracy = self._evaluate_accuracy(answer, confidence)
        dimensions["accuracy"] = accuracy
        if accuracy < 0.6:
            warnings.append(f"准确性不足({accuracy:.2f})：回答包含不确定性")
        
        # 2. 完整性评估（回答是否覆盖问题）
        completeness = self._evaluate_completeness(question, answer)
        dimensions["completeness"] = completeness
        if completeness < 0.5:
            warnings.append(f"完整性不足({completeness:.2f})：回答可能未覆盖问题")
        
        # 3. 可复用性评估（是否值得保存）
        reusability = self._evaluate_reusability(question, answer, intent_type)
        dimensions["reusability"] = reusability
        if reusability < 0.5:
            reasons.append(f"可复用性低({reusability:.2f})：过于具体或个性化")
        
        # 4. 一致性评估（是否与现有知识冲突）
        consistency = self._evaluate_consistency(question, answer)
        dimensions["consistency"] = consistency
        if consistency < 0.6:
            warnings.append(f"一致性不足({consistency:.2f})：可能与现有知识冲突")
        
        # 5. 用户反馈评估（只是参考，非决定因素）
        feedback_score = self._evaluate_user_feedback(user_feedback, context)
        dimensions["user_feedback"] = feedback_score
        if user_feedback > 0:
            reasons.append("用户正面反馈")
        elif user_feedback < 0:
            warnings.append("用户负面反馈")
        
        # 6. 内容质量评估（长度、结构等）
        content_quality = self._evaluate_content_quality(answer)
        dimensions["content_quality"] = content_quality
        
        # 计算综合得分
        weights = {
            "accuracy": 0.25,
            "completeness": 0.20,
            "reusability": 0.20,
            "consistency": 0.15,
            "user_feedback": 0.10,
            "content_quality": 0.10
        }
        
        overall_score = sum(
            dimensions[dim] * weights[dim]
            for dim in dimensions
        )
        
        # 决定是否注入
        should_inject = self._decide_injection(
            overall_score,
            dimensions,
            user_feedback,
            warnings
        )
        
        if should_inject:
            reasons.insert(0, f"综合得分{overall_score:.2f}达标")
        else:
            reasons.insert(0, f"综合得分{overall_score:.2f}未达标")
        
        return KnowledgeQualityAssessment(
            should_inject=should_inject,
            overall_score=overall_score,
            dimensions=dimensions,
            reasons=reasons,
            warnings=warnings
        )
    
    def _evaluate_accuracy(self, answer: str, confidence: float) -> float:
        """评估准确性"""
        # 检查不确定性短语
        uncertainty_phrases = [
            "不太确定", "不确定", "可能", "大概", "也许",
            "我不太清楚", "我不确定", "应该是", "可能是"
        ]
        
        uncertainty_count = sum(
            1 for phrase in uncertainty_phrases
            if phrase in answer
        )
        
        # 不确定性越多，准确性越低
        uncertainty_penalty = min(uncertainty_count * 0.15, 0.5)
        
        # 基础准确性来自置信度
        base_accuracy = confidence if confidence > 0 else 0.6
        
        accuracy = max(0.1, base_accuracy - uncertainty_penalty)
        
        return accuracy
    
    def _evaluate_completeness(self, question: str, answer: str) -> float:
        """评估完整性"""
        # 回答太短，可能不完整
        if len(answer) < 50:
            return 0.3
        
        # 回答长度合理
        if len(answer) < 100:
            return 0.6
        
        # 检查是否有结构化内容
        has_structure = any([
            "：" in answer or ":" in answer,  # 有分点
            "\n\n" in answer,  # 有段落
            "1." in answer or "第一" in answer,  # 有序号
            "**" in answer or "【" in answer  # 有强调
        ])
        
        if has_structure:
            return 0.9
        else:
            return 0.7
    
    def _evaluate_reusability(
        self,
        question: str,
        answer: str,
        intent_type: str = None
    ) -> float:
        """评估可复用性"""
        # 过于具体的问题，可复用性低
        specific_patterns = [
            r"我的", r"我正在", r"我的电脑", r"我的文件",
            r"刚才", r"上次", r"之前"
        ]
        
        for pattern in specific_patterns:
            if re.search(pattern, question):
                return 0.4
        
        # 元认知问题，可复用性低
        if intent_type and intent_type.startswith("meta"):
            return 0.3
        
        # 通用问题，可复用性高
        general_patterns = [
            r"如何", r"怎么", r"为什么", r"什么是",
            r"原理", r"机制", r"方法"
        ]
        
        for pattern in general_patterns:
            if re.search(pattern, question):
                return 0.9
        
        return 0.6
    
    def _evaluate_consistency(self, question: str, answer: str) -> float:
        """
        评估一致性（与现有知识是否冲突）
        
        使用语义分析而非简单的长度比较：
        1. 提取关键概念和关系
        2. 检查逻辑一致性
        3. 检查数值一致性
        4. 检查因果一致性
        """
        try:
            db_path = Path("data/knowledge_store.db")
            if not db_path.exists():
                return 0.95
            
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='knowledge_items'
                """)
                
                if not cursor.fetchone():
                    return 0.95
                
                new_concepts = self._extract_concepts(f"{question} {answer}")
                new_relations = self._extract_relations(answer)
                new_numbers = self._extract_numbers(answer)
                
                cursor.execute("""
                    SELECT question, answer FROM knowledge_items
                    WHERE question LIKE ? OR question LIKE ? OR question LIKE ?
                    LIMIT 10
                """, (f"%{question[:20]}%", f"%{question[10:30]}%", f"%{question[-20:]}%"))
                
                similar_entries = cursor.fetchall()
                
                if not similar_entries:
                    return 0.95
                
                conflicts = []
                consistencies = []
                
                for existing_question, existing_answer in similar_entries:
                    existing_concepts = self._extract_concepts(f"{existing_question} {existing_answer}")
                    existing_relations = self._extract_relations(existing_answer)
                    existing_numbers = self._extract_numbers(existing_answer)
                    
                    concept_conflict = self._check_concept_conflict(
                        new_concepts, existing_concepts
                    )
                    if concept_conflict:
                        conflicts.append(("concept", concept_conflict))
                    
                    relation_conflict = self._check_relation_conflict(
                        new_relations, existing_relations
                    )
                    if relation_conflict:
                        conflicts.append(("relation", relation_conflict))
                    
                    number_conflict = self._check_number_conflict(
                        new_numbers, existing_numbers
                    )
                    if number_conflict:
                        conflicts.append(("number", number_conflict))
                    
                    if new_concepts and existing_concepts:
                        overlap = len(new_concepts & existing_concepts) / len(new_concepts)
                        if overlap > 0.5:
                            consistencies.append(overlap)
                
                if conflicts:
                    severity_weights = {
                        "number": 0.4,
                        "relation": 0.35,
                        "concept": 0.25
                    }
                    
                    max_severity = max(
                        severity_weights.get(c[0], 0.25)
                        for c in conflicts
                    )
                    
                    consistency = 0.5 - max_severity
                    return max(0.2, consistency)
                
                if consistencies:
                    return 0.85 + max(consistencies) * 0.1
                
                return 0.9
        
        except Exception as e:
            logger.debug(f"一致性检查失败: {e}")
            return 0.7
    
    def _extract_concepts(self, text: str) -> set:
        """提取关键概念"""
        concepts = set()
        
        noun_patterns = [
            r'([^。！？\n]{2,8}的)',
            r'(\w+系统)',
            r'(\w+机制)',
            r'(\w+方法)',
            r'(\w+原理)',
            r'(\w+层)',
            r'(\w+模块)',
            r'(\w+架构)'
        ]
        
        for pattern in noun_patterns:
            matches = re.findall(pattern, text)
            concepts.update(m.lower() for m in matches)
        
        words = re.findall(r'\w+', text)
        words = [w.lower() for w in words if len(w) > 3]
        concepts.update(words[:10])
        
        return concepts
    
    def _extract_relations(self, text: str) -> List[Tuple[str, str, str]]:
        """提取关系三元组（主语，谓语，宾语）"""
        relations = []
        
        relation_patterns = [
            (r'(\w+)是(\w+)', '是'),
            (r'(\w+)包含(\w+)', '包含'),
            (r'(\w+)属于(\w+)', '属于'),
            (r'(\w+)导致(\w+)', '导致'),
            (r'(\w+)需要(\w+)', '需要'),
            (r'(\w+)调用(\w+)', '调用'),
            (r'(\w+)返回(\w+)', '返回')
        ]
        
        for pattern, rel_type in relation_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if len(match) == 2:
                    relations.append((match[0], rel_type, match[1]))
        
        return relations
    
    def _extract_numbers(self, text: str) -> Dict[str, float]:
        """提取数值信息"""
        numbers = {}
        
        percent_matches = re.findall(r'(\w+)[是为]?(\d+(?:\.\d+)?)\s*%', text)
        for label, value in percent_matches:
            numbers[f"{label}_percent"] = float(value)
        
        count_matches = re.findall(r'(\w+)[是为]?(\d+)\s*(个|次|层|个)', text)
        for label, value, unit in count_matches:
            numbers[f"{label}_{unit}"] = float(value)
        
        return numbers
    
    def _check_concept_conflict(self, new_concepts: set, existing_concepts: set) -> str:
        """检查概念冲突"""
        negation_words = ["不", "非", "无", "没", "not", "no", "never", "none"]
        
        for concept in new_concepts:
            for neg in negation_words:
                if neg in concept:
                    positive_form = concept.replace(neg, "")
                    if positive_form in existing_concepts:
                        return f"概念冲突: '{positive_form}' vs '{concept}'"
        
        for concept in existing_concepts:
            for neg in negation_words:
                if neg in concept:
                    positive_form = concept.replace(neg, "")
                    if positive_form in new_concepts:
                        return f"概念冲突: '{positive_form}' vs '{concept}'"
        
        return None
    
    def _check_relation_conflict(
        self,
        new_relations: List[Tuple],
        existing_relations: List[Tuple]
    ) -> str:
        """检查关系冲突"""
        for new_rel in new_relations:
            for exist_rel in existing_relations:
                if (new_rel[0] == exist_rel[0] and 
                    new_rel[2] == exist_rel[2] and
                    new_rel[1] != exist_rel[1]):
                    return f"关系冲突: {new_rel[0]} {new_rel[1]} vs {exist_rel[1]} {new_rel[2]}"
        
        return None
    
    def _check_number_conflict(
        self,
        new_numbers: Dict[str, float],
        existing_numbers: Dict[str, float]
    ) -> str:
        """检查数值冲突"""
        for key, new_value in new_numbers.items():
            if key in existing_numbers:
                exist_value = existing_numbers[key]
                if exist_value != 0:
                    diff_ratio = abs(new_value - exist_value) / abs(exist_value)
                    if diff_ratio > 0.2:
                        return f"数值冲突: {key} {exist_value} vs {new_value}"
        
        return None
    
    def _evaluate_user_feedback(self, user_feedback: int, context: Dict = None) -> float:
        """
        评估用户反馈（只是参考，非决定因素）
        
        用户反馈的动态评估：
        1. 反馈强度分级（强正面、弱正面、中性、弱负面、强负面）
        2. 结合上下文调整权重
        3. 考虑反馈历史模式
        """
        if context is None:
            context = {}
        
        if user_feedback > 0:
            base_score = 0.7
            
            if user_feedback >= 2:
                base_score = 0.85
            elif user_feedback == 1:
                base_score = 0.75
            
            if context.get("explicit_confirmation"):
                base_score += 0.1
            
            if context.get("user_expertise") == "high":
                base_score += 0.05
            
            return min(0.95, base_score)
        
        elif user_feedback < 0:
            base_score = 0.4
            
            if user_feedback <= -2:
                base_score = 0.15
            elif user_feedback == -1:
                base_score = 0.3
            
            if context.get("explicit_rejection"):
                base_score -= 0.1
            
            return max(0.1, base_score)
        
        else:
            base_score = 0.6
            
            if context.get("user_engaged"):
                base_score += 0.05
            
            if context.get("follow_up_question"):
                base_score -= 0.1
            
            return base_score
    
    def _evaluate_content_quality(self, answer: str) -> float:
        """评估内容质量"""
        score = 0.5
        
        # 长度合理
        if 100 <= len(answer) <= 2000:
            score += 0.2
        
        # 有结构
        if "：" in answer or ":\n" in answer:
            score += 0.1
        
        # 有代码示例
        if "```" in answer or "def " in answer:
            score += 0.1
        
        # 有列表
        if "\n-" in answer or "\n1." in answer:
            score += 0.1
        
        return min(score, 1.0)
    
    def _decide_injection(
        self,
        overall_score: float,
        dimensions: Dict[str, float],
        user_feedback: int,
        warnings: List[str]
    ) -> bool:
        """决定是否注入"""
        # 用户明确反对，不注入
        if user_feedback < 0:
            return False
        
        # 综合得分不足，不注入
        if overall_score < self.quality_threshold:
            return False
        
        # 关键维度太低，不注入
        critical_dims = ["accuracy", "completeness"]
        for dim in critical_dims:
            if dimensions.get(dim, 0) < 0.5:
                return False
        
        # 警告太多，不注入
        if len(warnings) > 2:
            return False
        
        return True


evaluator = KnowledgeQualityEvaluator()