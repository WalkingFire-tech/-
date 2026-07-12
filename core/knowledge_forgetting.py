"""
知识遗忘机制 (Knowledge Forgetting)

核心使命：让系统知道什么该保留、什么该淡化、什么该清除

设计哲学：
  - 遗忘不是"丢失"，而是"精简"——让重要的更突出
  - 类比生物记忆：短期记忆自动衰减，反复使用的被强化为长期记忆
  - 三维评估：使用频率 × 连接密度 × 时效性 → 保留价值分数
  
遗忘策略：
  - 保留（retain）：保留价值高，继续使用
  - 淡化（fade）：保留价值中等，降低优先级但不删除
  - 清除（prune）：保留价值低，删除以释放资源
"""
from infrastructure.database_manager import DatabaseManager
import json
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from loguru import logger


class KnowledgeForgetting:
    FADE_THRESHOLD = 0.3
    PRUNE_THRESHOLD = 0.1
    DORMANT_DAYS = 30
    LONG_UNUSED_DAYS = 60

    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self._last_report: Dict = {}

    def _db(self, name: str):
        return DatabaseManager.get(f"{self.root_dir}/data/{name}")

    def evaluate_rules(self) -> dict:
        result = {"retain": [], "fade": [], "prune": [], "stats": {}}
        try:
            db = self._db("learning_rules.db")
            rows = db.query("SELECT id, condition, action, confidence, status, apply_count, last_applied, created_at, success_count, trial_count FROM learning_rules")


            for row in rows:
                rid, condition, action, confidence, status, apply_count, last_applied, created_at, success_count, trial_count = row
                score = self._calculate_retention_score(
                    apply_count=apply_count or 0,
                    success_count=success_count or 0,
                    confidence=confidence or 0.5,
                    last_applied=last_applied,
                    created_at=created_at,
                    status=status,
                )
                entry = {
                    "id": rid,
                    "condition": (condition or "")[:60],
                    "status": status,
                    "confidence": confidence,
                    "apply_count": apply_count or 0,
                    "retention_score": round(score, 3),
                }
                if score >= self.FADE_THRESHOLD:
                    result["retain"].append(entry)
                elif score >= self.PRUNE_THRESHOLD:
                    result["fade"].append(entry)
                else:
                    result["prune"].append(entry)

            result["stats"] = {
                "total": len(rows),
                "retain": len(result["retain"]),
                "fade": len(result["fade"]),
                "prune": len(result["prune"]),
            }
        except Exception as e:
            logger.error(f"规则评估失败: {e}")
            result["stats"]["error"] = str(e)[:100]

        return result

    def evaluate_experiences(self) -> dict:
        result = {"retain": [], "fade": [], "prune": [], "stats": {}}
        try:
            db = self._db("experience_pool.db")
            total_row = db.query_one("SELECT COUNT(*) FROM experiences")
            total = total_row[0] if total_row else 0
            rows = db.query("SELECT id, raw_input, success, quality_score, timestamp, intent_type FROM experiences ORDER BY timestamp DESC LIMIT 500")


            for row in rows:
                eid, raw_input, success, quality, timestamp, intent_type = row
                score = self._calculate_experience_retention(
                    success=success,
                    quality_score=quality or 50,
                    timestamp=timestamp,
                    intent_type=intent_type,
                )
                entry = {
                    "id": eid,
                    "query": (raw_input or "")[:40],
                    "success": success,
                    "quality": quality,
                    "retention_score": round(score, 3),
                }
                if score >= self.FADE_THRESHOLD:
                    result["retain"].append(entry)
                elif score >= self.PRUNE_THRESHOLD:
                    result["fade"].append(entry)
                else:
                    result["prune"].append(entry)

            result["stats"] = {
                "total": total,
                "sampled": len(rows),
                "retain": len(result["retain"]),
                "fade": len(result["fade"]),
                "prune": len(result["prune"]),
            }
        except Exception as e:
            logger.error(f"经验评估失败: {e}")

        return result

    def _calculate_retention_score(self, apply_count: int, success_count: int,
                                    confidence: float, last_applied: str,
                                    created_at: str, status: str) -> float:
        if status == "active":
            frequency = min(apply_count / 10, 1.0)
        elif status == "trial":
            frequency = min(apply_count / 5, 1.0)
        else:
            frequency = min(apply_count / 3, 1.0)

        recency = 0.0
        if last_applied:
            try:
                last_dt = datetime.fromisoformat(last_applied)
                days_ago = (datetime.now() - last_dt).days
                recency = max(0, 1.0 - days_ago / self.LONG_UNUSED_DAYS)
            except Exception:
                recency = 0.3
        elif created_at:
            try:
                created_dt = datetime.fromisoformat(created_at)
                days_ago = (datetime.now() - created_dt).days
                if days_ago < 7:
                    recency = 0.5
                elif days_ago < 30:
                    recency = 0.3
                else:
                    recency = 0.1
            except Exception:
                recency = 0.2
        else:
            recency = 0.2

        connectivity = min(confidence, 1.0)
        if status == "active":
            connectivity = min(confidence + 0.2, 1.0)
        elif status == "pending" and apply_count == 0:
            connectivity = confidence * 0.5

        score = frequency * 0.4 + recency * 0.3 + connectivity * 0.3
        return score

    def _calculate_experience_retention(self, success, quality_score: int,
                                         timestamp: str, intent_type: str) -> float:
        quality = quality_score / 100.0

        success_bonus = 0.0
        if success == 1:
            success_bonus = 0.3
        elif success == 0:
            success_bonus = 0.1
        else:
            success_bonus = 0.15

        recency = 0.5
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                days_ago = (datetime.now() - dt).days
                recency = max(0, 1.0 - days_ago / 90)
            except Exception:
                pass

        tagged = 0.2 if intent_type and intent_type.strip() else 0.0

        score = quality * 0.3 + success_bonus + recency * 0.3 + tagged
        return min(score, 1.0)

    def execute_fading(self, dry_run: bool = True) -> dict:
        report = {
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
            "rules": self._fade_rules(dry_run),
            "experiences": self._fade_experiences(dry_run),
        }
        self._last_report = report
        return report

    def _fade_rules(self, dry_run: bool) -> dict:
        result = {"faded": 0, "pruned": 0, "reactivated": 0}
        try:
            db = self._db("learning_rules.db")

            pending = db.query("SELECT id, confidence, apply_count, status, trial_count, trial_success FROM learning_rules WHERE status='pending'")
            for row in pending:
                rid, conf, apply_cnt, status, trial_cnt, trial_succ = row
                trial_cnt = trial_cnt or 0
                trial_succ = trial_succ or 0
                if conf >= 0.5 and trial_cnt >= 3 and trial_succ / max(trial_cnt, 1) >= 0.6:
                    if not dry_run:
                        db.execute("UPDATE learning_rules SET status='active', promoted_at=?, promotion_reason='遗忘机制自动激活：置信度达标+试用期通过' WHERE id=?",
                                  (datetime.now().isoformat(), rid), commit=True)
                    result["reactivated"] += 1
                elif conf < 0.2 and (apply_cnt or 0) == 0:
                    if not dry_run:
                        db.execute("DELETE FROM learning_rules WHERE id=?", (rid,), commit=True)
                    result["pruned"] += 1
                elif conf < 0.3:
                    if not dry_run:
                        db.execute("UPDATE learning_rules SET status='dormant' WHERE id=?", (rid,), commit=True)
                    result["faded"] += 1

            active = db.query("SELECT id, apply_count, last_applied, confidence FROM learning_rules WHERE status='active'")
            for row in active:
                rid, apply_cnt, last_applied, conf = row
                apply_cnt = apply_cnt or 0
                if apply_cnt == 0 and last_applied is None:
                    days_old = 999
                    try:
                        cr = db.query_one("SELECT created_at FROM learning_rules WHERE id=?", (rid,))
                        if cr and cr[0]:
                            days_old = (datetime.now() - datetime.fromisoformat(cr[0])).days
                    except Exception:
                        pass
                    if days_old > self.DORMANT_DAYS:
                        if not dry_run:
                            db.execute("UPDATE learning_rules SET status='dormant' WHERE id=?", (rid,), commit=True)
                        result["faded"] += 1

        except Exception as e:
            logger.error(f"规则遗忘执行失败: {e}")
            result["error"] = str(e)[:100]

        return result

    def _fade_experiences(self, dry_run: bool) -> dict:
        result = {"faded": 0, "pruned": 0}
        try:
            db = self._db("experience_pool.db")

            lq_row = db.query_one("SELECT COUNT(*) FROM experiences WHERE success=0 AND quality_score < 30")
            low_quality_failures = lq_row[0] if lq_row else 0
            if low_quality_failures > 100:
                prune_limit = low_quality_failures - 50
                if not dry_run:
                    db.execute("DELETE FROM experiences WHERE id IN (SELECT id FROM experiences WHERE success=0 AND quality_score < 30 LIMIT ?)", (prune_limit,), commit=True)
                result["pruned"] += min(prune_limit, low_quality_failures)

            mf_row = db.query_one("SELECT COUNT(*) FROM experiences WHERE success=0 AND quality_score >= 30")
            medium_failures = mf_row[0] if mf_row else 0
            if medium_failures > 200:
                fade_limit = medium_failures - 100
                if not dry_run:
                    db.execute("DELETE FROM experiences WHERE id IN (SELECT id FROM experiences WHERE success=0 AND quality_score >= 30 AND quality_score < 50 LIMIT ?)", (fade_limit,), commit=True)
                result["faded"] += min(fade_limit, medium_failures)

        except Exception as e:
            logger.error(f"经验遗忘执行失败: {e}")

        return result

    def get_report(self) -> dict:
        if not self._last_report:
            return self.execute_fading(dry_run=True)
        return self._last_report


knowledge_forgetting = KnowledgeForgetting()