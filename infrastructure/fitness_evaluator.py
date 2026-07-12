"""
重构适应度评估器
将适应度函数拆分为：客观分(60%) + 主观分(40%)

核心理念：让系统具备"客观是非观"，不再唯用户情绪马首是瞻
"""
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from infrastructure.fact_store import fact_store
from infrastructure.triple_extractor import triple_extractor


@dataclass
class FitnessScore:
    """适应度评分结果"""
    final_score: float
    objective_score: float
    subjective_score: float
    is_factual_question: bool
    match_details: Dict
    timestamp: str


class FitnessEvaluator:
    """
    适应度评估器
    
    新适应度函数：
    - 事实性问题：客观分(60%) + 主观分(40%)
    - 开放性问题：主观分(100%)
    """
    
    def __init__(self, use_legacy: bool = False, config: Dict = None):
        """
        Args:
            use_legacy: 是否使用旧版适应度函数（回滚开关）
            config: 配置字典（可选）
        """
        self.use_legacy = use_legacy
        
        # 加载配置
        if config is None:
            try:
                from config.config_loader import config_loader
                config = config_loader.get_fitness_config()
            except Exception:
                config = {}
        
        # 从配置读取参数
        self.objective_weight = config.get('objective_weight', 0.6)
        self.subjective_weight = config.get('subjective_weight', 0.4)
        self.objective_threshold = config.get('objective_threshold', 30.0)
        self.total_threshold = config.get('total_threshold', 50.0)
        self.default_score = config.get('default_score', 50.0)
        
        # 事实性问题关键词
        self.factual_keywords = [
            "为什么", "是什么", "怎么形成", "原理", "机制",
            "定义", "公式", "数值", "时间", "地点",
            "等于", "多少", "哪个", "哪些",
            "形成", "产生", "发生", "导致"
        ]
        
        # 开放性问题关键词
        self.open_keywords = [
            "你觉得", "你认为", "怎么看", "如何理解",
            "聊聊", "谈谈", "说说", "讨论",
            "感觉", "想法", "观点", "看法"
        ]
        
        logger.info(
            f"⚖️ 适应度评估器已初始化 "
            f"(legacy={use_legacy}, obj_weight={self.objective_weight}, "
            f"obj_threshold={self.objective_threshold}, total_threshold={self.total_threshold})"
        )
    
    def evaluate(
        self,
        question: str,
        response: str,
        user_feedback: int = 0,
        intent_type: str = "chat"
    ) -> FitnessScore:
        """
        评估适应度
        
        Args:
            question: 用户问题
            response: 系统回答
            user_feedback: 用户反馈 (+1点赞, -1点踩, 0无反馈)
            intent_type: 意图类型
        
        Returns:
            适应度评分结果
        """
        if self.use_legacy:
            return self._legacy_evaluate(question, response, user_feedback)
        
        # 1. 判断问题类型
        is_factual = self._is_factual_question(question, intent_type)
        
        # 2. 计算客观分
        objective_score, match_details = self._calculate_objective_score(
            question, response, is_factual
        )
        
        # 3. 计算主观分
        subjective_score = self._calculate_subjective_score(user_feedback, question, response)
        
        # 4. 合并得分
        if is_factual:
            final_score = (objective_score * self.objective_weight) + (subjective_score * self.subjective_weight)
        else:
            final_score = subjective_score
        
        # 5. 钳位处理
        final_score = max(0, min(100, final_score))
        
        # 6. 检查是否需要触发知识注入
        if objective_score < self.objective_threshold:
            logger.warning(
                f"⚠️ 客观分过低 ({objective_score:.1f} < {self.objective_threshold}): "
                f"{question[:50]}..."
            )
            # 触发知识注入
            self._trigger_knowledge_injection(question, response, objective_score)
        
        return FitnessScore(
            final_score=final_score,
            objective_score=objective_score,
            subjective_score=subjective_score,
            is_factual_question=is_factual,
            match_details=match_details,
            timestamp=datetime.now().isoformat()
        )
    
    def _trigger_knowledge_injection(self, question: str, response: str, objective_score: float):
        """触发知识注入"""
        try:
            from infrastructure.knowledge_injector_trigger import knowledge_injector
            knowledge_injector.inject_for_question(
                question=question,
                response=response,
                objective_score=objective_score,
                source="low_objective_score"
            )
        except Exception as e:
            logger.error(f"知识注入触发失败: {e}")
    
    def _is_factual_question(self, question: str, intent_type: str) -> bool:
        """判断是否为事实性问题"""
        # 意图类型判断
        if intent_type in ["question", "factual", "verification"]:
            return True
        
        # 关键词判断
        question_lower = question.lower()
        factual_count = sum(1 for kw in self.factual_keywords if kw in question_lower)
        open_count = sum(1 for kw in self.open_keywords if kw in question_lower)
        
        return factual_count > open_count
    
    def _calculate_objective_score(
        self,
        question: str,
        response: str,
        is_factual: bool
    ) -> Tuple[float, Dict]:
        """
        计算客观分
        
        Returns:
            (score, match_details)
        """
        match_details = {
            'has_ground_truth': False,
            'extracted_triples': 0,
            'matched_triples': 0,
            'negation_matched': False,
            'match_rate': 0.0
        }
        
        if not is_factual:
            return 50.0, match_details  # 开放性问题给中性分
        
        # 1. 获取真值断言
        ground_truth = fact_store.get_assertions(question)
        negations = fact_store.get_negations(question)
        
        if not ground_truth and not negations:
            match_details['has_ground_truth'] = False
            return 50.0, match_details  # 无真值时返回中性分
        
        match_details['has_ground_truth'] = True
        
        # 2. 提取回答中的三元组
        extracted_triples = triple_extractor.extract(response)
        match_details['extracted_triples'] = len(extracted_triples)
        
        # 3. 检查是否匹配否定断言（错误示例）
        if triple_extractor.check_negation_match(extracted_triples, negations):
            match_details['negation_matched'] = True
            logger.warning(f"⚠️ 回答匹配到否定断言（错误示例）")
            return 0.0, match_details  # 匹配到错误示例，直接判死
        
        # 4. 计算与真值的匹配度
        match_rate = triple_extractor.calculate_overlap(extracted_triples, ground_truth)
        match_details['match_rate'] = match_rate
        match_details['matched_triples'] = int(match_rate * len(ground_truth))
        
        # 5. 转换为分数
        objective_score = match_rate * 100
        
        return objective_score, match_details
    
    def _calculate_subjective_score(self, user_feedback: int, question: str = "", response: str = "") -> float:
        """计算主观分（用户反馈 + 内容质量双重评估）"""
        base_score = 50.0

        if user_feedback > 0:
            base_score = min(100, base_score + (user_feedback * 10))
        elif user_feedback < 0:
            base_score = max(0, base_score + (user_feedback * 10))

        if not response or len(response.strip()) < 10:
            return base_score

        content_bonus = 0.0

        # 维度1：深度（有结构化分析、多角度探讨）
        depth_signals = ["首先", "其次", "另一方面", "从本质", "深层", "根本原因", "核心", "关键"]
        depth_count = sum(1 for s in depth_signals if s in response)
        content_bonus += min(15, depth_count * 5)

        # 维度2：温度（有同理心、陪伴感）
        warmth_signals = ["理解", "感受", "陪伴", "一起", "同行", "你", "我们"]
        warmth_count = sum(1 for s in warmth_signals if s in response)
        content_bonus += min(10, warmth_count * 3)

        # 维度3：坦诚（承认不确定性、给出方向而非绝对答案）
        honesty_signals = ["可能", "不确定", "建议", "方向", "值得考虑", "不同角度"]
        honesty_count = sum(1 for s in honesty_signals if s in response)
        content_bonus += min(10, honesty_count * 3)

        # 维度4：实用性（给出可操作建议）
        action_signals = ["可以", "尝试", "步骤", "方法", "具体", "例如", "比如"]
        action_count = sum(1 for s in action_signals if s in response)
        content_bonus += min(10, action_count * 3)

        # 维度5：完整性（回复长度适中，不太短也不冗长）
        resp_len = len(response)
        if resp_len >= 100:
            content_bonus += 5
        if resp_len >= 300:
            content_bonus += 5

        return min(100, base_score + content_bonus)
    
    def _legacy_evaluate(
        self,
        question: str,
        response: str,
        user_feedback: int
    ) -> FitnessScore:
        """旧版适应度函数（回滚用）"""
        # 原始逻辑：完全基于用户反馈
        base_score = 50.0
        
        if user_feedback > 0:
            score = min(100, base_score + (user_feedback * 15))
        elif user_feedback < 0:
            score = max(0, base_score + (user_feedback * 15))
        else:
            score = base_score
        
        return FitnessScore(
            final_score=score,
            objective_score=50.0,
            subjective_score=score,
            is_factual_question=False,
            match_details={'legacy_mode': True},
            timestamp=datetime.now().isoformat()
        )
    
    def should_inject_knowledge(self, score: FitnessScore) -> Tuple[bool, str]:
        """
        判断是否应该注入知识
        
        Returns:
            (should_inject, reason)
        """
        if self.use_legacy:
            return False, "legacy_mode"
        
        # 客观分过低且是事实性问题
        if score.is_factual_question and score.objective_score < 30:
            return True, f"客观分过低({score.objective_score:.1f})"
        
        # 匹配到否定断言
        if score.match_details.get('negation_matched'):
            return True, "匹配到错误示例"
        
        # 最终分过低
        if score.final_score < 30:
            return True, f"总分过低({score.final_score:.1f})"
        
        return False, "评分合格"


fitness_evaluator = FitnessEvaluator()