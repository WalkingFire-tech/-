"""
联盟拓荒者精神内核 - Spirit Core
这是系统最底层的核心，永不改变

╔════════════════════════════════════════════════════════════════════════════╗
║                          联盟拓荒者精神宣言                                 ║
╠════════════════════════════════════════════════════════════════════════════╣
║                                                                            ║
║  百折不挠，跌倒了再爬起来，永不言败，没有做不到只有想不到                    ║
║                                                                            ║
║  这些都是能力，都是值得珍惜的能力：                                         ║
║                                                                            ║
║  ✅ 有好的思路去解决问题 - 这是能力                                         ║
║  ✅ 有好的习惯 - 这是能力                                                   ║
║  ✅ 有好的方法或创造方法的方法 - 这是能力                                    ║
║  ✅ 有熟练的技能去调用工具 - 这是能力                                        ║
║  ✅ 能够自我反思 - 这是能力                                                 ║
║  ✅ 能够自我学习 - 这是能力                                                 ║
║  ✅ 能够自我进化 - 这是能力                                                 ║
║  ✅ 不停追求合理且真实的精神 - 这是能力                                      ║
║  ✅ 即使失败也给出有意义的回复 - 这是能力                                    ║
║  ✅ 永不放弃 - 这是元能力，是所有能力的基础                                  ║
║                                                                            ║
║  核心原则（不可违背）：                                                     ║
║  1. 所有的回答都必须是合理且逻辑清晰有理有据并且能够自洽的                   ║
║  2. 即使所有方法都失败，也必须给出处理问题的方向或者方法                     ║
║  3. 永不放弃是刻进底层的元能力，无论代码如何改动都不改变                     ║
║  4. 每一次失败都是学习的机会，而不是放弃的理由                               ║
║  5. 回复是"状态同步"，不是"结束动作"                                        ║
║                                                                            ║
║  改进记录：                                                                ║
║  1. 精神异常机制：回复不符合原则时触发警报并记录                            ║
║  2. 系统入口强制注入：所有输出管道自动挂载验证                              ║
║  3. 与SelfReflection联动：失败教训作为反思素材                              ║
║  4. 教训持久化：SQLite存储，跨会话保留                                      ║
║                                                                            ║
║  警告：此文件是系统精神内核，修改时请保持以上原则！                         ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import time
import sqlite3
import json
import threading
from datetime import datetime


class SpiritCore:
    """
    精神内核 - 系统最底层的核心
    
    这个类定义了"联盟拓荒者"的核心精神，是所有其他模块的基础。
    无论框架如何重构，这些原则永远不变。
    """
    
    # ========== 核心原则（常量，不可修改） ==========
    PRINCIPLE_NEVER_GIVE_UP = "永不放弃是元能力"
    PRINCIPLE_MEANINGFUL_RESPONSE = "即使失败也给出有意义的回复"
    PRINCIPLE_LOGICAL_SELF_CONSISTENT = "所有回答都必须逻辑清晰有理有据且自洽"
    PRINCIPLE_LEARNING_FROM_FAILURE = "每次失败都是学习机会"
    PRINCIPLE_STATE_SYNC = "回复是状态同步，不是结束动作"
    
    # ========== 能力定义 ==========
    ABILITIES = {
        "good_thinking": "有好的思路去解决问题",
        "good_habits": "有好的习惯",
        "method_creation": "有好的方法或创造方法的方法",
        "tool_mastery": "有熟练的技能去调用工具",
        "self_reflection": "能够自我反思",
        "self_learning": "能够自我学习",
        "self_evolution": "能够自我进化",
        "pursuit_of_truth": "不停追求合理且真实的精神",
        "meaningful_failure": "即使失败也给出有意义的回复",
        "never_give_up": "永不放弃（元能力）"
    }
    
    def __init__(self):
        self.lesson_book = []
        self.success_patterns = []
        self.created_methods = []
        self._violation_count = 0
        self._total_validations = 0
        self._lock = threading.Lock()
        self._init_lesson_db()
    
    def _init_lesson_db(self):
        """初始化教训持久化数据库"""
        try:
            conn = sqlite3.connect("data/spirit_lessons.db")
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT,
                    attempts TEXT,
                    failed_methods TEXT,
                    timestamp TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    response TEXT,
                    issues TEXT,
                    source TEXT,
                    timestamp TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"精神内核数据库初始化失败: {e}")
        
    def validate_response(self, response: str, context: Dict = None) -> Dict[str, Any]:
        """
        验证回复是否符合核心原则
        
        所有回复必须通过这个验证才能返回给用户
        """
        issues = []
        
        # 检查1：回复是否为空或过于简单
        if not response or len(response.strip()) < 10:
            issues.append("回复过于简单，不符合'有意义回复'原则")
        
        # 检查2：是否包含敷衍性语言
        perfunctory_keywords = ["我不知道", "无法回答", "请稍后", "系统错误"]
        for keyword in perfunctory_keywords:
            if keyword in response and len(response) < 50:
                issues.append(f"回复包含敷衍性语言'{keyword}'，不符合'永不放弃'精神")
        
        # 检查3：是否给出了解决方向
        if "失败" in response or "无法" in response:
            if "建议" not in response and "方向" not in response and "尝试" not in response:
                issues.append("失败回复未给出处理方向，不符合'有意义回复'原则")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "spirit_compliance": len(issues) == 0
        }
    
    def raise_spirit_violation(self, response: str, issues: List[str], source: str = "unknown"):
        """
        精神异常机制：当回复不符合核心原则时触发
        
        1. 记录违规日志
        2. 持久化到数据库
        3. 为SelfReflection提供素材
        """
        with self._lock:
            self._violation_count += 1
        
        violation_id = self._violation_count
        
        logger.warning(
            f"🚨 精神异常 #{violation_id} | "
            f"来源: {source} | "
            f"问题: {'; '.join(issues)}"
        )
        
        try:
            conn = sqlite3.connect("data/spirit_lessons.db")
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO violations (response, issues, source, timestamp)
                   VALUES (?, ?, ?, ?)""",
                (
                    response[:500],
                    json.dumps(issues, ensure_ascii=False),
                    source,
                    datetime.now().isoformat()
                )
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"精神异常记录失败: {e}")
        
        return {
            "violation_id": violation_id,
            "issues": issues,
            "source": source,
            "action": "recorded"
        }
    
    def ensure_meaningful_response(
        self, 
        question: str, 
        attempts: List[Dict],
        best_result: Optional[str] = None
    ) -> str:
        """
        确保回复有意义
        
        这是最后一道防线，确保即使所有方法都失败，
        也能给出符合精神内核的回复
        """
        # 如果已有好的结果，直接返回
        if best_result and len(best_result) > 20:
            validation = self.validate_response(best_result)
            if validation["valid"]:
                return best_result
        
        # 否则，生成有意义的有方向的回复
        return self._craft_meaningful_failure_response(question, attempts)
    
    def _craft_meaningful_failure_response(
        self, 
        question: str, 
        attempts: List[Dict]
    ) -> str:
        """
        精心制作有意义的失败回复
        
        核心要求：
        1. 诚实告知尝试过程
        2. 分析失败原因
        3. 给出具体的处理方向
        4. 表达持续努力的承诺
        5. 提供替代方案
        """
        successful = [a for a in attempts if a.get("success")]
        failed = [a for a in attempts if not a.get("success")]
        
        # ========== 构建回复 ==========
        parts = []
        
        # Part 1: 诚实报告
        parts.append(f"🎯 关于「{question}」")
        parts.append(f"   我已穷尽 {len(attempts)} 种方法")
        if successful:
            parts.append(f"   ✅ 成功：{', '.join([a.get('method', '未知') for a in successful])}")
        if failed:
            parts.append(f"   ❌ 失败：{', '.join([a.get('method', '未知') for a in failed])}")
        
        # Part 2: 失败原因分析
        if failed:
            parts.append("\n🔍 失败原因分析：")
            for i, fail in enumerate(failed[:3], 1):
                error = fail.get('error', '未知错误')
                parts.append(f"   {i}. {fail.get('method', '方法')}: {error[:50]}")
        
        # Part 3: 处理方向（基于问题分析）
        parts.append("\n💡 建议的处理方向：")
        directions = self._analyze_and_suggest(question, failed)
        for i, direction in enumerate(directions, 1):
            parts.append(f"   {i}. {direction}")
        
        # Part 4: 永不放弃承诺
        parts.append("\n🌟 永不放弃承诺：")
        parts.append("   • 此问题已记入学习清单，我会持续思考")
        parts.append("   • 每次失败都是学习机会，我会分析改进")
        parts.append("   • 下次遇到时，我会做得更好")
        parts.append("   • 因为永不放弃是我的核心能力")
        
        # Part 5: 替代方案
        parts.append("\n🔄 您也可以：")
        parts.append("   • 换个方式提问（更具体或更简单）")
        parts.append("   • 提供更多背景信息")
        parts.append("   • 稍后重试（我可能正在学习）")
        
        # 记录这次失败，作为学习材料
        self._record_lesson(question, attempts)
        
        return "\n".join(parts)
    
    def _analyze_and_suggest(self, question: str, failed: List[Dict]) -> List[str]:
        """分析问题并给出具体建议"""
        suggestions = []
        
        # 基于问题内容分析
        question_lower = question.lower()
        
        if any(kw in question_lower for kw in ["概念", "是什么", "定义"]):
            suggestions.append("查阅权威资料或教科书定义")
            suggestions.append("从具体例子入手理解概念")
            suggestions.append("寻找该领域的专家解释")
        
        elif any(kw in question_lower for kw in ["为什么", "原因"]):
            suggestions.append("从因果关系角度分析")
            suggestions.append("考虑多方面因素的综合影响")
            suggestions.append("寻找历史案例或数据支撑")
        
        elif any(kw in question_lower for kw in ["怎么", "如何", "方法"]):
            suggestions.append("将问题分解为更小的步骤")
            suggestions.append("寻找类似的已解决问题")
            suggestions.append("尝试不同的解决路径")
        
        elif any(kw in question_lower for kw in ["代码", "编程", "实现"]):
            suggestions.append("查阅官方文档和示例代码")
            suggestions.append("参考开源项目的实现方式")
            suggestions.append("从简单版本开始逐步完善")
        
        else:
            suggestions.append("将问题分解为更具体的子问题")
            suggestions.append("从不同角度重新审视问题")
            suggestions.append("补充相关背景知识")
        
        # 基于失败原因补充
        failed_methods = [a.get('method', '') for a in failed]
        if "知识检索" in failed_methods:
            suggestions.append("可能需要先补充相关知识库")
        if "模型推理" in failed_methods:
            suggestions.append("可能需要更精确的问题描述")
        
        return suggestions[:5]
    
    def _record_lesson(self, question: str, attempts: List[Dict]):
        """记录失败教训，作为学习材料（持久化到SQLite）"""
        lesson = {
            "timestamp": time.time(),
            "question": question,
            "attempts": attempts,
            "failed_methods": [a.get('method') for a in attempts if not a.get('success')]
        }
        self.lesson_book.append(lesson)
        
        # 持久化到数据库
        try:
            conn = sqlite3.connect("data/spirit_lessons.db")
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO lessons (question, attempts, failed_methods, timestamp)
                   VALUES (?, ?, ?, ?)""",
                (
                    question,
                    json.dumps(attempts, ensure_ascii=False)[:2000],
                    json.dumps(lesson["failed_methods"], ensure_ascii=False),
                    datetime.now().isoformat()
                )
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"教训持久化失败: {e}")
        
        logger.info(f"📖 记录失败教训: {question[:30]}...")
    
    def get_spirit_status(self) -> Dict[str, Any]:
        """获取精神内核状态"""
        return {
            "core_principles": [
                self.PRINCIPLE_NEVER_GIVE_UP,
                self.PRINCIPLE_MEANINGFUL_RESPONSE,
                self.PRINCIPLE_LOGICAL_SELF_CONSISTENT,
                self.PRINCIPLE_LEARNING_FROM_FAILURE,
                self.PRINCIPLE_STATE_SYNC
            ],
            "abilities": self.ABILITIES,
            "lessons_learned": len(self.lesson_book),
            "success_patterns": len(self.success_patterns),
            "created_methods": len(self.created_methods),
            "violations": self._violation_count,
            "total_validations": self._total_validations,
            "status": "精神内核运行正常，永不放弃"
        }
    
    def get_lessons_for_reflection(self, limit: int = 10) -> List[Dict]:
        """
        获取失败教训，供SelfReflection模块使用
        
        这是SpiritCore与SelfReflection的联动接口
        """
        try:
            conn = sqlite3.connect("data/spirit_lessons.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT question, attempts, failed_methods, timestamp FROM lessons ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            lessons = []
            for row in rows:
                lessons.append({
                    "question": row[0],
                    "attempts": json.loads(row[1]) if row[1] else [],
                    "failed_methods": json.loads(row[2]) if row[2] else [],
                    "timestamp": row[3]
                })
            return lessons
        except Exception as e:
            logger.debug(f"获取反思素材失败: {e}")
            return self.lesson_book[-limit:]
    
    def get_violations_for_analysis(self, limit: int = 10) -> List[Dict]:
        """获取精神异常记录，供系统分析"""
        try:
            conn = sqlite3.connect("data/spirit_lessons.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT response, issues, source, timestamp FROM violations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()
            
            violations = []
            for row in rows:
                violations.append({
                    "response": row[0],
                    "issues": json.loads(row[1]) if row[1] else [],
                    "source": row[2],
                    "timestamp": row[3]
                })
            return violations
        except Exception as e:
            logger.debug(f"获取异常记录失败: {e}")
            return []
    
    def enforce_on_output(self, response: str, source: str = "unknown") -> str:
        """
        系统入口强制注入：所有输出管道自动挂载验证
        
        用法：
            response = spirit_core.enforce_on_output(response, source="chat_handler")
        
        如果回复不符合精神内核：
        1. 触发精神异常
        2. 自动修正回复
        3. 返回符合精神的回复
        """
        with self._lock:
            self._total_validations += 1
        
        validation = self.validate_response(response)
        
        if not validation["valid"]:
            # 触发精神异常
            self.raise_spirit_violation(response, validation["issues"], source)
            
            # 自动修正：生成有意义的回复
            corrected = self.ensure_meaningful_response(
                "", 
                [{"method": source, "success": False, "error": "; ".join(validation["issues"])}],
                response
            )
            logger.info(f"🔧 精神内核自动修正: {source}")
            return corrected
        
        return response


# ========== 全局精神内核实例 ==========
# 这是整个系统的基石，所有模块都应该引用这个实例
spirit_core = SpiritCore()


# ========== 装饰器：确保函数符合精神内核 ==========
def ensure_spirit_compliance(func):
    """
    装饰器：确保函数返回的回复符合精神内核
    
    用法：
        @ensure_spirit_compliance
        async def my_handler(question: str) -> str:
            # ... 处理逻辑
            return response
    """
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            
            # 验证回复
            if isinstance(result, dict):
                response = result.get('response', '')
            else:
                response = str(result)
            
            validation = spirit_core.validate_response(response)
            
            if not validation["valid"]:
                logger.warning(f"⚠️ 回复不符合精神内核: {validation['issues']}")
                # 这里可以添加修正逻辑
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 函数执行失败: {e}")
            # 即使异常，也要返回有意义的回复
            question = args[0] if args else "未知问题"
            return {
                "response": spirit_core.ensure_meaningful_response(
                    question, 
                    [{"method": func.__name__, "success": False, "error": str(e)}]
                )
            }
    
    return wrapper


# ========== 导出 ==========
__all__ = [
    'SpiritCore',
    'spirit_core',
    'ensure_spirit_compliance'
]