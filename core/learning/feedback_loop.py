"""
经验反馈回路 - 验证学到的知识是否真正有效

核心理念：学习必须经过验证，形成完整的反馈闭环
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    CORRECTIVE = "corrective"


@dataclass
class Feedback:
    type: FeedbackType
    knowledge_id: str
    expected_outcome: Any
    actual_outcome: Any
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 0.0
    reason: str = ""


@dataclass
class ValidationRule:
    name: str
    condition: Callable[[Any, Any], bool]
    weight: float = 1.0


@dataclass
class LoopResult:
    validated: bool
    knowledge_id: str
    accuracy: float
    adjustments: List[str]
    confidence_delta: float
    should_refine: bool


class LearningFeedbackLoop:
    """
    学习反馈回路
    
    验证知识有效性，形成学习闭环
    """
    
    def __init__(self):
        self.knowledge_store: Dict[str, Dict] = {}
        self.feedback_history: List[Feedback] = []
        self.validation_rules: List[ValidationRule] = []
        self.adjustment_strategies: Dict[str, Callable] = {}
        self._setup_default_rules()
        self._setup_default_strategies()
    
    def _setup_default_rules(self):
        self.validation_rules = [
            ValidationRule(
                name="exact_match",
                condition=lambda expected, actual: expected == actual,
                weight=1.0,
            ),
            ValidationRule(
                name="type_match",
                condition=lambda expected, actual: type(expected) == type(actual),
                weight=0.5,
            ),
            ValidationRule(
                name="structure_match",
                condition=lambda expected, actual: (
                    isinstance(expected, dict) and isinstance(actual, dict) and
                    set(expected.keys()) == set(actual.keys())
                ),
                weight=0.7,
            ),
        ]
    
    def _setup_default_strategies(self):
        self.adjustment_strategies = {
            "positive": self._reinforce_knowledge,
            "negative": self._weaken_knowledge,
            "neutral": self._maintain_knowledge,
            "corrective": self._correct_knowledge,
        }
    
    def register_knowledge(
        self,
        knowledge_id: str,
        knowledge: Any,
        initial_confidence: float = 0.5,
    ) -> None:
        self.knowledge_store[knowledge_id] = {
            "content": knowledge,
            "confidence": initial_confidence,
            "validations": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    
    def validate(self, feedback: Feedback) -> LoopResult:
        if feedback.knowledge_id not in self.knowledge_store:
            return LoopResult(
                validated=False,
                knowledge_id=feedback.knowledge_id,
                accuracy=0.0,
                adjustments=["知识不存在"],
                confidence_delta=0.0,
                should_refine=False,
            )
        
        knowledge_entry = self.knowledge_store[feedback.knowledge_id]
        
        accuracy = self._calculate_accuracy(
            feedback.expected_outcome,
            feedback.actual_outcome,
        )
        
        adjustments = []
        confidence_delta = 0.0
        
        if accuracy >= 0.8:
            feedback.type = FeedbackType.POSITIVE
            confidence_delta = 0.1
            adjustments.append("知识验证成功，增强置信度")
        elif accuracy >= 0.5:
            feedback.type = FeedbackType.NEUTRAL
            adjustments.append("知识部分有效，保持观察")
        else:
            feedback.type = FeedbackType.NEGATIVE
            confidence_delta = -0.2
            adjustments.append("知识验证失败，降低置信度")
        
        if feedback.type in self.adjustment_strategies:
            self.adjustment_strategies[feedback.type](feedback, knowledge_entry)
        
        knowledge_entry["validations"].append({
            "accuracy": accuracy,
            "timestamp": feedback.timestamp.isoformat(),
            "type": feedback.type.value,
        })
        knowledge_entry["updated_at"] = datetime.now()
        
        self.feedback_history.append(feedback)
        
        should_refine = (
            accuracy < 0.5 or
            knowledge_entry["confidence"] < 0.3
        )
        
        return LoopResult(
            validated=accuracy >= 0.5,
            knowledge_id=feedback.knowledge_id,
            accuracy=accuracy,
            adjustments=adjustments,
            confidence_delta=confidence_delta,
            should_refine=should_refine,
        )
    
    def _calculate_accuracy(self, expected: Any, actual: Any) -> float:
        scores = []
        
        for rule in self.validation_rules:
            try:
                if rule.condition(expected, actual):
                    scores.append(rule.weight)
            except Exception:
                logger.warning("操作降级跳过")
        
        if not scores:
            return 0.0
        
        max_possible = sum(rule.weight for rule in self.validation_rules)
        if max_possible == 0:
            return 0.0
        
        return sum(scores) / max_possible
    
    def _reinforce_knowledge(self, feedback: Feedback, entry: Dict) -> None:
        entry["confidence"] = min(1.0, entry["confidence"] + 0.1)
    
    def _weaken_knowledge(self, feedback: Feedback, entry: Dict) -> None:
        entry["confidence"] = max(0.0, entry["confidence"] - 0.2)
    
    def _maintain_knowledge(self, feedback: Feedback, entry: Dict) -> None:
        pass
    
    def _correct_knowledge(self, feedback: Feedback, entry: Dict) -> None:
        if feedback.actual_outcome is not None:
            entry["content"] = feedback.actual_outcome
            entry["confidence"] = 0.5
    
    def batch_validate(self, feedbacks: List[Feedback]) -> List[LoopResult]:
        results = []
        for feedback in feedbacks:
            results.append(self.validate(feedback))
        return results
    
    def get_knowledge_confidence(self, knowledge_id: str) -> float:
        if knowledge_id not in self.knowledge_store:
            return 0.0
        return self.knowledge_store[knowledge_id]["confidence"]
    
    def get_validated_knowledge(self, min_confidence: float = 0.7) -> Dict[str, Any]:
        return {
            k: v["content"]
            for k, v in self.knowledge_store.items()
            if v["confidence"] >= min_confidence
        }
    
    def get_feedback_summary(self) -> Dict[str, Any]:
        if not self.feedback_history:
            return {"total": 0, "positive_rate": 0.0}
        
        positive = sum(1 for f in self.feedback_history if f.type == FeedbackType.POSITIVE)
        negative = sum(1 for f in self.feedback_history if f.type == FeedbackType.NEGATIVE)
        
        return {
            "total": len(self.feedback_history),
            "positive": positive,
            "negative": negative,
            "positive_rate": positive / len(self.feedback_history),
            "average_confidence": sum(
                self.knowledge_store[k]["confidence"]
                for k in self.knowledge_store
            ) / len(self.knowledge_store) if self.knowledge_store else 0.0,
        }
    
    def add_validation_rule(self, rule: ValidationRule) -> None:
        self.validation_rules.append(rule)
    
    def add_adjustment_strategy(
        self,
        name: str,
        strategy: Callable[[Feedback, Dict], None],
    ) -> None:
        self.adjustment_strategies[name] = strategy
    
    def clear_history(self) -> None:
        self.feedback_history.clear()
    
    def export_state(self) -> Dict:
        return {
            "knowledge_store": self.knowledge_store,
            "feedback_summary": self.get_feedback_summary(),
        }