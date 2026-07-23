"""
多维认知编排器 (Cognitive Dimension Orchestrator)

核心理念：智慧与真理在同一内核中贯通的关键不是增强单个维度，
而是让维度之间能够动态感知、切换、融合。

职责：
1. 感知当前哪些认知维度正在活跃
2. 评估每个维度输出的可靠性
3. 检测维度间的不一致
4. 在不一致时发出对齐信号
5. 根据wisdom_truth_balance基因参数动态调整倾向

这不是处理具体任务的层，而是让系统的"贯通"从静态连接走向动态响应的元层。

设计原则：
- 轻量：不处理具体任务，只感知和调度
- 非阻塞：信号发出后由下游模块决定是否响应
- 可观测：所有维度状态和对齐决策可追溯
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from collections import deque
from loguru import logger
try:
    from core.spirit_core import spirit_core
    SPIRIT_CORE_AVAILABLE = True
except ImportError:
    SPIRIT_CORE_AVAILABLE = False
    spirit_core = None


class CognitiveDimension(Enum):
    DIALOGUE = "dialogue"
    SEMANTIC = "semantic"
    CAUSAL = "causal"
    SYMBOLIC = "symbolic"
    METACOGNITIVE = "metacognitive"


@dataclass
class DimensionState:
    dimension: CognitiveDimension
    active: bool = False
    confidence: float = 0.5
    last_output: str = ""
    last_update: str = ""
    reliability_score: float = 0.5
    output_count: int = 0
    error_count: int = 0


@dataclass
class InconsistencySignal:
    dimensions: Tuple[CognitiveDimension, CognitiveDimension]
    inconsistency_type: str
    severity: float
    description: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class AlignmentDecision:
    primary_dimension: CognitiveDimension
    secondary_dimensions: List[CognitiveDimension]
    wisdom_truth_vector: float
    reason: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DimensionOrchestrator:
    """
    运行时维度切换/融合层

    持续感知各认知维度的状态，在维度间不一致时发出信号，
    供下游模块决定是否触发重新对齐。
    """

    MAX_HISTORY = 100

    def __init__(self):
        self._states: Dict[CognitiveDimension, DimensionState] = {
            d: DimensionState(dimension=d) for d in CognitiveDimension
        }
        self._inconsistency_history: deque = deque(maxlen=self.MAX_HISTORY)
        self._alignment_history: deque = deque(maxlen=self.MAX_HISTORY)
        self._wisdom_truth_balance = 0.5
        self._switch_sensitivity = 0.6
        self._alignment_vigilance = 0.5
        self._total_inconsistencies = 0
        self._total_alignments = 0

    def update_gene_params(self, params: Dict[str, float]):
        if "wisdom_truth_balance" in params:
            self._wisdom_truth_balance = params["wisdom_truth_balance"]
        if "dimension_switch_sensitivity" in params:
            self._switch_sensitivity = params["dimension_switch_sensitivity"]
        if "alignment_vigilance" in params:
            self._alignment_vigilance = params["alignment_vigilance"]

    def update_dimension(
        self,
        dimension: CognitiveDimension,
        confidence: float,
        output_summary: str = "",
        is_error: bool = False,
    ) -> Optional[InconsistencySignal]:
        state = self._states[dimension]
        state.active = True
        state.confidence = max(0.0, min(1.0, confidence))
        state.last_output = output_summary[:200] if output_summary else ""
        state.last_update = datetime.now().isoformat()
        state.output_count += 1
        if is_error:
            state.error_count += 1
        state.reliability_score = self._calc_reliability(state)
        return self._check_inconsistencies(dimension)

    def deactivate_dimension(self, dimension: CognitiveDimension):
        if dimension in self._states:
            self._states[dimension].active = False

    def _calc_reliability(self, state: DimensionState) -> float:
        if state.output_count == 0:
            return 0.5
        error_rate = state.error_count / max(1, state.output_count)
        recency = 1.0
        if state.last_update:
            try:
                elapsed = (datetime.now() - datetime.fromisoformat(state.last_update)).total_seconds()
                recency = max(0.1, 1.0 - elapsed / 300.0)
            except (ValueError, TypeError):
                pass
        return max(0.1, min(1.0, (1.0 - error_rate) * 0.7 + state.confidence * 0.2 + recency * 0.1))

    def _check_inconsistencies(self, updated_dim: CognitiveDimension) -> Optional[InconsistencySignal]:
        updated_state = self._states[updated_dim]
        active_dims = [d for d in CognitiveDimension if d != updated_dim and self._states[d].active]
        if not active_dims:
            return None

        for other_dim in active_dims:
            other_state = self._states[other_dim]
            conf_diff = abs(updated_state.confidence - other_state.confidence)
            if conf_diff > (1.0 - self._alignment_vigilance) * 0.6:
                severity = min(1.0, conf_diff * 1.5)
                signal = InconsistencySignal(
                    dimensions=(updated_dim, other_dim),
                    inconsistency_type="confidence_divergence",
                    severity=severity,
                    description=f"置信度分歧: {updated_dim.value}={updated_state.confidence:.2f} vs {other_dim.value}={other_state.confidence:.2f}",
                )
                self._inconsistency_history.append(signal)
                self._total_inconsistencies += 1
                logger.debug(f"维度不一致: {signal.description}")
                return signal

        return None

    def decide_primary_dimension(self, context: str = "", spirit_resonances: Optional[List[Dict[str, Any]]] = None) -> AlignmentDecision:
        active_states = {d: s for d, s in self._states.items() if s.active}
        if not active_states:
            return AlignmentDecision(
                primary_dimension=CognitiveDimension.DIALOGUE,
                secondary_dimensions=[],
                wisdom_truth_vector=self._wisdom_truth_balance,
                reason="无活跃维度，默认对话流",
            )

        # 获取精神共振结果（如果未提供）
        if spirit_resonances is None and SPIRIT_CORE_AVAILABLE and context:
            try:
                spirit_resonances = spirit_core.resonate(context, context_type="reasoning")
            except Exception as e:
                logger.warning(f"获取精神共振失败: {e}")
                spirit_resonances = []

        # 计算精神共振对维度的调整因子
        dimension_adjustments = {dim: 0.0 for dim in CognitiveDimension}
        if spirit_resonances:
            # 原则到维度的权重映射
            principle_to_dimensions = {
                "PURSUE_ESSENCE": [CognitiveDimension.SEMANTIC, CognitiveDimension.CAUSAL],
                "LOGICAL_SELF_CONSISTENT": [CognitiveDimension.SYMBOLIC],
                "HONEST_WHEN_LOST": [CognitiveDimension.METACOGNITIVE],
                "MULTI_SOURCE_VERIFY": [CognitiveDimension.SYMBOLIC, CognitiveDimension.CAUSAL],
                "THINK_BEFORE_ACT": [CognitiveDimension.METACOGNITIVE],
                "NEVER_GIVE_UP": list(CognitiveDimension),  # 所有维度
                "MEANINGFUL_RESPONSE": [CognitiveDimension.DIALOGUE],
                "STATE_SYNC": [CognitiveDimension.DIALOGUE],
                "LEARNING_FROM_FAILURE": [CognitiveDimension.METACOGNITIVE],
            }
            for resonance in spirit_resonances:
                principle = resonance.get("principle")
                strength = resonance.get("strength", 0.0)
                if principle in principle_to_dimensions:
                    for dim in principle_to_dimensions[principle]:
                        dimension_adjustments[dim] += strength * 0.2  # 调整系数

        scored = []
        for dim, state in active_states.items():
            truth_weight = self._truth_weight(dim)
            wisdom_weight = self._wisdom_weight(dim)
            balance = self._wisdom_truth_balance
            base_score = (
                state.reliability_score * 0.4
                + state.confidence * 0.3
                + (wisdom_weight * balance + truth_weight * (1 - balance)) * 0.3
            )
            # 应用精神共振调整
            adjusted_score = base_score * (1.0 + dimension_adjustments[dim])
            scored.append((dim, adjusted_score))

        scored.sort(key=lambda x: x[1], reverse=True)
        primary = scored[0][0]
        secondary = [d for d, _ in scored[1:]]

        # 构建决策原因，包含共振信息
        reason = self._build_decision_reason(primary, scored, context)
        if spirit_resonances:
            top_resonance = spirit_resonances[0] if spirit_resonances else None
            if top_resonance:
                reason += f" | 精神共振:{top_resonance['principle']}(强度={top_resonance['strength']:.2f})"

        decision = AlignmentDecision(
            primary_dimension=primary,
            secondary_dimensions=secondary,
            wisdom_truth_vector=self._wisdom_truth_balance,
            reason=reason,
        )
        self._alignment_history.append(decision)
        self._total_alignments += 1
        return decision

    def _truth_weight(self, dim: CognitiveDimension) -> float:
        weights = {
            CognitiveDimension.SYMBOLIC: 0.9,
            CognitiveDimension.CAUSAL: 0.7,
            CognitiveDimension.METACOGNITIVE: 0.6,
            CognitiveDimension.SEMANTIC: 0.4,
            CognitiveDimension.DIALOGUE: 0.3,
        }
        return weights.get(dim, 0.5)

    def _wisdom_weight(self, dim: CognitiveDimension) -> float:
        return 1.0 - self._truth_weight(dim)

    def _build_decision_reason(
        self, primary: CognitiveDimension, scored: List[Tuple[CognitiveDimension, float]], context: str
    ) -> str:
        parts = [f"主维度={primary.value}(得分={scored[0][1]:.2f})"]
        if len(scored) > 1:
            parts.append(f"次维度={','.join(d.value for d, _ in scored[1:])}")
        parts.append(f"智慧-真理平衡={self._wisdom_truth_balance:.2f}")
        if context:
            parts.append(f"上下文={context[:50]}")
        return " | ".join(parts)

    def get_dimension_states(self) -> Dict[str, Dict[str, Any]]:
        return {
            d.value: {
                "active": s.active,
                "confidence": s.confidence,
                "reliability": s.reliability_score,
                "output_count": s.output_count,
                "error_count": s.error_count,
                "last_update": s.last_update,
            }
            for d, s in self._states.items()
        }

    def get_status(self) -> Dict[str, Any]:
        active_count = sum(1 for s in self._states.values() if s.active)
        avg_confidence = (
            sum(s.confidence for s in self._states.values() if s.active) / active_count
            if active_count > 0
            else 0.0
        )
        return {
            "active_dimensions": active_count,
            "avg_confidence": round(avg_confidence, 3),
            "wisdom_truth_balance": self._wisdom_truth_balance,
            "switch_sensitivity": self._switch_sensitivity,
            "alignment_vigilance": self._alignment_vigilance,
            "total_inconsistencies": self._total_inconsistencies,
            "total_alignments": self._total_alignments,
            "recent_inconsistencies": len(self._inconsistency_history),
        }


_dimension_orchestrator: Optional[DimensionOrchestrator] = None


def get_dimension_orchestrator() -> DimensionOrchestrator:
    global _dimension_orchestrator
    if _dimension_orchestrator is None:
        _dimension_orchestrator = DimensionOrchestrator()
    return _dimension_orchestrator