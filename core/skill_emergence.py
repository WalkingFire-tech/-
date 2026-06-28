"""
技能涌现机制 (Skill Emergence) - 从反复成功的模式中自动提炼技能

核心理念：
- 技能不是预设的，是从反复成功的解决模式中"涌现"出来的
- 就像熟能生巧——处理得多了，技能自然出现
- 技能是"小逻辑循环"：遇到类似问题时自动激活的解决路径
- 技能沉淀后，后续遇到类似问题可以作为一种尝试手段

工作流程：
  交互完成 → 分析成功路径 → 匹配已有技能 → 更新或新建技能 → 概率优化
"""

import json
import sqlite3
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime


class SkillEmergence:
    """技能涌现引擎——从经验中提炼可复用的解决技能"""

    def __init__(self, db_path: str = "data/skills.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT UNIQUE NOT NULL,
                skill_type TEXT NOT NULL,
                trigger_patterns TEXT NOT NULL,
                solution_path TEXT NOT NULL,
                success_count INTEGER DEFAULT 1,
                fail_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 1.0,
                last_used TEXT,
                created_at TEXT,
                evolved_from TEXT,
                is_active INTEGER DEFAULT 1
            )''')
            c.execute('''CREATE TABLE IF NOT EXISTS skill_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT,
                query TEXT,
                was_successful INTEGER,
                elapsed REAL,
                timestamp TEXT
            )''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"技能库初始化失败: {e}")

    def analyze_and_learn(self, query: str, attempts: list, final_response: str, elapsed: float):
        """
        分析交互结果，提炼技能

        核心逻辑：
        1. 从成功路径中提取解决模式
        2. 如果该模式已存在，更新成功计数
        3. 如果是新模式，创建新技能
        4. 技能达到3次以上成功→标记为"成熟技能"
        """
        successful = [a for a in attempts if a[1]]
        failed = [a for a in attempts if not a[1]]

        if not successful:
            self._record_failure(query, failed)
            return None

        # 提取成功路径
        success_path = [a[0] for a in successful]
        path_signature = "→".join(success_path)

        # 识别技能类型
        skill_type = self._classify_skill_type(query, success_path)

        # 提取触发模式
        trigger = self._extract_trigger_pattern(query, skill_type)

        if not trigger:
            return None

        # 查找已有技能
        existing = self._find_matching_skill(trigger, skill_type)

        if existing:
            # 更新已有技能
            self._update_skill(existing, was_successful=True, elapsed=elapsed)
            return existing["skill_name"]
        else:
            # 创建新技能
            skill_name = self._generate_skill_name(skill_type, trigger)
            self._create_skill(skill_name, skill_type, trigger, path_signature)
            return skill_name

    def _classify_skill_type(self, query: str, success_path: list) -> str:
        """分类技能类型"""
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["代码", "编程", "函数", "算法", "单片机", "stm32", "实现"]):
            return "code_generation"
        if any(kw in query_lower for kw in ["为什么", "原理", "原因", "机制", "本质"]):
            return "essence_reasoning"
        if any(kw in query_lower for kw in ["天文", "物理", "化学", "生物", "医学", "数学"]):
            return "science_facts"
        if any(kw in query_lower for kw in ["命运", "意义", "哲学", "悖论"]):
            return "philosophical_analysis"
        if any(kw in query_lower for kw in ["如何", "怎么", "方法"]):
            return "method_guidance"

        # 根据成功路径推断
        if "代码验证" in success_path:
            return "code_generation"
        if "本质推理" in success_path or "本质闸门" in success_path:
            return "essence_reasoning"
        if "多源交叉验证" in success_path:
            return "multi_source_verify"

        return "general"

    def _extract_trigger_pattern(self, query: str, skill_type: str) -> str:
        """提取触发模式——什么样的输入会激活这个技能"""
        # 简化：用问题类型+关键词作为触发模式
        keywords = []
        type_triggers = {
            "code_generation": ["代码", "编程", "函数", "算法", "实现", "写一段"],
            "essence_reasoning": ["为什么", "原理", "本质", "机制", "原因"],
            "science_facts": ["天文", "物理", "化学", "生物", "科学"],
            "philosophical_analysis": ["命运", "意义", "哲学", "悖论"],
            "method_guidance": ["如何", "怎么", "方法", "怎样"],
        }

        triggers = type_triggers.get(skill_type, [])
        for t in triggers:
            if t in query.lower():
                keywords.append(t)

        if not keywords:
            # 回退：取问题前10个字符作为触发
            return query[:10]

        return "|".join(keywords)

    def _find_matching_skill(self, trigger: str, skill_type: str) -> Optional[dict]:
        """查找匹配的已有技能"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "SELECT skill_name, skill_type, trigger_patterns, solution_path, success_count, fail_count, success_rate FROM skills WHERE skill_type=? AND is_active=1",
                (skill_type,)
            )
            rows = c.fetchall()
            conn.close()

            for row in rows:
                existing_triggers = row[2].split("|")
                overlap = len(set(existing_triggers) & set(trigger.split("|")))
                if overlap >= 1:
                    return {
                        "skill_name": row[0],
                        "skill_type": row[1],
                        "trigger_patterns": row[2],
                        "solution_path": row[3],
                        "success_count": row[4],
                        "fail_count": row[5],
                        "success_rate": row[6],
                    }
        except:
            pass
        return None

    def _update_skill(self, skill: dict, was_successful: bool, elapsed: float):
        """更新技能统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            new_success = skill["success_count"] + (1 if was_successful else 0)
            new_fail = skill["fail_count"] + (0 if was_successful else 1)
            new_rate = new_success / max(new_success + new_fail, 1)
            c.execute(
                "UPDATE skills SET success_count=?, fail_count=?, success_rate=?, last_used=? WHERE skill_name=?",
                (new_success, new_fail, round(new_rate, 3), datetime.now().isoformat(), skill["skill_name"])
            )
            conn.commit()
            conn.close()

            if new_success >= 3 and new_rate >= 0.7:
                logger.info(f"🎯 技能成熟: {skill['skill_name']} (成功率{new_rate:.0%}, {new_success}次成功)")
        except:
            pass

    def _create_skill(self, skill_name: str, skill_type: str, trigger: str, solution_path: str):
        """创建新技能"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "INSERT OR IGNORE INTO skills (skill_name, skill_type, trigger_patterns, solution_path, success_count, fail_count, success_rate, last_used, created_at) VALUES (?, ?, ?, ?, 1, 0, 1.0, ?, ?)",
                (skill_name, skill_type, trigger, solution_path, datetime.now().isoformat(), datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
            logger.info(f"✨ 新技能涌现: {skill_name} (类型={skill_type}, 触发={trigger})")
        except:
            pass

    def _generate_skill_name(self, skill_type: str, trigger: str) -> str:
        """生成技能名称"""
        names = {
            "code_generation": "代码工匠",
            "essence_reasoning": "本质追溯者",
            "science_facts": "科学验证师",
            "philosophical_analysis": "思辨者",
            "method_guidance": "方法导航员",
            "multi_source_verify": "多源仲裁者",
            "general": "通用解题者",
        }
        base = names.get(skill_type, "解题者")
        return f"{base}_{trigger[:8]}"

    def _record_failure(self, query: str, failed: list):
        """记录失败，更新相关技能的失败计数"""
        if not failed:
            return
        # 查找可能相关的技能，增加失败计数
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT skill_name, fail_count FROM skills WHERE is_active=1")
            rows = c.fetchall()
            for row in rows:
                c.execute("UPDATE skills SET fail_count=?, success_rate=? WHERE skill_name=?",
                          (row[1] + 1, row[1] / max(row[1] + 2, 1), row[0]))
            conn.commit()
            conn.close()
        except:
            pass

    def get_applicable_skills(self, query: str) -> List[dict]:
        """获取适用于当前问题的技能（按成功率排序）"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "SELECT skill_name, skill_type, trigger_patterns, solution_path, success_count, success_rate FROM skills WHERE is_active=1 AND success_count >= 2 ORDER BY success_rate DESC, success_count DESC LIMIT 5"
            )
            rows = c.fetchall()
            conn.close()

            applicable = []
            for row in rows:
                triggers = row[2].split("|")
                matched = any(t in query.lower() for t in triggers)
                if matched:
                    applicable.append({
                        "skill_name": row[0],
                        "skill_type": row[1],
                        "solution_path": row[3],
                        "success_count": row[4],
                        "success_rate": row[5],
                    })
            return applicable
        except:
            return []

    def get_skill_stats(self) -> dict:
        """获取技能统计"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM skills WHERE is_active=1")
            total = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM skills WHERE success_count >= 3 AND success_rate >= 0.7 AND is_active=1")
            mature = c.fetchone()[0]
            c.execute("SELECT skill_name, success_count, success_rate FROM skills WHERE is_active=1 ORDER BY success_count DESC LIMIT 5")
            top = c.fetchall()
            conn.close()
            return {
                "total_skills": total,
                "mature_skills": mature,
                "top_skills": [{"name": r[0], "successes": r[1], "rate": r[2]} for r in top]
            }
        except:
            return {"total_skills": 0, "mature_skills": 0, "top_skills": []}


skill_emergence = SkillEmergence()