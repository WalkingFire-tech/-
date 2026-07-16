import asyncio
import json
from typing import Optional
from loguru import logger
from infrastructure.database_manager import DatabaseManager

from backend.services.path_handlers._shared import (
    _fast_executor,
    _RESOURCE_AWARE,
    _check_vector_available,
)

try:
    from core.resource_awareness.health_monitor import get_health_monitor
except ImportError:
    get_health_monitor = None

try:
    from core.services.cognitive_planner import get_cognitive_planner, CognitivePlanner
    _COGNITIVE_PLANNER_AVAILABLE = True
except ImportError:
    _COGNITIVE_PLANNER_AVAILABLE = False

try:
    from core.self.model import get_self_model
    _SELF_MODEL_AVAILABLE = True
except ImportError:
    _SELF_MODEL_AVAILABLE = False


def get_cognitive_planner_safe():
    if not _COGNITIVE_PLANNER_AVAILABLE:
        return None
    try:
        return get_cognitive_planner()
    except Exception:
        return None


def get_self_model_safe():
    if not _SELF_MODEL_AVAILABLE:
        return None
    try:
        return get_self_model()
    except Exception:
        return None


class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__}>"


def emit(event_type: str, data: dict) -> str:
    if event_type == "result" and _RESOURCE_AWARE:
        try:
            if get_health_monitor:
                get_health_monitor().unregister_query()
        except Exception:
            logger.warning("操作降级跳过")
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False, cls=SafeEncoder)}\n\n"


def build_uncertainty_note(query: str, response: str, attempts: list, prob_field, action: dict) -> str:
    entropy = prob_field._entropy if prob_field._candidates else 0
    candidates = prob_field._candidates if prob_field._candidates else {}

    verified_sources = []
    unverified_areas = []

    for name, result in attempts:
        if isinstance(result, bool) and result:
            if name in ("自我验证", "本质推理", "多源交叉验证", "代码验证", "科学免责"):
                verified_sources.append(name)
        if isinstance(result, bool) and not result:
            if name in ("自我验证", "本质推理", "多源交叉验证"):
                unverified_areas.append(name)

    source_names = []
    for cid, cinfo in candidates.items():
        src = cinfo.get("source", "")
        if src and src not in source_names:
            source_names.append(src)

    top_prob = 0.0
    if candidates:
        top_prob = max((c.get("probability", 0) for c in candidates.values()), default=0)

    lines = []
    lines.append("\n\n---")

    if top_prob >= 0.5 and verified_sources:
        confidence_desc = "主要结论经过了验证" if len(verified_sources) >= 2 else "核心观点有一定依据"
        lines.append(f"💡 {confidence_desc}——")
        for v in verified_sources[:3]:
            v_label = {"自我验证": "逻辑自洽检查", "本质推理": "第一性原理推演",
                       "多源交叉验证": "多来源比对", "代码验证": "代码语法验证",
                       "科学免责": "科学事实标注"}.get(v, v)
            lines.append(f"  ✓ {v_label}")
    else:
        lines.append("💡 这个回答我斟酌了一下——")

    if unverified_areas:
        lines.append("但以下方面我还没完全确认：")
        for u in unverified_areas[:2]:
            u_label = {"自我验证": "逻辑链条的完整性", "本质推理": "底层假设的可靠性",
                       "多源交叉验证": "不同来源的一致性"}.get(u, u)
            lines.append(f"  ✗ {u_label}")

    if source_names:
        sources_str = "、".join(source_names[:4])
        lines.append(f"参考来源：{sources_str}")

    if entropy > 0.85:
        lines.append("如果你有相关领域的经验，欢迎指正——我对这个话题的了解确实有限。")
    elif entropy > 0.7:
        specific_hint = ""
        q_lower = query.lower()
        if any(kw in q_lower for kw in ["代码", "编程", "函数", "api", "实现"]):
            specific_hint = "建议在实际环境中跑一遍确认。"
        elif any(kw in q_lower for kw in ["为什么", "原理", "机制", "本质"]):
            specific_hint = "如果需要更深入的推导，可以继续追问。"
        elif any(kw in q_lower for kw in ["多少", "什么时候", "哪个", "谁"]):
            specific_hint = "具体数据建议核对最新资料。"
        else:
            specific_hint = "关键细节建议再确认一下。"
        lines.append(specific_hint)

    lines.append("---")
    return "\n".join(lines)


def build_conversation_context(history: list) -> str:
    if not history:
        return ""
    parts = []
    for msg in history[-10:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not content:
            continue
        if "---\n⚠️" in content:
            content = content.split("---\n⚠️")[0].strip()
        if role == "user":
            parts.append(f"用户：{content[:300]}")
        elif role == "assistant":
            parts.append(f"助手：{content[:300]}")
    if not parts:
        return ""
    return "\n".join(parts)


def get_stereo_memory_context(query: str) -> str:
    try:
        from core.memory.stereo_memory import get_stereo_memory, MemoryType
        sm = get_stereo_memory()
        results = sm.search(query=query, limit=3)
        if not results:
            return ""
        parts = []
        for mem in results:
            content_str = str(mem.content)[:200] if mem.content else ""
            if content_str and len(content_str) > 20:
                emotion = mem.self_dimension.emotional_state
                confidence = mem.self_dimension.confidence
                parts.append(f"[记忆:{emotion} 置信度{confidence:.0%}] {content_str}")
        return "\n".join(parts) if parts else ""
    except Exception as e:
        logger.warning(f"立体记忆检索跳过: {e}")
        return ""


async def self_reason(query: str, conversation_context: str = "", truth_insights: str = "") -> Optional[dict]:
    """
    自我推理引擎 v2 — 本质推理+真谛类推驱动

    升级点：
    1. 真谛类推：用truth_accumulator.analogize()做跨域类推
    2. 本质推理：用essence_reasoner做第一性原理推理
    3. 知识聚合：经验+规则+真谛+本质推理综合
    4. 质量提升：从55→70+，高质量时无需调API
    """
    try:
        knowledge_parts = []
        quality_score = 50
        reasoning_depth = 0

        try:
            if _check_vector_available():
                from infrastructure.vector_retriever import vector_retriever
                if vector_retriever.is_available():
                    loop = asyncio.get_running_loop()
                    similar = await asyncio.wait_for(
                        loop.run_in_executor(_fast_executor, lambda: vector_retriever.search(query, top_k=5, threshold=0.4)),
                        timeout=5
                    )
                    for s in similar:
                        score = s.get('score', 0)
                        knowledge_parts.append(f"[经验 sim={score:.2f}] {s.get('text', '')[:250]}")
                        if score > 0.7:
                            quality_score += 5
                    reasoning_depth += 1
        except Exception:
            logger.warning("操作降级跳过")

        try:
            loop = asyncio.get_running_loop()
            def _query_rules():
                db = DatabaseManager.get("data/learning_rules.db")
                rows = db.query("SELECT rule_text, confidence FROM learning_rules WHERE status='active' AND rule_text LIKE ? ORDER BY confidence DESC LIMIT 5", (f"%{query[:10]}%",))
                return [(r[0], r[1]) for r in rows]
            rows = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_rules), timeout=3)
            for row in rows:
                knowledge_parts.append(f"[规则 conf={row[1]:.2f}] {row[0][:250]}")
                if row[1] > 0.8:
                    quality_score += 3
            reasoning_depth += 1
        except Exception:
            logger.warning("操作降级跳过")

        analogy_insights = []
        try:
            from core.truth_accumulator import truth_accumulator
            loop = asyncio.get_running_loop()
            analogies = await asyncio.wait_for(
                loop.run_in_executor(_fast_executor, lambda: truth_accumulator.analogize(query)),
                timeout=5
            )
            for a in analogies[:4]:
                insight_text = f"[真谛类推 {a['level']}] {a['name']}：{a['statement'][:200]}"
                if a.get('relevance', 0) > 0.5:
                    insight_text += f" (相关度{a['relevance']:.0%})"
                    quality_score += 5
                analogy_insights.append(insight_text)
            if analogies:
                reasoning_depth += 1
                quality_score += 3
        except Exception:
            logger.warning("操作降级跳过")

        essence_result = None
        try:
            from core.essence_reasoner import essence_reasoner
            loop = asyncio.get_running_loop()
            essence_result = await asyncio.wait_for(
                loop.run_in_executor(_fast_executor, lambda: essence_reasoner.reason(query, "")),
                timeout=10
            )
            if essence_result:
                reasoning_depth += 2
                quality_score += 8
                if essence_result.get("passed"):
                    quality_score += 5
                if essence_result.get("confidence", 0) > 0.7:
                    quality_score += 5
                if essence_result.get("facts"):
                    for fact in essence_result.get("facts", [])[:3]:
                        knowledge_parts.append(f"[本质事实] {str(fact)[:200]}")
                if essence_result.get("reasoning_chain"):
                    knowledge_parts.append(f"[推理链] {essence_result['reasoning_chain'][:300]}")
                if essence_result.get("verdict"):
                    knowledge_parts.append(f"[本质判断] {essence_result['verdict'][:200]}")
        except Exception:
            logger.warning("操作降级跳过")

        if truth_insights:
            knowledge_parts.append(f"[注入真谛] {truth_insights[:300]}")
            quality_score += 3

        all_parts = knowledge_parts + analogy_insights
        if not all_parts:
            return None

        reasoning_sections = []

        if analogy_insights:
            reasoning_sections.append("【真谛类推推理】")
            reasoning_sections.extend(analogy_insights)
            reasoning_sections.append("")

        if knowledge_parts:
            reasoning_sections.append("【知识推理】")
            reasoning_sections.extend(knowledge_parts)
            reasoning_sections.append("")

        if essence_result and essence_result.get("passed"):
            reasoning_sections.append(f"【本质推理结论】置信度{essence_result.get('confidence', 0):.0%}，推理自洽 ✅")
        elif essence_result and not essence_result.get("passed"):
            issues = essence_result.get("issues", [])
            reasoning_sections.append(f"【本质推理】发现{len(issues)}个自洽性问题，推理需谨慎 ⚠️")

        reasoning_sections.append("")
        reasoning_sections.append(f"[推理深度={reasoning_depth} | 质量分={quality_score}]")

        reasoning = f"关于「{query}」，基于本质推理与真谛类推的综合推理：\n\n" + "\n".join(reasoning_sections)

        quality_score = min(quality_score, 85)

        try:
            from backend.services.path_handlers.tool_path import query_needs_tools
            if query_needs_tools(query):
                quality_score = min(quality_score, 40)
                logger.info(f"自我推理: 操作类问题'{query[:30]}'降权 quality={quality_score}")
        except Exception:
            logger.warning("操作降级跳过")

        return {"source": "自我推理", "response": reasoning, "quality": quality_score}
    except Exception as e:
        logger.error(f"自我推理异常: {e}")
    return None


async def self_reason_deliberation(query: str, current_response: str, reason: str) -> str:
    try:
        from core.truth_accumulator import truth_accumulator
        insights = truth_accumulator.get_applicable_insights(query, "通用")
        insight_text = ""
        if insights:
            for ins in insights[:3]:
                insight_text += f"- {ins.get('name', '')}: {ins.get('essence_unit', '')[:100]}\n"
    except Exception:
        insight_text = ""

    try:
        db = DatabaseManager.get("data/spirit_lessons.db")
        lesson_rows = db.query(
            "SELECT lesson_type, lesson_text FROM spirit_lessons ORDER BY RANDOM() LIMIT 3"
        )
        lessons_text = ""
        for row in lesson_rows:
            lessons_text += f"- [{row[0]}] {row[1][:80]}\n"
    except Exception:
        lessons_text = ""

    try:
        from core.essence_gate import essence_gate
        eg_result = essence_gate.analyze(query)
        essence_unit = eg_result.get("essence_unit", "")
        dispatch_strategy = eg_result.get("dispatch_strategy", "")
    except Exception:
        essence_unit = ""
        dispatch_strategy = ""

    deliberation = f"## 深度分析：{query}\n\n"
    deliberation += f"**当前答案的问题**：{reason}\n\n"

    if essence_unit:
        deliberation += f"### 本质单元\n\n{essence_unit}\n\n"

    deliberation += "### 第一性原理分析\n\n"
    deliberation += "从最基本的原理出发，逐步推导：\n\n"

    constraint_patterns = [
        ("大.*小|高.*低|强.*弱|快.*慢|多.*少", "这是典型的**多目标优化问题**——存在相互冲突的约束条件。解决方向不是简单取舍，而是在帕累托边界上寻找最优解。"),
        ("如何|怎么|怎样|方法|方案|设计|优化", "这是**工程求解问题**——需要从约束条件反推可行方案，而非泛泛建议。"),
        ("静音|噪声|安静|噪音", "声学约束是**最严苛的非线性约束**——噪声与流速的5-6次方成正比，意味着微小的流速增加会导致巨大的噪声增加。"),
        ("效率|性能|功耗|能耗", "效率优化需要在**多个子系统之间协同**——局部最优不等于全局最优。"),
    ]

    analysis_added = False
    import re
    for pattern, analysis in constraint_patterns:
        if re.search(pattern, query):
            deliberation += f"1. {analysis}\n"
            analysis_added = True

    if not analysis_added:
        deliberation += "1. 识别问题中的核心变量和约束条件\n"
        deliberation += "2. 分析约束之间的矛盾和耦合关系\n"
        deliberation += "3. 在约束边界上寻找可行解\n"

    deliberation += "\n### 核心矛盾与权衡\n\n"
    deliberation += "以上分析揭示了根本性冲突，解决方向：\n"
    deliberation += "- 不是简单取舍，而是通过**技术创新**打破看似不可调和的矛盾\n"
    deliberation += "- 在约束边界上寻找**帕累托最优解**\n"
    deliberation += "- 利用**跨领域原理**（如仿生学、声学、流体力学）获得突破\n\n"

    deliberation += "### 工程解决方案\n\n"
    deliberation += "基于约束分析，可行的策略：\n\n"
    deliberation += "1. **原理层突破**：从第一性原理出发，找到约束的松弛条件\n"
    deliberation += "2. **结构层优化**：在相同约束下通过结构创新提升性能\n"
    deliberation += "3. **系统层协同**：多个子系统的联合优化，而非孤立优化单个指标\n"
    deliberation += "4. **边界层探索**：在约束边界上寻找意外可行解\n\n"

    if insight_text:
        deliberation += f"### 历史真谛洞察\n\n{insight_text}\n"

    if lessons_text:
        deliberation += f"### 经验教训参考\n\n{lessons_text}\n"

    deliberation += "### 结论\n\n"
    deliberation += "核心策略是**不追求单一指标最优，而是在约束边界上寻找帕累托最优解**。\n"
    deliberation += "通过原理层突破、结构层优化和系统层协同，在看似不可调和的矛盾中找到可行路径。\n"

    return deliberation


def is_goal_achieved(user_input: str, response: str, intent_type: str, attempts: list) -> bool:
    if not response or len(response) < 15:
        return False

    resp_lower = response.lower()
    user_lower = user_input.lower()

    is_operational = any(kw in user_lower for kw in [
        "读取", "获取", "执行", "运行", "访问", "打开", "写入", "发送",
        "串口", "com", "serial", "硬件", "设备", "端口", "命令", "cmd",
        "bash", "shell", "powershell", "安装", "部署", "启动", "停止",
        "gps", "nmea", "传感器", "扫描", "检测",
    ])

    if is_operational:
        code_block_count = resp_lower.count("```")
        has_real_data = any(kw in resp_lower for kw in [
            "$gpgga", "$gprmc", "$gpgsv", "nmea",
            "com8", "serial", "波特率", "baud",
            "成功打开", "读取到", "执行结果", "返回值",
            "pid", "进程", "exit code",
        ])
        is_just_instructions = (
            "你可以" in response or "你可以使用" in response or "你可以尝试" in response
            or "以下是" in response or "步骤如下" in response
            or "具体步骤" in response or "需要安装" in response
        ) and not has_real_data

        if is_just_instructions and code_block_count > 0 and not has_real_data:
            logger.info(f"🔄 目标未达成: 操作类问题只给了指导文本，没有实际执行结果")
            return False

    evasion_patterns = [
        "我无法访问", "我无法直接", "我不能访问", "我没有能力",
        "我无法连接", "我无法执行", "我无法获取", "我无法读取",
        "无法直接访问", "无法直接操作", "无法直接执行",
        "作为ai", "作为一个ai", "作为语言模型",
        "我建议你", "你可以自己", "你需要手动",
    ]
    for pattern in evasion_patterns:
        if pattern in resp_lower:
            logger.info(f"🔄 目标未达成: 回复包含敷衍模式'{pattern}'")
            return False

    if is_operational:
        fabricated_patterns = [
            "sensor data:", "sensor id:", "[device:main]",
            "temperature:", "humidity:", "pressure:",
        ]
        real_data_markers = ["$gpgga", "$gprmc", "$gngga", "$gnrmc", "nmea", "com8", "波特率", "serial_port"]
        has_fabricated = any(p in resp_lower for p in fabricated_patterns)
        has_real = any(p in resp_lower for p in real_data_markers)
        if has_fabricated and not has_real:
            logger.info(f"🔄 目标未达成: 检测到LLM伪造的硬件数据，非真实读取结果")
            try:
                from core.cognition.failure_classifier import FailureClassifier, FailureCategory
                FailureClassifier.classify_and_fix_sync(
                    {"status": "hallucination"}, user_input, {"fabricated": True})
            except Exception:
                pass
            return False

    if is_operational:
        has_execution = any(a[1] for a in attempts if isinstance(a, tuple) and len(a) >= 2
                          and any(kw in str(a[0]).lower() for kw in ["工具", "串口", "bash", "serial", "执行"]))
        code_block_count = resp_lower.count("```")
        if not has_execution and code_block_count == 0:
            tool_attempted = any("工具" in str(a[0]) for a in attempts if isinstance(a, tuple) and len(a) >= 1)
            if not tool_attempted:
                logger.info(f"🔄 目标未达成: 操作类问题没有尝试工具执行")
                return False

        best_source = ""
        for a in attempts:
            if isinstance(a, tuple) and len(a) >= 2 and a[1]:
                best_source = str(a[0])
                break
        if best_source == "自我推理":
            logger.info(f"🔄 目标未达成: 操作类问题最优来源是自我推理而非工具执行")
            return False

        has_real_data = any(kw in resp_lower for kw in [
            "$gpgga", "$gprmc", "$gpgsv", "nmea",
            "com8", "serial", "波特率", "baud",
            "成功打开", "读取到", "执行结果", "返回值",
            "pid", "进程", "exit code", "stdout", "stderr", "output",
        ])
        if not has_real_data and not code_block_count:
            logger.info(f"🔄 目标未达成: 操作类问题回复不含任何实际执行数据")
            return False

    return True


def perceive_continuity(user_input: str, history: list) -> dict:
    signal = {
        "topic_drift": False,
        "drift_distance": 0.0,
        "drift_direction": "",
        "reference_needs_resolution": False,
        "reference_text": "",
        "context_decay": False,
        "activity_level": 1.0,
        "previous_topics": [],
        "continuity_hint": "",
    }

    if not history or len(history) < 2:
        return signal

    recent_user_msgs = []
    for msg in history[-10:]:
        if msg.get("role") == "user" and msg.get("content"):
            recent_user_msgs.append(msg["content"])

    if not recent_user_msgs:
        return signal

    domain_keywords = {
        "hardware": ["串口", "com", "端口", "传感器", "gps", "nmea", "波特率", "arduino", "esp32", "电压", "电流", "引脚"],
        "code": ["代码", "函数", "编程", "算法", "python", "实现", "调试", "编译", "运行"],
        "science": ["为什么", "原理", "物理", "化学", "天文", "生物", "数学", "机制", "本质"],
        "philosophy": ["意义", "命运", "哲学", "悖论", "存在", "意识"],
        "daily": ["你好", "谢谢", "再见", "怎么样", "今天"],
    }

    def _detect_domain(text: str) -> str:
        text_lower = text.lower()
        best_domain = "unknown"
        best_count = 0
        for domain, keywords in domain_keywords.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > best_count:
                best_count = count
                best_domain = domain
        return best_domain if best_count > 0 else "unknown"

    current_domain = _detect_domain(user_input)
    previous_domains = [_detect_domain(msg) for msg in recent_user_msgs[-5:]]
    signal["previous_topics"] = previous_domains

    if previous_domains and current_domain != "unknown":
        last_domain = previous_domains[-1] if previous_domains else "unknown"
        if last_domain != "unknown" and current_domain != last_domain:
            signal["topic_drift"] = True
            signal["drift_direction"] = f"{last_domain}→{current_domain}"
            domain_distance = 1.0 if {last_domain, current_domain} in [
                {"hardware", "code"}, {"science", "philosophy"}
            ] else 0.5
            signal["drift_distance"] = domain_distance
            signal["continuity_hint"] = f"话题从{last_domain}跳转到{current_domain}"

    reference_patterns = ["它", "这个", "那个", "上面说的", "刚才的", "之前的", "他", "她"]
    for ref in reference_patterns:
        if ref in user_input and len(user_input) < 30:
            signal["reference_needs_resolution"] = True
            signal["reference_text"] = ref
            signal["continuity_hint"] = f"检测到指代词'{ref}'，需要消解上下文"
            break

    if len(history) > 20:
        recent_active = sum(1 for msg in history[-5:] if msg.get("role") == "user")
        signal["activity_level"] = recent_active / 5.0
        if recent_active < 2:
            signal["context_decay"] = True
            signal["continuity_hint"] = "长对话中近期交互稀疏，上下文可能衰减"

    return signal


def r4_self_check(user_input: str, intent_type: str, methodology: dict, capability_gap) -> dict:
    result = {"warnings": [], "adjustments": {}, "blocked": False, "block_reason": ""}

    strategy = methodology.get("strategy", "")
    if intent_type == "hardware" and strategy not in ("tool_first", "slow"):
        result["warnings"].append(f"方向不一致: hardware意图但策略={strategy}，建议tool_first")
        result["adjustments"]["strategy"] = "tool_first"
    if intent_type == "map" and strategy not in ("tool_first", "slow"):
        result["warnings"].append(f"方向不一致: map意图但策略={strategy}，建议tool_first")
        result["adjustments"]["strategy"] = "tool_first"
    if intent_type == "weather" and strategy not in ("tool_first", "slow"):
        result["warnings"].append(f"方向不一致: weather意图但策略={strategy}，建议tool_first")
        result["adjustments"]["strategy"] = "tool_first"

    if capability_gap and methodology.get("strategy") == "tool_first":
        result["warnings"].append(f"能力缺口: {capability_gap}，将尝试工具构建")

    if intent_type in ("hardware", "code", "map", "weather") and methodology.get("strategy") == "reasoning_only":
        result["warnings"].append(f"过度设计: {intent_type}意图不应走纯推理，切换为tool_first")
        result["adjustments"]["strategy"] = "tool_first"

    if intent_type == "challenge" and not methodology.get("challenge_history"):
        result["warnings"].append("质疑类无历史记录，已降级为complex_query")

    if intent_type == "hardware" and not methodology.get("source_priority"):
        result["adjustments"]["source_priority"] = ["工具执行", "经验池", "知识库", "Ollama"]
    if intent_type == "map" and not methodology.get("source_priority"):
        result["adjustments"]["source_priority"] = ["工具执行", "经验池", "知识库", "Ollama"]
    if intent_type == "weather" and not methodology.get("source_priority"):
        result["adjustments"]["source_priority"] = ["天气API", "经验池", "知识库", "Ollama"]

    if methodology.get("fabricated_data_detected"):
        result["blocked"] = True
        result["block_reason"] = "检测到伪造数据倾向，阻断执行以保护真实性"

    if methodology.get("topic_drift"):
        result["warnings"].append(f"话题漂移: {methodology.get('drift_direction', '')}，注意上下文衔接")

    return result



async def background_collect(task, query: str, task_name: str):
    try:
        result = await task
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and item.get("response"):
                    try:
                        from backend.services.path_handlers._shared import _save_to_experience_pool
                        _save_to_experience_pool(query, item["response"], success=True, intent_type="background_collect", model_name="ollama")
                    except Exception:
                        logger.warning("操作降级跳过")
                    logger.info(f"🔄 后台收集: {task_name}推理完成，已存入经验池")
        elif isinstance(result, dict) and result.get("response"):
            try:
                from backend.services.path_handlers._shared import _save_to_experience_pool
                _save_to_experience_pool(query, result["response"], success=True, intent_type="background_collect", model_name="external")
            except Exception:
                logger.warning("操作降级跳过")
            logger.info(f"🔄 后台收集: {task_name}推理完成，已存入经验池")
    except Exception as e:
        logger.error(f"后台收集异常: {e}")


_error_alchemy_instance = None

def alchemize_error(error: Exception, context: dict = None, phase: str = "unknown"):
    """错误炼金辅助函数：将异常交给ErrorAlchemy提炼学习信号

    在chat_orchestrator的关键except块中调用此函数，
    而非在每个except块中重复import+record+alchemize三步。
    """
    global _error_alchemy_instance
    try:
        if _error_alchemy_instance is None:
            from core.learning.error_alchemy import ErrorAlchemy
            _error_alchemy_instance = ErrorAlchemy()
        err_id = _error_alchemy_instance.record_error(error, context={
            **(context or {}),
            "phase": phase,
        })
        result = _error_alchemy_instance.alchemize(err_id)
        if result.gold_extracted:
            logger.info(f"🔮 错误炼金[{phase}]: 从'{type(error).__name__}'中提炼{result.lessons_learned}个学习信号({','.join(result.patterns_found)})")
            return result
    except Exception:
        logger.warning("操作降级跳过")
    return None