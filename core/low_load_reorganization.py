"""
低负载自我重组 (Low-Load Self-Reorganization)

核心使命：在系统空闲时，疏通闭环中的瓶颈，让知识在系统中流动

设计哲学：
  - 重组不是"重构一切"，而是"增量优化局部"
  - 类比睡眠：大脑在睡眠时整理白天记忆，建立新连接，清除冗余
  - 三个核心动作：激活(activate) / 合并(merge) / 重组(reorganize)
  
重组策略：
  1. 规则激活：重新评估pending规则，达标的自动激活
  2. 规则合并：相似规则合并为更强规则
  3. 知识连接：发现知识间的新关联
  4. 经验提炼：高质量经验提取为规则
"""
from infrastructure.database_manager import DatabaseManager
import re
from typing import Dict, List
from datetime import datetime
from loguru import logger


class LowLoadReorganization:
    def __init__(self, root_dir: str = "."):
        self.root_dir = root_dir
        self._last_result: Dict = {}

    def _db(self, name: str):
        return DatabaseManager.get(f"{self.root_dir}/data/{name}")._get_conn()

    def run(self) -> dict:
        result = {
            "timestamp": datetime.now().isoformat(),
            "rule_activation": self._activate_rules(),
            "rule_merging": self._merge_similar_rules(),
            "experience_extraction": self._extract_rules_from_experience(),
            "knowledge_connection": self._discover_connections(),
        }
        summary = {
            "rules_activated": result["rule_activation"]["activated"],
            "rules_merged": result["rule_merging"]["merged"],
            "rules_extracted": result["experience_extraction"]["extracted"],
            "connections_found": result["knowledge_connection"]["connections"],
        }
        result["summary"] = summary
        self._last_result = result
        if any(v > 0 for v in summary.values()):
            logger.info(f"🔄 低负载重组: {summary}")
        return result

    def _activate_rules(self) -> dict:
        result = {"activated": 0, "promoted_to_trial": 0, "examined": 0, "demoted_duplicate": 0}
        try:
            conn = self._db("learning_rules.db")
            c = conn.cursor()

            c.execute("SELECT id, confidence, trial_count, trial_success, apply_count, condition, action, source FROM learning_rules WHERE status='pending'")
            pending = c.fetchall()
            result["examined"] = len(pending)

            for row in pending:
                rid, conf, trial_cnt, trial_succ, apply_cnt, condition, action, source = row
                trial_cnt = trial_cnt or 0
                trial_succ = trial_succ or 0
                apply_cnt = apply_cnt or 0

                if conf >= 0.6 and trial_cnt >= 3 and trial_succ / max(trial_cnt, 1) >= 0.6:
                    c.execute("UPDATE learning_rules SET status='active', promoted_at=?, promotion_reason='低负载重组自动激活：高置信度+试用期通过' WHERE id=?",
                              (datetime.now().isoformat(), rid))
                    result["activated"] += 1
                elif conf >= 0.4 and apply_cnt >= 2:
                    c.execute("UPDATE learning_rules SET status='trial', promoted_at=?, promotion_reason='低负载重组晋升试用：中等置信度+有应用记录' WHERE id=?",
                              (datetime.now().isoformat(), rid))
                    result["promoted_to_trial"] += 1
                elif conf >= 0.3 and trial_cnt == 0 and apply_cnt == 0:
                    c.execute("UPDATE learning_rules SET status='trial', promoted_at=?, promotion_reason='低负载重组晋升试用：待验证规则进入试用期' WHERE id=?",
                              (datetime.now().isoformat(), rid))
                    result["promoted_to_trial"] += 1

            conn.commit()

        except Exception as e:
            logger.error(f"规则激活失败: {e}")

        return result

    def _merge_similar_rules(self) -> dict:
        result = {"merged": 0, "candidates": 0}
        try:
            conn = self._db("learning_rules.db")
            c = conn.cursor()
            c.execute("SELECT id, condition, action, confidence, status FROM learning_rules WHERE status='active'")
            active = c.fetchall()


            condition_groups: Dict[str, List] = {}
            for row in active:
                rid, condition, action, conf, status = row
                key = (condition or "").strip().lower()
                if not key:
                    continue
                if key not in condition_groups:
                    condition_groups[key] = []
                condition_groups[key].append(row)

            for key, rules in condition_groups.items():
                if len(rules) < 2:
                    continue
                result["candidates"] += 1
                best = max(rules, key=lambda r: r[3])
                for rule in rules:
                    if rule[0] != best[0]:
                        try:
                            conn2 = self._db("learning_rules.db")
                            conn2.execute("UPDATE learning_rules SET status='superseded' WHERE id=?", (rule[0],))
                            conn2.commit()

                            result["merged"] += 1
                        except:
                            pass
        except Exception as e:
            logger.error(f"规则合并失败: {e}")

        return result

    def _extract_rules_from_experience(self) -> dict:
        result = {"extracted": 0, "candidates": 0}
        try:
            conn = self._db("experience_pool.db")
            c = conn.cursor()
            c.execute("SELECT raw_input, response, intent_type FROM experiences WHERE success=1 AND quality_score >= 80 ORDER BY timestamp DESC LIMIT 50")
            high_quality = c.fetchall()

            result["candidates"] = len(high_quality)

            if not high_quality:
                return result

            conn2 = self._db("learning_rules.db")
            c2 = conn2.cursor()
            for raw_input, response, intent_type in high_quality:
                if not raw_input or not response:
                    continue
                condition = self._extract_pattern(raw_input)
                if not condition or len(condition) < 3:
                    continue
                c2.execute("SELECT COUNT(*) FROM learning_rules WHERE condition LIKE ?", (f"%{condition}%",))
                if c2.fetchone()[0] > 0:
                    continue
                action = response[:200] if response else ""
                c2.execute("INSERT INTO learning_rules (condition, action, confidence, status, source, created_at) VALUES (?, ?, ?, 'pending', ?, ?)",
                           (condition, action, 0.3, "experience_extraction", datetime.now().isoformat()))
                result["extracted"] += 1

            conn2.commit()

        except Exception as e:
            logger.error(f"经验提取失败: {e}")

        return result

    def _discover_connections(self) -> dict:
        result = {"connections": 0}
        try:
            conn = self._db("truths.db")
            c = conn.cursor()
            c.execute("SELECT content, level FROM truths WHERE level >= 3 LIMIT 20")
            truths = c.fetchall()


            if len(truths) < 2:
                return result

            keyword_map: Dict[str, List[int]] = {}
            for idx, (content, level) in enumerate(truths):
                words = re.findall(r'[\u4e00-\u9fff]{2,4}', content or "")
                for w in words:
                    if w not in keyword_map:
                        keyword_map[w] = []
                    keyword_map[w].append(idx)

            for keyword, indices in keyword_map.items():
                if len(indices) >= 2:
                    result["connections"] += 1
        except Exception as e:
            logger.debug(f"连接发现失败: {e}")

        return result

    def _normalize_condition(self, condition: str) -> str:
        normalized = re.sub(r'\d+', 'N', condition.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized[:50]

    def _extract_pattern(self, text: str) -> str:
        text = text.strip()
        if len(text) > 50:
            keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
            if keywords:
                return " ".join(keywords[:3])
        return text[:50]

    def get_last_result(self) -> dict:
        return self._last_result


low_load_reorganization = LowLoadReorganization()