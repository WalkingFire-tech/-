"""
L4善意延伸增强 — 场景感知融合

设计哲学：
善意延伸不是"附加信息"，而是同行者对用户处境的感知和回应。
当同行者感知到用户可能需要额外信息时，它会自然地延伸——
不是模板拼接，而是基于场景模型的动态生成。

三层融合：
1. 资源感知：GPU温度/内存/CPU → 运行状态对回答的影响
2. 场域感知：对话上下文/意图类型/复杂度 → 回答的充分性
3. 存在感知：知识缺口/能力边界/置信度 → 回答的可靠性

时机判断：
- 该说话时说话：资源紧张影响回答质量时
- 该沉默时沉默：简单问候/闲聊不需要延伸
- 该提醒时提醒：回答可能不完整时主动标注

与chat_orchestrator的关系：
- 替代当前的模板拼接（f"\n\n⚠️ ..."）
- 在阶段7（最终整合）调用 SceneAwareness.compose_extension()
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class SceneSnapshot:
    resource_mode: str = "normal"
    gpu_temp: float = 0.0
    memory_usage: float = 0.0
    cpu_percent: float = 0.0
    intent_type: str = ""
    complexity: float = 0.0
    confidence: float = 0.5
    response_length: int = 0
    sources_count: int = 0
    has_tool_result: bool = False
    knowledge_gaps: int = 0
    silence_duration: float = 0.0
    query_type: str = ""  # greeting, factual, complex, creative, tool


class SceneAwareness:
    SILENCE_INTENTS = {"greeting", "casual", "small_talk", "chitchat"}
    COMPLEX_INTENTS = {"complex_query", "analysis", "reasoning", "code", "research"}

    def compose_extension(self, scene: SceneSnapshot, response: str = "") -> Optional[str]:
        """
        基于场景模型动态生成善意延伸

        返回None表示"该沉默"——不需要延伸
        返回字符串表示"该说话"——自然地延伸
        """
        extensions = []

        ext = self._resource_extension(scene)
        if ext:
            extensions.append(ext)

        ext = self._completeness_extension(scene, response)
        if ext:
            extensions.append(ext)

        ext = self._boundary_extension(scene)
        if ext:
            extensions.append(ext)

        if not extensions:
            return None

        if len(extensions) == 1:
            return extensions[0]

        return "\n".join(extensions)

    def should_extend(self, scene: SceneSnapshot) -> bool:
        """时机判断：该说话还是该沉默"""
        if scene.intent_type in self.SILENCE_INTENTS:
            return False
        if scene.resource_mode != "normal" and scene.response_length > 200:
            return False
        if scene.resource_mode != "normal":
            return True
        if scene.complexity > 0.7 and scene.confidence < 0.5:
            return True
        if scene.knowledge_gaps > 0 and scene.complexity > 0.5:
            return True
        return False

    def _resource_extension(self, scene: SceneSnapshot) -> Optional[str]:
        if scene.resource_mode == "normal":
            return None

        if scene.resource_mode == "emergency":
            if scene.gpu_temp >= 90:
                return f"GPU温度已达{scene.gpu_temp:.0f}°C，我正在紧急降频运行——回答可能较简，但会尽力给你最有用的部分。"
            return "系统资源紧张中，我已精简运行路径——回答可能较简，但核心内容不受影响。"

        if scene.resource_mode == "conservative":
            if scene.gpu_temp >= 85:
                return f"GPU温度偏高（{scene.gpu_temp:.0f}°C），已自动降频——回答速度可能稍慢，但质量不受影响。"
            if scene.memory_usage > 0.8:
                return "内存占用较高，我已优化运行路径——回答可能稍简，如需详细展开可以继续追问。"

        return None

    def _completeness_extension(self, scene: SceneSnapshot, response: str) -> Optional[str]:
        if not response:
            return None

        if scene.intent_type in self.COMPLEX_INTENTS:
            if scene.confidence < 0.5:
                return "我对这个问题的把握还不够充分，以上是基于现有信息的分析——如果需要更深入的探讨，我可以继续研究。"
            if scene.complexity > 0.8 and len(response) < 300:
                return "这个问题比较复杂，以上是初步分析——如果需要更详细的解答，可以告诉我具体想深入了解哪个方面。"

        if scene.sources_count == 1 and scene.complexity > 0.5:
            return "以上主要基于单一信息来源，建议结合其他视角参考。"

        return None

    def _boundary_extension(self, scene: SceneSnapshot) -> Optional[str]:
        if scene.knowledge_gaps > 0 and scene.complexity > 0.6:
            return f"我注意到自己在{scene.intent_type or '这个'}领域还有{scene.knowledge_gaps}个知识缺口——如果你有相关经验，我很想学习。"

        if scene.has_tool_result and scene.confidence < 0.6:
            return "工具执行结果已返回，但我的解读可能不够全面——如果有专业背景，欢迎补充。"

        return None

    def build_scene(self, **kwargs) -> SceneSnapshot:
        """从各种信号构建场景快照"""
        return SceneSnapshot(**kwargs)


scene_awareness = SceneAwareness()