"""
现实校验器 — 检测叙事与现实的鸿沟

核心问题：系统生成的自我描述（叙事）可能与实际运行状态脱节。
例如：声称"生产就绪"但经验池质量低，声称"闭环完整"但trial_count=0。

解决方案：定期对比系统的自报告与可度量的运行时数据，
生成"叙事-现实差距"报告。这不是自评，而是自报告与客观事实的对照。
"""

from typing import Dict, List
from datetime import datetime
from loguru import logger


class RealityCheck:
    """现实校验器 — 对比自报告与运行时实际数据"""

    def __init__(self):
        self._check_history: List[Dict] = []

    def run_check(self) -> Dict:
        """执行一次完整的现实校验

        Returns:
            {
                "gaps": List[Dict],       # 叙事-现实差距
                "alignment_score": float, # 对齐度 0-1
                "narrative_claims": Dict,  # 系统自报告的关键声明
                "measured_reality": Dict,  # 可度量的运行时数据
            }
        """
        claims = self._collect_narrative_claims()
        reality = self._collect_measured_reality()
        gaps = self._detect_gaps(claims, reality)

        total_checks = len(gaps) + sum(1 for k in claims if k not in [g["claim_key"] for g in gaps])
        aligned = total_checks - len(gaps)
        alignment_score = aligned / total_checks if total_checks > 0 else 1.0

        result = {
            "gaps": gaps,
            "alignment_score": alignment_score,
            "narrative_claims": claims,
            "measured_reality": reality,
            "timestamp": datetime.now().isoformat(),
        }

        self._check_history.append(result)
        if len(self._check_history) > 50:
            self._check_history = self._check_history[-50:]

        if gaps:
            for g in gaps:
                logger.warning(
                    f"🔍 现实校验: [{g['claim_key']}] "
                    f"叙事={g['narrative_value']}, 实际={g['measured_value']}, "
                    f"差距={g['gap_description']}"
                )
        else:
            logger.debug(f"🔍 现实校验: 叙事与现实对齐 (score={alignment_score:.2f})")

        return result

    def _collect_narrative_claims(self) -> Dict:
        """收集系统自报告的关键声明"""
        claims = {}

        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            scores = sm.get_maturity_score()
            claims["maturity_overall"] = scores.get("overall", 0)
            claims["capability_strength"] = sm.capability_profile.get("overall_strength", 0)
        except Exception:
            claims["maturity_overall"] = None
            claims["capability_strength"] = None

        try:
            from core.self.external_calibration import external_calibration
            cal = external_calibration.get_status()
            claims["self_assessment_drift"] = cal.get("current_drift", 0)
        except Exception:
            claims["self_assessment_drift"] = None

        return claims

    def _collect_measured_reality(self) -> Dict:
        """收集可度量的运行时数据"""
        reality = {}

        try:
            from infrastructure.database_manager import DatabaseManager

            db_rules = DatabaseManager.get("data/learning_rules.db")
            total_rules = db_rules.query_one("SELECT COUNT(*) FROM learning_rules")
            active_rules = db_rules.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            trial_rules = db_rules.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='trial'")
            trial_with_count = db_rules.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='trial' AND trial_count > 0")

            reality["total_rules"] = total_rules[0] if total_rules else 0
            reality["active_rules"] = active_rules[0] if active_rules else 0
            reality["trial_rules"] = trial_rules[0] if trial_rules else 0
            reality["trial_rules_ever_matched"] = trial_with_count[0] if trial_with_count else 0
            reality["rule_activation_rate"] = (active_rules[0] / total_rules[0]) if (total_rules and total_rules[0] > 0) else 0

            db_exp = DatabaseManager.get("data/experience_pool.db")
            total_exp = db_exp.query_one("SELECT COUNT(*) FROM experiences")
            high_quality = db_exp.query_one("SELECT COUNT(*) FROM experiences WHERE quality_score >= 60")
            low_quality = db_exp.query_one("SELECT COUNT(*) FROM experiences WHERE quality_score < 30")

            reality["total_experiences"] = total_exp[0] if total_exp else 0
            reality["high_quality_experiences"] = high_quality[0] if high_quality else 0
            reality["low_quality_experiences"] = low_quality[0] if low_quality else 0
            reality["experience_quality_rate"] = (high_quality[0] / total_exp[0]) if (total_exp and total_exp[0] > 0) else 0

        except Exception as e:
            logger.warning(f"现实校验数据收集失败: {e}")

        try:
            from core.path_weight_manager import path_weight_manager
            weights = path_weight_manager.get_all_weights()
            reality["external_api_success_rate"] = weights.get("external_model", {}).get("success_rate", 0)
        except Exception:
            reality["external_api_success_rate"] = None

        return reality

    def _detect_gaps(self, claims: Dict, reality: Dict) -> List[Dict]:
        """检测叙事与现实之间的差距"""
        gaps = []

        # Gap 1: SelfModel成熟度 vs 客观综合分（双向检测）
        maturity = claims.get("maturity_overall")
        ext_cal = claims.get("external_calibration_score")
        if maturity is not None:
            if maturity > 0.6 and rule_rate is not None and rule_rate < 0.1:
                gaps.append({
                    "claim_key": "maturity_overall",
                    "narrative_value": f"{maturity:.2f} (成熟)",
                    "measured_value": f"{rule_rate:.2f} (规则激活率)",
                    "gap_description": "自评成熟度高但规则激活率极低，自评可能膨胀",
                })
            elif maturity < 0.3:
                try:
                    from core.self.external_calibration import external_calibration
                    ext_score = external_calibration._last_calibration.get("external_score", 0) if external_calibration._last_calibration else 0
                except Exception:
                    ext_score = 0
                if ext_score > 0.4:
                    gaps.append({
                        "claim_key": "maturity_overall",
                        "narrative_value": f"{maturity:.2f} (不成熟)",
                        "measured_value": f"{ext_score:.2f} (客观指标)",
                        "gap_description": "自评成熟度远低于客观指标，自评数据源可能未填充或评分逻辑有误",
                    })

        # Gap 2: 能力强度 vs 高质量经验占比
        capability = claims.get("capability_strength")
        exp_quality = reality.get("experience_quality_rate")
        if capability is not None and exp_quality is not None:
            if capability > 0.5 and exp_quality < 0.3:
                gaps.append({
                    "claim_key": "capability_strength",
                    "narrative_value": f"{capability:.2f} (强)",
                    "measured_value": f"{exp_quality:.2f} (高质量经验占比)",
                    "gap_description": "能力强度高但经验质量低，能力评估可能脱离实际",
                })

        # Gap 3: 自评漂移方向
        drift = claims.get("self_assessment_drift")
        if drift is not None and drift > 0.15:
            gaps.append({
                "claim_key": "self_assessment_drift",
                "narrative_value": f"{drift:+.2f} (膨胀)",
                "measured_value": "客观指标",
                "gap_description": "自评持续高于客观指标，存在正反馈漂移风险",
            })

        # Gap 4: trial规则从未被匹配
        trial_total = reality.get("trial_rules", 0)
        trial_matched = reality.get("trial_rules_ever_matched", 0)
        if trial_total > 10 and trial_matched == 0:
            gaps.append({
                "claim_key": "learning_loop",
                "narrative_value": "学习闭环运行中",
                "measured_value": f"{trial_total}条trial规则从未被匹配",
                "gap_description": "声称学习闭环运行，但trial规则从未被实际匹配和验证",
            })

        return gaps

    def get_status(self) -> Dict:
        if not self._check_history:
            return {"checks_run": 0, "latest_alignment": None}
        latest = self._check_history[-1]
        return {
            "checks_run": len(self._check_history),
            "latest_alignment": latest["alignment_score"],
            "latest_gaps": len(latest["gaps"]),
            "gap_details": latest["gaps"],
        }


reality_check = RealityCheck()