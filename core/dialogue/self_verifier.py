"""
自问自答验证器 - 验证理解的正确性

核心功能：
1. 基于理解结果，生成验证问题
2. 自问自答，检查理解一致性
3. 输出验证结果，指导后续处理

设计理念：
- 不确定时，主动验证比猜测更安全
- 自问自答是元认知能力的体现
- 验证结果决定是否需要澄清
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import json

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .dialogue_understander import DialogueUnderstanding, IntentType


class VerificationStatus(Enum):
    """验证状态"""
    CONFIRMED = "confirmed"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNCERTAIN = "uncertain"
    CONFLICT = "conflict"


@dataclass
class VerificationQuestion:
    """验证问题"""
    question: str
    purpose: str
    expected_answer_type: str
    
    def to_dict(self) -> Dict:
        return {
            "question": self.question,
            "purpose": self.purpose,
            "expected_answer_type": self.expected_answer_type
        }


@dataclass
class SelfVerificationResult:
    """自验证结果"""
    status: VerificationStatus
    confidence: float
    questions: List[VerificationQuestion]
    reasoning: str
    should_ask_user: bool
    clarification_prompt: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "confidence": self.confidence,
            "questions": [q.to_dict() for q in self.questions],
            "reasoning": self.reasoning,
            "should_ask_user": self.should_ask_user,
            "clarification_prompt": self.clarification_prompt
        }


class SelfVerifier:
    """
    自问自答验证器
    
    验证对话理解的正确性。
    """
    
    def __init__(self, config_path: str = "config/dialogue_cognitive_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.question_templates = self._load_question_templates()
        
        logger.info("🔄 自验证器已初始化")
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('self_verifier', {})
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "verification_threshold": 0.7,
            "max_questions": 3,
            "question_templates": {
                "assumption_check": "我理解的是{assumption}，对吗？",
                "intent_check": "您是想{intent}，还是{alternative}？",
                "context_check": "在这个上下文中，{context_understanding}是否准确？"
            }
        }
    
    def _load_question_templates(self) -> Dict:
        """加载问题模板"""
        return self.config.get('question_templates', {
            "assumption_check": "我理解的是{assumption}，对吗？",
            "intent_check": "您是想{intent}，还是{alternative}？",
            "context_check": "在这个上下文中，{context_understanding}是否准确？"
        })
    
    def verify(
        self,
        understanding: DialogueUnderstanding,
        user_input: str,
        dialogue_history: List[Dict] = None,
        context: Dict = None
    ) -> SelfVerificationResult:
        """
        验证理解
        
        Args:
            understanding: 对话理解结果
            user_input: 用户输入
            dialogue_history: 对话历史
            context: 额外上下文
            
        Returns:
            SelfVerificationResult: 验证结果
        """
        questions = self._generate_verification_questions(
            understanding, user_input, dialogue_history
        )
        
        internal_verification = self._self_answer_questions(questions, understanding)
        
        status, confidence = self._determine_verification_status(
            understanding, internal_verification
        )
        
        reasoning = self._generate_verification_reasoning(
            status, confidence, understanding
        )
        
        should_ask = self._should_ask_user(status, confidence, understanding)
        clarification = self._generate_clarification_prompt(
            status, questions, understanding
        ) if should_ask else None
        
        result = SelfVerificationResult(
            status=status,
            confidence=confidence,
            questions=questions,
            reasoning=reasoning,
            should_ask_user=should_ask,
            clarification_prompt=clarification
        )
        
        logger.debug(f"自验证: {status.value} (置信度={confidence:.2f})")
        
        return result
    
    def _generate_verification_questions(
        self,
        understanding: DialogueUnderstanding,
        user_input: str,
        dialogue_history: List[Dict] = None
    ) -> List[VerificationQuestion]:
        """生成验证问题"""
        questions = []
        max_q = self.config.get('max_questions', 3)
        
        primary_intent = understanding.deep_intent.primary
        
        if primary_intent.confidence < 0.7:
            questions.append(VerificationQuestion(
                question=self.question_templates['intent_check'].format(
                    intent=primary_intent.description,
                    alternative=understanding.deep_intent.alternatives[0].description if understanding.deep_intent.alternatives else "其他意图"
                ),
                purpose="确认用户真实意图",
                expected_answer_type="choice"
            ))
        
        if understanding.context_dependencies:
            questions.append(VerificationQuestion(
                question=f"用户输入依赖上下文: {', '.join(understanding.context_dependencies)}，理解是否准确？",
                purpose="验证上下文理解",
                expected_answer_type="confirmation"
            ))
        
        if primary_intent.intent_type in [IntentType.SHARE_KNOWLEDGE, IntentType.CORRECT_MISTAKE]:
            questions.append(VerificationQuestion(
                question=f"用户意图是{primary_intent.description}，是否应该学习此内容？",
                purpose="确认学习决策",
                expected_answer_type="boolean"
            ))
        
        return questions[:max_q]
    
    def _self_answer_questions(
        self,
        questions: List[VerificationQuestion],
        understanding: DialogueUnderstanding
    ) -> Dict[str, Tuple[str, float]]:
        """自问自答"""
        answers = {}
        
        for i, question in enumerate(questions):
            if "意图" in question.purpose or "intent" in question.purpose.lower():
                confidence = understanding.deep_intent.primary.confidence
                answer = "确认" if confidence > 0.7 else "不确定"
                answers[f"q{i}"] = (answer, confidence)
            
            elif "上下文" in question.purpose:
                if understanding.context_dependencies:
                    answers[f"q{i}"] = ("有依赖", 0.8)
                else:
                    answers[f"q{i}"] = ("无依赖", 0.9)
            
            elif "学习" in question.purpose:
                if understanding.learning_opportunity:
                    answers[f"q{i}"] = ("应该学习", 0.85)
                else:
                    answers[f"q{i}"] = ("无需学习", 0.9)
        
        return answers
    
    def _determine_verification_status(
        self,
        understanding: DialogueUnderstanding,
        internal_verification: Dict[str, Tuple[str, float]]
    ) -> Tuple[VerificationStatus, float]:
        """确定验证状态"""
        threshold = self.config.get('verification_threshold', 0.7)
        
        primary_conf = understanding.deep_intent.primary.confidence
        uncertainty = understanding.deep_intent.uncertainty
        
        if not internal_verification:
            if primary_conf >= threshold:
                return VerificationStatus.CONFIRMED, primary_conf
            else:
                return VerificationStatus.UNCERTAIN, primary_conf
        
        avg_conf = sum(ans[1] for ans in internal_verification.values()) / len(internal_verification)
        
        if avg_conf >= threshold and uncertainty < 0.3:
            return VerificationStatus.CONFIRMED, avg_conf
        elif avg_conf >= 0.5 and uncertainty < 0.5:
            return VerificationStatus.NEEDS_CLARIFICATION, avg_conf
        elif uncertainty >= 0.5:
            return VerificationStatus.UNCERTAIN, avg_conf
        else:
            return VerificationStatus.NEEDS_CLARIFICATION, avg_conf
    
    def _generate_verification_reasoning(
        self,
        status: VerificationStatus,
        confidence: float,
        understanding: DialogueUnderstanding
    ) -> str:
        """生成验证推理"""
        parts = [
            f"验证状态: {status.value}",
            f"置信度: {confidence:.2f}",
            f"主要意图: {understanding.deep_intent.primary.description}"
        ]
        
        if understanding.deep_intent.alternatives:
            parts.append(f"备选意图: {understanding.deep_intent.alternatives[0].description}")
        
        return "; ".join(parts)
    
    def _should_ask_user(
        self,
        status: VerificationStatus,
        confidence: float,
        understanding: DialogueUnderstanding
    ) -> bool:
        """是否应该询问用户"""
        from .dialogue_understander import IntentType
        
        primary_intent = understanding.deep_intent.primary
        
        if primary_intent.intent_type in [
            IntentType.SEEK_INFORMATION,
            IntentType.SEEK_GUIDANCE,
            IntentType.SHARE_KNOWLEDGE,
            IntentType.VERIFY_UNDERSTANDING
        ]:
            return False
        
        if status == VerificationStatus.CONFLICT and confidence < 0.4:
            return True
        
        if status == VerificationStatus.NEEDS_CLARIFICATION and confidence < 0.3:
            return True
        
        if understanding.deep_intent.uncertainty > 0.5:
            return True
        
        return False
    
    def _generate_clarification_prompt(
        self,
        status: VerificationStatus,
        questions: List[VerificationQuestion],
        understanding: DialogueUnderstanding
    ) -> Optional[str]:
        """生成澄清提示"""
        if not questions:
            return None
        
        primary_q = questions[0]
        
        if status == VerificationStatus.CONFLICT:
            return f"我需要确认一下: {primary_q.question}"
        elif status == VerificationStatus.NEEDS_CLARIFICATION:
            return f"让我确认我的理解: {primary_q.question}"
        else:
            return f"我想确认: {primary_q.question}"
