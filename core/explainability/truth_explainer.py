"""
真谛升级解释器 — 为四道筛子决策生成解释

覆盖决策点：
1. 筛子1: 跨域普适性
2. 筛子2: 逻辑自洽性
3. 筛子3: 认知降熵效应
4. 筛子4: 反脆弱性
5. 综合判定
"""

from typing import Any, Dict, List, Optional

from core.explainability.explanation_types import DecisionDomain, Explanation
from core.explainability.decision_explainer import explain


class TruthExplainer:
    """真谛升级决策解释器"""

    DOMAIN = DecisionDomain.TRUTH_UPGRADE

    SIEVE_NAMES = {
        "cross_domain": "跨域普适性",
        "self_consistency": "逻辑自洽性",
        "entropy_reduction": "认知降熵",
        "antifragility": "反脆弱性",
    }

    @staticmethod
    def explain_sieve_result(
        truth_name: str,
        sieve_name: str,
        passed: bool,
        details: Dict[str, Any] = None,
    ) -> Explanation:
        cn_name = TruthExplainer.SIEVE_NAMES.get(sieve_name, sieve_name)
        if passed:
            reasoning = f"真谛'{truth_name}'通过筛子'{cn_name}'"
            if details:
                extra = ", ".join(f"{k}={v}" for k, v in details.items() if k != "passed")
                if extra:
                    reasoning += f"（{extra}）"
        else:
            reasoning = f"真谛'{truth_name}'未通过筛子'{cn_name}'"
            if details:
                failed_reason = details.get("reason", "")
                if failed_reason:
                    reasoning += f": {failed_reason}"

        return explain(
            domain=TruthExplainer.DOMAIN,
            decision=f"sieve_{sieve_name}",
            outcome="passed" if passed else "failed",
            reasoning=reasoning,
            inputs={"truth_name": truth_name, "sieve": sieve_name},
            context=details or {},
        )

    @staticmethod
    def explain_upgrade_verdict(
        truth_name: str,
        eligible: bool,
        score: float,
        checks: Dict[str, Dict[str, Any]],
        is_seed: bool = False,
    ) -> Explanation:
        failed = [k for k, v in checks.items() if not v.get("passed", False)]
        cn_failed = [TruthExplainer.SIEVE_NAMES.get(k, k) for k in failed]
        cn_passed = [TruthExplainer.SIEVE_NAMES.get(k, k) for k in checks if checks[k].get("passed", False)]

        if eligible:
            reasoning = f"真谛'{truth_name}'通过全部四道筛子(评分{score:.0%})"
        else:
            reasoning = f"真谛'{truth_name}'未通过: {', '.join(cn_failed)}未通过(评分{score:.0%})"

        if is_seed:
            reasoning += "（种子真谛）"

        trace_steps = []
        for k, v in checks.items():
            cn = TruthExplainer.SIEVE_NAMES.get(k, k)
            trace_steps.append({
                "action": f"筛子: {cn}",
                "result": "通过" if v.get("passed") else "未通过",
            })

        return explain(
            domain=TruthExplainer.DOMAIN,
            decision="upgrade_verdict",
            outcome="eligible" if eligible else "ineligible",
            reasoning=reasoning,
            inputs={"truth_name": truth_name, "score": score, "is_seed": is_seed},
            context={"checks": checks, "failed_sieves": cn_failed},
            trace=trace_steps,
        )

    @staticmethod
    def explain_seed_write(
        truth_name: str,
        passed_sieves: bool,
        sieve_details: Dict[str, Dict[str, Any]] = None,
    ) -> Explanation:
        if passed_sieves:
            reasoning = f"种子真谛'{truth_name}'通过筛子验证，正常写入"
        else:
            failed = [k for k, v in (sieve_details or {}).items() if not v.get("passed", False)]
            cn_failed = [TruthExplainer.SIEVE_NAMES.get(k, k) for k in failed]
            reasoning = f"种子真谛'{truth_name}'未通过筛子({', '.join(cn_failed)})，仍作为种子写入"

        return explain(
            domain=TruthExplainer.DOMAIN,
            decision="seed_write",
            outcome="written",
            reasoning=reasoning,
            inputs={"truth_name": truth_name, "passed_sieves": passed_sieves},
            context=sieve_details or {},
        )