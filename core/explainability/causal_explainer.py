"""
因果推理解释器 — P5-3b可解释性增强

为因果推理决策点生成可解释输出：
1. 因果追溯解释 — 精神共振驱动的深层追溯
2. 因果预测解释 — 预测结果的可解释化
3. 反事实推理解释 — "如果选择B会怎样"的可解释化
"""

from typing import Dict, List, Any, Optional
from loguru import logger

from core.explainability.explanation_types import DecisionDomain
from core.explainability.decision_explainer import explain


SIEVE_NAMES = {
    "cross_domain": "跨域普适性",
    "self_consistency": "逻辑自洽性",
    "entropy_reduction": "认知降熵",
    "antifragility": "反脆弱性",
}


class CausalExplainer:

    @staticmethod
    def explain_trace(trace_result: Dict) -> Optional[str]:
        """P5-3b: 因果追溯解释"""
        if trace_result is None:
            return None

        resonances = trace_result.get("resonances", [])
        deep_trace = trace_result.get("deep_trace")
        truth_feedback = trace_result.get("truth_feedback", {})

        parts = []

        if resonances:
            top = resonances[0]
            parts.append(f"共振触发: {top['principle']}(强度={top['strength']:.2f}) → {top['drive_direction']}")

        if deep_trace:
            trigger = deep_trace.get("trigger", "")
            if trigger == "PURSUE_ESSENCE":
                seeds = deep_trace.get("seed_nodes", [])
                best = deep_trace.get("best_path")
                parts.append(f"追溯动机: 追求本质原则触发深层因果追溯")
                parts.append(f"追溯种子: {', '.join(seeds[:3])}")
                if best:
                    parts.append(f"最优路径: {' → '.join(best['path'])} (置信度={best['confidence']:.2f})")
            elif trigger == "LOGICAL_SELF_CONSISTENT":
                contradictions = deep_trace.get("contradictions", [])
                parts.append(f"追溯动机: 逻辑自洽原则触发矛盾检测")
                for c in contradictions[:2]:
                    parts.append(f"矛盾: 成功路径{' → '.join(c['success_path'][:3])} vs 失败路径{' → '.join(c['failure_path'][:3])}")

        if truth_feedback:
            action = truth_feedback.get("action", "none")
            conf = truth_feedback.get("path_confidence", 0)
            if action == "boost_evidence":
                parts.append(f"真谛反馈: 高置信因果路径({conf:.2f})，建议增强真谛证据")
            elif action == "flag_uncertainty":
                parts.append(f"真谛反馈: 低置信因果路径({conf:.2f})，标记不确定性")

        reasoning = "\n".join(parts) if parts else "因果追溯无深层结果"

        try:
            explain(
                domain=DecisionDomain.CAUSAL_REASONING,
                decision="trace_with_spirit",
                outcome=bool(deep_trace),
                reasoning=reasoning,
                inputs={"resonances": len(resonances)},
                context={"trigger": deep_trace.get("trigger") if deep_trace else None},
            )
        except Exception:
            pass

        return reasoning

    @staticmethod
    def explain_prediction(prediction, intent: str = "") -> str:
        """P5-3b: 因果预测解释"""
        if not prediction:
            return "无预测数据"

        parts = []
        pred_state = prediction.predicted_state if hasattr(prediction, 'predicted_state') else prediction.get("predicted_state", {})
        prob = prediction.probability if hasattr(prediction, 'probability') else prediction.get("probability", 0)
        conf = prediction.confidence if hasattr(prediction, 'confidence') else prediction.get("confidence", 0)
        path = prediction.causal_path if hasattr(prediction, 'causal_path') else prediction.get("causal_path", [])

        outcome = pred_state.get("outcome", "未知") if isinstance(pred_state, dict) else str(pred_state)
        parts.append(f"预测结果: {outcome}")
        parts.append(f"概率: {prob:.1%}, 置信度: {conf:.1%}")
        if path:
            parts.append(f"因果路径: {' → '.join(path)}")
        if intent:
            parts.append(f"意图: {intent}")

        if conf < 0.3:
            parts.append("⚠️ 低置信度预测，结果可能不可靠")
        elif conf >= 0.7:
            parts.append("✅ 高置信度预测")

        reasoning = "\n".join(parts)

        try:
            explain(
                domain=DecisionDomain.CAUSAL_REASONING,
                decision="predict",
                outcome=outcome,
                reasoning=reasoning,
                inputs={"intent": intent, "probability": prob},
                context={"confidence": conf, "path_length": len(path)},
            )
        except Exception:
            pass

        return reasoning

    @staticmethod
    def explain_counterfactual(cf_result: Dict) -> str:
        """P5-3b: 反事实推理解释"""
        if not cf_result:
            return "无反事实数据"

        parts = []
        actual = cf_result.get("actual", {})
        counter = cf_result.get("counterfactual", {})
        would_better = cf_result.get("would_have_been_better", False)
        advantage = cf_result.get("advantage", 0)

        parts.append(f"实际选择: {actual.get('action', '?')} (评分={actual.get('score', 0):.3f})")
        parts.append(f"替代选择: {counter.get('action', '?')} (评分={counter.get('score', 0):.3f})")
        if would_better:
            parts.append(f"替代方案更优(优势={advantage:.3f})")
        else:
            parts.append(f"实际选择更优(优势={abs(advantage):.3f})")

        lesson = cf_result.get("lesson", "")
        if lesson:
            parts.append(f"教训: {lesson}")

        reasoning = "\n".join(parts)

        try:
            explain(
                domain=DecisionDomain.CAUSAL_REASONING,
                decision="counterfactual",
                outcome=would_better,
                reasoning=reasoning,
                inputs={"actual_action": actual.get("action"), "alt_action": counter.get("action")},
                context={"advantage": advantage},
            )
        except Exception:
            pass

        return reasoning

    @staticmethod
    def explain_sieve_enhanced(checks: Dict) -> str:
        """P5-3b: 适配P5-2c结构化判定的真谛筛子增强解释"""
        parts = []

        sc = checks.get("self_consistency", {})
        if isinstance(sc, dict) and "score" in sc:
            parts.append(f"逻辑自洽: 评分={sc['score']:.2f}, 命题数={sc.get('proposition_count', 0)}")
            contradictions = sc.get("detected_contradictions", [])
            for c in contradictions[:2]:
                ctype = c.get("type", "")
                severity = c.get("severity", "")
                if ctype == "word_pair":
                    pair = c.get("pair", ())
                    parts.append(f"  矛盾词对: {pair[0]}/{pair[1]} ({severity})")
                elif ctype == "semantic_pattern":
                    parts.append(f"  语义矛盾: {c.get('conflict', '')} ({severity})")
                elif ctype == "cross_sentence":
                    parts.append(f"  跨句矛盾: {c.get('absolute', '')[:20]}... vs {c.get('qualified', '')[:20]}... ({severity})")

        er = checks.get("entropy_reduction", {})
        if isinstance(er, dict) and "score" in er:
            parts.append(f"认知降熵: 评分={er['score']:.2f}, 压缩率={er.get('compression_ratio', 0):.2f}, 信息密度={er.get('info_density', 0):.2f}")

        return "\n".join(parts) if parts else "无增强筛子数据"