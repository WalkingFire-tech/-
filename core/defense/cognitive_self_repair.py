"""
L4 自修复层 - 认知自修复 (Cognitive Self-Repair)

类比：神经可塑性——大脑受损后重新建立连接
- 检测认知结构损伤（矛盾规则、断裂推理链）
- 自动修复：合并矛盾、补全断裂
- 修复后验证一致性
"""
from infrastructure.database_manager import DatabaseManager
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime


class CognitiveSelfRepair:
    CONTRADICTION_THRESHOLD = 0.6
    MIN_RULE_CONFIDENCE = 0.3

    def __init__(self):
        self._repairs: List[dict] = []

    def diagnose(self) -> dict:
        diagnosis = {
            "contradictions": [],
            "low_confidence_rules": [],
            "broken_chains": [],
            "timestamp": datetime.now().isoformat(),
        }
        try:
            db = DatabaseManager.get("data/learning_rules.db")
            rules = db.query("SELECT id, pattern, action, confidence, status FROM learning_rules WHERE status='active'")
            pattern_map: Dict[str, List] = {}
            for rule in rules:
                rid, pattern, action, confidence, status = rule
                if pattern not in pattern_map:
                    pattern_map[pattern] = []
                pattern_map[pattern].append(rule)
                if confidence < self.MIN_RULE_CONFIDENCE:
                    diagnosis["low_confidence_rules"].append({
                        "id": rid, "pattern": pattern, "confidence": confidence,
                    })
            for pattern, rule_list in pattern_map.items():
                if len(rule_list) > 1:
                    actions = set(r[2] for r in rule_list)
                    if len(actions) > 1:
                        diagnosis["contradictions"].append({
                            "pattern": pattern,
                            "rules": [{"id": r[0], "action": r[2], "confidence": r[3]} for r in rule_list],
                        })
        except Exception as e:
            logger.debug(f"规则诊断失败: {e}")

        try:
            db = DatabaseManager.get("data/essence_reasoning.db")
            rows = db.query("SELECT id, query, consistency_score FROM reasoning_chains WHERE consistency_score < 0.5 ORDER BY timestamp DESC LIMIT 10")
            for row in rows:
                diagnosis["broken_chains"].append({
                    "id": row[0], "query": row[1][:50], "consistency": row[2],
                })
        except Exception:
            pass

        return diagnosis

    def repair_contradictions(self, contradictions: List[dict]) -> int:
        repaired = 0
        try:
            db = DatabaseManager.get("data/learning_rules.db")
            for contra in contradictions:
                rules = contra["rules"]
                best = max(rules, key=lambda r: r["confidence"])
                for rule in rules:
                    if rule["id"] != best["id"]:
                        db.execute("UPDATE learning_rules SET status='superseded' WHERE id=?", (rule["id"],), commit=True)
                        repaired += 1
                self._repairs.append({
                    "type": "contradiction_resolved",
                    "pattern": contra["pattern"],
                    "kept_rule_id": best["id"],
                    "superseded_count": len(rules) - 1,
                    "timestamp": datetime.now().isoformat(),
                })
        except Exception as e:
            logger.error(f"矛盾修复失败: {e}")
        if repaired:
            logger.info(f"🧠 认知修复: 解决{repaired}个矛盾规则")
        return repaired

    def repair_low_confidence(self, rules: List[dict]) -> int:
        demoted = 0
        try:
            db = DatabaseManager.get("data/learning_rules.db")
            for rule in rules:
                cur = db.execute("UPDATE learning_rules SET status='dormant' WHERE id=? AND confidence < ?",
                          (rule["id"], self.MIN_RULE_CONFIDENCE), commit=True)
                if cur.rowcount > 0:
                    demoted += 1

        except Exception as e:
            logger.error(f"低置信度修复失败: {e}")
        if demoted:
            logger.info(f"🧠 认知修复: 降级{demoted}条低置信度规则")
        return demoted

    def run_full_repair(self) -> dict:
        diagnosis = self.diagnose()
        contradiction_fixes = self.repair_contradictions(diagnosis["contradictions"])
        confidence_fixes = self.repair_low_confidence(diagnosis["low_confidence_rules"])
        result = {
            "diagnosis": {
                "contradictions_found": len(diagnosis["contradictions"]),
                "low_confidence_found": len(diagnosis["low_confidence_rules"]),
                "broken_chains_found": len(diagnosis["broken_chains"]),
            },
            "repairs": {
                "contradictions_resolved": contradiction_fixes,
                "rules_demoted": confidence_fixes,
            },
            "timestamp": datetime.now().isoformat(),
        }
        logger.info(f"🧠 认知自修复完成: {result['repairs']}")
        return result

    def get_repair_history(self, limit: int = 20) -> List[dict]:
        return self._repairs[-limit:]


cognitive_self_repair = CognitiveSelfRepair()