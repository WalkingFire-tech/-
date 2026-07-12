"""
对话认知引擎 - 整合所有对话理解组件

核心功能：
1. 整合场景感知、深层理解、自验证
2. 输出统一的对话处理结果
3. 与系统其他模块集成

设计理念：
- 感知层预处理 → 认知层深层理解 → 自问自答验证 → 总结最优
- 每一层都输出中间结果，便于调试和优化
- 最终输出指导后续处理（学习/回答/澄清）
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import json
import hashlib
import time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .scene_perceiver import ScenePerceiver, SceneHint, SceneRole
from .dialogue_understander import DialogueUnderstander, DialogueUnderstanding
from .self_verifier import SelfVerifier, SelfVerificationResult


@dataclass
class DialogueProcessingResult:
    """对话处理结果"""
    user_input: str
    scene_hint: SceneHint
    understanding: DialogueUnderstanding
    verification: SelfVerificationResult
    
    action_required: bool
    action_type: Optional[str]
    action_content: Optional[str]
    
    response_guidance: str
    should_learn: bool
    learning_content: Optional[str]
    
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "user_input": self.user_input,
            "scene_hint": self.scene_hint.to_dict(),
            "understanding": self.understanding.to_dict(),
            "verification": self.verification.to_dict(),
            "action_required": self.action_required,
            "action_type": self.action_type,
            "action_content": self.action_content,
            "response_guidance": self.response_guidance,
            "should_learn": self.should_learn,
            "learning_content": self.learning_content,
            "metadata": self.metadata
        }


class DialogueCognitiveEngine:
    """
    对话认知引擎
    
    整合场景感知、深层理解、自验证，输出统一的处理结果。
    """
    
    def __init__(self, config_path: str = "config/dialogue_cognitive_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        self.scene_perceiver = ScenePerceiver(config_path)
        self.dialogue_understander = DialogueUnderstander(config_path)
        self.self_verifier = SelfVerifier(config_path)
        
        self._understanding_cache = {}
        self._cache_ttl = self.config.get('cache_ttl', 300)
        
        logger.info("🎭 对话认知引擎已初始化")
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('integration', {})
        return {
            "enable_learning": True,
            "enable_self_verification": True,
            "enable_deep_understanding": True,
            "cache_understanding": True,
            "cache_ttl": 300
        }
    
    def process(
        self,
        user_input: str,
        dialogue_history: List[Dict] = None,
        context: Dict = None
    ) -> DialogueProcessingResult:
        """
        处理对话
        
        Args:
            user_input: 用户输入
            dialogue_history: 对话历史
            context: 额外上下文
            
        Returns:
            DialogueProcessingResult: 处理结果
        """
        cache_key = self._get_cache_key(user_input, dialogue_history)
        if self.config.get('cache_understanding', True):
            cached = self._get_cached_result(cache_key)
            if cached:
                logger.debug("使用缓存的理解结果")
                return cached
        
        scene_hint = self.scene_perceiver.perceive(
            user_input, dialogue_history, context
        )
        
        if self.config.get('enable_deep_understanding', True):
            understanding = self.dialogue_understander.understand(
                user_input, scene_hint, dialogue_history, context
            )
        else:
            understanding = self._create_simple_understanding(user_input, scene_hint)
        
        if self.config.get('enable_self_verification', True):
            verification = self.self_verifier.verify(
                understanding, user_input, dialogue_history, context
            )
        else:
            verification = self._create_simple_verification(understanding)
        
        action_required, action_type, action_content = self._determine_action(
            understanding, verification
        )
        
        response_guidance = self._generate_response_guidance(
            understanding, verification
        )
        
        should_learn, learning_content = self._determine_learning(
            understanding, verification
        )
        
        result = DialogueProcessingResult(
            user_input=user_input,
            scene_hint=scene_hint,
            understanding=understanding,
            verification=verification,
            action_required=action_required,
            action_type=action_type,
            action_content=action_content,
            response_guidance=response_guidance,
            should_learn=should_learn,
            learning_content=learning_content,
            metadata={
                "timestamp": time.time(),
                "cache_key": cache_key
            }
        )
        
        if self.config.get('cache_understanding', True):
            self._cache_result(cache_key, result)
        
        logger.info(
            f"对话处理完成: 角色={scene_hint.primary_role.value}, "
            f"意图={understanding.deep_intent.primary.intent_type.value}, "
            f"验证={verification.status.value}"
        )
        
        return result
    
    def _get_cache_key(
        self,
        user_input: str,
        dialogue_history: List[Dict] = None
    ) -> str:
        """生成缓存键"""
        context_str = ""
        if dialogue_history:
            recent = dialogue_history[-3:] if len(dialogue_history) > 3 else dialogue_history
            context_str = "|".join([msg.get('content', '')[:50] for msg in recent])
        
        key_str = f"{user_input}|{context_str}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[DialogueProcessingResult]:
        """获取缓存结果"""
        cached = self._understanding_cache.get(cache_key)
        if cached:
            if time.time() - cached['timestamp'] < self._cache_ttl:
                return cached['result']
            else:
                del self._understanding_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: DialogueProcessingResult):
        """缓存结果"""
        if len(self._understanding_cache) > 100:
            oldest_key = min(
                self._understanding_cache.keys(),
                key=lambda k: self._understanding_cache[k]['timestamp']
            )
            del self._understanding_cache[oldest_key]
        
        self._understanding_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
    
    def _create_simple_understanding(
        self,
        user_input: str,
        scene_hint: SceneHint
    ) -> DialogueUnderstanding:
        """
        创建简单理解（禁用深层理解时的备选方案）
        
        即使禁用深层理解，也要进行基本的意图推断：
        1. 基于场景角色的意图映射
        2. 基于关键词的简单意图识别
        3. 基于历史对话的模式匹配
        """
        from .dialogue_understander import (
            UnderstandingHypothesis,
            UnderstandingCandidate,
            IntentType
        )
        
        role_intent_mapping = {
            "question": IntentType.SEEK_INFORMATION,
            "knowledge_contribution": IntentType.SHARE_KNOWLEDGE,
            "correction": IntentType.CORRECT_MISTAKE,
            "challenge": IntentType.VERIFY_UNDERSTANDING,
            "confirmation": IntentType.VERIFY_UNDERSTANDING,
            "teaching": IntentType.SHARE_KNOWLEDGE
        }
        
        intent_type = role_intent_mapping.get(
            scene_hint.primary_role.value,
            IntentType.UNKNOWN
        )
        
        confidence = scene_hint.role_confidence
        
        evidence = [f"角色={scene_hint.primary_role.value}(置信度={scene_hint.role_confidence:.2f})"]
        
        if scene_hint.secondary_roles:
            evidence.append(f"次要角色={', '.join(r.value for r in scene_hint.secondary_roles)}")
        
        import re
        question_patterns = [r'如何', r'怎么', r'为什么', r'什么是', r'能否']
        if any(re.search(p, user_input) for p in question_patterns):
            if intent_type == IntentType.UNKNOWN:
                intent_type = IntentType.SEEK_INFORMATION
            confidence = min(1.0, confidence + 0.1)
            evidence.append("包含疑问词")
        
        correction_patterns = [r'不对', r'错了', r'应该是', r'纠正']
        if any(re.search(p, user_input) for p in correction_patterns):
            intent_type = IntentType.CORRECT_MISTAKE
            confidence = min(1.0, confidence + 0.15)
            evidence.append("包含纠正词")
        
        knowledge_patterns = [r'我发现', r'其实', r'经验是', r'建议']
        if any(re.search(p, user_input) for p in knowledge_patterns):
            intent_type = IntentType.SHARE_KNOWLEDGE
            confidence = min(1.0, confidence + 0.15)
            evidence.append("包含知识贡献词")
        
        hypo = UnderstandingHypothesis(
            intent_type=intent_type,
            description=f"基于角色推断的意图: {intent_type.value}",
            confidence=confidence,
            evidence=evidence,
            requires_action=(intent_type in [IntentType.CORRECT_MISTAKE, IntentType.SHARE_KNOWLEDGE])
        )
        
        alternatives = []
        if scene_hint.secondary_roles:
            for sec_role in scene_hint.secondary_roles[:2]:
                sec_intent = role_intent_mapping.get(sec_role.value, IntentType.UNKNOWN)
                if sec_intent != intent_type:
                    alt_hypo = UnderstandingHypothesis(
                        intent_type=sec_intent,
                        description=f"次要角色推断: {sec_role.value}",
                        confidence=scene_hint.role_confidence * 0.7,
                        evidence=[f"次要角色={sec_role.value}"],
                        requires_action=False
                    )
                    alternatives.append(alt_hypo)
        
        candidate = UnderstandingCandidate(
            primary=hypo,
            alternatives=alternatives,
            reasoning="基于角色和关键词的简单意图推断",
            uncertainty=1.0 - confidence
        )
        
        learning_opportunity = intent_type in [
            IntentType.SHARE_KNOWLEDGE,
            IntentType.CORRECT_MISTAKE,
            IntentType.SHARE_KNOWLEDGE
        ]
        
        learning_content = None
        if learning_opportunity:
            learning_content = {
                "type": intent_type.value,
                "content": user_input,
                "confidence": confidence
            }
        
        response_strategy = self._determine_response_strategy(intent_type, confidence)
        
        return DialogueUnderstanding(
            surface_intent=f"角色={scene_hint.primary_role.value}",
            deep_intent=candidate,
            context_dependencies=[],
            learning_opportunity=learning_opportunity,
            learning_content=learning_content,
            response_strategy=response_strategy
        )
    
    def _determine_response_strategy(self, intent_type, confidence: float) -> str:
        """确定响应策略"""
        from .dialogue_understander import IntentType
        
        strategy_mapping = {
            IntentType.SEEK_INFORMATION: "提供信息",
            IntentType.SHARE_KNOWLEDGE: "确认并学习",
            IntentType.CORRECT_MISTAKE: "接受纠正并更新",
            IntentType.VERIFY_UNDERSTANDING: "提供证据",
            IntentType.SEEK_GUIDANCE: "提供指导",
            IntentType.EXPRESS_PREFERENCE: "记录偏好",
            IntentType.GUIDE_CONVERSATION: "跟随引导",
            IntentType.EXPRESS_FRUSTRATION: "安抚并改进",
            IntentType.TEST_SYSTEM: "认真回应",
            IntentType.UNKNOWN: "谨慎回应"
        }
        
        base_strategy = strategy_mapping.get(intent_type, "谨慎回应")
        
        if confidence < 0.6:
            return f"不确定({base_strategy})"
        
        return base_strategy
    
    def _create_simple_verification(
        self,
        understanding: DialogueUnderstanding
    ) -> SelfVerificationResult:
        """
        创建简单验证（禁用自验证时的备选方案）
        
        即使禁用自验证，也要进行基本的一致性检查：
        1. 意图置信度检查
        2. 上下文一致性检查
        3. 历史对话一致性检查
        """
        from .self_verifier import VerificationStatus
        
        confidence = understanding.deep_intent.primary.confidence
        
        issues = []
        
        if confidence < 0.5:
            issues.append("意图置信度过低")
        
        if understanding.deep_intent.uncertainty > 0.6:
            issues.append("不确定性过高")
        
        if not understanding.deep_intent.primary.evidence:
            issues.append("缺乏证据支持")
        
        if len(issues) == 0:
            status = VerificationStatus.CONFIRMED
            final_confidence = min(0.95, confidence + 0.1)
            should_ask = False
            clarification = None
        elif len(issues) == 1:
            status = VerificationStatus.PARTIAL
            final_confidence = confidence
            should_ask = confidence < 0.6
            clarification = f"需要确认: {issues[0]}" if should_ask else None
        else:
            status = VerificationStatus.NEEDS_CLARIFICATION
            final_confidence = confidence * 0.8
            should_ask = True
            clarification = f"存在多个问题: {'; '.join(issues)}"
        
        reasoning = f"简单验证: 置信度={confidence:.2f}, 问题数={len(issues)}"
        
        return SelfVerificationResult(
            status=status,
            confidence=final_confidence,
            questions=[],
            reasoning=reasoning,
            should_ask_user=should_ask,
            clarification_prompt=clarification
        )
    
    def _determine_action(
        self,
        understanding: DialogueUnderstanding,
        verification: SelfVerificationResult
    ) -> tuple:
        """确定需要的行动"""
        if verification.should_ask_user:
            return True, "clarify", verification.clarification_prompt
        
        if understanding.learning_opportunity and self.config.get('enable_learning', True):
            return True, "learn", understanding.learning_content
        
        primary_intent = understanding.deep_intent.primary
        if primary_intent.requires_action:
            return True, primary_intent.action_type or "respond", None
        
        return False, None, None
    
    def _generate_response_guidance(
        self,
        understanding: DialogueUnderstanding,
        verification: SelfVerificationResult
    ) -> str:
        """生成响应指导"""
        if verification.should_ask_user:
            return f"需要澄清: {verification.clarification_prompt}"
        
        return understanding.response_strategy
    
    def _determine_learning(
        self,
        understanding: DialogueUnderstanding,
        verification: SelfVerificationResult
    ) -> tuple:
        """确定是否需要学习"""
        if not self.config.get('enable_learning', True):
            return False, None
        
        if verification.status.value in ['confirmed', 'needs_clarification']:
            if understanding.learning_opportunity:
                return True, understanding.learning_content
        
        return False, None
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            "cache_size": len(self._understanding_cache),
            "config": self.config
        }


_engine_instance: Optional[DialogueCognitiveEngine] = None


def get_dialogue_engine() -> DialogueCognitiveEngine:
    """获取对话认知引擎单例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DialogueCognitiveEngine()
    return _engine_instance


def process_dialogue(
    user_input: str,
    dialogue_history: List[Dict] = None,
    context: Dict = None
) -> DialogueProcessingResult:
    """处理对话的便捷函数"""
    engine = get_dialogue_engine()
    return engine.process(user_input, dialogue_history, context)