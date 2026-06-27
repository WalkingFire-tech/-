"""
用户反馈分类器
区分用户的"情感点赞"与"事实纠错"，分别处理

核心理念：防止"用户瞎点赞毁基因"
"""
import re
from typing import Tuple, Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """反馈类型"""
    CORRECTION = "correction"       # 事实纠错
    POSITIVE = "positive"           # 情感点赞
    NEGATIVE = "negative"           # 情感点踩
    NEUTRAL = "neutral"             # 中性反馈
    CLARIFICATION = "clarification" # 澄清请求


@dataclass
class ParsedCorrection:
    """解析后的纠错内容"""
    target_index: Optional[int]     # 指向第几条
    old_assertion: str              # 旧断言
    new_assertion: str              # 新断言
    reason: str                     # 纠错原因
    confidence: float               # 置信度


class FeedbackClassifier:
    """
    用户反馈分类器
    
    当用户回复时，先分类再处理：
    - CORRECTION: 触发L2学习层，直接更新fact_assertions表
    - POSITIVE/NEGATIVE: 计入主观分
    - NEUTRAL: 不计分，避免噪声
    """
    
    def __init__(self):
        # 纠错关键词（强否定）
        self.correction_keywords = [
            "不对", "错了", "错误", "不正确", "不准确",
            "应该是", "实际上是", "正确的是",
            "第.*条.*错", "第.*条.*不对",
            "❌", "✗", "×"
        ]
        
        # 点赞关键词
        self.positive_keywords = [
            "点赞", "👍", "好的", "对", "正确",
            "很好", "不错", "有道理", "明白了"
        ]
        
        # 点踩关键词
        self.negative_keywords = [
            "点踩", "👎", "不好", "不对", "错误",
            "没用", "没帮助", "胡说", "乱讲"
        ]
        
        # 澄清请求关键词
        self.clarification_keywords = [
            "什么意思", "能解释", "详细说",
            "为什么", "怎么理解", "举个例子"
        ]
        
        # 纠错模式（用于提取断言对）
        self.correction_patterns = [
            # "第X条：旧内容 → 新内容"
            r'第(\d+)条[：:](.+?)[→\-](.+?)(?:\n|$)',
            # "旧内容"应该是"新内容"
            r'"(.+?)"应该是"(.+?)"',
            # "旧内容"错误，应该是"新内容"
            r'"(.+?)"(错误|不对)[，,]应该是"(.+?)"',
        ]
        
        logger.info("🔍 用户反馈分类器已初始化")
    
    def classify(self, user_message: str) -> FeedbackType:
        """
        分类用户反馈
        
        Args:
            user_message: 用户消息
        
        Returns:
            反馈类型
        """
        message = user_message.strip()
        
        # 1. 检测事实纠错（最高优先级）
        for keyword in self.correction_keywords:
            if re.search(keyword, message):
                return FeedbackType.CORRECTION
        
        # 2. 检测澄清请求
        for keyword in self.clarification_keywords:
            if keyword in message:
                return FeedbackType.CLARIFICATION
        
        # 3. 检测点赞
        for keyword in self.positive_keywords:
            if keyword in message:
                return FeedbackType.POSITIVE
        
        # 4. 检测点踩
        for keyword in self.negative_keywords:
            if keyword in message:
                return FeedbackType.NEGATIVE
        
        # 5. 默认中性
        return FeedbackType.NEUTRAL
    
    def parse_correction(self, user_message: str) -> List[ParsedCorrection]:
        """
        解析纠错内容，提取(旧断言, 新断言)对
        
        Args:
            user_message: 用户消息
        
        Returns:
            纠错列表
        """
        corrections = []
        
        # 尝试各种模式匹配
        for pattern in self.correction_patterns:
            matches = re.findall(pattern, user_message, re.DOTALL)
            
            for match in matches:
                if len(match) == 3:
                    # 第X条模式
                    index = int(match[0]) if match[0].isdigit() else None
                    old = match[1].strip()
                    new = match[2].strip()
                elif len(match) == 2:
                    # 简单替换模式
                    index = None
                    old = match[0].strip()
                    new = match[1].strip()
                else:
                    continue
                
                if old and new and old != new:
                    corrections.append(ParsedCorrection(
                        target_index=index,
                        old_assertion=old,
                        new_assertion=new,
                        reason="user_correction",
                        confidence=0.9
                    ))
        
        # 如果没有匹配到模式，尝试简单提取
        if not corrections:
            simple_correction = self._extract_simple_correction(user_message)
            if simple_correction:
                corrections.append(simple_correction)
        
        return corrections
    
    def _extract_simple_correction(self, message: str) -> Optional[ParsedCorrection]:
        """简单纠错提取"""
        # 查找"应该是"后面的内容作为新断言
        should_be_match = re.search(r'应该是[：:]?\s*(.+?)(?:\n|$)', message)
        if should_be_match:
            new_assertion = should_be_match.group(1).strip()
            
            # 尝试提取旧断言（"XXX不对"或"XXX错误"）
            old_match = re.search(r'(.+?)(不对|错误|不正确)', message)
            if old_match:
                old_assertion = old_match.group(1).strip()
                
                return ParsedCorrection(
                    target_index=None,
                    old_assertion=old_assertion,
                    new_assertion=new_assertion,
                    reason="user_correction_simple",
                    confidence=0.7
                )
        
        return None
    
    def process_feedback(
        self,
        user_message: str,
        question: str = None,
        response: str = None
    ) -> Dict:
        """
        处理用户反馈
        
        Args:
            user_message: 用户消息
            question: 原始问题
            response: 系统回答
        
        Returns:
            处理结果
        """
        feedback_type = self.classify(user_message)
        
        result = {
            'type': feedback_type.value,
            'should_update_fitness': True,
            'should_update_facts': False,
            'corrections': [],
            'fitness_delta': 0
        }
        
        if feedback_type == FeedbackType.CORRECTION:
            # 纠错：更新事实库，不计入主观分
            corrections = self.parse_correction(user_message)
            result['corrections'] = [c.__dict__ for c in corrections]
            result['should_update_facts'] = True
            result['should_update_fitness'] = False  # 纠错不影响主观分
            
            logger.info(f"🔧 检测到纠错: {len(corrections)}条")
            
        elif feedback_type == FeedbackType.POSITIVE:
            # 点赞：计入主观分
            result['fitness_delta'] = 10
            logger.debug("👍 检测到点赞")
            
        elif feedback_type == FeedbackType.NEGATIVE:
            # 点踩：计入主观分
            result['fitness_delta'] = -10
            logger.debug("👎 检测到点踩")
            
        elif feedback_type == FeedbackType.CLARIFICATION:
            # 澄清请求：触发重新回答
            result['should_update_fitness'] = False
            logger.debug("❓ 检测到澄清请求")
            
        else:
            # 中性：不计分
            result['should_update_fitness'] = False
            logger.debug("➖ 中性反馈，不计分")
        
        return result


feedback_classifier = FeedbackClassifier()