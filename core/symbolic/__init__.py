"""
符号推理层 — 统一规则引擎 + LLM-符号混合推理

核心定位：
- 不是替换现有RuleMatcher/ReflexEngine/StrategyLibrary
- 而是提供统一的规则抽象层，让各模块的硬编码规则声明式化
- 支持LLM-符号混合推理：符号规则优先（可靠），LLM兜底（灵活）

设计原则：
- 复用RuleMatcher的条件求值能力
- 借鉴ReflexEngine的规则数据模型（优先级/阈值/启用/触发计数）
- 保留各模块的领域逻辑，只统一"条件→动作"的声明和求值
- 渐进迁移：先提供统一接口，各模块按需迁移

统一规则模型：
  SymbolicRule: name + condition + action + priority + confidence + domain + enabled
  condition: 可用RuleMatcher求值的表达式字符串
  action: 动作标识符（由调用方解释）
  domain: 规则所属域（intent/truth/patch/urgency/safety/...）
"""

from core.symbolic.rule import SymbolicRule, RuleDomain, RuleResult
from core.symbolic.engine import SymbolicRuleEngine, symbolic_engine
from core.symbolic.hybrid_reasoner import HybridReasoner, hybrid_reasoner

__all__ = [
    "SymbolicRule",
    "RuleDomain",
    "RuleResult",
    "SymbolicRuleEngine",
    "symbolic_engine",
    "HybridReasoner",
    "hybrid_reasoner",
]