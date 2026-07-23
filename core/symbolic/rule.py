"""
符号规则数据模型 — 统一的规则声明格式

借鉴ReflexEngine的Rule模型，扩展为支持多域的通用规则：
- name: 规则唯一标识
- condition: 条件表达式（可用RuleMatcher求值）
- action: 动作标识符
- priority: 优先级（0-100，越高越优先）
- confidence: 置信度（0-1，可随经验进化）
- domain: 规则域
- enabled: 是否启用
- trigger_count/fail_count: 触发统计
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RuleDomain(Enum):
    INTENT = "intent"
    TRUTH = "truth"
    PATCH = "patch"
    URGENCY = "urgency"
    SAFETY = "safety"
    ROUTING = "routing"
    LEARNING = "learning"
    CUSTOM = "custom"


@dataclass
class SymbolicRule:
    name: str
    condition: str
    action: str
    domain: RuleDomain = RuleDomain.CUSTOM
    priority: int = 50
    confidence: float = 1.0
    enabled: bool = True
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    trigger_count: int = 0
    success_count: int = 0
    fail_count: int = 0

    def record_outcome(self, success: bool) -> None:
        self.trigger_count += 1
        if success:
            self.success_count += 1
            self.confidence = min(1.0, self.confidence + 0.05)
        else:
            self.fail_count += 1
            self.confidence = max(0.0, self.confidence - 0.1)

    @property
    def success_rate(self) -> float:
        if self.trigger_count == 0:
            return 0.0
        return self.success_count / self.trigger_count

    def matches_domain(self, domain: RuleDomain) -> bool:
        return self.enabled and self.domain == domain

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "condition": self.condition,
            "action": self.action,
            "domain": self.domain.value,
            "priority": self.priority,
            "confidence": round(self.confidence, 3),
            "enabled": self.enabled,
            "trigger_count": self.trigger_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "success_rate": round(self.success_rate, 3),
        }


@dataclass
class RuleResult:
    rule_name: str
    matched: bool
    action: str = ""
    confidence: float = 0.0
    domain: RuleDomain = RuleDomain.CUSTOM
    evaluation_detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "matched": self.matched,
            "action": self.action,
            "confidence": round(self.confidence, 3),
            "domain": self.domain.value,
            "evaluation_detail": self.evaluation_detail,
        }