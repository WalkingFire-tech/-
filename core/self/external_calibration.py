"""
外部校准锚点 — 打破SelfModel的自指闭环

核心问题：SelfModel的get_maturity_score()完全从自身数据计算，没有外部锚点。
这形成正反馈循环：自评→评分影响行为→行为变化→自评变化→...

解决方案：从系统运行时的客观指标（非自评数据）构建校准分数，
与SelfModel的自评分数对比，检测漂移。

客观指标来源：
1. 外部API实际成功率（从experience_pool读取）
2. 用户拒绝率（user_rejection_count / apply_count）
3. 响应空值率（final_response为空的比例）
4. 规则激活率（active / total）
5. 经验池质量分布

这些指标不由SelfModel生成，不由测试框架验证，而是从真实运行数据中读取。
"""

from typing import Dict, Optional
from datetime import datetime
from loguru import logger


class ExternalCalibration:
    """外部校准锚点 — 用客观运行数据校准SelfModel自评"""

    def __init__(self):
        self._last_calibration: Optional[Dict] = None
        self._drift_history: list = []
        self._calibrating: bool = False

    def calibrate(self) -> Dict:
        """从客观运行数据计算校准分数

        Returns:
            {
                "external_score": float,        # 客观指标综合分
                "drift": float,                 # 与SelfModel自评的偏差
                "drift_direction": str,          # "inflated" / "deflated" / "aligned"
                "indicators": Dict[str, float],  # 各客观指标
                "warnings": List[str],           # 漂移警告
            }
        """
        if self._calibrating:
            logger.debug("外部校准: 检测到重入，跳过（防止get_maturity_score→calibrate递归）")
            return self._last_calibration or {
                "external_score": 0.5, "self_model_score": 0.5,
                "drift": 0.0, "drift_direction": "unknown",
                "indicators": {}, "warnings": ["重入保护：跳过本次校准"],
            }

        self._calibrating = True
        try:
            return self._calibrate_inner()
        finally:
            self._calibrating = False

    def _calibrate_inner(self) -> Dict:
        indicators = self._collect_objective_indicators()

        weights = {
            "external_api_success_rate": 0.25,
            "user_rejection_rate": 0.20,
            "empty_response_rate": 0.15,
            "rule_activation_rate": 0.15,
            "experience_quality_rate": 0.15,
            "trial_rule_conversion_rate": 0.10,
        }

        external_score = 0.0
        for key, weight in weights.items():
            val = indicators.get(key, 0.5)
            external_score += val * weight

        self_model_score = self._get_self_model_score()

        drift = self_model_score - external_score

        if drift > 0.15:
            direction = "inflated"
        elif drift < -0.15:
            direction = "deflated"
        else:
            direction = "aligned"

        warnings = []
        if direction == "inflated":
            warnings.append(
                f"SelfModel自评({self_model_score:.2f})高于客观指标({external_score:.2f})，"
                f"偏差{drift:+.2f}，可能存在自评膨胀"
            )
        elif direction == "deflated":
            warnings.append(
                f"SelfModel自评({self_model_score:.2f})低于客观指标({external_score:.2f})，"
                f"偏差{drift:+.2f}，可能存在自评低估"
            )

        result = {
            "external_score": external_score,
            "self_model_score": self_model_score,
            "drift": drift,
            "drift_direction": direction,
            "indicators": indicators,
            "warnings": warnings,
            "timestamp": datetime.now().isoformat(),
        }

        self._last_calibration = result
        self._drift_history.append({"drift": drift, "direction": direction, "ts": result["timestamp"]})
        if len(self._drift_history) > 100:
            self._drift_history = self._drift_history[-100:]

        if warnings:
            for w in warnings:
                logger.warning(f"⚠️ 外部校准: {w}")
        else:
            logger.debug(f"外部校准: 自评与客观指标对齐 (偏差{drift:+.2f})")

        return result

    def _collect_objective_indicators(self) -> Dict[str, float]:
        """收集客观运行指标"""
        indicators = {}

        indicators["external_api_success_rate"] = self._read_external_api_success_rate()
        indicators["user_rejection_rate"] = self._read_user_rejection_rate()
        indicators["empty_response_rate"] = self._read_empty_response_rate()
        indicators["rule_activation_rate"] = self._read_rule_activation_rate()
        indicators["experience_quality_rate"] = self._read_experience_quality_rate()
        indicators["trial_rule_conversion_rate"] = self._read_trial_conversion_rate()

        return indicators

    def _read_external_api_success_rate(self) -> float:
        """外部API实际成功率（从path_weight_manager读取）"""
        try:
            from core.path_weight_manager import path_weight_manager
            weights = path_weight_manager.get_all_weights()
            ext = weights.get("external_model", {})
            return ext.get("success_rate", 0.5)
        except Exception:
            return 0.5

    def _read_user_rejection_rate(self) -> float:
        """用户拒绝率 → 反转为满意度（1 - rejection_rate）"""
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/learning_rules.db")
            row = db.query_one(
                "SELECT SUM(apply_count), SUM(user_rejection_count) FROM learning_rules WHERE status='active'"
            )
            if row and row[0] and row[0] > 0:
                rejection_rate = (row[1] or 0) / row[0]
                return 1.0 - min(rejection_rate, 1.0)
        except Exception:
            pass
        return 0.5

    def _read_empty_response_rate(self) -> float:
        """非空响应率（从experience_pool读取quality_score>0的比例）"""
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/experience_pool.db")
            total = db.query_one("SELECT COUNT(*) FROM experiences")
            quality = db.query_one("SELECT COUNT(*) FROM experiences WHERE quality_score > 0")
            if total and total[0] > 0:
                return (quality[0] or 0) / total[0]
        except Exception:
            pass
        return 0.5

    def _read_rule_activation_rate(self) -> float:
        """规则激活率（active / total）"""
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/learning_rules.db")
            total = db.query_one("SELECT COUNT(*) FROM learning_rules")
            active = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            if total and total[0] > 0:
                return (active[0] or 0) / total[0]
        except Exception:
            pass
        return 0.5

    def _read_experience_quality_rate(self) -> float:
        """高质量经验占比（quality_score >= 60）"""
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/experience_pool.db")
            total = db.query_one("SELECT COUNT(*) FROM experiences")
            high = db.query_one("SELECT COUNT(*) FROM experiences WHERE quality_score >= 60")
            if total and total[0] > 0:
                return (high[0] or 0) / total[0]
        except Exception:
            pass
        return 0.5

    def _read_trial_conversion_rate(self) -> float:
        """trial→active转化率"""
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/learning_rules.db")
            total = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status IN ('active','expired','trial')")
            active = db.query_one("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            if total and total[0] > 0:
                return (active[0] or 0) / total[0]
        except Exception:
            pass
        return 0.5

    def _get_self_model_score(self) -> float:
        """读取SelfModel的当前自评分 — 使用skip_calibration避免递归"""
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            if not sm.values:
                sm.sync_from_cognitive_planner(None)
            scores = sm.get_maturity_score(skip_calibration=True)
            return scores.get("overall", 0.5)
        except Exception:
            return 0.5

    def get_drift_trend(self) -> Dict:
        """获取漂移趋势"""
        if len(self._drift_history) < 3:
            return {"trend": "insufficient_data", "avg_drift": 0.0}

        recent = [d["drift"] for d in self._drift_history[-5:]]
        older = [d["drift"] for d in self._drift_history[-10:-5]] if len(self._drift_history) >= 10 else recent

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        if recent_avg > older_avg + 0.05:
            trend = "drifting_inflated"
        elif recent_avg < older_avg - 0.05:
            trend = "drifting_deflated"
        else:
            trend = "stable"

        return {"trend": trend, "avg_drift": recent_avg, "data_points": len(self._drift_history)}

    def get_status(self) -> Dict:
        """获取校准状态"""
        result = {
            "last_calibration": self._last_calibration,
            "drift_trend": self.get_drift_trend(),
        }
        if self._last_calibration:
            result["current_drift"] = self._last_calibration.get("drift", 0)
            result["drift_direction"] = self._last_calibration.get("drift_direction", "unknown")
        return result


external_calibration = ExternalCalibration()