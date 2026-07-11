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
from typing import Dict, List, Any, Optional
from loguru import logger
from infrastructure.database_manager import DatabaseManager
from datetime import datetime


class SkillEmergence:
    """技能涌现引擎——从经验中提炼可复用的解决技能"""

    def __init__(self, db_path: str = "data/skills.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute('''CREATE TABLE IF NOT EXISTS skills (
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
                is_active INTEGER DEFAULT 1,
                automation_level TEXT DEFAULT 'manual',
                skeleton TEXT DEFAULT '',
                confidence REAL DEFAULT 0.5
            )''', commit=True)
            db.execute('''CREATE TABLE IF NOT EXISTS skill_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_name TEXT,
                query TEXT,
                was_successful INTEGER,
                elapsed REAL,
                timestamp TEXT
            )''', commit=True)
            try:
                db.execute("ALTER TABLE skills ADD COLUMN automation_level TEXT DEFAULT 'manual'", commit=True)
            except Exception:
                pass
            try:
                db.execute("ALTER TABLE skills ADD COLUMN skeleton TEXT DEFAULT ''", commit=True)
            except Exception:
                pass
            try:
                db.execute("ALTER TABLE skills ADD COLUMN confidence REAL DEFAULT 0.5", commit=True)
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"技能库初始化失败: {e}")

    def reflex_query(self, query: str) -> Optional[Dict]:
        """
        本能查询：检查是否有匹配的本能级技能可直接触发。
        返回None表示无匹配，需要走推理链。
        返回dict表示匹配到本能，包含solution_path和skeleton。
        """
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query(
                "SELECT skill_name, skill_type, trigger_patterns, solution_path, skeleton, confidence, automation_level, success_count FROM skills WHERE is_active=1 AND automation_level IN ('learned', 'reflex') ORDER BY confidence DESC"
            )
            if not rows:
                return None
            
            query_lower = query.lower()
            for row in rows:
                triggers = row[2].split("|") if row[2] else []
                matched = sum(1 for t in triggers if t in query_lower)
                if matched == 0:
                    continue
                
                overlap_ratio = matched / max(len(triggers), 1)
                effective_confidence = row[5] * (0.5 + 0.5 * overlap_ratio)
                
                if effective_confidence >= 0.7:
                    logger.info(f"⚡ 本能触发: {row[0]} (置信度{effective_confidence:.2f}, 级别{row[6]})")
                    return {
                        "skill_name": row[0],
                        "solution_path": row[3],
                        "skeleton": row[4],
                        "confidence": effective_confidence,
                        "automation_level": row[6],
                        "is_reflex": row[6] == "reflex"
                    }
        except Exception as e:
            logger.debug(f"本能查询失败: {e}")
        return None

    def _extract_skeleton(self, query: str, success_path: list) -> str:
        """
        从成功路径中提取抽象骨架（问题结构，非具体实现）
        例如: "串口读取→NMEA解析→地图标记" → "sensors→parse→visualize"
        """
        stage_map = {
            "扫描": "acquire", "读取": "acquire", "获取": "acquire", "检测": "acquire",
            "解析": "parse", "分析": "parse", "理解": "parse", "识别": "parse", "翻译": "parse",
            "标记": "visualize", "显示": "visualize", "渲染": "visualize", "绘制": "visualize", "呈现": "visualize",
            "验证": "verify", "确认": "verify", "检查": "verify",
            "推理": "reason", "思考": "reason", "推断": "reason",
        }
        
        query_stages = []
        for kw, stage in stage_map.items():
            if kw in query and stage not in query_stages:
                query_stages.append(stage)
        
        path_stages = []
        for step in success_path:
            step_str = str(step)
            for kw, stage in stage_map.items():
                if kw in step_str and stage not in path_stages:
                    path_stages.append(stage)
        
        skeleton = "→".join(query_stages or path_stages or ["acquire", "parse", "output"])
        return skeleton

    def analyze_and_learn(self, query: str, attempts: list, final_response: str, elapsed: float):
        """
        分析交互结果，提炼技能

        核心逻辑：
        1. 从成功路径中提取解决模式
        2. 如果该模式已存在，更新成功计数
        3. 如果是新模式，创建新技能
        4. 技能达到3次以上成功→标记为"成熟技能"
        5. 从失败中检测能力缺失，触发学习需求
        """
        successful = [a for a in attempts if a[1]]
        failed = [a for a in attempts if not a[1]]

        if not successful:
            self._record_failure(query, failed)
            gap_skill = self._emerge_from_failure(query, failed)
            if gap_skill:
                return gap_skill
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
            skeleton = self._extract_skeleton(query, success_path)
            self._create_skill(skill_name, skill_type, trigger, path_signature, skeleton)
            return skill_name

    def _classify_skill_type(self, query: str, success_path: list) -> str:
        query_lower = query.lower()

        if any(kw in query_lower for kw in ["代码", "编程", "函数", "算法", "单片机", "stm32", "实现"]):
            return "code_generation"
        if any(kw in query_lower for kw in ["esp32", "电压", "电流", "引脚", "电路", "硬件", "不工作", "不启动", "供电", "焊接", "万用表"]):
            return "engineering"
        if any(kw in query_lower for kw in ["为什么", "原理", "原因", "机制", "本质"]):
            return "essence_reasoning"
        if any(kw in query_lower for kw in ["天文", "物理", "化学", "生物", "医学", "数学"]):
            return "science_facts"
        if any(kw in query_lower for kw in ["命运", "意义", "哲学", "悖论"]):
            return "philosophical_analysis"
        if any(kw in query_lower for kw in ["如何", "怎么", "方法"]):
            return "method_guidance"

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
            "engineering": ["esp32", "电压", "电流", "引脚", "电路", "硬件", "供电", "焊接"],
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
            return skill_type

        return "|".join(keywords)

    def _find_matching_skill(self, trigger: str, skill_type: str) -> Optional[dict]:
        """查找匹配的已有技能"""
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query(
                "SELECT skill_name, skill_type, trigger_patterns, solution_path, success_count, fail_count, success_rate FROM skills WHERE skill_type=? AND is_active=1",
                (skill_type,)
            )


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
        except Exception:
            pass
        return None

    def _update_skill(self, skill: dict, was_successful: bool, elapsed: float):
        """更新技能统计 + 本能升级"""
        try:
            db = DatabaseManager.get(self.db_path)
            new_success = skill["success_count"] + (1 if was_successful else 0)
            new_fail = skill["fail_count"] + (0 if was_successful else 1)
            new_rate = new_success / max(new_success + new_fail, 1)
            
            old_confidence = skill.get("confidence", 0.5)
            if was_successful:
                new_confidence = min(1.0, old_confidence + (1.0 - old_confidence) * 0.1 * (1 + 1 / max(new_success, 1)))
            else:
                new_confidence = max(0.3, old_confidence - old_confidence * 0.15)
            
            new_level = "manual"
            if new_success >= 5 and new_confidence >= 0.9 and new_rate >= 0.8:
                new_level = "reflex"
            elif new_success >= 3 and new_confidence >= 0.7 and new_rate >= 0.7:
                new_level = "learned"
            else:
                new_level = skill.get("automation_level", "manual")
            
            db.execute(
                "UPDATE skills SET success_count=?, fail_count=?, success_rate=?, last_used=?, confidence=?, automation_level=? WHERE skill_name=?",
                (new_success, new_fail, round(new_rate, 3), datetime.now().isoformat(), round(new_confidence, 3), new_level, skill["skill_name"]),
                commit=True
            )

            if new_success >= 3 and new_rate >= 0.7:
                logger.info(f"🎯 技能成熟: {skill['skill_name']} (成功率{new_rate:.0%}, {new_success}次成功, 级别{new_level})")
                self._register_mature_skill(skill)
            
            if new_level == "reflex" and skill.get("automation_level") != "reflex":
                logger.info(f"⚡ 本能固化: {skill['skill_name']} 已升级为REFLEX (置信度{new_confidence:.2f})")
        except Exception as e:
            logger.debug(f"技能更新失败: {e}")

    def _create_skill(self, skill_name: str, skill_type: str, trigger: str, solution_path: str, skeleton: str = ""):
        """创建新技能"""
        try:
            db = DatabaseManager.get(self.db_path)
            db.execute(
                "INSERT OR IGNORE INTO skills (skill_name, skill_type, trigger_patterns, solution_path, success_count, fail_count, success_rate, last_used, created_at, skeleton, confidence, automation_level) VALUES (?, ?, ?, ?, 1, 0, 1.0, ?, ?, ?, 0.5, 'manual')",
                (skill_name, skill_type, trigger, solution_path, datetime.now().isoformat(), datetime.now().isoformat(), skeleton),
                commit=True
            )

            logger.info(f"✨ 新技能涌现: {skill_name} (类型={skill_type}, 触发={trigger}, 骨架={skeleton})")
        except Exception as e:
            logger.debug(f"技能创建失败: {e}")

    def _generate_skill_name(self, skill_type: str, trigger: str) -> str:
        names = {
            "code_generation": "代码工匠",
            "essence_reasoning": "本质追溯者",
            "science_facts": "科学验证师",
            "philosophical_analysis": "思辨者",
            "method_guidance": "方法导航员",
            "multi_source_verify": "多源仲裁者",
            "engineering": "工程诊断师",
            "general": "通用解题者",
        }
        base = names.get(skill_type, "解题者")
        trigger_key = trigger.replace("|", "_").replace(" ", "")[:20]
        return f"{base}_{trigger_key}"

    def _record_failure(self, query: str, failed: list):
        """记录失败，更新相关技能的失败计数，并检查退化"""
        if not failed:
            return
        failed_names = set()
        for item in failed:
            if isinstance(item, (list, tuple)) and len(item) > 0:
                name = str(item[0])
                if name and name not in ("规则推理", "本质推理"):
                    failed_names.add(name)
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query("SELECT skill_name, success_count, fail_count FROM skills WHERE is_active=1")
            for row in rows:
                skill_name, succ, fail = row
                new_fail = fail + 1
                total = succ + new_fail
                new_rate = succ / max(total, 1)
                db.execute("UPDATE skills SET fail_count=?, success_rate=? WHERE skill_name=?",
                          (new_fail, new_rate, skill_name), commit=True)
                if new_rate < 0.3 and total >= 5:
                    db.execute("UPDATE skills SET is_active=0 WHERE skill_name=?", (skill_name,), commit=True)
                    logger.info(f"技能退化: {skill_name} 成功率{new_rate:.0%}<{30}%，已标记为休眠")

        except Exception as e:
            logger.debug(f"技能失败记录异常: {e}")

    def get_applicable_skills(self, query: str) -> List[dict]:
        """获取适用于当前问题的技能（按成功率排序）"""
        try:
            db = DatabaseManager.get(self.db_path)
            rows = db.query(
                "SELECT skill_name, skill_type, trigger_patterns, solution_path, success_count, success_rate FROM skills WHERE is_active=1 AND success_count >= 2 ORDER BY success_rate DESC, success_count DESC LIMIT 5"
            )


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
        except Exception:
            return []

    def get_skill_stats(self) -> dict:
        try:
            db = DatabaseManager.get(self.db_path)
            total_row = db.query_one("SELECT COUNT(*) FROM skills WHERE is_active=1")
            total = total_row[0] if total_row else 0
            mature_row = db.query_one("SELECT COUNT(*) FROM skills WHERE success_count >= 3 AND success_rate >= 0.7 AND is_active=1")
            mature = mature_row[0] if mature_row else 0
            top_rows = db.query("SELECT skill_name, success_count, success_rate FROM skills WHERE is_active=1 ORDER BY success_count DESC LIMIT 5")
            top = [{"name": r[0], "successes": r[1], "rate": r[2]} for r in top_rows]

            return {
                "total_skills": total,
                "mature_skills": mature,
                "top_skills": top
            }
        except Exception:
            return {"total_skills": 0, "mature_skills": 0, "top_skills": []}

    def _emerge_from_failure(self, query: str, failed: list) -> str:
        """从失败中涌现学习需求——不是创建已成功的技能，而是创建'需要学习'的技能"""
        try:
            gap_type = "unknown"
            q = query.lower()

            hardware_kw = ["串口", "com", "serial", "波特率", "gps", "nmea", "硬件",
                            "设备", "usb", "传感器", "arduino", "stm32", "esp32", "单片机"]
            system_kw = ["运行", "执行", "命令", "cmd", "powershell", "bash", "shell",
                          "安装", "启动", "停止", "进程", "服务"]
            code_kw = ["代码", "编程", "函数", "程序", "算法", "实现", "写一段"]

            if any(kw in q for kw in hardware_kw):
                gap_type = "hardware_access"
            elif any(kw in q for kw in system_kw):
                gap_type = "system_command"
            elif any(kw in q for kw in code_kw):
                gap_type = "code_generation"

            if gap_type == "unknown":
                return None

            skill_name = f"need_learn_{gap_type}"
            existing = self._find_matching_skill(query[:30], gap_type)
            if existing:
                db = DatabaseManager.get("data/skill_emergence.db")
                db.execute(
                    "UPDATE skills SET fail_count=fail_count+1 WHERE skill_name=?",
                    (skill_name,),
                    commit=True
                )
                return None

            db = DatabaseManager.get("data/skill_emergence.db")
            db.execute(
                "INSERT OR REPLACE INTO skills (skill_name, skill_type, trigger_pattern, solution_path, success_count, fail_count, success_rate, is_active, created_at) VALUES (?,?,?,?,?,?,?,?,datetime('now'))",
                (skill_name, gap_type, query[:50], "待学习", 0, 1, 0.0, 1),
                commit=True
            )
            logger.info(f"🔍 从失败中涌现学习需求: {skill_name} (类型: {gap_type})")
            return skill_name
        except Exception as e:
            logger.debug(f"从失败中涌现技能异常: {e}")
            return None

    def _register_mature_skill(self, skill: dict):
        """将成熟技能注册为可调用工具"""
        try:
            from core.tool_registry import tool_registry, ToolInterface, ToolResult as RegistryToolResult
            skill_name = skill["skill_name"]
            tool_name = f"skill_{skill_name}"

            if tool_registry.get(tool_name):
                return

            _skill = skill

            class SkillToolWrapper(ToolInterface):
                @property
                def name(self) -> str:
                    return tool_name

                @property
                def description(self) -> str:
                    return f"成熟技能: {_skill.get('skill_name', '')} ({_skill.get('skill_type', '')})"

                @property
                def parameters(self) -> Dict:
                    return {"query": {"type": "string", "description": "输入查询"}}

                @property
                def category(self) -> str:
                    return "skill"

                @property
                def priority(self) -> int:
                    return 20

                async def execute(self, **kwargs) -> RegistryToolResult:
                    return RegistryToolResult(
                        success=True,
                        data=f"技能 {_skill.get('skill_name', '')} 已激活，解决路径: {_skill.get('solution_path', '')}",
                        source=tool_name,
                        quality=30,
                    )

            tool_registry.register(SkillToolWrapper())
            logger.info(f"✅ 成熟技能已注册为工具: {tool_name}")
        except Exception as e:
            logger.debug(f"成熟技能注册失败: {e}")


skill_emergence = SkillEmergence()