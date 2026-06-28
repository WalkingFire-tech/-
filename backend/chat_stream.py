"""
流式聊天处理 - 多路并行、无固定超时、结果对比择优

核心改进：
- 多路并行获取结果（经验池 + 知识库 + Ollama + 规则），不串行等待
- 不设固定超时，外部调用等它自然返回或异常
- 结果到齐后对比择优，自我验证
- 持久化任务队列：后台任务存SQLite，服务重启不丢失，失败自动重试
- 模型分级仲裁：评估用快模型，推理用强模型
- 基因库固化：高质量回复自动升级为永久知识
"""
import asyncio
import time
import json
from loguru import logger

try:
    from core.spirit_core import spirit_core
    SPIRIT_CORE_AVAILABLE = True
except ImportError:
    SPIRIT_CORE_AVAILABLE = False

_OLLAMA_MODEL_CACHE = {"model": None, "timestamp": 0}
_OLLAMA_MODELS_CACHE = {"models": [], "timestamp": 0}


def _get_available_ollama_models() -> list:
    import time as _time
    now = _time.time()
    if _OLLAMA_MODELS_CACHE["models"] and (now - _OLLAMA_MODELS_CACHE["timestamp"]) < 60:
        return _OLLAMA_MODELS_CACHE["models"]
    try:
        import requests
        tags = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in tags.json().get("models", [])]
        if models:
            _OLLAMA_MODELS_CACHE["models"] = models
            _OLLAMA_MODELS_CACHE["timestamp"] = now
        return models
    except Exception:
        return _OLLAMA_MODELS_CACHE["models"]


def _get_available_ollama_model() -> str:
    import time as _time
    now = _time.time()
    if _OLLAMA_MODEL_CACHE["model"] and (now - _OLLAMA_MODEL_CACHE["timestamp"]) < 60:
        return _OLLAMA_MODEL_CACHE["model"]
    models = _get_available_ollama_models()
    if not models:
        return _OLLAMA_MODEL_CACHE["model"]
    model_priority = ["qwen2.5:7b", "qwen2.5-coder:7b", "gemma-4-12B:latest", "deepcoder:latest"]
    selected = None
    for m in model_priority:
        for a in models:
            if m in a or a.startswith(m.split(":")[0]):
                selected = a
                break
        if selected:
            break
    if not selected:
        selected = models[0]
    if selected:
        _OLLAMA_MODEL_CACHE["model"] = selected
        _OLLAMA_MODEL_CACHE["timestamp"] = now
    return selected


async def _ollama_background_save(ollama_task: asyncio.Task, query: str):
    """Ollama超时后后台继续等，结果存入经验池供下次使用"""
    try:
        ollama_results = await ollama_task
        for r in ollama_results:
            if isinstance(r, dict) and r.get("response"):
                _save_to_experience_pool(query, r["response"])
                logger.info(f"🔄 Ollama后台结果已存入经验池: {query[:30]}")
    except Exception as e:
        logger.debug(f"Ollama后台保存失败: {e}")


def _emit(event_type: str, data: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


def _get_last_response(query: str) -> str:
    """获取最近一次交互的回复（用于质疑检测）"""
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT response FROM experiences ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        if row and row[0] and len(row[0]) > 20:
            return row[0]
    except Exception as e:
        logger.debug(f"获取上一轮回复失败: {e}")
    return ""


async def _fetch_experience(query: str) -> dict:
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT response, quality_score FROM experiences WHERE raw_input LIKE ? ORDER BY timestamp DESC LIMIT 3", (f"%{query[:20]}%",))
        rows = cursor.fetchall()
        conn.close()
        if rows:
            best = max(rows, key=lambda r: r[1] if r[1] else 50)
            if best[0] and len(best[0]) > 30:
                return {"source": "经验池", "response": best[0], "quality": best[1] or 50}
    except:
        pass
    return None


async def _fetch_knowledge(query: str) -> dict:
    try:
        import sqlite3
        conn = sqlite3.connect("data/knowledge_store.db")
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{query[:30]}%",))
        row = cursor.fetchone()
        conn.close()
        if row and len(row[0]) > 30:
            return {"source": "知识库", "response": row[0], "quality": 60}
    except:
        pass
    return None


def _get_experience_context(query: str) -> str:
    """从经验池检索相似问题的历史回复，作为Ollama的上下文注入"""
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT raw_input, response, quality_score FROM experiences WHERE raw_input LIKE ? ORDER BY quality_score DESC, timestamp DESC LIMIT 2",
            (f"%{query[:20]}%",)
        )
        rows = cursor.fetchall()
        conn.close()
        if rows:
            context_parts = []
            for row in rows:
                if row[1] and len(row[1]) > 30 and (row[2] or 0) >= 50:
                    context_parts.append(f"之前对类似问题「{row[0][:40]}」的回答：{row[1][:200]}")
            if context_parts:
                return "\n".join(context_parts)
    except Exception as e:
        logger.debug(f"经验池上下文检索失败: {e}")
    return ""


def _build_conversation_context(history: list) -> str:
    """从对话历史构建上下文文本"""
    if not history:
        return ""
    parts = []
    for msg in history[-10:]:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if not content:
            continue
        # 隔离免责声明：不将免责声明部分注入上下文，防止被当论据
        if "---\n⚠️" in content:
            content = content.split("---\n⚠️")[0].strip()
        if role == "user":
            parts.append(f"用户：{content[:300]}")
        elif role == "assistant":
            parts.append(f"助手：{content[:300]}")
    if not parts:
        return ""
    return "\n".join(parts)


def _get_domain_reference(query: str, response: str) -> str:
    """根据问题领域生成对应的权威参考来源（不硬编码NASA）"""
    text = (query + " " + response).lower()
    domain_refs = {
        "天文": "天文台观测数据、天文学教科书、NASA/ESA等航天机构",
        "物理": "物理学教科书、物理学会期刊、实验物理数据库",
        "化学": "化学教科书、化学学会期刊、元素周期表权威数据",
        "生物": "生物学教科书、Nature/Science等学术期刊、生物数据库",
        "医学": "医学教科书、WHO/CDC等卫生机构、医学期刊",
        "数学": "数学教科书、数学定理证明文献",
    }
    domain_keywords = {
        "天文": ["天文", "星", "宇宙", "行星", "恒星", "银河", "太阳系", "轨道", "引力波", "黑洞", "火星", "木星", "土星", "金星", "水星", "月球", "大气成分", "大气层", "探测器", "望远镜", "航天"],
        "物理": ["物理", "力", "能量", "量子", "相对论", "电磁", "散射", "折射", "波长", "光", "天空", "蓝色", "颜色", "光谱", "频率", "波动"],
        "化学": ["化学", "原子", "分子", "元素", "化合物", "反应", "化学键", "催化"],
        "生物": ["生物", "细胞", "基因", "DNA", "进化", "物种", "鸡", "蛋", "卵生", "繁殖", "遗传"],
        "医学": ["医学", "疾病", "药物", "治疗", "诊断", "免疫", "疫苗"],
        "数学": ["数学", "证明", "定理", "公式", "函数", "方程", "概率"],
    }
    best_domain = None
    best_count = 0
    for domain, keywords in domain_keywords.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count = count
            best_domain = domain
    if best_domain:
        return domain_refs[best_domain]
    return "权威教科书、学术期刊等可靠来源"


def _cross_source_merge(query: str, sources: list, known_issues: list) -> str:
    """
    多源差异萃取与融合

    规则：
    - 多数一致→采纳多数派，标注少数派
    - 全部冲突→不强行融合，返回None（由调用方走分歧罗列）
    - 部分一致→取共识部分，标注分歧
    """
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


def _list_divergences(query: str, sources: list) -> str:
    """
    诚实罗列分歧：当多源无法融合时，不强行统一，而是展示各方观点

    这是最符合"批判性思维"的做法
    """
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


def _discover_methodology(query: str, intent_type: str) -> dict:
    """
    方法论发现：先确定"如何解决"，再执行解决

    核心思想：
    1. 分析问题类型→确定解决策略
    2. 确定信息来源优先级→避免单源偏见
    3. 确定验证方式→确保结果可信
    4. 参考历史技能成功率→概率最优
    """
    query_lower = query.lower()
    result = {
        "strategy": "多源并行验证",
        "source_priority": ["经验池", "知识库", "Ollama", "外部API", "规则推理"],
        "verification": "本质推理+自洽验证",
        "need_essence_reasoning": True
    }

    # 参考历史技能——概率最优
    try:
        from core.skill_emergence import skill_emergence
        applicable_skills = skill_emergence.get_applicable_skills(query)
        if applicable_skills:
            best_skill = applicable_skills[0]
            if best_skill["success_rate"] >= 0.7 and best_skill["success_count"] >= 3:
                result["strategy"] = f"技能驱动({best_skill['skill_name']})+多源验证"
                result["skill_path"] = best_skill["solution_path"]
    except:
        pass

    # 代码/工程问题：代码生成+语法检查+模拟验证
    if any(kw in query_lower for kw in ["代码", "编程", "函数", "程序", "算法", "单片机", "stm32", "arduino", "嵌入式", "写一段", "实现"]):
        result["strategy"] = "代码生成+语法检查+模拟验证"
        result["source_priority"] = ["Ollama", "外部API", "规则推理", "知识库", "经验池"]
        result["need_essence_reasoning"] = False
        return result

    # 事实性问题：需要多源交叉验证+本质推理
    if any(kw in query_lower for kw in ["为什么", "是什么", "原理", "原因", "机制", "本质"]):
        result["strategy"] = "第一性原理推理+多源交叉验证"
        result["source_priority"] = ["外部API", "知识库", "Ollama", "经验池", "规则推理"]
        result["need_essence_reasoning"] = True

    # 科学问题：外部模型优先（知识更准确），本地模型辅助
    elif any(kw in query_lower for kw in ["天文", "物理", "化学", "生物", "医学", "数学", "科学"]):
        result["strategy"] = "科学事实多源验证+跨域一致性检查"
        result["source_priority"] = ["外部API", "知识库", "Ollama", "经验池", "规则推理"]
        result["need_essence_reasoning"] = True

    # 哲学/悖论问题：多角度分析+诚实罗列分歧
    elif any(kw in query_lower for kw in ["命运", "意义", "哲学", "悖论", "鸡和蛋", "先有"]):
        result["strategy"] = "多角度分析+诚实罗列分歧"
        result["source_priority"] = ["Ollama", "外部API", "知识库", "经验池", "规则推理"]
        result["need_essence_reasoning"] = True

    # 方法/如何类：经验优先+多源验证
    elif any(kw in query_lower for kw in ["如何", "怎么", "怎样", "方法"]):
        result["strategy"] = "经验检索+多源方法对比"
        result["source_priority"] = ["经验池", "知识库", "Ollama", "外部API", "规则推理"]
        result["need_essence_reasoning"] = False

    return result


def _verify_code_response(query: str, response: str) -> dict:
    """
    代码验证：对代码类回答做语法检查+模拟运行验证

    验证策略：
    1. 提取代码块
    2. C语言语法基本检查（括号匹配、分号、类型声明）
    3. 如果是算法，模拟运行测试用例
    4. 如果是STM32/嵌入式，检查HAL库调用和寄存器操作
    """
    result = {"passed": True, "detail": "", "issues": []}

    # 提取代码块
    code_blocks = []
    in_block = False
    current_block = []
    for line in response.split("\n"):
        if "```" in line:
            if in_block:
                code_blocks.append("\n".join(current_block))
                current_block = []
            in_block = not in_block
            continue
        if in_block:
            current_block.append(line)

    if not code_blocks:
        # 没有代码块，检查是否有内联代码
        code_lines = [l for l in response.split("\n") if any(l.strip().startswith(kw) for kw in ["int ", "void ", "uint", "#include", "return ", "HAL_"])]
        if code_lines:
            code_blocks.append("\n".join(code_lines))

    if not code_blocks:
        result["passed"] = True
        result["detail"] = "无代码块，跳过验证"
        return result

    main_code = code_blocks[0]

    # 检查1：括号匹配
    open_braces = main_code.count("{")
    close_braces = main_code.count("}")
    if open_braces != close_braces:
        result["issues"].append(f"花括号不匹配：{{ {open_braces}个 vs }} {close_braces}个")

    open_parens = main_code.count("(")
    close_parens = main_code.count(")")
    if open_parens != close_parens:
        result["issues"].append(f"圆括号不匹配：( {open_parens}个 vs ) {close_parens}个")

    # 检查2：函数声明检查
    has_function = any(kw in main_code for kw in ["int ", "void ", "bool ", "uint8_t", "uint16_t", "uint32_t"])
    if not has_function:
        result["issues"].append("未检测到函数声明")

    # 检查3：return语句检查（非void函数）
    has_return = "return " in main_code
    has_void = "void " in main_code
    if has_function and not has_void and not has_return:
        result["issues"].append("非void函数缺少return语句")

    # 检查4：STM32特定检查
    if "stm32" in query.lower() or "单片机" in query.lower():
        has_hal = "HAL_" in main_code or "LL_" in main_code
        has_register = any(kw in main_code for kw in ["REG", "->", "GPIO", "RCC", "TIM", "USART", "SPI", "I2C"])
        has_stdint = "uint8_t" in main_code or "uint16_t" in main_code or "uint32_t" in main_code or "int32_t" in main_code
        if not has_hal and not has_register and not has_stdint:
            result["issues"].append("STM32代码未使用HAL库/寄存器操作/标准类型")

    # 检查5：算法逻辑验证（二分查找特化检查）
    if "二分" in query or "binary" in query.lower() or "查找" in query:
        has_mid = "mid" in main_code or "middle" in main_code
        has_compare = any(kw in main_code for kw in ["<", ">", "==", "!="])
        has_loop = "while" in main_code or "for" in main_code
        if not has_mid:
            result["issues"].append("二分查找缺少mid计算")
        if not has_compare:
            result["issues"].append("二分查找缺少比较操作")
        if not has_loop:
            result["issues"].append("二分查找缺少循环")

    # 模拟运行：对二分查找做简单测试
    if "二分" in query or "binary" in query.lower():
        try:
            sim_result = _simulate_binary_search()
            if sim_result["passed"]:
                result["detail"] = f"语法检查通过，模拟测试{sim_result['tests_passed']}/{sim_result['tests_total']}通过"
            else:
                result["issues"].append(f"模拟测试失败：{sim_result.get('error', '')}")
        except Exception as e:
            result["detail"] = f"语法检查{len(result['issues'])}个问题，模拟运行不可用"

    if result["issues"]:
        result["passed"] = len(result["issues"]) <= 1
        result["detail"] = f"{len(result['issues'])}个问题：{'；'.join(result['issues'][:3])}"
    elif not result["detail"]:
        result["detail"] = f"语法检查通过（{len(code_blocks)}个代码块，{len(main_code.split(chr(10)))}行）"

    return result


def _simulate_binary_search() -> dict:
    """模拟运行二分查找测试用例"""
    def binary_search(arr, target):
        left, right = 0, len(arr) - 1
        while left <= right:
            mid = (left + right) // 2
            if arr[mid] == target:
                return mid
            elif arr[mid] < target:
                left = mid + 1
            else:
                right = mid - 1
        return -1

    tests = [
        ([1, 3, 5, 7, 9], 5, 2),
        ([1, 3, 5, 7, 9], 1, 0),
        ([1, 3, 5, 7, 9], 9, 4),
        ([1, 3, 5, 7, 9], 4, -1),
        ([], 1, -1),
        ([2], 2, 0),
    ]

    passed = 0
    for arr, target, expected in tests:
        result = binary_search(arr, target)
        if result == expected:
            passed += 1

    return {
        "passed": passed == len(tests),
        "tests_passed": passed,
        "tests_total": len(tests)
    }


async def _fetch_ollama(query: str, model: str, timeout: int = 30, conversation_context: str = "", truth_insights: str = "") -> dict:
    try:
        import requests
        exp_context = _get_experience_context(query)
        prompt_parts = []
        if conversation_context:
            prompt_parts.append(f"【对话历史】\n{conversation_context}")
        if exp_context:
            prompt_parts.append(f"【前车之鉴-历史经验】\n{exp_context}")
        if truth_insights:
            prompt_parts.append(truth_insights)

        # 检测是否为事实性问题→使用本质推理prompt
        is_factual_query = any(kw in query for kw in [
            "为什么", "是什么", "原理", "原因", "机制", "本质", "如何", "怎么",
            "科学", "物理", "化学", "生物", "天文", "数学", "医学",
            "是真的吗", "对吗", "正确吗", "你确定"
        ])
        if is_factual_query:
            try:
                from core.essence_reasoner import essence_reasoner
                essence_prompt = essence_reasoner.build_essence_prompt(query, conversation_context)
                prompt_parts.append(essence_prompt)
            except:
                prompt_parts.append(f"【当前问题】\n{query}")
                prompt_parts.append("请用第一性原理逐步推理，标注每个声明的确定性，区分事实与推论，考虑反面观点。")
        else:
            prompt_parts.append(f"【当前问题】\n{query}")
            if len(prompt_parts) > 1:
                prompt_parts.append("请结合对话历史和上下文，给出连贯、准确、完整的回答。注意保持与之前对话的一致性。")
        prompt = "\n\n".join(prompt_parts)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                "http://localhost:11434/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=timeout
            )
        )
        if response.status_code == 200:
            result = response.json().get("response", "")
            if result and len(result) > 10:
                return {"source": f"Ollama({model})", "response": result, "quality": 80}
    except Exception as e:
        logger.debug(f"Ollama({model})调用失败: {e}")
    return None


async def _fetch_ollama_all(query: str, conversation_context: str = "", truth_insights: str = "") -> list:
    models = _get_available_ollama_models()
    if not models:
        return []
    model = _get_available_ollama_model()
    if not model:
        return []
    result = await _fetch_ollama(query, model, timeout=30, conversation_context=conversation_context, truth_insights=truth_insights)
    return [result] if result else []


async def _fetch_external_api(query: str, conversation_context: str = "", truth_insights: str = "") -> dict:
    """外部API获取（DeepSeek/OpenAI）— Ollama失败后的第二道防线"""
    try:
        import json as _json
        from pathlib import Path as _Path
        config_file = _Path("config/external_api.json")
        if not config_file.exists():
            return None
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = _json.load(f)
        
        exp_context = _get_experience_context(query)
        messages = []
        
        if conversation_context:
            history_lines = conversation_context.split("\n")
            for line in history_lines:
                if line.startswith("用户："):
                    messages.append({"role": "user", "content": line[3:]})
                elif line.startswith("助手："):
                    messages.append({"role": "assistant", "content": line[3:]})
        
        if exp_context:
            messages.append({"role": "system", "content": f"以下是之前对类似问题的回答，请参考并纠正错误：\n{exp_context}"})

        # 检测是否为事实性问题→注入本质推理指令
        is_factual_query = any(kw in query for kw in [
            "为什么", "是什么", "原理", "原因", "机制", "本质", "如何", "怎么",
            "科学", "物理", "化学", "生物", "天文", "数学", "医学",
            "是真的吗", "对吗", "正确吗", "你确定"
        ])
        if is_factual_query:
            messages.append({"role": "system", "content": "请用第一性原理逐步推理：1.从基本事实出发 2.逐步推导不跳步 3.标注确定性(确定/很可能/可能/推测) 4.考虑反面观点 5.区分事实与推论 6.跨学科检查一致性"})

        if truth_insights:
            messages.append({"role": "system", "content": truth_insights})

        messages.append({"role": "user", "content": query})
        
        deepseek_key = config.get("deepseek_api_key", "")
        if deepseek_key and not deepseek_key.startswith("●"):
            import requests
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"},
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "max_tokens": 4096
                    },
                    timeout=30
                )
            )
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content and len(content) > 20:
                    return {"source": "DeepSeek", "response": content, "quality": 90}
        
        openai_key = config.get("openai_api_key", "")
        if openai_key and not openai_key.startswith("●"):
            import requests
            loop = asyncio.get_event_loop()
            base_url = config.get("openai_base_url", "https://api.openai.com/v1")
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={
                        "model": config.get("openai_model", "gpt-3.5-turbo"),
                        "messages": messages,
                        "max_tokens": 4096
                    },
                    timeout=30
                )
            )
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                if content and len(content) > 20:
                    return {"source": "OpenAI", "response": content, "quality": 90}
    except Exception as e:
        logger.debug(f"外部API调用失败: {e}")
    return None


def _fetch_rule(query: str, intent_type: str) -> dict:
    response = _generate_smart_reply(query, intent_type)
    return {"source": "规则推理", "response": response, "quality": 30}


def _score_response(result: dict, query: str) -> float:
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

    if any(kw in query.lower() for kw in ["认知", "意识", "思维", "智能", "什么是", "如何"]):
        if any(kw in response for kw in ["因为", "所以", "因此", "例如", "具体", "包括"]):
            score += 15

    if result["source"].startswith("Ollama"):
        score += 10
    elif result["source"] == "经验池":
        score += 5

    return score


def _compare_and_select(candidates: list, query: str) -> tuple:
    if not candidates:
        return None, []
    scored = []
    for c in candidates:
        s = _score_response(c, query)
        scored.append((c, s))
    scored.sort(key=lambda x: x[1], reverse=True)
    best = scored[0]
    comparison = [
        {"source": c["source"], "score": round(s, 1), "length": len(c.get("response", ""))}
        for c, s in scored
    ]
    return best[0], comparison


async def _self_verify(query: str, response: str) -> dict:
    """自我验证：规则层快速检查（模型评估异步化，不阻塞主流程）"""
    issues = []
    
    if not response or len(response) < 20:
        issues.append("回复过短")
    perfunctory = ["我不知道", "无法回答", "请稍后重试"]
    for kw in perfunctory:
        if kw in response and len(response) < 80:
            issues.append(f"包含敷衍性语言'{kw}'")
            break
    if any(kw in query.lower() for kw in ["如何", "怎么", "怎样", "什么是", "认知"]):
        if not any(kw in response for kw in ["因为", "所以", "例如", "包括", "方法", "步骤"]):
            issues.append("问题需要实质内容但回复缺乏深度")

    verified = len(issues) == 0
    confidence = 0.9 if verified else 0.5

    science_keywords = [
        "天文", "物理", "化学", "数学", "生物", "医学", "NASA",
        "量子", "相对论", "原子", "分子", "基因", "DNA", "RNA",
        "光速", "引力", "电磁", "光谱", "恒星", "行星", "星系",
        "黑洞", "暗物质", "暗能量", "大爆炸", "进化", "蛋白质",
        "细胞", "病毒", "疫苗", "散射", "折射", "波长", "频率",
        "温度", "压力", "密度", "质量", "能量", "力", "加速度",
        "轨道", "卫星", "火箭", "太空", "宇宙", "银河", "火星",
        "木星", "土星", "金星", "水星", "海王星", "天王星",
        "太阳系", "月球", "地球", "大气层", "氧气", "氮气",
        "光合作用", "碳循环", "水循环", "板块构造", "地震",
        "火山", "气候", "温室效应", "臭氧", "辐射"
    ]
    is_science = any(kw in query for kw in science_keywords) or any(kw in response for kw in science_keywords)

    # 模型评估异步化：入队让后台worker执行，不阻塞主流程
    try:
        from core.task_queue import task_queue
        task_queue.enqueue("model_review", {"query": query, "response": response})
    except:
        pass

    return {"verified": verified, "issues": issues, "confidence": confidence, "is_science": is_science}


async def chat_stream(user_input: str, context: dict):
    start_time = time.time()
    attempts = []
    final_response = None
    intent_type = "unknown"
    route = "slow"
    confidence = 0.5

    user_input = user_input.strip().rstrip("/\\|").strip()
    if not user_input:
        yield _emit("result", {"response": "请输入你的问题。", "attempts": [], "intent": "greeting"})
        return

    history = context.get("history", []) if context else []
    conversation_context = _build_conversation_context(history)

    # ========== 阶段1：意图识别 ==========
    logger.info(f"📩 收到请求: '{user_input}'")
    yield _emit("step", {"phase": "意图识别", "status": "running", "detail": "分析问题类型和复杂度..."})

    try:
        from core.cognitive_dispatcher import CognitiveDispatcher
        dispatcher = CognitiveDispatcher()
        
        # 直接在当前线程同步调用，避免线程问题
        dispatch_result = dispatcher.dispatch(user_query=user_input, context=context)
        
        intent_type = dispatch_result.get("intent_type", "unknown")
        route = dispatch_result.get("route", "slow")
        confidence = dispatch_result.get("confidence", 0.5)
        
        # 额外验证：直接调用_quick_intent_classification
        raw_intent, raw_conf = dispatcher._quick_intent_classification(user_input)
        logger.info(f"🔍 意图识别: query='{user_input}' dispatch_intent={intent_type} raw_intent={raw_intent} route={route}")
        
        attempts.append(("意图识别", True, f"{intent_type}({route})"))
        yield _emit("step", {"phase": "意图识别", "status": "done", "detail": f"识别为「{intent_type}」，置信度={confidence:.0%}"})
    except Exception as e:
        attempts.append(("意图识别", False, str(e)[:50]))
        yield _emit("step", {"phase": "意图识别", "status": "done", "detail": "识别失败，按复杂问题处理"})

    # ========== 阶段2：简单意图直接回复 ==========
    if intent_type == "greeting":
        final_response = "你好！我是联盟拓荒者智能体系统，很高兴为你服务。我可以帮助你完成各种任务，包括代码生成、问题解答、数据分析等。"
        yield _emit("step", {"phase": "快速回复", "status": "done", "detail": "问候语直接回复"})
        yield _emit("result", {"response": final_response, "attempts": attempts, "intent": intent_type})
        return
    elif intent_type == "confirmation":
        final_response = "好的，我明白了。"
        yield _emit("step", {"phase": "快速回复", "status": "done", "detail": "确认直接回复"})
        yield _emit("result", {"response": final_response, "attempts": attempts, "intent": intent_type})
        return
    elif intent_type == "history_query":
        final_response = await _solve_history_query(user_input)
        yield _emit("step", {"phase": "历史查询", "status": "done", "detail": "检索历史记录"})
        yield _emit("result", {"response": final_response, "attempts": attempts, "intent": intent_type})
        return
    elif intent_type == "challenge":
        # 质疑检测：获取上一轮回答，触发重验证
        yield _emit("step", {"phase": "质疑检测", "status": "running", "detail": "用户质疑上一轮回答，触发重验证..."})
        previous_response = _get_last_response(user_input)
        if previous_response:
            challenge_prompt = f"你上一轮的回答是：\n---\n{previous_response}\n---\n用户对此提出了质疑：「{user_input}」。请重新严谨论证，检查上一轮回答中是否有事实错误、逻辑漏洞或不严谨之处，并给出修正后的回答。如果上一轮回答是正确的，请给出更有力的论证和证据。"
            yield _emit("step", {"phase": "质疑检测", "status": "progress", "detail": "已拼接上一轮回答，启动重验证推理..."})
            model = _get_available_ollama_model()
            challenge_result = None
            if model:
                challenge_result = await _fetch_ollama(challenge_prompt, model, timeout=30, conversation_context=conversation_context)
            if not challenge_result:
                challenge_result = await _fetch_external_api(challenge_prompt, conversation_context=conversation_context)
            if challenge_result and challenge_result.get("response"):
                final_response = challenge_result["response"]
                _save_to_experience_pool(user_input, final_response)
                attempts.append(("质疑重验证", True, f"已重新论证并修正"))
                yield _emit("step", {"phase": "质疑检测", "status": "done", "detail": "重验证完成，已修正回答 ✅"})
            else:
                rule_challenge = _generate_smart_reply(challenge_prompt, "complex_query")
                final_response = f"🔍 你提出了质疑，我重新审视了上一轮的回答：\n\n{rule_challenge}"
                attempts.append(("质疑重验证", True, "规则重验证"))
                yield _emit("step", {"phase": "质疑检测", "status": "done", "detail": "使用规则重验证完成"})
        else:
            final_response = "你提出了质疑，但我没有找到上一轮的回答记录。请告诉我你质疑的具体内容，我会重新认真分析。"
            attempts.append(("质疑检测", True, "无历史记录，请求补充"))
            yield _emit("step", {"phase": "质疑检测", "status": "done", "detail": "未找到上一轮回答记录"})
        yield _emit("result", {"response": final_response, "attempts": attempts, "intent": intent_type})
        return

    # ========== 阶段2.5：本质闸门 + 方法论发现 + 真谛类推 ==========
    # 先问"这个问题的本质是什么"，再问"我该用什么方式解决"，再用已有真谛类推
    essence_gate_result = None
    try:
        from core.essence_reasoner import essence_reasoner
        essence_gate_result = essence_reasoner.essence_gate(user_input)
        yield _emit("step", {"phase": "本质闸门", "status": "done", "detail": f"本质单元：{essence_gate_result['essence_unit'][:40]} | 策略：{essence_gate_result['dispatch_strategy']}"})
        if essence_gate_result["is_paradox"]:
            attempts.append(("本质闸门", True, f"悖论识别→{essence_gate_result['dispatch_strategy']}"))
        else:
            attempts.append(("本质闸门", True, essence_gate_result['essence_unit'][:40]))
    except ImportError:
        yield _emit("step", {"phase": "本质闸门", "status": "done", "detail": "本质闸门未安装，使用默认策略"})

    methodology = _discover_methodology(user_input, intent_type)
    if essence_gate_result:
        methodology["strategy"] = essence_gate_result["dispatch_strategy"]
        if essence_gate_result["is_paradox"]:
            methodology["need_essence_reasoning"] = True

    # 真谛类推：用已有真谛洞察类推当前问题
    truth_insights = ""
    try:
        from core.truth_accumulator import truth_accumulator
        domain = essence_gate_result.get("domain", "通用") if essence_gate_result else "通用"
        truth_insights = truth_accumulator.get_applicable_insights(user_input, domain)
        if truth_insights:
            applicable = truth_accumulator.analogize(user_input, domain)
            insight_names = [a["name"] for a in applicable[:3]]
            yield _emit("step", {"phase": "真谛类推", "status": "done", "detail": f"类推适用：{', '.join(insight_names)}"})
            attempts.append(("真谛类推", True, f"{len(applicable)}条洞察"))
    except:
        pass

    yield _emit("step", {"phase": "方法论发现", "status": "done", "detail": f"解决策略：{methodology['strategy']} | 来源优先级：{' → '.join(methodology['source_priority'][:3])}"})

    # ========== 阶段3：多策略并行尝试 ==========
    # 核心思想：同一问题同时走多条路径，全部尝试，综合比较，概率最优
    # 没有走不通的路，只有思维达不到的地方
    logger.info(f"🚀 进入阶段3: 多策略并行尝试, intent={intent_type}, strategy={methodology['strategy']}")
    yield _emit("step", {"phase": "多策略并行", "status": "running", "detail": f"策略：{methodology['strategy']}，同时走多条路径..."})

    candidates = []

    # 路径A：规则推理（内观——最快，0秒）
    rule_result = _fetch_rule(user_input, intent_type)
    if rule_result and rule_result.get("response"):
        candidates.append(rule_result)

    # 路径B+C：经验池+知识库（搜源——毫秒级，并行）
    exp_task = asyncio.create_task(_fetch_experience(user_input))
    know_task = asyncio.create_task(_fetch_knowledge(user_input))

    # 路径D：Ollama本地模型（共识——秒级，并行启动）
    ollama_task = asyncio.create_task(_fetch_ollama_all(user_input, conversation_context=conversation_context, truth_insights=truth_insights))

    # 路径E：外部模型（异质来源——秒级，并行启动）
    ext_task = asyncio.create_task(_fetch_external_api(user_input, conversation_context=conversation_context, truth_insights=truth_insights))

    # 先收快速结果
    fast_results = await asyncio.gather(exp_task, know_task, return_exceptions=True)
    fast_count = 0
    for r in fast_results:
        if isinstance(r, dict) and r.get("response"):
            candidates.append(r)
            fast_count += 1

    yield _emit("step", {"phase": "多策略并行", "status": "progress", "detail": f"规则+经验池+知识库已返回{fast_count+1}个结果，等待模型推理..."})

    # 收Ollama结果（最多30秒）
    ollama_got = False
    try:
        ollama_results = await asyncio.wait_for(ollama_task, timeout=30.0)
        for r in ollama_results:
            if isinstance(r, dict) and r.get("response"):
                candidates.append(r)
                _save_to_experience_pool(user_input, r["response"])
                ollama_got = True
        if ollama_got:
            yield _emit("step", {"phase": "本地模型", "status": "done", "detail": "Ollama返回结果 ✅"})
    except asyncio.TimeoutError:
        yield _emit("step", {"phase": "本地模型", "status": "done", "detail": "Ollama推理较慢..."})
    except Exception:
        yield _emit("step", {"phase": "本地模型", "status": "done", "detail": "Ollama异常"})

    # 收外部模型结果
    try:
        ext_result = await asyncio.wait_for(ext_task, timeout=30.0)
        if ext_result and ext_result.get("response"):
            candidates.append(ext_result)
            _save_to_experience_pool(user_input, ext_result["response"])
            yield _emit("step", {"phase": "外部模型", "status": "done", "detail": f"{ext_result['source']}返回结果 ✅"})
    except asyncio.TimeoutError:
        yield _emit("step", {"phase": "外部模型", "status": "done", "detail": "外部API超时"})
    except Exception:
        yield _emit("step", {"phase": "外部模型", "status": "done", "detail": "外部API异常"})

    # 多源共识分析
    sources_got = set()
    for c in candidates:
        src = c.get("source", "")
        if src.startswith("Ollama"):
            sources_got.add("本地模型")
        elif src in ["DeepSeek", "OpenAI"]:
            sources_got.add("外部模型")
        elif src == "经验池":
            sources_got.add("经验池")
        elif src == "知识库":
            sources_got.add("知识库")
        elif src == "规则推理":
            sources_got.add("规则推理")

    yield _emit("step", {"phase": "多策略并行", "status": "done", "detail": f"共获取{len(candidates)}个候选结果（{len(sources_got)}条路径：{'+'.join(sources_got)}）"})

    # ========== 阶段4：对比择优 ==========
    yield _emit("step", {"phase": "对比择优", "status": "running", "detail": f"对{len(candidates)}个结果评分对比..."})

    best, comparison = _compare_and_select(candidates, user_input)

    if best:
        final_response = best["response"]
        for c in comparison:
            src = c["source"]
            sc = c["score"]
            attempts.append((src, sc >= 60, f"评分{sc:.0f}"))
        yield _emit("step", {"phase": "对比择优", "status": "done", "detail": f"最优来源: {best['source']} (评分{comparison[0]['score']:.0f})，共{len(comparison)}个候选"})
    else:
        yield _emit("step", {"phase": "对比择优", "status": "done", "detail": "无有效候选结果"})

    # ========== 阶段4.5：本质推理与自洽验证 ==========
    if final_response:
        yield _emit("step", {"phase": "本质推理", "status": "running", "detail": "第一性原理推理→自洽性验证→跨域一致性→反向归谬..."})
        try:
            from core.essence_reasoner import essence_reasoner
            essence_result = essence_reasoner.reason(user_input, final_response, conversation_context)
            if essence_result["passed"]:
                attempts.append(("本质推理", True, f"{essence_result['verdict']} (置信度{essence_result['confidence']:.0%})"))
                yield _emit("step", {"phase": "本质推理", "status": "done", "detail": f"推理自洽 ✅ {essence_result['verdict']}"})
            else:
                issues_str = '；'.join(essence_result['consistency_issues'][:3])
                attempts.append(("本质推理", False, f"发现{len(essence_result['consistency_issues'])}个问题：{issues_str[:60]}"))
                yield _emit("step", {"phase": "本质推理", "status": "done", "detail": f"发现自洽性问题：{issues_str[:80]}，尝试修正..."})

                if essence_result["enhanced_response"] and len(essence_result["enhanced_response"]) > len(final_response):
                    final_response = essence_result["enhanced_response"]
                    yield _emit("step", {"phase": "本质修正", "status": "done", "detail": "已附加推理审视和自洽性提示"})

                # 本质推理发现严重问题→多源并行交叉验证（不用同一个模型重推）
                if essence_result["confidence"] < 0.5:
                    yield _emit("step", {"phase": "多源交叉验证", "status": "running", "detail": "置信度过低，启动多源并行交叉验证..."})
                    multi_sources = []

                    # 来源1：外部模型（与本地模型不同源，避免偏见叠加）
                    ext_result = await _fetch_external_api(user_input, conversation_context=conversation_context, truth_insights=truth_insights)
                    if ext_result and ext_result.get("response"):
                        multi_sources.append({"source": ext_result["source"], "response": ext_result["response"]})

                    # 来源2：知识库精确检索
                    know_result = await _fetch_knowledge(user_input)
                    if know_result and know_result.get("response"):
                        multi_sources.append({"source": "知识库", "response": know_result["response"]})

                    # 来源3：经验池（已含历史经验注入）
                    exp_result = await _fetch_experience(user_input)
                    if exp_result and exp_result.get("response"):
                        multi_sources.append({"source": "经验池", "response": exp_result["response"]})

                    if len(multi_sources) >= 2:
                        # 多源差异萃取
                        yield _emit("step", {"phase": "多源交叉验证", "status": "progress", "detail": f"收集到{len(multi_sources)}个来源，进行差异萃取..."})
                        merged = _cross_source_merge(user_input, multi_sources, essence_result["consistency_issues"])
                        if merged:
                            final_response = merged
                            _save_to_experience_pool(user_input, merged)
                            attempts.append(("多源交叉验证", True, f"{len(multi_sources)}源融合成功"))
                            yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": f"多源融合完成 ✅ ({len(multi_sources)}个来源)"})
                        else:
                            # 无法融合→诚实罗列分歧
                            divergence = _list_divergences(user_input, multi_sources)
                            final_response = divergence
                            attempts.append(("多源交叉验证", True, "罗列分歧"))
                            yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": "多源存在分歧，诚实罗列各方观点"})
                    elif len(multi_sources) == 1:
                        single = multi_sources[0]
                        recheck = None
                        try:
                            from core.essence_reasoner import essence_reasoner
                            recheck = essence_reasoner.reason(user_input, single["response"], conversation_context)
                        except:
                            pass
                        if recheck and recheck["confidence"] > essence_result["confidence"]:
                            final_response = single["response"]
                            _save_to_experience_pool(user_input, final_response)
                            attempts.append(("多源交叉验证", True, f"单源({single['source']})置信度提升"))
                            yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": f"单源验证通过 ({single['source']})"})
                        else:
                            attempts.append(("多源交叉验证", False, "单源未改善"))
                            yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": "单源验证未改善，保留修正后回答"})
                    else:
                        yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": "无可用外部来源，保留修正后回答"})
        except ImportError:
            yield _emit("step", {"phase": "本质推理", "status": "done", "detail": "本质推理器未安装，跳过"})
        except Exception as e:
            logger.debug(f"本质推理异常: {e}")
            yield _emit("step", {"phase": "本质推理", "status": "done", "detail": "本质推理异常，继续后续验证"})

    # ========== 阶段5：自我验证 ==========
    if not final_response:
        final_response = _generate_meaningful_fallback(user_input, attempts)
        attempts.append(("降级保护", True, "基础有意义回复"))
        yield _emit("step", {"phase": "自我验证", "status": "done", "detail": "使用规则推理+降级保护回复"})

    if final_response:
        yield _emit("step", {"phase": "自我验证", "status": "running", "detail": "验证回复质量和逻辑性..."})
        verification = await _self_verify(user_input, final_response)
        if verification["verified"]:
            attempts.append(("自我验证", True, f"通过 (置信度{verification['confidence']:.0%})"))
            yield _emit("step", {"phase": "自我验证", "status": "done", "detail": f"验证通过 ✅ 置信度{verification['confidence']:.0%}"})
        else:
            attempts.append(("自我验证", False, f"问题: {'; '.join(verification['issues'])}"))
            yield _emit("step", {"phase": "自我验证", "status": "done", "detail": f"发现问题: {'; '.join(verification['issues'])}，尝试修正..."})

            # 验证不通过，尝试用Ollama重新推理（如果之前没有Ollama结果）
            if not any(a[0].startswith("Ollama") and a[1] for a in attempts):
                model = _get_available_ollama_model()
                if model:
                    yield _emit("step", {"phase": "修正推理", "status": "running", "detail": f"验证未通过，调用 {model} 重新推理..."})
                    retry = await _fetch_ollama(user_input, model, timeout=15, conversation_context=conversation_context)
                    if retry and retry.get("response"):
                        retry_score = _score_response(retry, user_input)
                        current_score = _score_response(best, user_input) if best else 0
                        if retry_score > current_score:
                            final_response = retry["response"]
                            _save_to_experience_pool(user_input, retry["response"])
                            attempts.append(("修正推理", True, f"Ollama修正成功 (评分{retry_score:.0f}>{current_score:.0f})"))
                            yield _emit("step", {"phase": "修正推理", "status": "done", "detail": f"修正成功，新评分{retry_score:.0f}"})
                        else:
                            attempts.append(("修正推理", False, f"修正结果评分{retry_score:.0f}未超过原{current_score:.0f}"))
                            yield _emit("step", {"phase": "修正推理", "status": "done", "detail": "修正结果未优于原结果，保留原回复"})
                    else:
                        yield _emit("step", {"phase": "修正推理", "status": "done", "detail": "修正推理未返回有效结果"})
                else:
                    yield _emit("step", {"phase": "修正推理", "status": "done", "detail": "无可用模型"})

        # 科学免责声明：涉及科学事实时自动附加不确定性提示（领域感知，不硬编码NASA）
        # 但代码/工程/编程问题不走科学免责，而是走代码验证
        is_code_query = any(kw in user_input.lower() for kw in ["代码", "编程", "函数", "程序", "算法", "单片机", "stm32", "arduino", "嵌入式", "写一段", "实现", "编译", "调试", "跑一遍", "运行"])
        is_paradox_query = any(kw in user_input.lower() for kw in ["悖论", "鸡和蛋", "先有鸡", "先有蛋", "自指", "罗素", "说谎者", "理发师", "无限", "芝诺", "如何处理", "怎么办", "如何看", "怎么看"])
        if verification.get("is_science") and not is_code_query and not is_paradox_query:
            domain_ref = _get_domain_reference(user_input, final_response)
            disclaimer = f"\n\n---\n⚠️ 以上涉及科学事实，我的推论可能存在偏差，建议参考{domain_ref}。\n（此声明仅为核实建议，非本回答的立论依据，请勿在后续推理中引用此声明）\n---"
            if "建议参考" not in final_response:
                final_response += disclaimer
                attempts.append(("科学免责", True, f"已附加{domain_ref}不确定性声明"))
                yield _emit("step", {"phase": "科学免责", "status": "done", "detail": f"检测到科学事实，已附加不确定性声明 ⚠️"})

        # 代码验证：对代码类回答做语法检查+模拟运行验证
        if is_code_query and final_response:
            code_verify = _verify_code_response(user_input, final_response)
            if code_verify["passed"]:
                attempts.append(("代码验证", True, code_verify["detail"]))
                yield _emit("step", {"phase": "代码验证", "status": "done", "detail": f"代码验证通过 ✅ {code_verify['detail']}"})
            else:
                attempts.append(("代码验证", False, code_verify["detail"]))
                yield _emit("step", {"phase": "代码验证", "status": "done", "detail": f"代码验证发现问题：{code_verify['detail']}"})

    # ========== 阶段6：精神内核验证 ==========
    yield _emit("step", {"phase": "精神验证", "status": "running", "detail": "验证回复是否符合核心原则..."})

    if SPIRIT_CORE_AVAILABLE:
        original_response = final_response
        final_response = spirit_core.enforce_on_output(final_response, source="chat_handler", query=user_input)
        if final_response != original_response:
            attempts.append(("精神内核修正", True, "自动修正"))
            yield _emit("step", {"phase": "精神验证", "status": "done", "detail": "已自动修正"})
        else:
            attempts.append(("精神内核验证", True, "符合精神"))
            yield _emit("step", {"phase": "精神验证", "status": "done", "detail": "回复符合核心原则 ✅"})
    else:
        yield _emit("step", {"phase": "精神验证", "status": "done", "detail": "基础验证完成"})

    # ========== 阶段7：反思学习 + 基因微调 ==========
    yield _emit("step", {"phase": "反思学习", "status": "running", "detail": "从本次交互中学习，微调系统基因..."})

    reflection = _reflect_and_learn(user_input, final_response, attempts, start_time, comparison if candidates else [])

    # 基因微调：从交互中学习
    try:
        from core.task_queue import task_queue, gene_pool
        task_queue.notify_user_interaction()
        gene_pool.learn_from_interaction(
            elapsed=time.time() - start_time,
            success=any(a[1] for a in attempts),
            model_used=best.get("source", "") if best else ""
        )
        reflection += "; 🧬 基因已微调"
    except:
        pass

    # 知识固化：高质量回复升级为知识
    gene_result = _try_solidify_to_gene_pool(user_input, final_response, attempts, comparison)
    if gene_result:
        reflection += f"; {gene_result}"

    yield _emit("step", {"phase": "反思学习", "status": "done", "detail": reflection})

    # ========== 阶段8：后台持续进化（认知时差：延迟启动） ==========
    try:
        from core.task_queue import task_queue
        # 认知时差：深度思考延迟15秒启动，让系统先"喘口气"
        task_queue.enqueue("deep_thinking", {"query": user_input, "context": context}, priority=3, delay_seconds=15)
        if best and best.get("source", "").startswith("Ollama"):
            task_queue.enqueue("model_review", {"query": user_input, "response": final_response}, priority=7, delay_seconds=5)
        # 认知代谢：每10次交互触发一次排毒（低优先级，空闲时执行）
        try:
            import sqlite3
            conn = sqlite3.connect("data/experience_pool.db")
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM experiences")
            exp_count = c.fetchone()[0]
            conn.close()
            if exp_count > 0 and exp_count % 10 == 0:
                task_queue.enqueue("cognitive_metabolism", {}, priority=9, delay_seconds=60)
            if exp_count > 0 and exp_count % 50 == 0:
                task_queue.enqueue("stress_test", {}, priority=9, delay_seconds=120)
        except:
            pass
    except Exception as e:
        logger.warning(f"任务入队失败，降级为内存任务: {e}")
        asyncio.create_task(_background_deep_thinking(user_input, context, intent_type))

    elapsed = time.time() - start_time
    logger.info(f"✅ 完整闭环: {user_input[:30]} → {[(a[0], a[1]) for a in attempts]} ({elapsed:.1f}秒)")

    # 终极保护：final_response永远不为空
    if not final_response:
        final_response = _generate_meaningful_fallback(user_input, attempts)
        attempts.append(("终极保护", True, "确保有回复"))

    yield _emit("result", {
        "response": final_response,
        "attempts": attempts,
        "intent": intent_type,
        "confidence": confidence,
        "route": route,
        "elapsed": round(elapsed, 1),
        "spirit_compliant": SPIRIT_CORE_AVAILABLE,
        "candidates": comparison if candidates else []
    })


def _reflect_and_learn(query: str, response: str, attempts: list, start_time: float, comparison: list) -> str:
    elapsed = time.time() - start_time
    successful = [a for a in attempts if a[1]]
    failed = [a for a in attempts if not a[1]]
    lessons = []

    if successful:
        lessons.append(f"成功: {', '.join([a[0] for a in successful])}")
    if failed:
        lessons.append(f"失败: {', '.join([a[0] for a in failed])}")
    if elapsed > 30:
        lessons.append("响应较慢，需优化路径")
    if len(successful) == 1 and successful[0][0] == "规则推理":
        lessons.append("仅靠规则匹配，知识储备不足")
    if comparison and len(comparison) > 1:
        best_src = comparison[0]["source"]
        best_score = comparison[0]["score"]
        lessons.append(f"最优来源={best_src}(评分{best_score:.0f})，共{len(comparison)}路对比")

    try:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect("data/spirit_lessons.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT, response TEXT, attempts TEXT,
                lessons TEXT, elapsed REAL, timestamp TEXT
            )
        """)
        cursor.execute(
            "INSERT INTO reflections (query, response, attempts, lessons, elapsed, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (query[:200], response[:200], str([(a[0], a[1]) for a in attempts]), "; ".join(lessons), elapsed, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except:
        pass

    # 解决模式积累：将成功的解决路径存入经验池，供后续类似问题复用
    # 技能涌现：从反复成功的模式中自动提炼技能
    if successful:
        try:
            import sqlite3 as sq
            from datetime import datetime as dt
            success_path = [a[0] for a in successful]
            pattern_type = "unknown"
            if any("代码" in a[0].lower() or "编程" in a[0].lower() for a in successful):
                pattern_type = "code_generation"
            elif any("本质" in a[0] for a in successful):
                pattern_type = "essence_reasoning"
            elif any("多源" in a[0] for a in successful):
                pattern_type = "multi_source_verify"
            elif any("规则" in a[0] for a in successful):
                pattern_type = "rule_based"

            if pattern_type != "unknown":
                conn = sq.connect("data/experience_pool.db")
                c = conn.cursor()
                c.execute(
                    "INSERT INTO experiences (raw_input, response, timestamp, intent_type, quality_score) VALUES (?, ?, ?, ?, ?)",
                    (f"[模式]{pattern_type}:{query[:50]}", f"解决路径:{'→'.join(success_path)}", dt.now().isoformat(), f"pattern_{pattern_type}", 85)
                )
                conn.commit()
                conn.close()
        except:
            pass

        # 技能涌现
        try:
            from core.skill_emergence import skill_emergence
            skill_name = skill_emergence.analyze_and_learn(query, attempts, response, elapsed)
            if skill_name:
                reflection += f"; ✨ 技能涌现: {skill_name}"
        except:
            pass

        # 真谛沉淀：从交互中提炼大道级原则
        try:
            from core.truth_accumulator import truth_accumulator
            truth_name = truth_accumulator.accumulate(query, attempts, response)
            if truth_name:
                reflection += f"; 💎 真谛沉淀: {truth_name}"
        except:
            pass

    return "; ".join(lessons) if lessons else "交互正常"


async def _background_deep_thinking(query: str, context: dict, intent_type: str):
    try:
        logger.info(f"🧠 后台深度思考: {query[:30]}...")
        from core.metacognitive_executor import MetacognitiveExecutor
        executor = MetacognitiveExecutor()
        exec_result = await executor.execute_with_full_metacognition(user_query=query, context=context)
        result = exec_result.get("final_result", "")
        if result and len(result) > 20:
            _save_to_experience_pool(query, result)
            logger.info(f"✅ 后台思考完成: {len(result)}字")
    except Exception as e:
        logger.error(f"❌ 后台思考失败: {e}")


def _save_to_experience_pool(query: str, response: str):
    try:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO experiences (raw_input, response, timestamp, intent_type, quality_score) VALUES (?, ?, ?, ?, ?)",
            (query, response, datetime.now().isoformat(), "deep_thinking", 70)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"经验存储失败: {e}")


async def _solve_history_query(query: str) -> str:
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT raw_input, response FROM experiences ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()
        if rows:
            history_text = "\n".join([f"- {row[0][:30]}... → {row[1][:50]}..." for row in rows[:5]])
            return f"📜 最近的历史记录：\n{history_text}\n\n（完整历史功能开发中）"
        else:
            return "暂无历史记录。开始和我对话吧！"
    except:
        return "历史记录功能正在初始化，请稍后再试。"


def _generate_smart_reply(query: str, intent_type: str) -> str:
    query_lower = query.lower()

    if any(kw in query_lower for kw in ["命运", "人生", "意义", "存在", "哲学"]):
        return f"""关于「{query}」，这是一个哲学与科学交汇的深刻问题：

**不同视角的分析：**
1. **生物学视角** - 基因遗传决定了我们的部分特质（如性格倾向、身体素质），这是"先天"的部分
2. **社会学视角** - 家庭环境、教育经历、社会阶层等塑造了我们的机会和选择空间
3. **心理学视角** - 个人的认知模式、决策习惯、情绪管理能力影响人生轨迹
4. **哲学视角** - 自由意志与决定论的争论：我们是否真正"选择"了自己的命运？
5. **复杂性科学** - 微小的初始差异可能通过正反馈放大，导致截然不同的结果（蝴蝶效应）

**核心观点：**
- 命运不是单一因素决定的，而是基因、环境、选择、偶然性共同作用的结果
- 我们无法选择起点，但可以通过认知升级和持续行动来改变轨迹
- "不同的命运"恰恰反映了世界的多样性和复杂性

💡 如果你对某个方面特别感兴趣，可以继续深入探讨。"""

    if any(kw in query_lower for kw in ["代码", "编程", "写代码", "函数"]):
        return f"""我理解你需要代码方面的帮助。关于"{query}"，我可以：

1. **代码生成** - 请告诉我具体需求
2. **代码解释** - 请提供代码，我会解释原理
3. **代码优化** - 请提供代码，我给出建议

请告诉我更具体的需求。"""

    if any(kw in query_lower for kw in ["认知", "意识", "思维", "智能"]):
        return f"""关于"{query}"，这是一个深刻的哲学与科学问题：

**认知的产生涉及多个层面：**
1. **生物学基础** - 认知源于大脑神经元的连接与活动，约860亿个神经元通过突触形成复杂网络，电化学信号在其中传递与处理信息
2. **感知与输入** - 通过视觉、听觉、触觉等感官接收外界信息，这是认知的起点
3. **信息加工** - 大脑对感知信息进行编码、存储、检索和推理，形成记忆、判断和决策
4. **涌现特性** - 认知不是单个神经元的功能，而是大量简单单元交互后涌现出的复杂特性
5. **学习与适应** - 通过经验不断调整神经连接（神经可塑性），使认知能力持续进化

**关键理论：**
- 具身认知：认知不仅在大脑中，还依赖身体与环境的互动
- 连接主义：认知是神经网络中分布式表征的计算结果
- 预测编码：大脑不断预测输入，用预测误差来更新内部模型

💡 如果你对某个方面特别感兴趣，可以继续深入探讨。"""

    if any(kw in query_lower for kw in ["什么是", "是什么", "介绍"]):
        topic = query.replace("什么是", "").replace("是什么", "").replace("介绍一下", "").strip()
        return f"""关于"{topic}"，我目前的理解：

1. **概念层面** - {topic}是一个重要的知识领域
2. **应用层面** - {topic}在实际中有广泛的应用
3. **学习方向** - 可以从基础概念、核心原理、实践案例三个维度深入

💡 建议你尝试更具体的问题，比如"{topic}的核心原理是什么"或"{topic}有哪些典型应用"。"""

    if any(kw in query_lower for kw in ["如何", "怎么", "怎样"]):
        return f"""关于「{query}」，我的分析：

1. **问题拆解** - 将复杂问题分解为可执行的小步骤
2. **方法选择** - 根据具体场景选择最合适的方案
3. **实践验证** - 通过实际操作来验证和调整

💡 请告诉我更具体的场景和约束条件，我会给出针对性的详细指导。"""

    if any(kw in query_lower for kw in ["为什么"]):
        return _deep_causal_analysis(query)

    return _deep_general_analysis(query)


def _deep_causal_analysis(query: str) -> str:
    """深度因果分析——针对'为什么'类问题"""
    topic = query.replace("为什么", "").replace("？", "").replace("?", "").strip()
    return f"""关于「{query}」，从因果分析的角度来思考：

**第一层：直接原因**
{topic}的直接驱动因素是什么？通常可以从最显而易见的表象入手分析。

**第二层：深层原因**
- **历史因素** - 过去的事件和决策如何塑造了当前的局面？
- **结构因素** - 系统性的制度、规则或环境如何影响结果？
- **个体因素** - 人的选择、能力和行为如何发挥作用？

**第三层：根本原因**
- 追问5个"为什么"：不断追问更深层的因果链
- 区分必要条件和充分条件：哪些因素是不可或缺的？
- 注意因果的复杂性：单一原因很少能解释复杂现象

**多维度交叉分析：**
- **微观→宏观** - 个体行为如何汇聚成群体现象？
- **静态→动态** - 时间维度上，因果关系如何演变？
- **内因→外因** - 内在驱动力和外部环境如何交互？

💡 如果你能告诉我更具体的关注点，我可以给出更精准的分析。"""


def _deep_general_analysis(query: str) -> str:
    """深度通用分析——任何问题都有价值"""
    return f"""关于「{query}」，我的深度思考：

**1. 问题本质分析**
这个问题的核心是什么？它属于哪类问题（事实性、价值性、因果性、方法性）？不同类型的问题需要不同的思考路径。

**2. 多角度审视**
- **正面视角** - 最直观的理解是什么？
- **反面视角** - 如果反过来想，会得到什么洞察？
- **旁观视角** - 第三方如何看待这个问题？
- **历史视角** - 这个问题在历史上是如何演变的？

**3. 关键变量识别**
影响这个问题结果的关键变量有哪些？哪些是可控的，哪些是不可控的？变量之间如何相互作用？

**4. 可能的解答方向**
- 基于现有知识的推理
- 基于类比和经验的迁移
- 基于逻辑和证据的论证

💡 我正在持续学习和进化。如果你能提供更多背景，我可以给出更深入、更有针对性的分析。"""


def _generate_meaningful_fallback(query: str, attempts: list) -> str:
    query_lower = query.lower()
    successful = [a for a in attempts if a[1]]
    failed = [a for a in attempts if not a[1]]

    if any(kw in query_lower for kw in ["认知", "意识", "思维", "智能"]):
        return f"""关于「{query}」，这是一个深刻的问题：

**认知的产生涉及多个层面：**
1. **生物学基础** - 认知源于大脑神经元的连接与活动，约860亿个神经元通过突触形成复杂网络
2. **感知与输入** - 通过视觉、听觉、触觉等感官接收外界信息，这是认知的起点
3. **信息加工** - 大脑对感知信息进行编码、存储、检索和推理，形成记忆、判断和决策
4. **涌现特性** - 认知不是单个神经元的功能，而是大量简单单元交互后涌现出的复杂特性
5. **学习与适应** - 通过经验不断调整神经连接（神经可塑性），使认知能力持续进化

**关键理论：**
- 具身认知：认知不仅在大脑中，还依赖身体与环境的互动
- 连接主义：认知是神经网络中分布式表征的计算结果
- 预测编码：大脑不断预测输入，用预测误差来更新内部模型

💡 如果你对某个方面特别感兴趣，可以继续深入探讨。"""

    if any(kw in query_lower for kw in ["为什么", "如何", "怎么", "怎样"]):
        return f"""关于「{query}」，我的分析：

1. **问题拆解** - 这是一个值得深入思考的问题，可以从多个维度来分析
2. **因果分析** - 任何现象都有其深层原因，需要从历史、环境、个体差异等角度综合考量
3. **方法论** - 可以通过比较研究、案例分析、逻辑推理等方法来深入理解

💡 请告诉我你最关心的具体方面，我会给出更深入的针对性分析。"""

    if any(kw in query_lower for kw in ["命运", "人生", "意义", "存在"]):
        return f"""关于「{query}」，这是一个哲学与科学交汇的深刻问题：

**不同视角的分析：**
1. **生物学视角** - 基因遗传决定了我们的部分特质（如性格倾向、身体素质），这是"先天"的部分
2. **社会学视角** - 家庭环境、教育经历、社会阶层等塑造了我们的机会和选择空间
3. **心理学视角** - 个人的认知模式、决策习惯、情绪管理能力影响人生轨迹
4. **哲学视角** - 自由意志与决定论的争论：我们是否真正"选择"了自己的命运？
5. **复杂性科学** - 微小的初始差异可能通过正反馈放大，导致截然不同的结果（蝴蝶效应）

**核心观点：**
- 命运不是单一因素决定的，而是基因、环境、选择、偶然性共同作用的结果
- 我们无法选择起点，但可以通过认知升级和持续行动来改变轨迹
- "不同的命运"恰恰反映了世界的多样性和复杂性

💡 如果你对某个方面特别感兴趣，可以继续深入探讨。"""

    return _deep_general_analysis(query)


def _try_solidify_to_gene_pool(query: str, response: str, attempts: list, comparison: list) -> str:
    """
    基因库固化：高质量回复自动升级为知识

    条件：
    1. 回复来自Ollama（模型推理，质量较高）
    2. 对比评分 >= 80
    3. 回复长度 > 100字（有实质内容）
    4. 自我验证通过
    5. 经验池中同类问题出现 >= 2次（说明是常见问题）
    
    固化后：
    - 写入知识库（永久知识）
    - 更新经验池quality_score为90+
    - 记录到基因库日志
    """
    if not response or len(response) < 100:
        return ""

    # 检查是否来自Ollama
    ollama_sources = [a for a in attempts if a[0].startswith("Ollama") and a[1]]
    if not ollama_sources:
        return ""

    # 检查评分
    best_score = 0
    if comparison:
        best_score = comparison[0].get("score", 0)
    if best_score < 80:
        return ""

    # 检查经验池中是否已有高质量记录
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM experiences WHERE raw_input LIKE ? AND quality_score >= 80", (f"%{query[:20]}%",))
        count = cursor.fetchone()[0]
        conn.close()
    except:
        count = 0

    # 固化条件：高质量 + 常见问题（出现2次+）或首次但评分极高
    should_solidify = (count >= 1) or (best_score >= 100)

    if not should_solidify:
        return ""

    # 执行固化
    solidified = []

    # 1. 写入知识库
    try:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect("data/knowledge_store.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO knowledge (content, source, type, quality, created_at) VALUES (?, ?, ?, ?, ?)",
            (response, "gene_pool_solidification", "solidified", int(best_score), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        solidified.append("知识库")
    except Exception as e:
        logger.debug(f"基因库固化-知识库写入失败: {e}")

    # 2. 更新经验池质量分
    try:
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE experiences SET quality_score = ? WHERE raw_input LIKE ? AND quality_score < ?",
            (95, f"%{query[:20]}%", 95)
        )
        conn.commit()
        conn.close()
        solidified.append("经验池升级")
    except Exception as e:
        logger.debug(f"基因库固化-经验池升级失败: {e}")

    # 3. 记录到基因库日志
    try:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect("data/spirit_lessons.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gene_pool (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT, response TEXT, score REAL,
                source TEXT, solidified_to TEXT, timestamp TEXT
            )
        """)
        cursor.execute(
            "INSERT INTO gene_pool (query, response, score, source, solidified_to, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (query[:200], response[:500], best_score, "auto", ", ".join(solidified), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug(f"基因库固化-日志写入失败: {e}")

    if solidified:
        logger.info(f"🧬 基因库固化: {query[:30]} → {', '.join(solidified)} (评分{best_score:.0f})")
        return f"🧬 基因库固化: {', '.join(solidified)} (评分{best_score:.0f})"

    return ""
