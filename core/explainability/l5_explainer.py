"""
L5自修改解释器 — 为L5递归自我改进的决策生成解释

覆盖决策点：
1. 补丁策略选择（策略库/模板/LLM）
2. 安全验证拒绝原因
3. 自修改自举验证
4. 世界模型风险评估
5. 自动审批判断
6. 渐进部署各阶段
7. 策略进化调整

使用方式：
    from core.explainability.l5_explainer import L5Explainer
    
    # 补丁策略选择
    explanation = L5Explainer.explain_patch_strategy(
        strategy="template", category="exception_handling",
        reason="模板匹配成功：裸except→except Exception",
        alternatives=["llm_patch"], confidence=0.95
    )
    
    # 自动审批判断
    explanation = L5Explainer.explain_auto_approve(
        approved=True, confidence=0.95, threshold=0.9,
        category="exception_handling", is_self_mod=False
    )
"""

from typing import Any, Dict, List, Optional

from core.explainability.explanation_types import DecisionDomain, Explanation
from core.explainability.decision_explainer import explain


class L5Explainer:
    """L5自修改决策解释器 — 纯函数式，无状态"""

    DOMAIN = DecisionDomain.L5_MODIFICATION

    @staticmethod
    def explain_patch_strategy(
        strategy: str,
        category: str,
        reason: str,
        alternatives: List[str] = None,
        confidence: float = 0.0,
        strategy_library_hit: bool = False,
        template_name: str = "",
    ) -> Explanation:
        if strategy == "strategy_library":
            reasoning = f"策略库命中(category={category}): {reason}"
        elif strategy == "template":
            reasoning = f"模板补丁匹配({template_name or category}): {reason}"
        elif strategy == "llm":
            reasoning = f"LLM补丁生成(category={category}): {reason}"
        else:
            reasoning = f"无可用补丁策略: {reason}"

        trace_steps = []
        if strategy_library_hit:
            trace_steps.append({"action": "策略库查询", "result": "命中"})
        if strategy == "template":
            trace_steps.append({"action": "模板匹配", "result": f"匹配到{template_name or category}"})
        elif strategy_library_hit and strategy != "strategy_library":
            trace_steps.append({"action": "策略库查询", "result": "未命中或低置信度"})
        if strategy == "llm":
            trace_steps.append({"action": "模板匹配", "result": "未命中"})
            trace_steps.append({"action": "LLM补丁生成", "result": "成功"})

        return explain(
            domain=L5Explainer.DOMAIN,
            decision="patch_strategy",
            outcome=strategy,
            reasoning=reasoning,
            inputs={"category": category, "confidence": confidence},
            context={"strategy_library_hit": strategy_library_hit, "template_name": template_name},
            alternatives=alternatives or [],
            trace=trace_steps,
        )

    @staticmethod
    def explain_safety_rejection(
        file_path: str,
        violations: List[str],
        check_type: str = "sandbox",
    ) -> Explanation:
        violation_summary = "; ".join(violations[:3])
        if len(violations) > 3:
            violation_summary += f" 等{len(violations)}项"
        reasoning = f"安全验证未通过({check_type}): {violation_summary}"

        return explain(
            domain=L5Explainer.DOMAIN,
            decision="safety_rejection",
            outcome="rejected",
            reasoning=reasoning,
            inputs={"file_path": file_path, "check_type": check_type},
            context={"violations": violations},
        )

    @staticmethod
    def explain_bootstrap_verification(
        file_path: str,
        can_bootstrap: bool,
        errors: List[str] = None,
        is_self_mod: bool = True,
    ) -> Explanation:
        if can_bootstrap:
            reasoning = f"自修改自举验证通过: {file_path} 可安全自举"
        else:
            err_summary = "; ".join((errors or [])[:3])
            reasoning = f"自修改自举验证失败: {err_summary}"

        return explain(
            domain=L5Explainer.DOMAIN,
            decision="bootstrap_verification",
            outcome="passed" if can_bootstrap else "failed",
            reasoning=reasoning,
            inputs={"file_path": file_path, "is_self_mod": is_self_mod},
            context={"errors": errors or []},
        )

    @staticmethod
    def explain_world_model_risk(
        file_path: str,
        risk_level: str,
        improves_outcome: bool,
        confidence_delta: float = 0.0,
        risk_details: Dict[str, Any] = None,
    ) -> Explanation:
        if risk_level == "high":
            reasoning = f"世界模型评估为高风险: {risk_details or '模拟显示可能退化'}"
        elif improves_outcome:
            reasoning = f"世界模型评估为低风险且改善预期: 置信度调整+{confidence_delta:.1f}"
        else:
            reasoning = f"世界模型评估为低风险: 风险等级{risk_level}"

        return explain(
            domain=L5Explainer.DOMAIN,
            decision="world_model_risk",
            outcome="rejected" if risk_level == "high" else "approved",
            reasoning=reasoning,
            inputs={"file_path": file_path, "risk_level": risk_level},
            context={"improves_outcome": improves_outcome, "confidence_delta": confidence_delta, "risk_details": risk_details},
        )

    @staticmethod
    def explain_auto_approve(
        approved: bool,
        confidence: float,
        threshold: float,
        category: str,
        is_self_mod: bool = False,
        effective_threshold: float = None,
        auto_approve_categories: List[str] = None,
    ) -> Explanation:
        eff_th = effective_threshold or threshold
        if approved:
            reasoning = (
                f"自动批准: 置信度{confidence:.2f}≥阈值{eff_th:.2f}"
                f"，类别'{category}'在白名单中"
            )
            if is_self_mod:
                reasoning += "（自修改，阈值已调整）"
        else:
            if category not in (auto_approve_categories or []):
                reasoning = f"拒绝自动批准: 类别'{category}'不在白名单{auto_approve_categories}中"
            else:
                reasoning = f"拒绝自动批准: 置信度{confidence:.2f}<阈值{eff_th:.2f}"
                if is_self_mod:
                    reasoning += "（自修改，阈值已提高）"

        return explain(
            domain=L5Explainer.DOMAIN,
            decision="auto_approve",
            outcome=approved,
            reasoning=reasoning,
            inputs={"confidence": confidence, "threshold": threshold, "category": category, "is_self_mod": is_self_mod},
            context={"effective_threshold": eff_th, "auto_approve_categories": auto_approve_categories},
        )

    @staticmethod
    def explain_deployment_stage(
        file_path: str,
        stage: str,
        passed: bool,
        details: str = "",
        rollback: bool = False,
    ) -> Explanation:
        if passed:
            reasoning = f"部署阶段'{stage}'通过: {details or '正常'}"
        else:
            reasoning = f"部署阶段'{stage}'失败: {details or '未通过验证'}"
            if rollback:
                reasoning += "，已回滚"

        return explain(
            domain=L5Explainer.DOMAIN,
            decision="deployment_stage",
            outcome=f"{'passed' if passed else 'failed'}{'_rollback' if rollback else ''}",
            reasoning=reasoning,
            inputs={"file_path": file_path, "stage": stage},
            context={"rollback": rollback},
        )

    @staticmethod
    def explain_strategy_evolution(
        adjustments: List[Dict[str, Any]],
        current_params: Dict[str, Any] = None,
    ) -> Explanation:
        if not adjustments:
            reasoning = "策略进化: 无调整（样本不足或成功率在50%-80%之间）"
        else:
            adj_descs = []
            for adj in adjustments[:5]:
                if "category" in adj:
                    adj_descs.append(f"{adj.get('category', '?')}: {adj.get('direction', '?')}({adj.get('old', '?')}→{adj.get('new', '?')})")
                elif "param" in adj:
                    adj_descs.append(f"{adj['param']}: {adj.get('old', '?')}→{adj.get('new', '?')}")
            reasoning = f"策略进化: {len(adjustments)}项调整 — {'; '.join(adj_descs)}"

        return explain(
            domain=L5Explainer.DOMAIN,
            decision="strategy_evolution",
            outcome=f"{len(adjustments)}_adjustments",
            reasoning=reasoning,
            inputs={"adjustment_count": len(adjustments)},
            context={"adjustments": adjustments, "current_params": current_params},
        )