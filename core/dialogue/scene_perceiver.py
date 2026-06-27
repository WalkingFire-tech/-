"""
场景感知器 - 判断用户输入在对话中的角色

核心功能：
1. 识别输入类型（提问/贡献知识/纠正/质疑/确认/教学）
2. 分析上下文线索
3. 输出场景提示（SceneHint）供后续处理

设计理念：
- 不做单一判断，而是输出多维度线索
- 允许角色叠加（一个输入可能同时是"提问"和"质疑"）
- 上下文敏感（结合历史对话判断）
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


class SceneRole(Enum):
    """场景角色"""
    QUESTION = "question"
    KNOWLEDGE_CONTRIBUTION = "knowledge_contribution"
    CORRECTION = "correction"
    CHALLENGE = "challenge"
    CONFIRMATION = "confirmation"
    TEACHING = "teaching"
    UNKNOWN = "unknown"


@dataclass
class SceneHint:
    """场景提示"""
    primary_role: SceneRole
    role_scores: Dict[SceneRole, float]
    confidence: float
    indicators_matched: List[str]
    context_clues: List[str]
    is_multi_role: bool
    secondary_roles: List[SceneRole] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "primary_role": self.primary_role.value,
            "role_scores": {k.value: v for k, v in self.role_scores.items()},
            "confidence": self.confidence,
            "indicators_matched": self.indicators_matched,
            "context_clues": self.context_clues,
            "is_multi_role": self.is_multi_role,
            "secondary_roles": [r.value for r in self.secondary_roles]
        }


class ScenePerceiver:
    """
    场景感知器
    
    判断用户输入在当前对话场景中的角色。
    """
    
    def __init__(self, config_path: str = "config/dialogue_cognitive_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.role_indicators = self._load_role_indicators()
        
        logger.info("🔍 场景感知器已初始化")
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('scene_perceiver', {})
        return self._default_config()
    
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            "role_confidence_threshold": 0.6,
            "multi_role_threshold": 0.4,
            "context_window": 5,
            "role_indicators": {
                "question": ["？", "?", "如何", "怎么", "为什么"],
                "knowledge_contribution": ["我发现", "其实", "实际上"],
                "correction": ["不对", "错了", "不是这样"],
                "challenge": ["质疑", "怀疑", "真的吗"],
                "confirmation": ["好的", "明白", "懂了"],
                "teaching": ["教你", "告诉你", "记住"]
            }
        }
    
    def _load_role_indicators(self) -> Dict[SceneRole, List[str]]:
        """加载角色指示词"""
        indicators = self.config.get('role_indicators', {})
        return {
            SceneRole.QUESTION: indicators.get('question', []),
            SceneRole.KNOWLEDGE_CONTRIBUTION: indicators.get('knowledge_contribution', []),
            SceneRole.CORRECTION: indicators.get('correction', []),
            SceneRole.CHALLENGE: indicators.get('challenge', []),
            SceneRole.CONFIRMATION: indicators.get('confirmation', []),
            SceneRole.TEACHING: indicators.get('teaching', [])
        }
    
    def perceive(
        self,
        user_input: str,
        dialogue_history: List[Dict] = None,
        context: Dict = None
    ) -> SceneHint:
        """
        感知场景
        
        Args:
            user_input: 用户输入
            dialogue_history: 对话历史
            context: 额外上下文
            
        Returns:
            SceneHint: 场景提示
        """
        role_scores = self._calculate_role_scores(user_input)
        indicators_matched = self._find_matched_indicators(user_input)
        context_clues = self._extract_context_clues(user_input, dialogue_history)
        
        primary_role, confidence = self._determine_primary_role(role_scores)
        is_multi_role, secondary_roles = self._check_multi_role(role_scores, primary_role)
        
        hint = SceneHint(
            primary_role=primary_role,
            role_scores=role_scores,
            confidence=confidence,
            indicators_matched=indicators_matched,
            context_clues=context_clues,
            is_multi_role=is_multi_role,
            secondary_roles=secondary_roles
        )
        
        logger.debug(f"场景感知: {primary_role.value} (置信度={confidence:.2f}, 多角色={is_multi_role})")
        
        return hint
    
    def _calculate_role_scores(self, user_input: str) -> Dict[SceneRole, float]:
        """计算各角色得分"""
        scores = {}
        input_lower = user_input.lower()
        
        for role, indicators in self.role_indicators.items():
            score = 0.0
            matched_count = 0
            
            for indicator in indicators:
                if indicator in user_input or indicator in input_lower:
                    matched_count += 1
                    score += 1.0
            
            if matched_count > 0:
                # 根据角色类型设置不同的基础分和优先级
                if role == SceneRole.CHALLENGE:
                    # 质疑优先级最高
                    score = min(1.0, 0.7 + matched_count * 0.15)
                elif role == SceneRole.CORRECTION:
                    # 纠正优先级次高
                    score = min(1.0, 0.65 + matched_count * 0.15)
                elif role == SceneRole.QUESTION:
                    # 问题优先级较低
                    score = min(1.0, 0.5 + matched_count * 0.1)
                else:
                    score = min(1.0, 0.5 + matched_count * 0.15)
            
            scores[role] = score
        
        scores[SceneRole.UNKNOWN] = 0.1
        
        return scores
    
    def _find_matched_indicators(self, user_input: str) -> List[str]:
        """找出匹配的指示词"""
        matched = []
        
        for role, indicators in self.role_indicators.items():
            for indicator in indicators:
                if indicator in user_input:
                    matched.append(f"{role.value}:{indicator}")
        
        return matched
    
    def _extract_context_clues(
        self,
        user_input: str,
        dialogue_history: List[Dict] = None
    ) -> List[str]:
        """
        提取上下文线索
        
        多维度上下文分析：
        1. 对话历史主题追踪
        2. 逻辑连接词分析
        3. 代词引用解析
        4. 情绪变化检测
        5. 话题转换识别
        """
        clues = []
        
        if not dialogue_history:
            return clues
        
        window = self.config.get('context_window', 5)
        recent_history = dialogue_history[-window:] if len(dialogue_history) > window else dialogue_history
        
        for i, msg in enumerate(recent_history):
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'assistant':
                import re
                key_terms = re.findall(r'([^。！？\n]{4,10})', content)
                if key_terms:
                    clues.append(f"系统提到: {key_terms[0]}")
            
            if role == 'user':
                if i < len(recent_history) - 1:
                    prev_content = recent_history[i + 1].get('content', '') if i + 1 < len(recent_history) else ''
                    if prev_content:
                        current_len = len(content)
                        prev_len = len(prev_content)
                        if abs(current_len - prev_len) > prev_len * 0.5:
                            clues.append("用户输入长度显著变化")
        
        continuation_words = ["那", "那么", "既然", "所以", "因此", "于是", "接着", "然后"]
        if any(word in user_input for word in continuation_words):
            clues.append("用户在延续前文逻辑")
        
        reference_patterns = [
            (r'它(是|有|在)', "指代前文对象"),
            (r'这个(是|有|在)', "指代前文概念"),
            (r'那个(是|有|在)', "指代前文实例"),
            (r'上述', "引用前文内容"),
            (r'前面', "引用前文内容"),
            (r'刚才', "引用前文内容")
        ]
        
        import re
        for pattern, description in reference_patterns:
            if re.search(pattern, user_input):
                clues.append(description)
                break
        
        emotion_indicators = {
            "positive": ["好的", "谢谢", "明白了", "很好", "太好了"],
            "negative": ["不对", "错了", "不行", "糟糕", "还是不行"],
            "frustrated": ["怎么又", "还是", "一直", "总是"],
            "curious": ["为什么", "怎么回事", "如何", "能不能"]
        }
        
        current_emotion = None
        for emotion, indicators in emotion_indicators.items():
            if any(ind in user_input for ind in indicators):
                current_emotion = emotion
                break
        
        if current_emotion:
            for msg in reversed(recent_history[:-1]):
                if msg.get('role') == 'user':
                    prev_content = msg.get('content', '')
                    prev_emotion = None
                    for emotion, indicators in emotion_indicators.items():
                        if any(ind in prev_content for ind in indicators):
                            prev_emotion = emotion
                            break
                    
                    if prev_emotion and prev_emotion != current_emotion:
                        clues.append(f"情绪变化: {prev_emotion} → {current_emotion}")
                    break
        
        topic_shift_indicators = [
            "换个话题", "说点别的", "另外", "对了",
            "顺便问一下", "还有个问题"
        ]
        if any(ind in user_input for ind in topic_shift_indicators):
            clues.append("用户主动转换话题")
        
        if recent_history:
            last_user_msg = None
            for msg in reversed(recent_history):
                if msg.get('role') == 'user':
                    last_user_msg = msg.get('content', '')
                    break
            
            if last_user_msg:
                last_words = set(re.findall(r'\w+', last_user_msg.lower()))
                current_words = set(re.findall(r'\w+', user_input.lower()))
                
                if last_words and current_words:
                    overlap = len(last_words & current_words) / len(last_words)
                    if overlap < 0.2:
                        clues.append("话题可能已转换")
        
        return clues
    
    def _determine_primary_role(
        self,
        role_scores: Dict[SceneRole, float]
    ) -> Tuple[SceneRole, float]:
        """确定主要角色"""
        sorted_scores = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)
        
        if not sorted_scores or sorted_scores[0][1] < 0.1:
            return SceneRole.UNKNOWN, 0.0
        
        primary_role, confidence = sorted_scores[0]
        threshold = self.config.get('role_confidence_threshold', 0.6)
        
        if confidence < threshold:
            return SceneRole.UNKNOWN, confidence
        
        return primary_role, confidence
    
    def _check_multi_role(
        self,
        role_scores: Dict[SceneRole, float],
        primary_role: SceneRole
    ) -> Tuple[bool, List[SceneRole]]:
        """检查是否有多角色"""
        threshold = self.config.get('multi_role_threshold', 0.4)
        primary_score = role_scores.get(primary_role, 0.0)
        
        secondary_roles = []
        
        for role, score in role_scores.items():
            if role != primary_role and role != SceneRole.UNKNOWN:
                if score >= threshold and score >= primary_score * 0.7:
                    secondary_roles.append(role)
        
        is_multi_role = len(secondary_roles) > 0
        
        return is_multi_role, secondary_roles
    
    def get_role_description(self, role: SceneRole) -> str:
        """获取角色描述"""
        descriptions = {
            SceneRole.QUESTION: "用户在提问，寻求信息或答案",
            SceneRole.KNOWLEDGE_CONTRIBUTION: "用户在贡献知识，分享经验或见解",
            SceneRole.CORRECTION: "用户在纠正系统的错误",
            SceneRole.CHALLENGE: "用户在质疑或挑战系统的输出",
            SceneRole.CONFIRMATION: "用户在确认或表示理解",
            SceneRole.TEACHING: "用户在教学，主动传授知识",
            SceneRole.UNKNOWN: "角色不明确，需要进一步分析"
        }
        return descriptions.get(role, "未知角色")