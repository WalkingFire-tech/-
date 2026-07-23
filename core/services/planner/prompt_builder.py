"""提示构建 mixin — 上下文组装、历史解析"""
from typing import Optional, List, Dict
from loguru import logger
from core.services.intent_parser import Intent


class PromptBuilderMixin:
    """提示构建能力：上下文组装、历史提取"""

    def _init_prompt_builder(self):
        self._context_window = self.config.get("context_window", 4096)

    def _get_recent_context(self, rounds: int = None) -> str:
        """获取最近上下文"""
        if not hasattr(self, '_context_memory'):
            return ""
        rounds = rounds or self.config.get("context_rounds", 5)
        context = ""
        for i, entry in enumerate(self._context_memory[-rounds:]):
            role = entry.get("role", "user")
            content = entry.get("content", "")[:200]
            context += f"{role}: {content}\n"
        return context

    def _load_context_from_file(self):
        """从文件加载上下文"""
        try:
            with open("data/context_cache.txt", "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _build_prompt(self, intent: Intent) -> str:
        """构建完整提示词"""
        base = f"用户问题: {intent.raw_text}\n意图类型: {intent.type}\n"
        if hasattr(intent, 'urgency') and intent.urgency > 0.7:
            base = f"[紧急] {base}"
        return base

    def _parse_history(self, context: str) -> list:
        """解析历史记录"""
        history = []
        if not context:
            return history
        for line in context.strip().split("\n"):
            if ": " in line:
                role, content = line.split(": ", 1)
                history.append({"role": role.strip(), "content": content.strip()})
        return history
