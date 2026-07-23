"""
解释数据类型 — 可解释性模块的基础数据结构

Explanation: 单条解释记录
ExplanationLevel: 解释详细程度枚举
DecisionDomain: 决策域枚举
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExplanationLevel(Enum):
    BRIEF = "brief"
    DETAILED = "detailed"


class DecisionDomain(Enum):
    L5_MODIFICATION = "l5_modification"
    PATH_SELECTION = "path_selection"
    TRUTH_UPGRADE = "truth_upgrade"
    RESOURCE_ALLOCATION = "resource_allocation"
    CURIOSITY_EXPLORATION = "curiosity_exploration"
    CAUSAL_REASONING = "causal_reasoning"


@dataclass
class Explanation:
    domain: DecisionDomain
    decision: str
    outcome: Any
    reasoning: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    alternatives: List[str] = field(default_factory=list)
    trace: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    _id: Optional[str] = None

    def summary(self) -> str:
        return self.reasoning

    def details(self) -> str:
        parts = [f"[{self.domain.value}] {self.decision} → {self.outcome}"]
        parts.append(f"原因: {self.reasoning}")
        if self.inputs:
            parts.append(f"输入: {self._format_dict(self.inputs)}")
        if self.context:
            parts.append(f"上下文: {self._format_dict(self.context)}")
        if self.alternatives:
            parts.append(f"备选方案: {', '.join(self.alternatives)}")
        if self.trace:
            parts.append("决策链路:")
            for i, step in enumerate(self.trace, 1):
                parts.append(f"  {i}. {step.get('action', '?')}: {step.get('result', '?')}")
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "domain": self.domain.value,
            "decision": self.decision,
            "outcome": str(self.outcome),
            "reasoning": self.reasoning,
            "inputs": self.inputs,
            "context": self.context,
            "alternatives": self.alternatives,
            "trace": self.trace,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def _format_dict(d: Dict[str, Any]) -> str:
        items = []
        for k, v in d.items():
            sv = f"{v:.3f}" if isinstance(v, float) else str(v)
            items.append(f"{k}={sv}")
        return ", ".join(items)