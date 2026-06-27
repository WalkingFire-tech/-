"""
统一意图路由器 - 整合IntentParser和AutoIntentParser
实现分层级联 + 智能路由策略
"""
from typing import Optional, Dict
from loguru import logger

from core.intent import Intent
from core.services.intent_parser import IntentParser
from core.services.auto_intent_parser import AutoIntentParser


class IntentRouter:
    """统一意图路由器 - 整合IntentParser和AutoIntentParser"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.fast_parser = IntentParser()
        self.smart_parser = AutoIntentParser()
        
        self.fast_threshold = self.config.get("fast_threshold", 0.7)
        self.smart_threshold = self.config.get("smart_threshold", 0.6)
        self.enable_smart = self.config.get("enable_smart", True)
        
        self.stats = {
            "fast": 0,
            "smart": 0,
            "fallback": 0,
            "fast_high_conf": 0,
            "smart_boost": 0
        }
        
        logger.info("🎯 意图路由器已初始化")
    
    def parse(self, user_input: str, context: Optional[Dict] = None) -> Intent:
        """主解析入口
        
        Args:
            user_input: 用户输入文本
            context: 上下文信息（文件、历史等）
        
        Returns:
            Intent: 统一意图对象
        """
        fast_result = self._parse_fast(user_input, context)
        self.stats["fast"] += 1
        
        if fast_result.confidence >= self.fast_threshold:
            self.stats["fast_high_conf"] += 1
            logger.info(f"✓ 快速路径: {fast_result.type} (置信度: {fast_result.confidence:.2f})")
            return fast_result
        
        if not self.enable_smart:
            self.stats["fallback"] += 1
            return fast_result
        
        should_use_smart = self._should_use_smart(user_input, context, fast_result)
        
        if should_use_smart:
            smart_result = self._parse_smart(user_input)
            self.stats["smart"] += 1
            
            if smart_result.confidence > fast_result.confidence + 0.1:
                self.stats["smart_boost"] += 1
                logger.info(
                    f"🚀 智能增强: {fast_result.type}→{smart_result.type} "
                    f"({fast_result.confidence:.2f}→{smart_result.confidence:.2f})"
                )
                return smart_result
            
            if smart_result.confidence > fast_result.confidence:
                return smart_result
        
        self.stats["fallback"] += 1
        return fast_result
    
    def _parse_fast(self, user_input: str, context: Optional[Dict]) -> Intent:
        """快速路径：使用IntentParser"""
        try:
            result = self.fast_parser.parse(user_input, context or {})
            return Intent(
                type=result.type,
                raw_text=result.raw_text,
                entities=result.entities,
                confidence=result.confidence,
                source="rule"
            )
        except Exception as e:
            logger.warning(f"快速解析失败: {e}")
            return Intent(
                type="chat",
                raw_text=user_input,
                entities={},
                confidence=0.3,
                source="fallback"
            )
    
    def _parse_smart(self, user_input: str) -> Intent:
        """智能路径：使用AutoIntentParser"""
        try:
            result = self.smart_parser.parse(user_input)
            return Intent(
                type=result.type,
                raw_text=result.raw_text,
                entities=result.entities,
                confidence=result.confidence,
                source=result.source
            )
        except Exception as e:
            logger.warning(f"智能解析失败: {e}")
            return Intent(
                type="chat",
                raw_text=user_input,
                entities={},
                confidence=0.4,
                source="fallback"
            )
    
    def _should_use_smart(self, user_input: str, context: Dict, fast_result: Intent) -> bool:
        """判断是否应该使用智能解析
        
        Args:
            user_input: 用户输入
            context: 上下文
            fast_result: 快速解析结果
        
        Returns:
            bool: 是否使用智能解析
        """
        if fast_result.confidence < 0.5:
            return True
        
        if len(user_input) > 80:
            return True
        
        vague_indicators = ["可能", "也许", "大概", "不确定", "好像", "不太清楚"]
        if any(kw in user_input for kw in vague_indicators):
            return True
        
        complex_keywords = ["并且", "同时", "先", "再", "比较", "分析", "对比", "分别"]
        if any(kw in user_input for kw in complex_keywords):
            return True
        
        if context and context.get("file_input"):
            file_info = context["file_input"]
            file_ext = file_info.get("extension", "")
            smart_extensions = {'.pdf', '.docx', '.xlsx', '.pptx'}
            if file_ext in smart_extensions:
                return True
        
        return False
    
    def learn_from_correction(self, text: str, correct_intent: str, wrong_intent: str = None):
        """从纠正中学习
        
        Args:
            text: 用户输入文本
            correct_intent: 正确的意图
            wrong_intent: 错误的意图（可选）
        """
        try:
            self.smart_parser.learn_from_correction(text, correct_intent, wrong_intent)
            self.fast_parser.learn_from_correction(text, correct_intent)
            logger.info(f"✓ 学习纠正: '{text[:30]}...' -> {correct_intent}")
        except Exception as e:
            logger.warning(f"学习纠正失败: {e}")
    
    def add_custom_rule(self, intent_type: str, pattern: str):
        """添加自定义规则
        
        Args:
            intent_type: 意图类型
            pattern: 正则模式
        """
        try:
            self.fast_parser.add_custom_rule(intent_type, pattern)
            logger.info(f"✓ 添加规则: {intent_type} <- {pattern}")
        except Exception as e:
            logger.warning(f"添加规则失败: {e}")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        total = self.stats["fast"] + self.stats["smart"]
        return {
            **self.stats,
            "total": total,
            "fast_ratio": self.stats["fast"] / max(1, total),
            "smart_ratio": self.stats["smart"] / max(1, total),
            "boost_ratio": self.stats["smart_boost"] / max(1, self.stats["smart"])
        }
    
    def get_learning_stats(self) -> Dict:
        """获取学习统计"""
        try:
            return self.smart_parser.get_statistics()
        except:
            return {"total_corrections": 0, "learned_rules_count": 0}


_intent_router: Optional[IntentRouter] = None


def get_intent_router(config: Optional[Dict] = None) -> IntentRouter:
    """获取意图路由器单例
    
    Args:
        config: 配置字典
    
    Returns:
        IntentRouter: 意图路由器实例
    """
    global _intent_router
    if _intent_router is None:
        _intent_router = IntentRouter(config)
    return _intent_router


def parse_intent(user_input: str, context: Optional[Dict] = None) -> Intent:
    """便捷函数：解析意图
    
    Args:
        user_input: 用户输入
        context: 上下文
    
    Returns:
        Intent: 意图对象
    """
    router = get_intent_router()
    return router.parse(user_input, context)