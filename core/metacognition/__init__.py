"""
元认知智能体 — "观察观察者"的系统级元认知

核心定位：
- 不是执行层元认知（MetacognitiveExecutor已覆盖）
- 不是被动记录器（MetaCognitiveLayer已覆盖）
- 而是"系统级元认知"：跨模块状态聚合→趋势分析→异常检测→主动干预

设计原则：
- 复用优先：SelfModel.snapshot() + ResourceSnapshot + DispatchHistory + DecisionLog
- 不重复造轮子：不新建状态收集器/调度框架/闭环机制
- 非侵入式干预：通过回调/事件通知，不直接修改被管理模块的内部状态
- 渐进干预：检测→告警→建议→自动调整（4级递进）

元认知闭环：
  聚合状态 → 趋势分析 → 异常检测 → 干预决策 → 效果评估 → 阈值调整

与P3-1可解释性的关系：
  元认知决策通过explain()生成解释，确保"为什么干预"可被人类理解
"""

from core.metacognition.snapshot import SystemMetacognitiveSnapshot
from core.metacognition.trend_analyzer import TrendAnalyzer, TrendResult
from core.metacognition.agent import MetacognitiveAgent, metacognitive_agent

__all__ = [
    "SystemMetacognitiveSnapshot",
    "TrendAnalyzer",
    "TrendResult",
    "MetacognitiveAgent",
    "metacognitive_agent",
]