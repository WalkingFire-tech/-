"""工具执行 mixin — 工具调用、反射级检查、系统状态"""
from typing import Optional, Dict, Any
from loguru import logger
from core.services.intent_parser import Intent


class ToolExecutorMixin:
    """工具执行能力：优先工具调用、反射级检查、防御链"""

    def _init_tool_executor(self):
        self._tool_timeout = 10.0

    def _try_tool_first(self, intent: Intent) -> Optional[str]:
        """优先尝试工具执行"""
        try:
            from core.tool_registry import tool_registry
            tools = tool_registry.list_tools()
            for tool in tools:
                if any(kw in intent.raw_text for kw in tool.get("keywords", [])):
                    result = tool_registry.execute(tool["name"], {"query": intent.raw_text})
                    if result and result.get("success"):
                        logger.info(f"工具执行成功: {tool['name']}")
                        return result.get("response", "")
            return None
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            return None

    def _check_reflex_level(self, intent: Intent) -> Optional[str]:
        """检查是否需要触发反射级响应"""
        urgency = getattr(intent, 'urgency', 0.5)
        if urgency > 0.8:
            logger.info(f"高紧迫度({urgency})，触发快速响应")
            if "time" in intent.raw_text or "日期" in intent.raw_text:
                from datetime import datetime
                return f"现在{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        return None

    def _infer_emotion(self, intent: Intent) -> Dict[str, Any]:
        """推断用户情绪"""
        text = intent.raw_text
        emotion = {"type": "neutral", "intensity": 0.5}
        urgency_keywords = ["急", "立刻", "马上", "赶紧"]
        frustration_keywords = ["又", "还是不行", "错了", "不对"]
        if any(kw in text for kw in frustration_keywords):
            emotion = {"type": "frustrated", "intensity": 0.7}
        elif any(kw in text for kw in urgency_keywords):
            emotion = {"type": "urgent", "intensity": 0.8}
        return emotion

    def _check_system_state(self) -> Optional[str]:
        """检查系统状态"""
        return None

    def _apply_five_layer_defense(self, intent: Intent) -> Optional[str]:
        """五层防御链"""
        if hasattr(intent, 'raw_text') and len(intent.raw_text) > 1000:
            return "输入过长，请精简后重试。"
        return None

    def _check_periodic_induction(self):
        """检查周期归纳（空操作，由定时任务驱动）"""
        pass
