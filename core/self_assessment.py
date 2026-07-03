"""
持续自我评估器 (Continuous Self-Assessment)

核心使命：让系统持续感知自身状态，发现闭环中的断裂点

设计哲学：
  - 不依赖硬编码的感知数据，从真实数据库读取
  - 不只是"打分"，而是识别"闭环是否完整"
  - 不只是"发现问题"，而是定位"问题在闭环的哪个环节"
  
评估维度：
  1. 闭环完整性 — 经验→反思→规则→技能，每一步是否畅通
  2. 知识活力   — 知识是否在被使用，还是在"沉睡"
  3. 学习效率   — 新输入是否在转化为有效输出
  4. 行为偏差   — 系统是否在偏离核心身份
  5. 适应速度   — 面对变化时的调整能力
"""
import sqlite3
import time
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger


class SelfAssessment:
    HISTORY_MAX = 200

    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self._history: List[dict] = []
        self._last_assessment: Optional[dict] = None

    def assess(self) -> dict:
        report = {
            "timestamp": datetime.now().isoformat(),
            "loop_integrity": self._assess_loop_integrity(),
            "knowledge_vitality": self._assess_knowledge_vitality(),
            "learning_efficiency": self._assess_learning_efficiency(),
            "behavior_deviation": self._assess_behavior_deviation(),
            "adaptation_speed": self._assess_adaptation_speed(),
        }
        report["overall"] = self._calculate_overall(report)
        report["recommendations"] = self._generate_recommendations(report)
        self._history.append(report)
        if len(self._history) > self.HISTORY_MAX:
            self._history = self._history[-self.HISTORY_MAX:]
        self._last_assessment = report
        return report

    def _db(self, name: str) -> sqlite3.Connection:
        return sqlite3.connect(f"{self.root_dir}/data/{name}")

    def _assess_loop_integrity(self) -> dict:
        result = {"stages": {}, "breaks": [], "score": 0.0}
        try:
            conn = self._db("experience_pool.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM experiences")
            total_exp = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM experiences WHERE success=1")
            success_exp = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM experiences WHERE intent_type IS NOT NULL AND intent_type != ''")
            tagged_exp = c.fetchone()[0]
            conn.close()
            result["stages"]["experience_collection"] = {
                "total": total_exp,
                "success_rate": success_exp / max(total_exp, 1),
                "tagged_ratio": tagged_exp / max(total_exp, 1),
                "status": "healthy" if total_exp > 100 and tagged_exp / max(total_exp, 1) > 0.5 else "degraded",
            }
        except Exception as e:
            result["stages"]["experience_collection"] = {"status": "error", "error": str(e)[:100]}

        try:
            conn = self._db("learning_rules.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active_rules = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
            pending_rules = c.fetchone()[0]
            c.execute("SELECT AVG(confidence) FROM learning_rules WHERE status='active'")
            avg_conf = c.fetchone()[0] or 0.5
            conn.close()
            result["stages"]["reflection_to_rules"] = {
                "active": active_rules,
                "pending": pending_rules,
                "avg_confidence": round(avg_conf, 3),
                "status": "healthy" if active_rules > 10 and avg_conf > 0.5 else "degraded",
            }
            if pending_rules > active_rules * 3:
                result["breaks"].append({
                    "stage": "reflection_to_rules",
                    "issue": f"待激活规则({pending_rules})远超活跃规则({active_rules})，规则激活瓶颈",
                    "severity": "medium",
                })
        except Exception as e:
            result["stages"]["reflection_to_rules"] = {"status": "error", "error": str(e)[:100]}

        try:
            conn = self._db("skills.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM skills WHERE success_count >= 3 AND success_rate >= 0.7 AND is_active=1")
            mature = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM skills")
            total_skills = c.fetchone()[0]
            conn.close()
            result["stages"]["rules_to_skills"] = {
                "total": total_skills,
                "mature": mature,
                "maturation_rate": mature / max(total_skills, 1),
                "status": "healthy" if mature > 2 else "degraded",
            }
        except Exception as e:
            result["stages"]["rules_to_skills"] = {"status": "error", "error": str(e)[:100]}

        try:
            conn = self._db("truths.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM truths")
            total_truths = c.fetchone()[0]
            c.execute("SELECT level, COUNT(*) FROM truths GROUP BY level")
            by_level = {str(row[0]): row[1] for row in c.fetchall()}
            conn.close()
            result["stages"]["skills_to_truths"] = {
                "total": total_truths,
                "by_level": by_level,
                "status": "healthy" if total_truths > 10 else "degraded",
            }
        except Exception as e:
            result["stages"]["skills_to_truths"] = {"status": "error", "error": str(e)[:100]}

        stage_scores = []
        for name, stage in result["stages"].items():
            if stage.get("status") == "healthy":
                stage_scores.append(1.0)
            elif stage.get("status") == "degraded":
                stage_scores.append(0.5)
            else:
                stage_scores.append(0.0)
        result["score"] = sum(stage_scores) / max(len(stage_scores), 1)

        if len(result["breaks"]) == 0:
            all_healthy = all(s.get("status") == "healthy" for s in result["stages"].values())
            if not all_healthy:
                degraded = [n for n, s in result["stages"].items() if s.get("status") != "healthy"]
                result["breaks"].append({
                    "stage": ", ".join(degraded),
                    "issue": f"闭环阶段降级: {', '.join(degraded)}",
                    "severity": "low",
                })

        return result

    def _assess_knowledge_vitality(self) -> dict:
        result = {"metrics": {}, "dormant_count": 0, "score": 0.0}
        try:
            conn = self._db("experience_pool.db")
            c = conn.cursor()
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            c.execute("SELECT COUNT(*) FROM experiences WHERE timestamp >= ?", (week_ago,))
            recent_exp = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM experiences")
            total_exp = c.fetchone()[0]
            conn.close()
            result["metrics"]["recent_experiences_7d"] = recent_exp
            result["metrics"]["experience_total"] = total_exp
            result["metrics"]["experience_activity"] = recent_exp / max(total_exp, 1)
        except:
            pass

        try:
            conn = self._db("learning_rules.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active' AND apply_count > 0")
            used_rules = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active_rules = c.fetchone()[0]
            c.execute("SELECT AVG(apply_count) FROM learning_rules WHERE status='active'")
            avg_apply = c.fetchone()[0] or 0
            conn.close()
            result["metrics"]["used_active_rules"] = used_rules
            result["metrics"]["active_rules"] = active_rules
            result["metrics"]["rule_usage_rate"] = used_rules / max(active_rules, 1)
            result["metrics"]["avg_rule_apply"] = round(avg_apply, 1)
            dormant = active_rules - used_rules
            result["dormant_count"] = dormant
        except:
            pass

        try:
            conn = self._db("skills.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM skills WHERE status='mature'")
            mature = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM skills WHERE status='dormant'")
            dormant_skills = c.fetchone()[0]
            conn.close()
            result["metrics"]["mature_skills"] = mature
            result["metrics"]["dormant_skills"] = dormant_skills
            result["dormant_count"] += dormant_skills
        except:
            pass

        usage_rate = result["metrics"].get("rule_usage_rate", 0)
        activity = result["metrics"].get("experience_activity", 0)
        result["score"] = (usage_rate * 0.6 + min(activity * 10, 1.0) * 0.4)
        return result

    def _assess_learning_efficiency(self) -> dict:
        result = {"metrics": {}, "score": 0.0}
        try:
            conn = self._db("experience_pool.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM experiences WHERE success=1")
            success = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM experiences WHERE success=0")
            failure = c.fetchone()[0]
            conn.close()
            total = success + failure
            result["metrics"]["success_count"] = success
            result["metrics"]["failure_count"] = failure
            result["metrics"]["success_rate"] = success / max(total, 1)
        except:
            pass

        try:
            conn = self._db("learning_rules.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
            pending = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
            active = c.fetchone()[0]
            conn.close()
            conversion = active / max(active + pending, 1)
            result["metrics"]["pending_rules"] = pending
            result["metrics"]["active_rules"] = active
            result["metrics"]["rule_conversion_rate"] = round(conversion, 3)
        except:
            pass

        try:
            conn = self._db("skills.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM skills WHERE status='mature'")
            mature = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM skills")
            total_skills = c.fetchone()[0]
            conn.close()
            result["metrics"]["skill_maturation_rate"] = mature / max(total_skills, 1)
        except:
            pass

        success_rate = result["metrics"].get("success_rate", 0.5)
        conversion = result["metrics"].get("rule_conversion_rate", 0.2)
        maturation = result["metrics"].get("skill_maturation_rate", 0.3)
        result["score"] = success_rate * 0.4 + conversion * 0.3 + maturation * 0.3
        return result

    def _assess_behavior_deviation(self) -> dict:
        result = {"checks": {}, "deviations": [], "score": 1.0}
        try:
            conn = self._db("experience_pool.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM experiences WHERE success=0")
            failures = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM experiences")
            total = c.fetchone()[0]
            conn.close()
            error_rate = failures / max(total, 1)
            result["checks"]["error_rate"] = round(error_rate, 3)
            if error_rate > 0.15:
                result["deviations"].append({
                    "type": "high_error_rate",
                    "value": round(error_rate, 3),
                    "threshold": 0.15,
                    "description": f"错误率{error_rate:.0%}超过15%阈值",
                })
        except:
            pass

        try:
            conn = self._db("learning_rules.db")
            c = conn.cursor()
            c.execute("SELECT AVG(confidence) FROM learning_rules WHERE status='active'")
            avg_conf = c.fetchone()[0] or 0.5
            conn.close()
            result["checks"]["avg_rule_confidence"] = round(avg_conf, 3)
            if avg_conf < 0.4:
                result["deviations"].append({
                    "type": "low_confidence",
                    "value": round(avg_conf, 3),
                    "threshold": 0.4,
                    "description": f"规则平均置信度{avg_conf:.2f}低于0.4",
                })
        except:
            pass

        try:
            from core.module_health import module_health
            report = module_health.get_health_report()
            isolated = len(report.get("isolated", []))
            degraded = len(report.get("degraded", []))
            result["checks"]["isolated_modules"] = isolated
            result["checks"]["degraded_modules"] = degraded
            if isolated > 0:
                result["deviations"].append({
                    "type": "isolated_modules",
                    "value": isolated,
                    "threshold": 0,
                    "description": f"{isolated}个模块被隔离",
                })
        except:
            pass

        deviation_penalty = len(result["deviations"]) * 0.2
        result["score"] = max(0.0, 1.0 - deviation_penalty)
        return result

    def _assess_adaptation_speed(self) -> dict:
        result = {"metrics": {}, "score": 0.0}
        try:
            conn = self._db("experience_pool.db")
            c = conn.cursor()
            day_ago = (datetime.now() - timedelta(days=1)).isoformat()
            c.execute("SELECT COUNT(*) FROM experiences WHERE timestamp >= ?", (day_ago,))
            daily_exp = c.fetchone()[0]
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            c.execute("SELECT COUNT(*) FROM experiences WHERE timestamp >= ?", (week_ago,))
            weekly_exp = c.fetchone()[0]
            conn.close()
            result["metrics"]["daily_experiences"] = daily_exp
            result["metrics"]["weekly_experiences"] = weekly_exp
        except:
            pass

        try:
            conn = self._db("learning_rules.db")
            c = conn.cursor()
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            c.execute("SELECT COUNT(*) FROM learning_rules WHERE created_at >= ?", (week_ago,))
            new_rules = c.fetchone()[0]
            conn.close()
            result["metrics"]["new_rules_7d"] = new_rules
        except:
            pass

        try:
            conn = self._db("skills.db")
            c = conn.cursor()
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            c.execute("SELECT COUNT(*) FROM skills WHERE created_at >= ?", (week_ago,))
            new_skills = c.fetchone()[0]
            conn.close()
            result["metrics"]["new_skills_7d"] = new_skills
        except:
            pass

        daily = result["metrics"].get("daily_experiences", 0)
        new_rules = result["metrics"].get("new_rules_7d", 0)
        new_skills = result["metrics"].get("new_skills_7d", 0)
        input_score = min(daily / 10, 1.0)
        process_score = min(new_rules / 5, 1.0)
        output_score = min(new_skills / 2, 1.0)
        result["score"] = input_score * 0.3 + process_score * 0.4 + output_score * 0.3
        return result

    def _calculate_overall(self, report: dict) -> dict:
        scores = {
            "loop_integrity": report["loop_integrity"]["score"],
            "knowledge_vitality": report["knowledge_vitality"]["score"],
            "learning_efficiency": report["learning_efficiency"]["score"],
            "behavior_deviation": report["behavior_deviation"]["score"],
            "adaptation_speed": report["adaptation_speed"]["score"],
        }
        overall = (
            scores["loop_integrity"] * 0.30 +
            scores["knowledge_vitality"] * 0.20 +
            scores["learning_efficiency"] * 0.20 +
            scores["behavior_deviation"] * 0.15 +
            scores["adaptation_speed"] * 0.15
        )
        if overall >= 0.8:
            level = "thriving"
        elif overall >= 0.6:
            level = "healthy"
        elif overall >= 0.4:
            level = "degraded"
        elif overall >= 0.2:
            level = "struggling"
        else:
            level = "critical"
        return {
            "score": round(overall, 3),
            "level": level,
            "dimension_scores": {k: round(v, 3) for k, v in scores.items()},
        }

    def _generate_recommendations(self, report: dict) -> List[dict]:
        recs = []
        loop = report["loop_integrity"]
        for brk in loop.get("breaks", []):
            recs.append({
                "priority": "high" if brk.get("severity") == "medium" else "medium",
                "area": "loop_integrity",
                "action": brk["issue"],
                "stage": brk.get("stage", ""),
            })

        vitality = report["knowledge_vitality"]
        if vitality["dormant_count"] > 5:
            recs.append({
                "priority": "medium",
                "area": "knowledge_vitality",
                "action": f"{vitality['dormant_count']}条知识/规则处于休眠，考虑遗忘或激活",
            })

        efficiency = report["learning_efficiency"]
        conversion = efficiency["metrics"].get("rule_conversion_rate", 1.0)
        if conversion < 0.2:
            recs.append({
                "priority": "high",
                "area": "learning_efficiency",
                "action": f"规则转化率仅{conversion:.0%}，反思管道可能断裂",
            })

        deviation = report["behavior_deviation"]
        for dev in deviation.get("deviations", []):
            recs.append({
                "priority": "high",
                "area": "behavior_deviation",
                "action": dev["description"],
            })

        speed = report["adaptation_speed"]
        if speed["score"] < 0.3:
            recs.append({
                "priority": "medium",
                "area": "adaptation_speed",
                "action": "适应速度偏低，系统学习活跃度不足",
            })

        recs.sort(key=lambda r: 0 if r["priority"] == "high" else 1)
        return recs[:10]

    def get_latest(self) -> Optional[dict]:
        return self._last_assessment

    def get_history(self, limit: int = 10) -> List[dict]:
        return self._history[-limit:]

    def get_trend(self, dimension: str = "overall", window: int = 5) -> str:
        if len(self._history) < 2:
            return "insufficient_data"
        recent = self._history[-window:]
        if dimension == "overall":
            values = [r["overall"]["score"] for r in recent]
        else:
            values = [r.get(dimension, {}).get("score", 0) for r in recent]
        if len(values) < 2:
            return "stable"
        first_half = sum(values[:len(values)//2]) / max(len(values)//2, 1)
        second_half = sum(values[len(values)//2:]) / max(len(values) - len(values)//2, 1)
        diff = second_half - first_half
        if abs(diff) < 0.02:
            return "stable"
        return "improving" if diff > 0 else "declining"


self_assessment = SelfAssessment()