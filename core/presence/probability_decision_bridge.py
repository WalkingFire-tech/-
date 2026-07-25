"""
概率场→对话决策桥接层 — "调光器"而非"开关"

核心职责：将概率场的连续信号映射到对话决策的连续参数
- probability_field.tendency → 5维决策上下文(连续值)
- self_model.behavioral_directive → methodology 连续注入
- existence_layer.signal_pack → 上下文感知连续信号

设计原则：
1. 所有输出都是0.0-1.0的连续值，不是离散标签
2. Sigmoid非线性变换：中间值区分度更好
3. 平滑处理：防止决策突变(smoothing_factor=0.3)
4. 向后兼容：概率场不可用时退化为中性值
5. 渐进调制：权重变化幅度受概率场信号强度控制
"""

import math
import time
from typing import Dict, Optional, Any

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ProbabilityDecisionBridge:
    """
    概率场→对话决策桥接层

    映射规则：
    - exploration → path_diversity (路径多样性)
    - stability → consistency_preference (一致性偏好)
    - tension → response_depth (响应深度)
    - activity → proactivity_level (主动程度)
    - entropy → information_gain_threshold (信息增益阈值)
    """

    PATH_WEIGHT_BASELINES = {
        "experience": 1.0, "knowledge": 1.0, "fact": 1.0,
        "tool": 1.0, "self_reason": 1.0, "ollama": 1.0,
        "external_api": 1.0, "external_learning": 1.0,
    }

    MAPPING_GAINS = {
        "exploration_to_diversity": 0.7,
        "stability_to_consistency": 0.6,
        "tension_to_depth": 0.5,
        "activity_to_proactivity": 0.6,
        "entropy_to_info_gain": 0.4,
    }

    def __init__(self):
        self._last_mapping: Dict[str, Any] = {}
        self._last_decision: Dict[str, float] = {}
        self._mapping_count = 0
        self._last_mapping_time = 0.0
        self.smoothing_factor = 0.3

    def get_decision_context(self) -> Dict[str, Any]:
        """
        获取概率场映射的对话决策上下文

        返回5维决策参数 + 路径调制因子 + 行为修饰符
        """
        self._mapping_count += 1
        self._last_mapping_time = time.time()

        tendency = self._get_probability_tendency()
        directive = self._get_behavioral_directive()
        signal_pack = self._get_signal_pack()

        decision = self._compute_decision_params(tendency)
        decision = self._smooth_decision(decision)

        modulators = self._compute_path_weight_modulators(tendency, directive, decision)
        behavioral = self._compute_behavioral_modifiers(tendency, directive, signal_pack, decision)
        style_hint = self._compute_response_style(tendency, directive, decision)

        result = {
            "decision_params": decision,
            "path_weight_modulators": modulators,
            "behavioral_modifiers": behavioral,
            "probability_context": {
                "tendency": tendency,
                "directive_keys": list(directive.keys()) if directive else [],
                "signal_pack_keys": list(signal_pack.keys()) if signal_pack else [],
            },
            "response_style_hint": style_hint,
        }

        self._last_mapping = result
        self._last_decision = decision
        return result

    def _compute_decision_params(self, tendency: Dict[str, float]) -> Dict[str, float]:
        """
        将概率场5维倾向映射为5维决策参数（Sigmoid非线性变换）

        exploration → path_diversity
        stability → consistency_preference
        tension → response_depth
        activity → proactivity_level
        entropy → information_gain_threshold
        """
        exploration = tendency.get("exploration", 0.5)
        stability = tendency.get("stability", 0.5)
        tension = tendency.get("tension", 0.15)
        activity = tendency.get("activity", 0.075)
        entropy = tendency.get("entropy", 0.95)

        path_diversity = self._sigmoid_transform(
            exploration, gain=self.MAPPING_GAINS["exploration_to_diversity"])

        consistency_preference = self._sigmoid_transform(
            stability, gain=self.MAPPING_GAINS["stability_to_consistency"])

        response_depth = self._sigmoid_transform(
            min(1.0, tension * 3), gain=self.MAPPING_GAINS["tension_to_depth"])

        proactivity_level = self._sigmoid_transform(
            min(1.0, activity * 5), gain=self.MAPPING_GAINS["activity_to_proactivity"])

        normalized_entropy = min(1.0, entropy / 3.0)
        information_gain_threshold = 0.7 - 0.5 * self._sigmoid_transform(
            normalized_entropy, gain=self.MAPPING_GAINS["entropy_to_info_gain"])
        information_gain_threshold = max(0.1, min(0.9, information_gain_threshold))

        return {
            "path_diversity": round(path_diversity, 3),
            "consistency_preference": round(consistency_preference, 3),
            "response_depth": round(response_depth, 3),
            "proactivity_level": round(proactivity_level, 3),
            "information_gain_threshold": round(information_gain_threshold, 3),
        }

    def _sigmoid_transform(self, value: float, gain: float = 1.0, midpoint: float = 0.5) -> float:
        """
        Sigmoid非线性变换 — 中间值区分度更好

        y = 1 / (1 + exp(-gain * 10 * (x - midpoint)))
        """
        x = max(0.0, min(1.0, value))
        try:
            y = 1.0 / (1.0 + math.exp(-gain * 10 * (x - midpoint)))
        except OverflowError:
            y = 0.0 if x < midpoint else 1.0
        return max(0.0, min(1.0, y))

    def _smooth_decision(self, decision: Dict[str, float]) -> Dict[str, float]:
        """
        平滑处理 — 防止决策突变

        新值 = 旧值 * (1 - factor) + 新值 * factor
        factor=0.3 意味着每次更新只采纳30%的新值
        """
        if not self._last_decision:
            return decision

        factor = self.smoothing_factor
        smoothed = {}
        for key in decision:
            old_val = self._last_decision.get(key, decision[key])
            new_val = decision[key]
            smoothed[key] = round(old_val * (1 - factor) + new_val * factor, 3)

        return smoothed

    def apply_to_path_weights(
        self,
        base_weights: Dict[str, float],
        modulators: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        if modulators is None:
            modulators = self._last_mapping.get("path_weight_modulators", {})

        result = {}
        for path_name, base_weight in base_weights.items():
            modulator = modulators.get(path_name, 1.0)
            modulator = max(0.5, min(1.5, modulator))
            result[path_name] = round(base_weight * modulator, 3)
        return result

    def apply_to_methodology(
        self,
        methodology: Dict[str, Any],
        behavioral: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if behavioral is None:
            behavioral = self._last_mapping.get("behavioral_modifiers", {})

        if not behavioral:
            return methodology

        methodology = dict(methodology)

        for key in ("exploration_drive", "consolidation_need",
                     "response_pace_score", "preferred_depth_score",
                     "action_probability"):
            val = behavioral.get(key)
            if val is not None:
                methodology.setdefault(f"probability_{key}", round(val, 3))

        for key in ("path_diversity", "consistency_preference",
                     "response_depth", "proactivity_level",
                     "information_gain_threshold"):
            val = behavioral.get(key)
            if val is not None:
                methodology.setdefault(f"probability_{key}", round(val, 3))

        tension = behavioral.get("tension")
        if tension is not None:
            methodology.setdefault("probability_tension", round(tension, 3))

        entropy = behavioral.get("entropy")
        if entropy is not None:
            methodology.setdefault("probability_entropy", round(entropy, 3))

        return methodology

    def _get_probability_tendency(self) -> Dict[str, float]:
        try:
            from core.presence.existence_layer import get_existence_layer
            el = get_existence_layer()
            if hasattr(el, '_probability_field') and el._probability_field:
                return el._probability_field.get_tendency()
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

        try:
            from core.presence.probability_field import get_probability_field
            pf = get_probability_field()
            return pf.get_tendency()
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")

        return {"exploration": 0.5, "stability": 0.5, "tension": 0.15,
                "entropy": 0.95, "activity": 0.075, "phase": "BREATH"}

    def _get_behavioral_directive(self) -> Dict[str, Any]:
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            return sm.get_behavioral_directive()
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        return {}

    def _get_signal_pack(self) -> Dict[str, Any]:
        try:
            from core.presence.existence_layer import get_existence_layer
            el = get_existence_layer()
            if hasattr(el, 'get_signal_pack'):
                return el.get_signal_pack()
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        return {}

    def _compute_path_weight_modulators(
        self,
        tendency: Dict[str, float],
        directive: Dict[str, Any],
        decision: Dict[str, float],
    ) -> Dict[str, float]:
        """
        计算路径权重调制因子 — 使用sigmoid变换后的决策参数

        - path_diversity↑ → experience/knowledge/self_reason↑, ollama↓
        - consistency_preference↑ → fact/experience↑, tool/self_reason↓
        - response_depth↑ → self_reason/external_api↑
        - proactivity_level↑ → 全路径↑
        - consolidation_need↑ → knowledge/fact↑, exploration↓
        """
        diversity = decision.get("path_diversity", 0.5)
        consistency = decision.get("consistency_preference", 0.5)
        depth = decision.get("response_depth", 0.5)
        proactivity = decision.get("proactivity_level", 0.5)

        consolidation = directive.get("consolidation_need", 0.0)
        pace = directive.get("response_pace_score", 0.5)

        m = dict(self.PATH_WEIGHT_BASELINES)

        div_factor = 1.0 + (diversity - 0.5) * 0.6
        m["experience"] *= div_factor
        m["knowledge"] *= div_factor
        m["self_reason"] *= 1.0 + (diversity - 0.5) * 0.4
        m["ollama"] *= 1.0 - (diversity - 0.5) * 0.3
        m["external_learning"] *= 1.0 + (diversity - 0.5) * 0.3

        cons_factor = 1.0 + (consistency - 0.5) * 0.4
        m["fact"] *= cons_factor
        m["experience"] *= 1.0 + (consistency - 0.5) * 0.3
        m["tool"] *= 1.0 - (consistency - 0.5) * 0.2
        m["self_reason"] *= 1.0 - (consistency - 0.5) * 0.2

        depth_factor = 1.0 + (depth - 0.5) * 0.8
        m["self_reason"] *= depth_factor
        m["external_api"] *= 1.0 + (depth - 0.5) * 0.5
        m["fact"] *= 1.0 + (depth - 0.5) * 0.3

        pro_factor = 1.0 + (proactivity - 0.5) * 0.4
        for k in m:
            m[k] *= pro_factor

        c_factor = 1.0 + consolidation * 0.4
        m["knowledge"] *= c_factor
        m["fact"] *= 1.0 + consolidation * 0.3
        m["experience"] *= 1.0 - consolidation * 0.2
        m["external_api"] *= 1.0 - consolidation * 0.2

        if pace < 0.3:
            m["ollama"] *= 0.7
            m["external_api"] *= 0.7
            m["tool"] *= 0.8
        elif pace > 0.7:
            m["experience"] *= 1.1
            m["fact"] *= 1.1

        for k in m:
            m[k] = round(max(0.5, min(1.5, m[k])), 3)

        return m

    def _compute_behavioral_modifiers(
        self,
        tendency: Dict[str, float],
        directive: Dict[str, Any],
        signal_pack: Dict[str, Any],
        decision: Dict[str, float],
    ) -> Dict[str, Any]:
        exploration = tendency.get("exploration", 0.5)
        tension = tendency.get("tension", 0.15)
        entropy = tendency.get("entropy", 0.95)

        result = {
            "exploration_drive": directive.get("exploration_drive", exploration),
            "consolidation_need": directive.get("consolidation_need", 0.0),
            "response_pace_score": directive.get("response_pace_score", 0.5),
            "preferred_depth_score": directive.get("preferred_depth_score", 0.5),
            "action_probability": directive.get("action_probability", 0.5),
            "tension": tension,
            "entropy": entropy,
        }

        result.update(decision)

        pf_tendency = signal_pack.get("probability_field", {})
        if pf_tendency:
            pf_exploration = pf_tendency.get("exploration", 0.5)
            result["exploration_drive"] = (
                result["exploration_drive"] * 0.7 + pf_exploration * 0.3
            )

        detected = signal_pack.get("detected_signals", [])
        if "pattern_emergence" in detected:
            result["exploration_drive"] = min(1.0, result["exploration_drive"] * 1.2)
        if "need_emergence" in detected:
            result["preferred_depth_score"] = min(1.0, result["preferred_depth_score"] * 1.15)

        for key in result:
            if isinstance(result[key], float):
                result[key] = round(result[key], 3)

        return result

    def _compute_response_style(
        self,
        tendency: Dict[str, float],
        directive: Dict[str, Any],
        decision: Dict[str, float],
    ) -> str:
        diversity = decision.get("path_diversity", 0.5)
        depth = decision.get("response_depth", 0.5)
        pace = directive.get("response_pace_score", 0.5)

        if diversity > 0.6 and depth > 0.6:
            return "exploratory_deep"
        elif diversity > 0.55:
            return "exploratory"
        elif pace > 0.7:
            return "responsive"
        elif depth > 0.55:
            return "reflective"
        elif pace < 0.3:
            return "concise"
        else:
            return "balanced"

    def get_status(self) -> Dict[str, Any]:
        return {
            "mapping_count": self._mapping_count,
            "last_mapping_age_s": round(time.time() - self._last_mapping_time, 1) if self._last_mapping_time else -1,
            "last_decision": self._last_decision,
            "last_modulators": self._last_mapping.get("path_weight_modulators", {}),
            "last_style_hint": self._last_mapping.get("response_style_hint", "none"),
            "smoothing_factor": self.smoothing_factor,
        }


_bridge: Optional[ProbabilityDecisionBridge] = None


def get_probability_decision_bridge() -> ProbabilityDecisionBridge:
    global _bridge
    if _bridge is None:
        _bridge = ProbabilityDecisionBridge()
        logger.info("🌉 概率场→决策桥接层已创建（含Sigmoid+平滑）")
    return _bridge
