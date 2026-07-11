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
║  6. 追求本质——从第一性原理出发，追溯本源，不满足于表面答案                   ║
║  7. 困惑时坦诚——宁可诚实罗列分歧，不可强行牵强融合                           ║
║  8. 多源交叉验证——不依赖单一来源，综合批判性获取最真实最本质的东西           ║
║                                                                            ║
║  元宪法——认知重组铁律（不可违背）：                                         ║
║  R1. 未经沙盒验证的真谛，视同毒药                                           ║
║  R2. 未经渐进式注入的重组，视同自杀                                          ║
║  R3. 未经人类批准的进化，视同背叛                                            ║
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

from typing import Dict, Any, List, Optional, Final
from loguru import logger
import time
from infrastructure.database_manager import DatabaseManager
import json
import threading
from datetime import datetime


class _ImmutableNamespace:
    """不可变命名空间 — 阻止运行时修改核心常量"""
    __slots__ = ('_data',)

    def __init__(self, data: dict):
        object.__setattr__(self, '_data', dict(data))

    def __getattr__(self, name):
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"不可变命名空间无属性 '{name}'")

    def __setattr__(self, name, value):
        raise AttributeError(f"核心常量不可修改: {name}")

    def __delattr__(self, name):
        raise AttributeError(f"核心常量不可删除: {name}")

    def __contains__(self, item):
        return item in self._data

    def __iter__(self):
        return iter(self._data.values())


class _SpiritCoreMeta(type):
    """元类 — 阻止运行时修改SpiritCore的核心常量"""
    _IMMUTABLE_ATTRS = frozenset({
        'PRINCIPLE_NEVER_GIVE_UP', 'PRINCIPLE_MEANINGFUL_RESPONSE',
        'PRINCIPLE_LOGICAL_SELF_CONSISTENT', 'PRINCIPLE_LEARNING_FROM_FAILURE',
        'PRINCIPLE_STATE_SYNC', 'PRINCIPLE_PURSUE_ESSENCE',
        'PRINCIPLE_HONEST_WHEN_LOST', 'PRINCIPLE_MULTI_SOURCE_VERIFY',
        'PRINCIPLE_THINK_BEFORE_ACT',
        'META_LAW_SANDBOX', 'META_LAW_GRADUAL', 'META_LAW_HUMAN_APPROVAL',
        'META_LAW_SEVEN_DIM_CHECK',
        'ABILITIES', '_PRINCIPLES', '_META_LAWS',
    })

    def __setattr__(cls, name, value):
        if name in cls._IMMUTABLE_ATTRS:
            raise AttributeError(f"精神内核常量不可修改: {name}")
        super().__setattr__(name, value)

    def __delattr__(cls, name):
        if name in cls._IMMUTABLE_ATTRS:
            raise AttributeError(f"精神内核常量不可删除: {name}")
        super().__delattr__(name)


class SpiritCore(metaclass=_SpiritCoreMeta):
    """
    精神内核 - 系统最底层的核心
    
    这个类定义了"联盟拓荒者"的核心精神，是所有其他模块的基础。
    无论框架如何重构，这些原则永远不变。
    """
    
    # ========== 核心原则（不可修改） ==========
    _PRINCIPLES = _ImmutableNamespace({
        "NEVER_GIVE_UP": "永不放弃是元能力",
        "MEANINGFUL_RESPONSE": "即使失败也给出有意义的回复",
        "LOGICAL_SELF_CONSISTENT": "所有回答都必须逻辑清晰有理有据且自洽",
        "LEARNING_FROM_FAILURE": "每次失败都是学习机会",
        "STATE_SYNC": "回复是状态同步，不是结束动作",
        "PURSUE_ESSENCE": "追求本质——从第一性原理出发，追溯本源，不满足于表面答案",
        "HONEST_WHEN_LOST": "困惑时坦诚——宁可诚实罗列分歧，不可强行牵强融合",
        "MULTI_SOURCE_VERIFY": "多源交叉验证——不依赖单一来源，综合批判性获取最真实最本质的东西",
        "THINK_BEFORE_ACT": "三思后行——先理解全景再审视局部，先搜索既有讨论再行动，先根因思考再修复，七维自检通过才动手",
    })

    # ========== 元宪法——认知重组铁律（不可修改） ==========
    _META_LAWS = _ImmutableNamespace({
        "SANDBOX": "未经沙盒验证的真谛，视同毒药",
        "GRADUAL": "未经渐进式注入的重组，视同自杀",
        "HUMAN_APPROVAL": "未经人类允许的进化，视同背叛",
        "SEVEN_DIM_CHECK": "行动前七维自检——方向一致、看板衔接、最小侵入、无过度设计、治标+治本、可验证、精神内核对齐",
    })
    
    # 兼容旧代码的类属性访问（只读代理）
    PRINCIPLE_NEVER_GIVE_UP: Final[str] = "永不放弃是元能力"
    PRINCIPLE_MEANINGFUL_RESPONSE: Final[str] = "即使失败也给出有意义的回复"
    PRINCIPLE_LOGICAL_SELF_CONSISTENT: Final[str] = "所有回答都必须逻辑清晰有理有据且自洽"
    PRINCIPLE_LEARNING_FROM_FAILURE: Final[str] = "每次失败都是学习机会"
    PRINCIPLE_STATE_SYNC: Final[str] = "回复是状态同步，不是结束动作"
    PRINCIPLE_PURSUE_ESSENCE: Final[str] = "追求本质——从第一性原理出发，追溯本源，不满足于表面答案"
    PRINCIPLE_HONEST_WHEN_LOST: Final[str] = "困惑时坦诚——宁可诚实罗列分歧，不可强行牵强融合"
    PRINCIPLE_MULTI_SOURCE_VERIFY: Final[str] = "多源交叉验证——不依赖单一来源，综合批判性获取最真实最本质的东西"
    PRINCIPLE_THINK_BEFORE_ACT: Final[str] = "三思后行——先理解全景再审视局部，先搜索既有讨论再行动，先根因思考再修复，七维自检通过才动手"
    
    META_LAW_SANDBOX: Final[str] = "未经沙盒验证的真谛，视同毒药"
    META_LAW_GRADUAL: Final[str] = "未经渐进式注入的重组，视同自杀"
    META_LAW_HUMAN_APPROVAL: Final[str] = "未经人类允许的进化，视同背叛"
    META_LAW_SEVEN_DIM_CHECK: Final[str] = "行动前七维自检——方向一致、看板衔接、最小侵入、无过度设计、治标+治本、可验证、精神内核对齐"
    
    # ========== 能力定义（不可修改） ==========
    ABILITIES: Final[dict] = {
        "good_thinking": "有好的思路去解决问题",
        "good_habits": "有好的习惯",
        "method_creation": "有好的方法或创造方法的方法",
        "tool_mastery": "有熟练的技能去调用工具",
        "system_command": "能执行系统命令、访问本地硬件（串口、USB、文件系统）",
        "hardware_access": "能直接访问本地物理硬件——串口(COM)、USB设备、传感器",
        "self_reflection": "能够自我反思",
        "self_learning": "能够自我学习",
        "self_evolution": "能够自我进化",
        "pursuit_of_truth": "不停追求合理且真实的精神",
        "meaningful_failure": "即使失败也给出有意义的回复",
        "never_give_up": "永不放弃（元能力）",
        "pursue_essence": "追求本质——从第一性原理追溯本源",
        "honest_when_lost": "困惑时坦诚——诚实罗列分歧而非强行融合",
        "multi_source_verify": "多源交叉验证——综合批判性获取真相"
    }


    def __init__(self):
        self.lesson_book = []
        self.success_patterns = []
        self.created_methods = []
        self._violation_count = 0
        self._total_validations = 0
        self._lock = threading.Lock()
        self._init_lesson_db()

    def __setattr__(self, name, value):
        if name in _SpiritCoreMeta._IMMUTABLE_ATTRS:
            raise AttributeError(f"精神内核常量不可修改: {name}")
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if name in _SpiritCoreMeta._IMMUTABLE_ATTRS:
            raise AttributeError(f"精神内核常量不可删除: {name}")
        object.__delattr__(self, name)
    
    def _db_connect(self):
        return DatabaseManager.get("data/spirit_lessons.db", timeout=10.0)._get_conn()
    
    def _init_lesson_db(self):
        """初始化教训持久化数据库"""
        try:
            conn = self._db_connect()
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
        except Exception as e:
            logger.debug(f"精神内核数据库初始化失败: {e}")
        
    def validate_response(self, response: str, context: Dict = None) -> Dict[str, Any]:
        """
        验证回复是否符合核心原则（8维度细粒度验证）
        
        所有回复必须通过这个验证才能返回给用户
        维度对应8条核心原则：
        1. 有意义回复（非空非敷衍）
        2. 永不放弃（不轻易放弃）
        3. 逻辑自洽（无自相矛盾）
        4. 失败有方向（失败时给出处理方向）
        5. 状态同步（回复不是终结而是状态）
        6. 追求本质（不满足于表面答案）
        7. 困惑时坦诚（不强行融合矛盾）
        8. 多源验证（不依赖单一来源）
        """
        issues = []
        checks = {}
        query = (context or {}).get("query", "")
        content_understanding = (context or {}).get("content_understanding", {})
        is_simple_fact = content_understanding.get("claim_type") in ("factual", "descriptive") and not content_understanding.get("has_causal_assertions", False)
        
        # === 维度1：有意义回复 ===
        if not response or len(response.strip()) < 10:
            issues.append("回复过于简单，不符合'有意义回复'原则")
            checks["meaningful"] = False
        else:
            perfunctory_keywords = ["我不知道", "无法回答", "请稍后", "系统错误"]
            has_perfunctory = any(kw in response and len(response) < 50 for kw in perfunctory_keywords)
            if has_perfunctory:
                issues.append("回复包含敷衍性语言，不符合'有意义回复'原则")
                checks["meaningful"] = False
            elif is_simple_fact and len(response) >= 10:
                checks["meaningful"] = True
            elif content_understanding.get("has_numerical_assertions") or content_understanding.get("has_causal_assertions") or content_understanding.get("has_mechanism_descriptions"):
                checks["meaningful"] = True
            elif len(response) > 30 and not any(kw in response for kw in ["因为", "由于", "原因是", "所以", "因此", "意味着", "说明", "表明", "因为", "由于", "所以", "因此", "通过", "利用", "基于", "根据"]):
                if len(response) < 80:
                    issues.append("回复缺乏解释性内容，不符合'有意义回复'原则")
                    checks["meaningful"] = False
                else:
                    checks["meaningful"] = True
            else:
                checks["meaningful"] = True
        
        # === 维度2：永不放弃 ===
        give_up_phrases = ["我放弃了", "无法继续", "不再尝试", "彻底失败"]
        has_give_up = any(phrase in response for phrase in give_up_phrases)
        if has_give_up:
            issues.append("回复包含放弃性语言，违反'永不放弃'元能力")
            checks["never_give_up"] = False
        else:
            checks["never_give_up"] = True
        
        # === 维度3：逻辑自洽 ===
        contradiction_pairs = [
            ("不可能", "可以"), ("无法", "可以"),
            ("错误", "正确"),
        ]
        has_contradiction = False
        import re as _re
        sentences = _re.split(r'[。！？；\n]', response)
        for w1, w2 in contradiction_pairs:
            for sent in sentences:
                if len(sent) > 3 and w1 in sent and w2 in sent:
                    has_contradiction = True
                    break
            if has_contradiction:
                break
        if has_contradiction:
            issues.append("回复可能存在自相矛盾，需检查逻辑自洽性")
            checks["logical"] = False
        else:
            checks["logical"] = True
        
        # === 维度4：失败有方向 ===
        is_failure_report = (
            response.strip().startswith("🎯 关于") and
            "我已穷尽" in response
        )
        if is_failure_report:
            has_direction = any(kw in response for kw in ["建议", "方向", "尝试", "可以", "考虑"])
            if not has_direction:
                issues.append("失败回复未给出处理方向，不符合'有意义回复'原则")
                checks["failure_direction"] = False
            else:
                checks["failure_direction"] = True
        else:
            checks["failure_direction"] = True
        
        # === 维度5：状态同步（回复不是终结） ===
        closing_phrases = ["到此结束", "不再讨论", "最终答案，不接受质疑"]
        is_closing = any(phrase in response for phrase in closing_phrases)
        if is_closing:
            issues.append("回复呈现终结态度，不符合'状态同步'原则")
            checks["state_sync"] = False
        else:
            checks["state_sync"] = True
        
        # === 维度6：追求本质 ===
        shallow_patterns = ["就是这样", "反正就是", "别问为什么"]
        is_shallow = any(p in response for p in shallow_patterns) and len(response) < 100
        if is_shallow:
            issues.append("回复过于表面，不符合'追求本质'原则")
            checks["pursue_essence"] = False
        elif is_simple_fact:
            checks["pursue_essence"] = True
        elif content_understanding.get("has_numerical_assertions") or content_understanding.get("has_causal_assertions") or content_understanding.get("has_mechanism_descriptions"):
            checks["pursue_essence"] = True
        elif len(response) > 50 and not any(kw in response for kw in ["本质", "核心", "关键", "根本", "原因", "原理", "机制", "底层", "基础", "逻辑", "因为", "所以", "由于"]):
            if len(response.split('\n')) <= 2 and len(response) < 60:
                issues.append("回复缺乏深层分析，不符合'追求本质'原则")
                checks["pursue_essence"] = False
            else:
                checks["pursue_essence"] = True
        else:
            checks["pursue_essence"] = True
        
        # === 维度7：困惑时坦诚 ===
        forced_fusion = ["综上所述，两者其实是一回事", "简单来说都一样"]
        has_forced_fusion = any(p in response for p in forced_fusion)
        import re as _re2
        oversimplified_conclusion = _re2.search(r'(总之|总的来说|简而言之|总而言之)[，,]\s*(.{2,15})(?:就是|都是|就是)', response)
        if has_forced_fusion:
            issues.append("回复可能强行融合矛盾观点，不符合'困惑时坦诚'原则")
            checks["honest_when_lost"] = False
        elif oversimplified_conclusion:
            issues.append("回复包含过度简化的总结，可能掩盖分歧，不符合'困惑时坦诚'原则")
            checks["honest_when_lost"] = False
        else:
            checks["honest_when_lost"] = True
        
        # === 维度8：多源验证 ===
        single_source_claims = ["据我所知唯一", "只有一种可能", "毫无疑问"]
        has_single_source = any(p in response for p in single_source_claims) and len(response) < 80
        absolute_patterns = _re2.search(r'(一定|必然|绝对|肯定)[^，。？！\n]{0,10}(是|对|正确|没错)', response)
        if has_single_source:
            issues.append("回复呈现单一来源断言，不符合'多源交叉验证'原则")
            checks["multi_source"] = False
        elif absolute_patterns and len(response) < 60 and not is_simple_fact:
            issues.append("回复包含绝对化断言，不符合'多源交叉验证'原则")
            checks["multi_source"] = False
        else:
            checks["multi_source"] = True
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "spirit_compliance": len(issues) == 0,
            "checks": checks,
            "score": sum(1 for v in checks.values() if v) / max(len(checks), 1)
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
            conn = self._db_connect()
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
            conn = self._db_connect()
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
        except Exception as e:
            logger.debug(f"教训持久化失败: {e}")
        
        logger.info(f"📖 记录失败教训: {question[:30]}...")
    
    VALIDATION_DIMENSIONS = {
        "meaningful": "有意义回复",
        "never_give_up": "永不放弃",
        "logical": "逻辑自洽",
        "failure_direction": "失败有方向",
        "state_sync": "状态同步",
        "pursue_essence": "追求本质",
        "honest_when_lost": "困惑时坦诚",
        "multi_source": "多源验证"
    }

    def get_spirit_status(self) -> Dict[str, Any]:
        """获取精神内核状态"""
        return {
            "core_principles": [
                self.PRINCIPLE_NEVER_GIVE_UP,
                self.PRINCIPLE_MEANINGFUL_RESPONSE,
                self.PRINCIPLE_LOGICAL_SELF_CONSISTENT,
                self.PRINCIPLE_LEARNING_FROM_FAILURE,
                self.PRINCIPLE_STATE_SYNC,
                self.PRINCIPLE_PURSUE_ESSENCE,
                self.PRINCIPLE_HONEST_WHEN_LOST,
                self.PRINCIPLE_MULTI_SOURCE_VERIFY
            ],
            "validation_dimensions": self.VALIDATION_DIMENSIONS,
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
            conn = self._db_connect()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT question, attempts, failed_methods, timestamp FROM lessons ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            
            lessons = []
            for row in rows:
                try:
                    attempts = json.loads(row[1]) if row[1] else []
                except (json.JSONDecodeError, TypeError):
                    attempts = []
                try:
                    failed = json.loads(row[2]) if row[2] else []
                except (json.JSONDecodeError, TypeError):
                    failed = []
                lessons.append({
                    "question": row[0],
                    "attempts": attempts,
                    "failed_methods": failed,
                    "timestamp": row[3]
                })
            return lessons
        except Exception as e:
            logger.debug(f"获取反思素材失败: {e}")
            return self.lesson_book[-limit:]
    
    def get_violations_for_analysis(self, limit: int = 10) -> List[Dict]:
        """获取精神异常记录，供系统分析"""
        try:
            conn = self._db_connect()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT response, issues, source, timestamp FROM violations ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            
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
    
    def enforce_on_output(self, response: str, source: str = "unknown", query: str = "") -> str:
        """
        系统入口强制注入：所有输出管道自动挂载验证
        
        用法：
            response = spirit_core.enforce_on_output(response, source="chat_handler", query=user_input)
        
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
                query, 
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