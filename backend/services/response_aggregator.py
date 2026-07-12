from backend.services.intent_service import understand_response_content
from backend.services.path_handlers.tool_path import query_needs_tools


def score_response(result: dict, query: str) -> float:
    if not result or not result.get("response"):
        return 0
    response = result["response"]
    base = result.get("quality", 50)
    score = float(base)

    if len(response) > 100:
        score += 10
    if len(response) > 200:
        score += 5

    perfunctory = ["我不知道", "无法回答", "请稍后", "请告诉我更具体"]
    for kw in perfunctory:
        if kw in response and len(response) < 80:
            score -= 30
            break

    if query_needs_tools(query):
        hardware_copout = ["无法直接访问", "没有直接访问", "不能访问硬件", "无法获取数据", "无法访问您", "作为云端", "作为AI", "我无法访问"]
        for kw in hardware_copout:
            if kw in response:
                score -= 50
                break

    if any(kw in query.lower() for kw in ["认知", "意识", "思维", "智能", "什么是", "如何"]):
        if any(kw in response for kw in ["因为", "所以", "因此", "例如", "具体", "包括"]):
            score += 15

    if result["source"].startswith("Ollama"):
        pass
    elif result["source"] == "经验池":
        score += 15
    elif result["source"] in ("serial_port", "bash", "file_reader", "project_scanner", "code_indexer", "dependency_analyzer", "工具调用"):
        score += 15
        real_data_patterns = ["$gpgga", "$gprmc", "$gpgsv", "nmea", "com", "serial",
                              "波特率", "baud", "成功打开", "读取到", "执行结果",
                              "exit code", "pid", "进程", "返回值",
                              "stdout", "stderr", "output"]
        if any(p in response.lower() for p in real_data_patterns):
            score += 20
    elif result["source"] == "事实锚点":
        score += 10
    elif result["source"] == "自我推理":
        score += 12
    elif "外部" in result["source"]:
        score -= 5

    search_snippet_patterns = ["...", "…:", "CSDN", "博客园", "知乎", "Stack Overflow", "GitHub -"]
    snippet_count = sum(1 for p in search_snippet_patterns if p in response)
    if snippet_count >= 2:
        score -= 30

    if any(kw in query for kw in ["代码", "code", ".c", ".h", ".py", "实现", "算法", "函数"]):
        has_code = "```" in response or "int " in response or "void " in response or "def " in response or "function " in response
        if has_code:
            score += 20
        elif len(response) > 200:
            score -= 15

    query_topic_keywords = set()
    topic_groups = {
        "ai_system": ["AI", "智能", "系统", "感知", "修复", "自愈", "闭环", "架构", "模块", "能力", "自我", "认知", "推理", "学习", "进化", "反思", "记忆"],
        "physics": ["物理", "力学", "量子", "相对论", "引力", "电磁", "光速", "原子", "分子", "散射", "折射", "波长"],
        "astronomy": ["天文", "星球", "行星", "恒星", "火星", "木星", "太阳", "月球", "星系", "宇宙", "太空"],
        "biology": ["生物", "细胞", "基因", "DNA", "进化", "蛋白质", "病毒", "免疫"],
        "philosophy": ["哲学", "意义", "价值", "伦理", "存在", "本质", "思辨", "意识", "理性"],
    }
    for topic, keywords in topic_groups.items():
        if any(kw in query for kw in keywords):
            query_topic_keywords.add(topic)

    if query_topic_keywords:
        response_topic_keywords = set()
        for topic, keywords in topic_groups.items():
            if any(kw in response for kw in keywords):
                response_topic_keywords.add(topic)

        overlap = query_topic_keywords & response_topic_keywords
        if not overlap and response_topic_keywords:
            score -= 40

    return score


def compare_and_select(candidates: list, query: str, cbnr_ctx: dict = None) -> tuple:
    if not candidates:
        return None, []
    path_weights = {}
    try:
        from core.path_weight_manager import path_weight_manager
        path_weights = path_weight_manager.get_weights()
    except Exception:
        logger.warning("操作降级跳过")
    _surprise_boost = 1.0
    _deep_sources = {"Ollama", "DeepSeek", "Ollama(qwen2.5-coder:7b)", "self_reasoning", "本质推理"}
    _tool_sources = {"file_reader", "project_scanner", "code_indexer", "dependency_analyzer", "工具调用", "serial_port", "bash"}
    _query_is_tool_intent = query_needs_tools(query)
    if cbnr_ctx:
        _pred_err = cbnr_ctx.get("l1_prediction_error", 0.5)
        if cbnr_ctx.get("l1_high_surprise", False):
            _surprise_boost = 1.0 + _pred_err * 0.5
    scored = []
    for c in candidates:
        s = score_response(c, query)
        source = c.get("source", "")
        pw = path_weights.get(source, 0.1)
        s_weighted = s * (0.7 + 0.3 * pw / max(path_weights.values()) if path_weights else s)
        if _surprise_boost > 1.0 and any(ds in source for ds in _deep_sources):
            s_weighted *= _surprise_boost
        elif _surprise_boost > 1.0 and "经验池" in source:
            s_weighted *= (2.0 - _surprise_boost)
        if _query_is_tool_intent and any(ts in source for ts in _tool_sources):
            s_weighted *= 1.5
        scored.append((c, s, s_weighted))
    scored.sort(key=lambda x: x[2], reverse=True)
    best = scored[0]
    comparison = [
        {"source": c["source"], "score": round(s, 1), "weighted_score": round(ws, 1), "length": len(c.get("response", ""))}
        for c, s, ws in scored
    ]
    return best[0], comparison


async def self_verify(query: str, response: str) -> dict:
    issues = []

    if not response or len(response) < 20:
        issues.append("回复过短")
    perfunctory = ["我不知道", "无法回答", "请稍后重试", "无法访问", "无法直接", "没有能力", "不能访问", "无法获取数据",
                   "我无法访问", "我无法直接", "我不能访问", "作为ai", "作为一个ai", "作为语言模型",
                   "你需要手动", "你可以自己", "我建议你"]
    for kw in perfunctory:
        if kw in response:
            issues.append(f"包含敷衍性语言'{kw}'")
            break
    if query_needs_tools(query):
        hardware_copout = ["无法直接访问", "没有直接访问", "不能访问硬件", "无法获取", "无法访问您", "作为云端", "作为AI",
                          "我无法访问", "我无法连接", "我无法执行", "你不能", "你需要手动",
                          "你可以使用以下命令", "以下是具体步骤", "你可以尝试", "你可以这样做"]
        for kw in hardware_copout:
            if kw in response:
                issues.append(f"硬件请求被拒绝或仅给指导'{kw}'")
                break
    if any(kw in query.lower() for kw in ["如何", "怎么", "怎样", "什么是", "认知"]):
        if not any(kw in response for kw in ["因为", "所以", "例如", "包括", "方法", "步骤"]):
            issues.append("问题需要实质内容但回复缺乏深度")

    verified = len(issues) == 0
    confidence = 0.9 if verified else 0.5

    content_understanding = understand_response_content(query, response)
    is_science = content_understanding["claim_type"] == "scientific"

    education_keywords = [
        "建议", "暑假", "寒假", "学习计划", "复习", "预习", "升学", "小升初",
        "中考", "高考", "课程", "培训班", "作业", "考试", "成绩", "分数",
        "教育", "教学", "老师", "学生", "家长", "孩子", "小学", "初中",
        "高中", "幼儿园", "阅读", "写作", "作文", "背诵", "练习",
    ]
    is_education = any(kw in query for kw in education_keywords)

    history_philosophy_keywords = [
        "古文明", "文明", "历史", "朝代", "帝国", "王朝", "古代", "近代",
        "考古", "遗址", "文物", "文献", "史料", "编年", "纪年",
        "哲学", "思想", "意义", "价值", "伦理", "道德", "存在", "本质",
        "思辨", "辩证", "逻辑", "理性", "感性", "意识", "认知",
        "文化", "传统", "传承", "民俗", "信仰", "宗教", "神话",
        "社会", "制度", "政治", "经济", "法律", "治理", "组织",
        "人类", "人性", "心理", "行为", "动机", "恐惧", "希望",
        "进步", "发展", "演化", "变迁", "兴衰", "崩溃", "复兴",
    ]
    is_history_philosophy = any(kw in query for kw in history_philosophy_keywords)

    if is_education or is_history_philosophy:
        is_science = False

    try:
        from core.task_queue import task_queue
        task_queue.enqueue("model_review", {"query": query, "response": response})
    except Exception:
        logger.warning("操作降级跳过")

    return {"verified": verified, "issues": issues, "confidence": confidence, "is_science": is_science}


def cross_source_merge(query: str, sources: list, known_issues: list) -> str:
    if not sources:
        return ""

    responses = [s["response"] for s in sources]
    source_names = [s["source"] for s in sources]

    if len(sources) == 1:
        return responses[0]

    best_response = ""
    best_score = -1
    for i, resp in enumerate(responses):
        score = 0
        for j, other in enumerate(responses):
            if i == j:
                continue
            overlap_words = sum(1 for w in other[:200] if w in resp)
            score += overlap_words
        if score > best_score:
            best_score = score
            best_response = resp

    parts = [f"关于「{query}」，综合{len(sources)}个来源的交叉验证结果：\n"]
    parts.append(best_response)
    parts.append(f"\n**验证来源：** {', '.join(source_names)}")

    if known_issues:
        parts.append("\n**仍需注意的问题：**")
        for issue in known_issues[:2]:
            parts.append(f"- {issue}")

    return "\n".join(parts)


def list_divergences(query: str, sources: list) -> str:
    parts = [f"关于「{query}」，我检索到的信息存在显著分歧。以下分别罗列各方观点，供您判断：\n"]

    for i, src in enumerate(sources, 1):
        source_name = src["source"]
        response = src["response"]
        key_sentences = []
        for sent in response.replace("。", "。\n").split("\n"):
            sent = sent.strip()
            if sent and len(sent) > 10 and not sent.startswith("#") and not sent.startswith("**"):
                key_sentences.append(sent)
                if len(key_sentences) >= 3:
                    break
        parts.append(f"**观点{i}（来源：{source_name}）：**")
        for ks in key_sentences:
            parts.append(f"- {ks}")
        parts.append("")

    parts.append("---")
    parts.append("💡 以上观点来自不同来源，可能存在矛盾。建议您参考权威资料做最终判断，也欢迎继续追问，我会尝试更深入地分析。")

    return "\n".join(parts)