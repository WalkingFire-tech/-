"""
对话理解器 - 深层意图推断

核心功能：
1. 基于场景提示，推断用户真实意图
2. 多假设并行推理（不急于下结论）
3. 结合历史模式，识别深层意图

设计理念：
- "听见"不等于"听懂"
- 用户说的可能是表层，真实意图在深层
- 允许多个理解假设并存，等待验证
"""

from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import json
import re

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .scene_perceiver import SceneRole, SceneHint


class IntentType(Enum):
    """意图类型"""
    SEEK_INFORMATION = "seek_information"
    SEEK_GUIDANCE = "seek_guidance"
    VERIFY_UNDERSTANDING = "verify_understanding"
    CORRECT_MISTAKE = "correct_mistake"
    SHARE_KNOWLEDGE = "share_knowledge"
    TEST_SYSTEM = "test_system"
    EXPRESS_PREFERENCE = "express_preference"
    GUIDE_CONVERSATION = "guide_conversation"
    EXPRESS_FRUSTRATION = "express_frustration"
    UNKNOWN = "unknown"


@dataclass
class UnderstandingHypothesis:
    """理解假设"""
    intent_type: IntentType
    description: str
    confidence: float
    evidence: List[str]
    requires_action: bool
    action_type: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "intent_type": self.intent_type.value,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "requires_action": self.requires_action,
            "action_type": self.action_type
        }


@dataclass
class UnderstandingCandidate:
    """理解候选"""
    primary: UnderstandingHypothesis
    alternatives: List[UnderstandingHypothesis]
    reasoning: str
    uncertainty: float
    
    def to_dict(self) -> Dict:
        return {
            "primary": self.primary.to_dict(),
            "alternatives": [h.to_dict() for h in self.alternatives],
            "reasoning": self.reasoning,
            "uncertainty": self.uncertainty
        }


@dataclass
class DialogueUnderstanding:
    """对话理解结果"""
    surface_intent: str
    deep_intent: UnderstandingCandidate
    context_dependencies: List[str]
    learning_opportunity: bool
    learning_content: Optional[str]
    response_strategy: str
    
    def to_dict(self) -> Dict:
        return {
            "surface_intent": self.surface_intent,
            "deep_intent": self.deep_intent.to_dict(),
            "context_dependencies": self.context_dependencies,
            "learning_opportunity": self.learning_opportunity,
            "learning_content": self.learning_content,
            "response_strategy": self.response_strategy
        }


class DialogueUnderstander:
    """
    对话理解器
    
    推断用户输入的深层意图。
    """
    
    def __init__(self, config_path: str = "config/dialogue_cognitive_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.deep_intent_patterns = self._load_deep_intent_patterns()
        
        logger.info("🧠 对话理解器已初始化")
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('dialogue_understander', {})
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "max_hypotheses": 5,
            "hypothesis_scoring_weights": {
                "context_consistency": 0.3,
                "role_match": 0.25,
                "intent_clarity": 0.25,
                "historical_pattern": 0.2
            },
            "deep_intent_patterns": {}
        }
    
    def _load_deep_intent_patterns(self) -> Dict:
        """加载深层意图模式"""
        return self.config.get('deep_intent_patterns', {
            "learn_from_example": {
                "indicators": ["比如", "例如", "举个例子", "像这样"],
                "implied_intent": "用户在通过实例教学"
            },
            "test_understanding": {
                "indicators": ["那如果", "假如", "假设", "换个情况"],
                "implied_intent": "用户在测试系统的泛化能力"
            },
            "guide_direction": {
                "indicators": ["我想", "我希望", "目标是", "最终要"],
                "implied_intent": "用户在引导对话方向"
            },
            "express_frustration": {
                "indicators": ["还是不行", "又错了", "怎么总是", "一直"],
                "implied_intent": "用户对当前进展不满"
            }
        })
    
    def understand(
        self,
        user_input: str,
        scene_hint: SceneHint,
        dialogue_history: List[Dict] = None,
        context: Dict = None
    ) -> DialogueUnderstanding:
        """
        理解对话
        
        Args:
            user_input: 用户输入
            scene_hint: 场景提示
            dialogue_history: 对话历史
            context: 额外上下文
            
        Returns:
            DialogueUnderstanding: 对话理解结果
        """
        hypotheses = self._generate_hypotheses(user_input, scene_hint, dialogue_history)
        
        primary, alternatives = self._select_primary_hypothesis(hypotheses)
        
        reasoning = self._generate_reasoning(primary, alternatives, scene_hint)
        uncertainty = self._calculate_uncertainty(primary, alternatives)
        
        candidate = UnderstandingCandidate(
            primary=primary,
            alternatives=alternatives,
            reasoning=reasoning,
            uncertainty=uncertainty
        )
        
        surface_intent = self._extract_surface_intent(user_input, scene_hint)
        context_deps = self._identify_context_dependencies(user_input, dialogue_history)
        learning_opp, learning_content = self._identify_learning_opportunity(
            user_input, scene_hint, primary
        )
        response_strategy = self._determine_response_strategy(primary, scene_hint)
        
        understanding = DialogueUnderstanding(
            surface_intent=surface_intent,
            deep_intent=candidate,
            context_dependencies=context_deps,
            learning_opportunity=learning_opp,
            learning_content=learning_content,
            response_strategy=response_strategy
        )
        
        logger.debug(f"深层理解: {primary.intent_type.value} (置信度={primary.confidence:.2f})")
        
        return understanding
    
    def _generate_hypotheses(
        self,
        user_input: str,
        scene_hint: SceneHint,
        dialogue_history: List[Dict] = None
    ) -> List[UnderstandingHypothesis]:
        """生成理解假设"""
        hypotheses = []
        
        role_based = self._generate_role_based_hypothesis(user_input, scene_hint)
        hypotheses.extend(role_based)
        
        pattern_based = self._generate_pattern_based_hypothesis(user_input)
        hypotheses.extend(pattern_based)
        
        context_based = self._generate_context_based_hypothesis(user_input, dialogue_history)
        hypotheses.extend(context_based)
        
        hypotheses = self._deduplicate_hypotheses(hypotheses)
        
        max_hypo = self.config.get('max_hypotheses', 5)
        hypotheses = sorted(hypotheses, key=lambda h: h.confidence, reverse=True)[:max_hypo]
        
        return hypotheses
    
    def _generate_role_based_hypothesis(
        self,
        user_input: str,
        scene_hint: SceneHint
    ) -> List[UnderstandingHypothesis]:
        """基于角色生成假设"""
        hypotheses = []
        
        role_intent_map = {
            SceneRole.QUESTION: [
                (IntentType.SEEK_INFORMATION, "用户在寻求信息", 0.8),
                (IntentType.SEEK_GUIDANCE, "用户在寻求指导", 0.6)
            ],
            SceneRole.KNOWLEDGE_CONTRIBUTION: [
                (IntentType.SHARE_KNOWLEDGE, "用户在分享知识", 0.85)
            ],
            SceneRole.CORRECTION: [
                (IntentType.CORRECT_MISTAKE, "用户在纠正错误", 0.9)
            ],
            SceneRole.CHALLENGE: [
                (IntentType.TEST_SYSTEM, "用户在测试系统", 0.75),
                (IntentType.VERIFY_UNDERSTANDING, "用户在验证理解", 0.65)
            ],
            SceneRole.CONFIRMATION: [
                (IntentType.VERIFY_UNDERSTANDING, "用户在确认理解", 0.7)
            ],
            SceneRole.TEACHING: [
                (IntentType.SHARE_KNOWLEDGE, "用户在教学", 0.9)
            ]
        }
        
        primary_role = scene_hint.primary_role
        if primary_role in role_intent_map:
            for intent_type, desc, base_conf in role_intent_map[primary_role]:
                role_conf = scene_hint.confidence
                
                context_bonus = 0.0
                if scene_hint.secondary_roles:
                    context_bonus = 0.05 * len(scene_hint.secondary_roles)
                
                evidence_bonus = 0.0
                if scene_hint.indicators_matched:
                    strong_indicators = ["纠正", "错了", "不对", "我发现", "经验是"]
                    if any(ind in str(scene_hint.indicators_matched) for ind in strong_indicators):
                        evidence_bonus = 0.1
                
                conf = base_conf * (0.7 + 0.3 * role_conf)
                conf += context_bonus
                conf += evidence_bonus
                conf = min(1.0, conf)
                
                evidence = [f"角色={primary_role.value}(置信度={role_conf:.2f})"]
                if scene_hint.indicators_matched:
                    evidence.append(f"匹配指示词={scene_hint.indicators_matched[:3]}")
                
                hypotheses.append(UnderstandingHypothesis(
                    intent_type=intent_type,
                    description=desc,
                    confidence=conf,
                    evidence=evidence,
                    requires_action=intent_type in [IntentType.SHARE_KNOWLEDGE, IntentType.CORRECT_MISTAKE],
                    action_type="learn" if intent_type == IntentType.SHARE_KNOWLEDGE else None
                ))
        
        return hypotheses
    
    def _generate_pattern_based_hypothesis(
        self,
        user_input: str
    ) -> List[UnderstandingHypothesis]:
        """基于深层模式生成假设"""
        hypotheses = []
        
        for pattern_name, pattern_data in self.deep_intent_patterns.items():
            indicators = pattern_data.get('indicators', [])
            implied_intent = pattern_data.get('implied_intent', '')
            
            matched = [ind for ind in indicators if ind in user_input]
            
            if matched:
                intent_type = self._map_pattern_to_intent(pattern_name)
                
                base_confidence = 0.6
                match_ratio = len(matched) / len(indicators)
                match_bonus = match_ratio * 0.2
                
                position_bonus = 0.0
                for ind in matched:
                    pos = user_input.find(ind)
                    if pos != -1 and pos < len(user_input) * 0.3:
                        position_bonus = 0.1
                        break
                
                frequency_bonus = 0.0
                for ind in matched:
                    count = user_input.count(ind)
                    if count > 1:
                        frequency_bonus = min(0.1, (count - 1) * 0.05)
                
                confidence = base_confidence + match_bonus + position_bonus + frequency_bonus
                confidence = min(1.0, confidence)
                
                evidence = [
                    f"匹配模式={pattern_name}",
                    f"匹配指示词={matched}",
                    f"匹配率={match_ratio:.2f}"
                ]
                
                hypotheses.append(UnderstandingHypothesis(
                    intent_type=intent_type,
                    description=implied_intent,
                    confidence=confidence,
                    evidence=evidence,
                    requires_action=intent_type in [IntentType.SHARE_KNOWLEDGE, IntentType.CORRECT_MISTAKE]
                ))
        
        return hypotheses
    
    def _map_pattern_to_intent(self, pattern_name: str) -> IntentType:
        """映射模式到意图"""
        mapping = {
            "learn_from_example": IntentType.SHARE_KNOWLEDGE,
            "test_understanding": IntentType.TEST_SYSTEM,
            "guide_direction": IntentType.GUIDE_CONVERSATION,
            "express_frustration": IntentType.EXPRESS_FRUSTRATION
        }
        return mapping.get(pattern_name, IntentType.UNKNOWN)
    
    def _generate_context_based_hypothesis(
        self,
        user_input: str,
        dialogue_history: List[Dict] = None
    ) -> List[UnderstandingHypothesis]:
        """基于上下文生成假设"""
        hypotheses = []
        
        if not dialogue_history:
            return hypotheses
        
        last_msg = dialogue_history[-1] if dialogue_history else None
        if last_msg and last_msg.get('role') == 'assistant':
            if any(word in user_input for word in ["不对", "错了", "不是"]):
                hypotheses.append(UnderstandingHypothesis(
                    intent_type=IntentType.CORRECT_MISTAKE,
                    description="用户在纠正上一轮回复",
                    confidence=0.85,
                    evidence=["上下文=上一轮是系统回复"],
                    requires_action=True,
                    action_type="correct"
                ))
        
        return hypotheses
    
    def _deduplicate_hypotheses(
        self,
        hypotheses: List[UnderstandingHypothesis]
    ) -> List[UnderstandingHypothesis]:
        """去重假设"""
        seen = {}
        
        for hypo in hypotheses:
            key = hypo.intent_type
            if key not in seen or hypo.confidence > seen[key].confidence:
                seen[key] = hypo
        
        return list(seen.values())
    
    def _select_primary_hypothesis(
        self,
        hypotheses: List[UnderstandingHypothesis]
    ) -> Tuple[UnderstandingHypothesis, List[UnderstandingHypothesis]]:
        """选择主要假设"""
        if not hypotheses:
            return UnderstandingHypothesis(
                intent_type=IntentType.UNKNOWN,
                description="无法确定意图",
                confidence=0.0,
                evidence=[],
                requires_action=False
            ), []
        
        sorted_hypo = sorted(hypotheses, key=lambda h: h.confidence, reverse=True)
        primary = sorted_hypo[0]
        alternatives = sorted_hypo[1:]
        
        return primary, alternatives
    
    def _generate_reasoning(
        self,
        primary: UnderstandingHypothesis,
        alternatives: List[UnderstandingHypothesis],
        scene_hint: SceneHint
    ) -> str:
        """生成推理说明"""
        parts = [f"主要意图: {primary.description}"]
        
        if primary.evidence:
            parts.append(f"证据: {', '.join(primary.evidence[:3])}")
        
        if alternatives:
            parts.append(f"备选意图: {alternatives[0].description}")
        
        return "; ".join(parts)
    
    def _calculate_uncertainty(
        self,
        primary: UnderstandingHypothesis,
        alternatives: List[UnderstandingHypothesis]
    ) -> float:
        """计算不确定性"""
        if not alternatives:
            return 1.0 - primary.confidence
        
        gap = primary.confidence - alternatives[0].confidence
        uncertainty = (1.0 - primary.confidence) + (1.0 - gap) * 0.5
        
        return min(1.0, max(0.0, uncertainty))
    
    def _extract_surface_intent(
        self,
        user_input: str,
        scene_hint: SceneHint
    ) -> str:
        """提取表层意图"""
        return f"用户输入类型={scene_hint.primary_role.value}"
    
    def _identify_context_dependencies(
        self,
        user_input: str,
        dialogue_history: List[Dict] = None
    ) -> List[str]:
        """识别上下文依赖"""
        deps = []
        
        if not dialogue_history:
            return deps
        
        if any(word in user_input for word in ["那", "那么", "它", "这个", "那个"]):
            deps.append("依赖前文指代")
        
        if any(word in user_input for word in ["继续", "接着", "还有"]):
            deps.append("延续前文话题")
        
        return deps
    
    def _identify_learning_opportunity(
        self,
        user_input: str,
        scene_hint: SceneHint,
        primary_hypothesis: UnderstandingHypothesis
    ) -> Tuple[bool, Optional[str]]:
        """识别学习机会"""
        if primary_hypothesis.intent_type == IntentType.SHARE_KNOWLEDGE:
            return True, user_input
        
        if primary_hypothesis.intent_type == IntentType.CORRECT_MISTAKE:
            return True, f"纠正: {user_input}"
        
        if scene_hint.primary_role == SceneRole.TEACHING:
            return True, user_input
        
        return False, None
    
    def _determine_response_strategy(
        self,
        primary_hypothesis: UnderstandingHypothesis,
        scene_hint: SceneHint
    ) -> str:
        """确定响应策略"""
        strategy_map = {
            IntentType.SEEK_INFORMATION: "提供信息",
            IntentType.SEEK_GUIDANCE: "提供指导",
            IntentType.VERIFY_UNDERSTANDING: "确认理解",
            IntentType.CORRECT_MISTAKE: "接受纠正并学习",
            IntentType.SHARE_KNOWLEDGE: "学习并感谢",
            IntentType.TEST_SYSTEM: "认真应对测试",
            IntentType.EXPRESS_PREFERENCE: "记录偏好",
            IntentType.GUIDE_CONVERSATION: "跟随引导",
            IntentType.EXPRESS_FRUSTRATION: "调整策略并道歉",
            IntentType.UNKNOWN: "谨慎回应"
        }
        
        return strategy_map.get(primary_hypothesis.intent_type, "谨慎回应")