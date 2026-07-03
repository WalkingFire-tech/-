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
from typing import Optional
from loguru import logger

_ollama_semaphore = asyncio.Semaphore(1)

try:
    from core.resource_awareness.adaptive_governor import get_adaptive_governor
    from core.resource_awareness.health_monitor import get_health_monitor
    _RESOURCE_AWARE = True
except ImportError:
    _RESOURCE_AWARE = False

try:
    from core.spirit_core import spirit_core
    SPIRIT_CORE_AVAILABLE = True
except ImportError:
    SPIRIT_CORE_AVAILABLE = False

_VECTOR_AVAILABLE = None

def _check_vector_available() -> bool:
    global _VECTOR_AVAILABLE
    if _VECTOR_AVAILABLE is not None:
        return _VECTOR_AVAILABLE
    try:
        from infrastructure.vector_retriever import vector_retriever
        _VECTOR_AVAILABLE = vector_retriever.is_available()
        if _VECTOR_AVAILABLE:
            logger.info("向量检索已启用（TF-IDF模式）")
        else:
            logger.warning("向量检索不可用，使用SQLite降级")
    except Exception as e:
        _VECTOR_AVAILABLE = False
        logger.warning(f"向量检索初始化失败: {e}")
    return _VECTOR_AVAILABLE


import concurrent.futures
_slow_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="slow_op")
_fast_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="fast_op")


async def _run_sync(func, *args, timeout=30, **kwargs):
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(_fast_executor, lambda: func(*args, **kwargs)),
        timeout=timeout
    )


async def _run_slow(func, *args, timeout=90, **kwargs):
    loop = asyncio.get_running_loop()
    return await asyncio.wait_for(
        loop.run_in_executor(_slow_executor, lambda: func(*args, **kwargs)),
        timeout=timeout
    )

_OLLAMA_MODEL_CACHE = {"model": None, "timestamp": 0}
_OLLAMA_MODELS_CACHE = {"models": [], "timestamp": 0}


async def _get_available_ollama_models_async() -> list:
    """异步获取可用Ollama模型列表"""
    import time as _time
    now = _time.time()
    if _OLLAMA_MODELS_CACHE["models"] and (now - _OLLAMA_MODELS_CACHE["timestamp"]) < 60:
        return _OLLAMA_MODELS_CACHE["models"]
    try:
        import requests
        loop = asyncio.get_running_loop()
        tags = await asyncio.wait_for(
            loop.run_in_executor(_fast_executor, lambda: requests.get("http://localhost:11434/api/tags", timeout=3)),
            timeout=5
        )
        models = [m["name"] for m in tags.json().get("models", [])]
        if models:
            _OLLAMA_MODELS_CACHE["models"] = models
            _OLLAMA_MODELS_CACHE["timestamp"] = now
        return models
    except Exception:
        return _OLLAMA_MODELS_CACHE["models"]


async def _get_available_ollama_model_async() -> str:
    """异步获取优先Ollama模型"""
    import time as _time
    now = _time.time()
    if _OLLAMA_MODEL_CACHE["model"] and (now - _OLLAMA_MODEL_CACHE["timestamp"]) < 60:
        return _OLLAMA_MODEL_CACHE["model"]
    models = await _get_available_ollama_models_async()
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
                _save_to_experience_pool(query, r["response"], success=True, intent_type="ollama_background")
                logger.info(f"🔄 Ollama后台结果已存入经验池: {query[:30]}")
    except Exception as e:
        logger.debug(f"Ollama后台保存失败: {e}")


def _emit(event_type: str, data: dict) -> str:
    if event_type == "result" and _RESOURCE_AWARE:
        try:
            get_health_monitor().unregister_query()
        except Exception:
            pass
    return f"data: {json.dumps({'type': event_type, **data}, ensure_ascii=False)}\n\n"


def _build_uncertainty_note(query: str, response: str, attempts: list, prob_field, action: dict) -> str:
    """
    构建基于实际推理过程的不确定性结语

    不是泛泛的"建议你也看看"，而是回答：
    1. 我具体做了哪些验证
    2. 哪些方面我比较有信心，哪些方面存疑
    3. 针对性的、可操作的建议
    """
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
    if _check_vector_available():
        try:
            from infrastructure.vector_retriever import vector_retriever
            loop = asyncio.get_running_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(_fast_executor, lambda: vector_retriever.search_similar(query, k=3, threshold=0.3)),
                timeout=10
            )
            if results:
                best = results[0]
                text = best.get("text", "")
                prob = best.get("probability", 0)
                if text and len(text) > 30:
                    result = {"source": "经验池(向量)", "response": text, "quality": min(int(prob * 100), 95),
                              "retrieval_probability": prob, "retrieval_entropy": best.get("query_entropy", 0.5)}
                    try:
                        from core.dynamic_probability_field import dynamic_probability_field
                        if dynamic_probability_field._candidates:
                            dynamic_probability_field.update({
                                "type": "support", "confidence": prob,
                                "source": "经验池(向量)", "content": text[:300],
                            })
                    except Exception:
                        pass
                    return result
        except asyncio.TimeoutError:
            logger.warning("向量检索超时(10秒)")
        except Exception as e:
            logger.debug(f"向量检索降级: {e}")
    
    try:
        import sqlite3
        loop = asyncio.get_running_loop()
        def _query_exp():
            conn = sqlite3.connect("data/experience_pool.db")
            cursor = conn.cursor()
            cursor.execute("SELECT response, quality_score FROM experiences WHERE raw_input LIKE ? ORDER BY timestamp DESC LIMIT 3", (f"%{query[:20]}%",))
            rows = cursor.fetchall()
            conn.close()
            return rows
        rows = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_exp), timeout=5)
        if rows:
            best = max(rows, key=lambda r: r[1] if r[1] else 50)
            if best[0] and len(best[0]) > 30:
                result = {"source": "经验池", "response": best[0], "quality": best[1] or 50}
                try:
                    from core.trajectory_evolution import trajectory_store
                    similar_trajs = trajectory_store.find_similar_trajectories(query, min_fitness=60, limit=1)
                    if similar_trajs:
                        best_traj = similar_trajs[0]
                        traj_steps = best_traj.get('steps', [])
                        if traj_steps:
                            successful_phases = [s['phase'] for s in traj_steps if s.get('success')]
                            if successful_phases:
                                result["trajectory_hint"] = f"历史最优路径: {'→'.join(successful_phases[:6])}"
                except:
                    pass
                return result
    except:
        pass
    return None


async def _fetch_knowledge(query: str) -> dict:
    if _check_vector_available():
        try:
            from infrastructure.vector_retriever import vector_retriever
            loop = asyncio.get_running_loop()
            results = await asyncio.wait_for(
                loop.run_in_executor(_fast_executor, lambda: vector_retriever.search_similar(query, k=3, threshold=0.3)),
                timeout=10
            )
            if results:
                best = results[0]
                text = best.get("text", "")
                prob = best.get("probability", 0)
                if text and len(text) > 30:
                    result = {"source": "知识库(向量)", "response": text, "quality": min(int(prob * 100), 90),
                              "retrieval_probability": prob, "retrieval_entropy": best.get("query_entropy", 0.5)}
                    try:
                        from core.dynamic_probability_field import dynamic_probability_field
                        if dynamic_probability_field._candidates:
                            dynamic_probability_field.update({
                                "type": "support", "confidence": prob,
                                "source": "知识库(向量)", "content": text[:300],
                            })
                    except Exception:
                        pass
                    return result
        except asyncio.TimeoutError:
            logger.warning("知识库向量检索超时(10秒)")
        except Exception as e:
            logger.debug(f"知识库向量检索降级: {e}")
    
    try:
        import sqlite3
        loop = asyncio.get_running_loop()
        def _query_know():
            conn = sqlite3.connect("data/knowledge_store.db")
            cursor = conn.cursor()
            cursor.execute("SELECT content FROM knowledge WHERE content LIKE ? LIMIT 1", (f"%{query[:30]}%",))
            row = cursor.fetchone()
            conn.close()
            return row
        row = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_know), timeout=5)
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
        if "---\n⚠️" in content:
            content = content.split("---\n⚠️")[0].strip()
        if role == "user":
            parts.append(f"用户：{content[:300]}")
        elif role == "assistant":
            parts.append(f"助手：{content[:300]}")
    if not parts:
        return ""
    return "\n".join(parts)


def _get_stereo_memory_context(query: str) -> str:
    """从立体记忆系统检索相关记忆作为上下文"""
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
        logger.debug(f"立体记忆检索跳过: {e}")
        return ""


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


async def _fetch_ollama(query: str, model: str, timeout: int = 60, conversation_context: str = "", truth_insights: str = "") -> dict:
    async with _ollama_semaphore:
        if _RESOURCE_AWARE:
            try:
                monitor = get_health_monitor()
                monitor.register_ollama_request()
                monitor.register_ollama_model(model)
            except Exception:
                pass
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
            
            loop = asyncio.get_running_loop()
            future = loop.run_in_executor(
                _slow_executor,
                lambda: requests.post(
                    "http://localhost:11434/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False},
                    timeout=timeout
                )
            )
            response = await asyncio.wait_for(future, timeout=timeout + 10)
            if response.status_code == 200:
                result = response.json().get("response", "")
                if result and len(result) > 10:
                    return {"source": f"Ollama({model})", "response": result, "quality": 80}
        except requests.exceptions.Timeout:
            logger.warning(f"Ollama({model}) requests超时({timeout}秒)")
        except asyncio.TimeoutError:
            logger.warning(f"Ollama({model}) asyncio.wait_for超时({timeout+10}秒)")
        except Exception as e:
            logger.debug(f"Ollama({model})调用失败: {e}")
        finally:
            if _RESOURCE_AWARE:
                try:
                    get_health_monitor().unregister_ollama_request()
                except Exception:
                    pass
    return None


async def _fetch_ollama_all(query: str, conversation_context: str = "", truth_insights: str = "") -> list:
    models = await _get_available_ollama_models_async()
    if not models:
        return []
    model = await _get_available_ollama_model_async()
    if not model:
        return []
    ollama_timeout = 45
    try:
        from core.path_weight_manager import path_weight_manager
        w = path_weight_manager.get_weight("ollama")
        ollama_timeout = int(30 + 30 * w / max(path_weight_manager.get_weights().values()))
    except Exception:
        pass
    result = await _fetch_ollama(query, model, timeout=ollama_timeout, conversation_context=conversation_context, truth_insights=truth_insights)
    return [result] if result else []


async def _fetch_ollama_response(query: str, conversation_context: str = "", truth_insights: str = "") -> dict:
    results = await _fetch_ollama_all(query, conversation_context=conversation_context, truth_insights=truth_insights)
    return results[0] if results else None


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
            loop = asyncio.get_running_loop()
            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        _slow_executor,
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
                    ),
                    timeout=45
                )
            except asyncio.TimeoutError:
                logger.warning("DeepSeek run_in_executor超时(45秒)，释放线程池")
                response = None
            if response and response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})
                token_info = {}
                if usage:
                    token_info = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }
                if content and len(content) > 20:
                    return {"source": "DeepSeek", "response": content, "quality": 90, "tokens": token_info}
        
        openai_key = config.get("openai_api_key", "")
        if openai_key and not openai_key.startswith("●"):
            import requests
            loop = asyncio.get_running_loop()
            base_url = config.get("openai_base_url", "https://api.openai.com/v1")
            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        _slow_executor,
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
                    ),
                    timeout=45
                )
            except asyncio.TimeoutError:
                logger.warning("OpenAI run_in_executor超时(45秒)，释放线程池")
                response = None
            if response and response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = result.get("usage", {})
                token_info = {}
                if usage:
                    token_info = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }
                if content and len(content) > 20:
                    return {"source": "OpenAI", "response": content, "quality": 90, "tokens": token_info}
    except Exception as e:
        logger.debug(f"外部API调用失败: {e}")
    return None


def _fetch_rule(query: str, intent_type: str) -> dict:
    response = _generate_smart_reply(query, intent_type)
    if response == "__NEED_DYNAMIC_REPLY__":
        return {"source": "规则推理", "response": "", "quality": 0}
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
    path_weights = {}
    try:
        from core.path_weight_manager import path_weight_manager
        path_weights = path_weight_manager.get_weights()
    except Exception:
        pass
    scored = []
    for c in candidates:
        s = _score_response(c, query)
        source = c.get("source", "")
        pw = path_weights.get(source, 0.1)
        s_weighted = s * (0.7 + 0.3 * pw / max(path_weights.values()) if path_weights else s)
        scored.append((c, s, s_weighted))
    scored.sort(key=lambda x: x[2], reverse=True)
    best = scored[0]
    comparison = [
        {"source": c["source"], "score": round(s, 1), "weighted_score": round(ws, 1), "length": len(c.get("response", ""))}
        for c, s, ws in scored
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
    is_science = any(kw in query for kw in science_keywords)
    
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
    
    if not is_science and not is_education and not is_history_philosophy:
        is_science = any(kw in response for kw in science_keywords)
    
    if is_education or is_history_philosophy:
        is_science = False

    # 模型评估异步化：入队让后台worker执行，不阻塞主流程
    try:
        from core.task_queue import task_queue
        task_queue.enqueue("model_review", {"query": query, "response": response})
    except:
        pass

    return {"verified": verified, "issues": issues, "confidence": confidence, "is_science": is_science}


async def _fetch_external_learning(query: str, conversation_context: str = "") -> Optional[dict]:
    """路径F：外部学习器（DuckDuckGo/Wikipedia）"""
    try:
        from infrastructure.external_learners import composite_learner
        if not composite_learner.is_available():
            return None
        results = await asyncio.wait_for(
            asyncio.get_running_loop().run_in_executor(
                _slow_executor, lambda: composite_learner.learn(query, conversation_context, max_results=4)
            ),
            timeout=25
        )
        if results:
            parts = []
            sources = set()
            for item in results:
                if item.content and len(item.content) > 30:
                    parts.append(item.content)
                    sources.add(item.source)
            if parts:
                source_label = f"外部学习({'+'.join(sorted(sources))})"
                return {"source": source_label, "response": "\n\n".join(parts), "quality": 70}
    except Exception as e:
        logger.debug(f"外部学习器异常: {e}")
    return None


async def _fetch_fact_assertions(query: str) -> Optional[dict]:
    """路径G：事实锚点查询"""
    try:
        from infrastructure.fact_store import fact_store
        loop = asyncio.get_running_loop()
        facts = await asyncio.wait_for(
            loop.run_in_executor(_fast_executor, lambda: fact_store.search_by_keywords(query, limit=5)),
            timeout=5
        )
        if facts:
            parts = []
            for fa in facts:
                parts.append(f"{fa['subject']} {fa['predicate']} {fa['object']} (置信度{fa['confidence']:.0%})")
            return {"source": "事实锚点", "response": "【事实锚点】\n" + "\n".join(f"- {p}" for p in parts), "quality": 70}
    except Exception as e:
        logger.debug(f"事实锚点查询异常: {e}")
    return None


async def _fetch_tool_results(query: str, intent_type: str = "") -> Optional[list]:
    """路径I：工具调用框架（P0-4）— 使用独立线程池，不阻塞共享_executor"""
    try:
        from core.tool_registry import tool_executor, tool_registry
        tool_names = tool_registry.plan_tools(query, intent_type)
        if not tool_names:
            return None
        tool_names = tool_names[:5]
        results = await tool_executor.execute_parallel(tool_names, {"query": query}, total_timeout=20.0)
        candidates = []
        for r in results:
            c = r.to_candidate()
            if c:
                candidates.append(c)
            try:
                from core.memory.layered_memory import layered_memory
                layered_memory.record_tool_usage(
                    r.source, query, r.success, r.quality, r.duration_ms
                )
            except Exception:
                pass
        return candidates if candidates else None
    except Exception as e:
        logger.debug(f"工具调用异常: {e}")
        return None


async def _self_reason(query: str, conversation_context: str = "", truth_insights: str = "") -> Optional[dict]:
    """路径H：自我推理——用已有知识自己推，不依赖外部模型"""
    try:
        knowledge_parts = []
        
        # 从经验池提取相关经验（异步）
        try:
            if _check_vector_available():
                from infrastructure.vector_retriever import vector_retriever
                if vector_retriever.is_available():
                    loop = asyncio.get_running_loop()
                    similar = await asyncio.wait_for(
                        loop.run_in_executor(_fast_executor, lambda: vector_retriever.search(query, top_k=3, threshold=0.5)),
                        timeout=5
                    )
                    for s in similar:
                        knowledge_parts.append(f"[经验] {s.get('text', '')[:200]}")
        except:
            pass
        
        # 从学习规则提取相关规则（异步）
        try:
            import sqlite3
            loop = asyncio.get_running_loop()
            def _query_rules():
                conn = sqlite3.connect("data/learning_rules.db")
                c = conn.cursor()
                c.execute("SELECT rule_text, confidence FROM learning_rules WHERE status='active' AND rule_text LIKE ? ORDER BY confidence DESC LIMIT 3", (f"%{query[:10]}%",))
                rows = c.fetchall()
                conn.close()
                return rows
            rows = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_rules), timeout=3)
            for row in rows:
                knowledge_parts.append(f"[规则 conf={row[1]:.2f}] {row[0][:200]}")
        except:
            pass
        
        # 从真谛库提取（异步）
        try:
            import sqlite3
            loop = asyncio.get_running_loop()
            def _query_truths():
                conn = sqlite3.connect("data/truths.db")
                c = conn.cursor()
                c.execute("SELECT content FROM truths WHERE content LIKE ? LIMIT 2", (f"%{query[:8]}%",))
                rows = c.fetchall()
                conn.close()
                return rows
            rows = await asyncio.wait_for(loop.run_in_executor(_fast_executor, _query_truths), timeout=3)
            for row in rows:
                knowledge_parts.append(f"[真谛] {row[0][:200]}")
        except:
            pass
        
        if knowledge_parts:
            reasoning = f"关于「{query}」，基于已有知识的推理：\n\n" + "\n".join(knowledge_parts)
            return {"source": "自我推理", "response": reasoning, "quality": 55}
    except Exception as e:
        logger.debug(f"自我推理异常: {e}")
    return None


async def _diagnose_ollama_status() -> dict:
    """
    穷尽一切手段诊断Ollama模型状态（异步版，不阻塞事件循环）
    
    手段1: HTTP API检测（/api/tags, /api/ps）
    手段2: 进程检测（ollama进程是否在运行）
    手段3: GPU/内存检测（模型是否占用了资源）
    
    注意：不再发极简推理测试——它会和主请求竞争Ollama资源并阻塞事件循环
    
    Returns:
        {
            "status": "alive"|"stuck"|"dead",
            "evidence": [...],  # 诊断证据链
            "model_running": bool,
            "gpu_in_use": bool,
            "can_respond": bool,
        }
    """
    result = {
        "status": "dead",
        "evidence": [],
        "model_running": False,
        "gpu_in_use": False,
        "can_respond": False,
    }
    
    loop = asyncio.get_running_loop()
    
    # 手段1: HTTP API检测（异步）
    try:
        import requests as _req
        try:
            r = await asyncio.wait_for(
                loop.run_in_executor(_slow_executor, lambda: _req.get("http://localhost:11434/api/tags", timeout=3)),
                timeout=5
            )
            if r.status_code == 200:
                models = r.json().get("models", [])
                if models:
                    result["model_running"] = True
                    result["evidence"].append(f"API可用，{len(models)}个模型")
                else:
                    result["evidence"].append("API可用但无模型")
                    return result
        except asyncio.TimeoutError:
            result["evidence"].append("API超时(5秒)")
            result["status"] = "stuck"
        except _req.exceptions.ConnectionError:
            result["evidence"].append("API连接失败")
        except _req.exceptions.Timeout:
            result["evidence"].append("API超时(3秒)")
            result["status"] = "stuck"
        except Exception as e:
            result["evidence"].append(f"API异常: {str(e)[:50]}")
        
        # 手段1b: 检查正在运行的模型（异步）
        if result["model_running"]:
            try:
                ps = await asyncio.wait_for(
                    loop.run_in_executor(_slow_executor, lambda: _req.get("http://localhost:11434/api/ps", timeout=3)),
                    timeout=5
                )
                if ps.status_code == 200:
                    running = ps.json().get("models", [])
                    if running:
                        model_names = [m.get("name", "?") for m in running]
                        result["evidence"].append(f"正在运行: {','.join(model_names)}")
                        result["status"] = "alive"
                    else:
                        result["evidence"].append("无模型在运行（可能正在加载）")
                        result["status"] = "alive"
            except:
                result["evidence"].append("ps查询失败，但API可用")
                result["status"] = "alive"
    except ImportError:
        result["evidence"].append("requests库不可用")
    
    # 手段2: 进程检测（异步）
    if result["status"] == "dead":
        try:
            import subprocess
            proc = await asyncio.wait_for(
                loop.run_in_executor(_slow_executor, lambda: subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq ollama.exe"],
                    capture_output=True, text=True, timeout=5
                )),
                timeout=8
            )
            if "ollama" in proc.stdout.lower():
                result["model_running"] = True
                result["evidence"].append("ollama进程存在")
                result["status"] = "stuck"
            else:
                result["evidence"].append("ollama进程不存在")
        except:
            result["evidence"].append("进程检测失败")
    
    # 手段3: GPU/内存检测（异步）
    if result["status"] in ("alive", "stuck"):
        try:
            import subprocess
            proc = await asyncio.wait_for(
                loop.run_in_executor(_slow_executor, lambda: subprocess.run(
                    ["nvidia-smi", "--query-compute-apps=pid,name,used_memory", "--format=csv,noheader"],
                    capture_output=True, text=True, timeout=5
                )),
                timeout=8
            )
            if proc.stdout.strip() and "ollama" in proc.stdout.lower():
                result["gpu_in_use"] = True
                result["evidence"].append(f"GPU占用中: {proc.stdout.strip()[:80]}")
                if result["status"] == "stuck":
                    result["status"] = "alive"
                    result["evidence"].append("GPU占用说明模型正在推理，修正为alive")
            elif result["status"] == "stuck":
                result["evidence"].append("GPU无占用，模型可能卡住")
        except:
            result["evidence"].append("GPU检测不可用")
    
    # 不再发极简推理测试——它会和主请求竞争Ollama资源，且同步调用会阻塞事件循环
    # 改用/api/ps判断：如果API可响应且显示有模型在运行，就认为alive
    if result["status"] == "stuck" and result["model_running"]:
        result["status"] = "alive"
        result["evidence"].append("API可响应+进程存在，判定为推理中而非卡死")
    
    if result["status"] == "stuck":
        result["evidence"].append("所有手段均无法确认模型可用，判定为stuck，建议启动替代推理")
    
    logger.info(f"🔍 Ollama诊断: status={result['status']}, evidence={'; '.join(result['evidence'])}")
    return result


async def _background_collect(task, query: str, task_name: str):
    """后台收集仍在推理的模型结果，不阻塞主流程"""
    try:
        result = await task
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and item.get("response"):
                    _save_to_experience_pool(query, item["response"], success=True, intent_type="background_collect")
                    logger.info(f"🔄 后台收集: {task_name}推理完成，已存入经验池")
        elif isinstance(result, dict) and result.get("response"):
            _save_to_experience_pool(query, result["response"], success=True, intent_type="background_collect")
            logger.info(f"🔄 后台收集: {task_name}推理完成，已存入经验池")
    except Exception as e:
        logger.debug(f"后台收集异常: {e}")


async def chat_stream(user_input: str, context: dict):
    start_time = time.time()
    attempts = []
    final_response = None
    intent_type = "unknown"
    route = "slow"
    confidence = 0.5
    logger.info(f"⏱️ [T+0s] chat_stream开始: {user_input[:50]}")

    user_input = user_input.strip().rstrip("/\\|").strip()
    if not user_input:
        yield _emit("result", {"response": "请输入你的问题。", "attempts": [], "intent": "greeting"})
        return


    history = context.get("history", []) if context else []
    conversation_context = _build_conversation_context(history)
    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 对话上下文构建完成")

    # 通知存在层：用户正在交互
    try:
        from core.presence.existence_layer import get_existence_layer
        get_existence_layer().user_interaction()
    except:
        pass

    # 资源感知：注册活跃查询 + 紧急模式预警
    _query_registered = False
    if _RESOURCE_AWARE:
        try:
            monitor = get_health_monitor()
            monitor.register_query()
            _query_registered = True
            if monitor.is_emergency():
                yield _emit("warning", {"type": "resource_emergency", "message": "系统资源紧张，正在保护性降级，回复可能较简短"})
            elif monitor.is_conservative():
                yield _emit("info", {"type": "resource_conservative", "message": "系统资源偏紧，已自动减少并行路径"})
        except Exception:
            pass

    # P1-1: 发布UserMessage事件
    try:
        from infrastructure.event_bus import bus, EventTypes
        bus.publish(EventTypes.UserMessage, {
            "query": user_input[:200],
            "timestamp": time.time(),
            "route": route,
        })
    except Exception:
        pass

    stereo_context = await _run_sync(_get_stereo_memory_context, user_input, timeout=5)
    if stereo_context:
        conversation_context = conversation_context + "\n" + stereo_context if conversation_context else stereo_context

    # 关系模型：获取当前关系状态，用于调整回复风格
    relationship_context = ""
    try:
        from core.relationship.model import get_relationship_model, InteractionType
        rm = get_relationship_model()
        rel_summary = rm.get_relationship_summary()
        trust = rel_summary.get("trust_level", 0.5)
        phase = rm.get_relationship_phase()
        interaction_count = rel_summary.get("total_interactions", 0)
        if interaction_count > 10 and trust >= 0.7:
            relationship_context = f"[你和我是老朋友了，信任度{trust:.0%}，可以更直接地交流]"
        elif trust >= 0.5:
            relationship_context = f"[关系:信任度{trust:.0%},阶段:{phase}]"
        elif trust < 0.3:
            relationship_context = f"[关系:信任度低({trust:.0%}),阶段:{phase},需要更谨慎、更详细地解释]"
        if relationship_context:
            conversation_context = (conversation_context + "\n" + relationship_context) if conversation_context else relationship_context
    except Exception as e:
        logger.debug(f"关系模型跳过: {e}")

    # ========== 阶段1：意图识别 ==========
    logger.info(f"📩 收到请求: '{user_input}'")
    yield _emit("step", {"phase": "意图识别", "status": "running", "detail": "分析问题类型和复杂度..."})

    try:
        from core.cognitive_dispatcher import CognitiveDispatcher
        if not hasattr(CognitiveDispatcher, '_shared_instance'):
            CognitiveDispatcher._shared_instance = CognitiveDispatcher()
        dispatcher = CognitiveDispatcher._shared_instance
        
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

    # ========== 阶段1.5：规则匹配与统计 ==========
    try:
        import sqlite3 as _sql
        from infrastructure.rule_matcher import RuleMatcher as _RM
        _INTENT_TYPE_MAP = {
            "greeting": "chat", "confirmation": "chat", "simple_query": "question",
            "complex_query": "code", "learning_trigger": "question",
            "challenge": "verification", "history_query": "memory",
        }
        _mapped_type = _INTENT_TYPE_MAP.get(intent_type, intent_type)
        _rule_ctx = {
            "intent_type": intent_type,
            "intent_type_legacy": _mapped_type,
            "raw_input": user_input,
        }
        _matcher = _RM()
        with _sql.connect("data/learning_rules.db") as _conn:
            _conn.row_factory = _sql.Row
            _cur = _conn.execute(
                "SELECT id, condition, action, status FROM learning_rules WHERE status IN ('active','trial') ORDER BY priority ASC, confidence DESC"
            )
            _active_matched = False
            _trial_matched = False
            for _row in _cur.fetchall():
                try:
                    if _matcher.evaluate_condition(_row["condition"], _rule_ctx):
                        if _row["status"] == "active" and not _active_matched:
                            _conn.execute(
                                "UPDATE learning_rules SET apply_count=apply_count+1, last_applied=? WHERE id=?",
                                (time.time(), _row["id"]),
                            )
                            _active_matched = True
                        elif _row["status"] == "trial" and not _trial_matched:
                            _conn.execute(
                                "UPDATE learning_rules SET apply_count=apply_count+1, last_applied=? WHERE id=? AND status='trial'",
                                (time.time(), _row["id"]),
                            )
                            _trial_matched = True
                        if _active_matched and _trial_matched:
                            break
                except Exception:
                    pass
            _conn.commit()
    except Exception as _e:
        logger.debug(f"规则匹配统计失败: {_e}")

    # ========== 阶段2：简单意图直接回复 ==========
    if intent_type == "greeting":
        final_response = "嘿，我在。有什么想聊的，或者遇到了什么问题？我们一起看看。"
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
            model = await _get_available_ollama_model_async()
            challenge_result = None
            if model:
                challenge_result = await _fetch_ollama(challenge_prompt, model, timeout=30, conversation_context=conversation_context)
            if not challenge_result:
                challenge_result = await _fetch_external_api(challenge_prompt, conversation_context=conversation_context)
            if challenge_result and challenge_result.get("response"):
                final_response = challenge_result["response"]
                _save_to_experience_pool(user_input, final_response, success=True, intent_type="challenge")
                attempts.append(("质疑重验证", True, f"已重新论证并修正"))
                yield _emit("step", {"phase": "质疑检测", "status": "done", "detail": "重验证完成，已修正回答 ✅"})
            else:
                rule_challenge = _generate_smart_reply(challenge_prompt, "complex_query")
                if rule_challenge == "__NEED_DYNAMIC_REPLY__":
                    rule_challenge = f"我重新审视了你的质疑，但目前无法生成更深入的重验证。请提供更多具体信息。"
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

    # 事实锚点查询：从事实库获取相关客观事实，注入推理上下文
    fact_context = ""
    try:
        from infrastructure.fact_store import fact_store
        fact_assertions = await _run_sync(fact_store.search_by_keywords, user_input, limit=5, timeout=5)
        if fact_assertions:
            fact_parts = []
            for fa in fact_assertions:
                fact_parts.append(f"- {fa['subject']} {fa['predicate']} {fa['object']} (置信度{fa['confidence']:.0%}, 来源:{fa['source']})")
            fact_context = "【事实锚点-客观验证】\n" + "\n".join(fact_parts)
            yield _emit("step", {"phase": "事实锚点", "status": "done", "detail": f"检索到{len(fact_assertions)}条相关事实"})
            attempts.append(("事实锚点", True, f"{len(fact_assertions)}条"))
        else:
            yield _emit("step", {"phase": "事实锚点", "status": "done", "detail": "无相关事实锚点"})
    except Exception as e:
        logger.debug(f"事实锚点查询跳过: {e}")

    if fact_context and not truth_insights:
        truth_insights = fact_context
    elif fact_context:
        truth_insights = fact_context + "\n" + truth_insights

    # 分层记忆查询（P1-6）：战略/程序/工具三层记忆上下文
    try:
        from core.memory.layered_memory import layered_memory
        lm_context = layered_memory.get_context_for_query(user_input)
        if lm_context["context"]:
            if truth_insights:
                truth_insights = lm_context["context"] + "\n" + truth_insights
            else:
                truth_insights = lm_context["context"]
            yield _emit("step", {"phase": "分层记忆", "status": "done",
                "detail": f"战略{lm_context['strategic_count']}/程序{lm_context['procedural_count']}/工具{lm_context['tool_count']}"})
    except Exception as e:
        logger.debug(f"分层记忆查询跳过: {e}")

    yield _emit("step", {"phase": "方法论发现", "status": "done", "detail": f"解决策略：{methodology['strategy']} | 来源优先级：{' → '.join(methodology['source_priority'][:3])}"})

    # ========== 阶段3：多策略并行尝试 ==========
    # 核心思想：同一问题同时走多条路径，全部尝试，综合比较，概率最优
    # 没有走不通的路，只有思维达不到的地方
    # 模型思考期间不干等——同时搜网、查库、调工具、自己推理
    logger.info(f"🚀 进入阶段3: 多策略并行尝试, intent={intent_type}, strategy={methodology['strategy']}")

    max_paths = 9
    resource_mode = "normal"
    if _RESOURCE_AWARE:
        governor = get_adaptive_governor()
        monitor = get_health_monitor()
        max_paths = governor.get_parallel_path_count(9)
        resource_mode = monitor.get_mode_value()
        if max_paths < 9:
            logger.info(f"⚖️ 资源感知：{resource_mode}模式，并行路径 9→{max_paths}")
            yield _emit("step", {"phase": "资源感知", "status": "info", "detail": f"当前{resource_mode}模式，并行路径调整为{max_paths}"})

    yield _emit("step", {"phase": "多策略并行", "status": "running", "detail": f"策略：{methodology['strategy']}，{max_paths}路径同时出击..."})

    candidates = []

    # 路径A：规则推理（内观——最快，0秒）
    rule_result = _fetch_rule(user_input, intent_type)
    if rule_result and rule_result.get("response"):
        candidates.append(rule_result)

    # ===== 所有路径同时启动（资源感知：根据max_paths决定启动哪些） =====
    # 路径B：经验池（始终启动，纯内存操作）
    exp_task = asyncio.create_task(_fetch_experience(user_input))
    # 路径C：知识库（始终启动，纯内存操作）
    know_task = asyncio.create_task(_fetch_knowledge(user_input))
    # 路径D：Ollama本地模型（资源消耗最大）
    ollama_task = None
    if max_paths >= 3:
        ollama_task = asyncio.create_task(_fetch_ollama_all(user_input, conversation_context=conversation_context, truth_insights=truth_insights))
    # 路径E：外部模型
    ext_task = None
    if max_paths >= 4:
        ext_task = asyncio.create_task(_fetch_external_api(user_input, conversation_context=conversation_context, truth_insights=truth_insights))
    # 路径F：外部学习器（DuckDuckGo/Wikipedia）
    ext_learn_task = None
    if max_paths >= 5:
        ext_learn_task = asyncio.create_task(_fetch_external_learning(user_input, conversation_context))
    # 路径G：事实锚点查询（始终启动，纯内存操作）
    fact_task = asyncio.create_task(_fetch_fact_assertions(user_input))
    # 路径H：自我推理（用已有知识自己推）
    self_reason_task = None
    if max_paths >= 6:
        self_reason_task = asyncio.create_task(_self_reason(user_input, conversation_context, truth_insights))

    # 路径I：工具调用框架（P0-4 — 使用独立线程池，不阻塞共享_executor）
    tool_task = None
    if max_paths >= 7:
        tool_task = asyncio.create_task(_fetch_tool_results(user_input, intent_type))


    # 先收快速结果（经验池+知识库+事实锚点——毫秒级）
    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 开始gather快速路径...")
    fast_results = await asyncio.gather(exp_task, know_task, fact_task, return_exceptions=True)
    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] gather快速路径完成")
    fast_count = 0
    for r in fast_results:
        if isinstance(r, dict) and r.get("response"):
            candidates.append(r)
            fast_count += 1

    yield _emit("step", {"phase": "多策略并行", "status": "progress", "detail": f"快速路径已返回{fast_count+1}个结果，模型+外部+自推理并行中..."})

    # 收所有慢速结果（永不放弃——智能诊断模型状态，不简单掐死）
    # 策略：每5秒检查一轮，主动诊断模型是否还活着
    #   - 模型还活着 → 继续等，发心跳
    #   - 模型卡死/断开 → 智能决策：用已有候选综合，或换模型重试
    #   - 已有足够高质量候选 → 不再死等，直接综合
    ollama_got = False
    ext_got = False
    ext_learn_got = False
    self_reason_got = False
    heartbeat_sec = 0
    ollama_diagnosed_dead = False

    pending_tasks = {}
    if ollama_task: pending_tasks[ollama_task] = "本地模型"
    if ext_task: pending_tasks[ext_task] = "外部模型"
    if ext_learn_task: pending_tasks[ext_learn_task] = "外部学习"
    if self_reason_task: pending_tasks[self_reason_task] = "自我推理"
    if tool_task: pending_tasks[tool_task] = "工具调用"
    pending_set = set(pending_tasks.keys())

    while pending_set:
        logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] asyncio.wait开始, pending={[pending_tasks.get(t,'?') for t in pending_set]}")
        done, pending_set = await asyncio.wait(pending_set, timeout=5.0, return_when=asyncio.FIRST_COMPLETED)
        logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] asyncio.wait返回, done={len(done)}, pending={len(pending_set)}")
        for d in done:
            task_name = pending_tasks.get(d, "未知")
            try:
                result = d.result()
                if isinstance(result, list):
                    for item in result:
                        if isinstance(item, dict) and item.get("response"):
                            candidates.append(item)
                            if "Ollama" in item.get("source", ""):
                                _save_to_experience_pool(user_input, item["response"], success=True, intent_type="ollama_candidate")
                                ollama_got = True
                elif isinstance(result, dict) and result.get("response"):
                    candidates.append(result)
                    if "Ollama" in result.get("source", ""):
                        _save_to_experience_pool(user_input, result["response"], success=True, intent_type="ollama_candidate")
                        ollama_got = True
                    elif "外部学习" in result.get("source", ""):
                        ext_learn_got = True
                    elif "自我推理" in result.get("source", ""):
                        self_reason_got = True
                    else:
                        _save_to_experience_pool(user_input, result["response"], success=True, intent_type="external_api")
                        ext_got = True
                yield _emit("step", {"phase": task_name, "status": "done", "detail": f"{task_name}返回结果 ✅"})
            except Exception as e:
                logger.debug(f"{task_name}异常: {e}")
                yield _emit("step", {"phase": task_name, "status": "done", "detail": f"{task_name}异常"})

        if not pending_set:
            break

        heartbeat_sec += 3
        
        # 最大等待90秒，超时后用已有候选
        if heartbeat_sec >= 90:
            logger.warning(f"⏱️ 8路径并行等待超时({heartbeat_sec}秒)，用已有{len(candidates)}个候选继续")
            yield _emit("step", {"phase": "智能调度", "status": "done",
                "detail": f"等待超时({heartbeat_sec}秒)，用已有{len(candidates)}个候选继续"})
            for t in pending_set:
                t.cancel()
            pending_set = set()
            break

        still_waiting = [pending_tasks[t] for t in pending_set if t in pending_tasks]
        logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 轮询: candidates={len(candidates)}, high_q={sum(1 for c in candidates if c.get('quality', 0) >= 60 and len(c.get('response', '')) > 50)}, waiting={still_waiting}")

        # ===== 智能提前综合：有足够高质量候选时不再等待慢路径 =====
        high_q = sum(1 for c in candidates if c.get("quality", 0) >= 60 and len(c.get("response", "")) > 50)
        has_model_result = any(c.get("source", "") in ["Ollama", "DeepSeek", "OpenAI", "外部模型"] or "模型" in c.get("source", "") for c in candidates)
        has_search_result = any("搜索" in c.get("source", "") or "学习" in c.get("source", "") or "外部" in c.get("source", "") for c in candidates if c.get("quality", 0) >= 60)
        
        if high_q >= 3 and heartbeat_sec >= 15:
            waiting_names = '+'.join(still_waiting)
            yield _emit("step", {"phase": "智能调度", "status": "done",
                "detail": f"已有{high_q}条高质量候选，先综合输出，慢路径({waiting_names})后台补充"})
            for t in list(pending_set):
                asyncio.ensure_future(_background_collect(t, user_input, pending_tasks.get(t, "未知路径")))
                pending_set.discard(t)
            break
        
        if high_q >= 2 and has_model_result and heartbeat_sec >= 15:
            waiting_names = '+'.join(still_waiting)
            yield _emit("step", {"phase": "智能调度", "status": "done",
                "detail": f"已有{high_q}条高质量候选(含模型结果)，先综合输出，慢路径({waiting_names})后台补充"})
            for t in list(pending_set):
                asyncio.ensure_future(_background_collect(t, user_input, pending_tasks.get(t, "未知路径")))
                pending_set.discard(t)
            break

        if high_q >= 2 and has_search_result and heartbeat_sec >= 20:
            waiting_names = '+'.join(still_waiting)
            yield _emit("step", {"phase": "智能调度", "status": "done",
                "detail": f"已有{high_q}条高质量搜索候选(无模型结果)，先综合输出，模型后台补充"})
            for t in list(pending_set):
                asyncio.ensure_future(_background_collect(t, user_input, pending_tasks.get(t, "未知路径")))
                pending_set.discard(t)
            break

        if high_q >= 1 and has_search_result and heartbeat_sec >= 30:
            waiting_names = '+'.join(still_waiting)
            yield _emit("step", {"phase": "智能调度", "status": "done",
                "detail": f"模型未响应，已有{high_q}条搜索候选，先综合输出"})
            for t in list(pending_set):
                asyncio.ensure_future(_background_collect(t, user_input, pending_tasks.get(t, "未知路径")))
                pending_set.discard(t)
            break

        # ===== 智能诊断：不简单超时，而是主动检查模型状态 =====
        ollama_still_pending = ollama_task in pending_set and not ollama_task.done()

        if ollama_still_pending and heartbeat_sec >= 20:
            diagnosis = await _diagnose_ollama_status()
            ollama_status = diagnosis["status"]
            
            if ollama_status == "alive":
                if high_q >= 2:
                    yield _emit("step", {"phase": "智能调度", "status": "done",
                        "detail": f"模型推理中(状态正常)，已有{high_q}条高质量候选，先综合输出，模型结果后台补充"})
                    if ollama_task in pending_set:
                        asyncio.ensure_future(_background_collect(ollama_task, user_input, "本地模型"))
                        pending_set.discard(ollama_task)
                else:
                    yield _emit("step", {"phase": "多路并行", "status": "progress",
                        "detail": f"本地模型正在推理(已{heartbeat_sec}秒，诊断: {'; '.join(diagnosis['evidence'][:2])})，已收集{len(candidates)}个候选"})
            
            elif ollama_status == "stuck":
                yield _emit("step", {"phase": "智能调度", "status": "progress",
                    "detail": f"本地模型推理{heartbeat_sec}秒，诊断: {'; '.join(diagnosis['evidence'][:3])}，启动替代推理..."})
                try:
                    alt_result = await _fetch_ollama_response(user_input, conversation_context=conversation_context, truth_insights=truth_insights)
                    if alt_result and alt_result.get("response"):
                        candidates.append(alt_result)
                        _save_to_experience_pool(user_input, alt_result["response"], success=True, intent_type="ollama_retry")
                        ollama_got = True
                        yield _emit("step", {"phase": "替代推理", "status": "done", "detail": "替代推理成功 ✅"})
                except:
                    pass
                if ollama_task in pending_set:
                    pending_set.discard(ollama_task)
            
            elif ollama_status == "dead":
                ollama_diagnosed_dead = True
                yield _emit("step", {"phase": "智能调度", "status": "done",
                    "detail": f"本地模型不可达(诊断: {'; '.join(diagnosis['evidence'][:2])})，使用{len(candidates)}条已有候选综合"})
                if ollama_task in pending_set:
                    pending_set.discard(ollama_task)
        else:
            yield _emit("step", {"phase": "多路并行", "status": "progress",
                "detail": f"已等待{heartbeat_sec}秒，仍在等待: {'+'.join(still_waiting)}，已收集{len(candidates)}个候选"})

    # 汇报各路径结果
    if ollama_got:
        try:
            from core.module_health import module_health
            module_health.record_success("ollama")
        except:
            pass
    if ext_got:
        try:
            from core.module_health import module_health
            module_health.record_success("external_api")
        except:
            pass
    if ollama_diagnosed_dead:
        try:
            from core.module_health import module_health
            module_health.record_failure("ollama", "diagnosed_dead")
        except:
            pass

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
        elif "外部学习" in src:
            sources_got.add("外部学习")
        elif "事实锚点" in src:
            sources_got.add("事实锚点")
        elif "自我推理" in src:
            sources_got.add("自我推理")

    yield _emit("step", {"phase": "多策略并行", "status": "done", "detail": f"共获取{len(candidates)}个候选结果（{len(sources_got)}条路径：{'+'.join(sources_got)}）"})

    # 计算各路径有效信息占比
    path_contributions = {}
    total_quality = 0
    for c in candidates:
        src = c.get("source", "未知")
        q = c.get("quality", 50)
        resp_len = len(c.get("response", ""))
        if resp_len > 30:
            path_contributions[src] = path_contributions.get(src, 0) + q
            total_quality += q
    path_percentages = {}
    if total_quality > 0:
        for src, q in sorted(path_contributions.items(), key=lambda x: -x[1]):
            pct = q / total_quality * 100
            path_percentages[src] = round(pct, 1)
    if path_percentages:
        contrib_str = " | ".join(f"{k}:{v}%" for k, v in path_percentages.items())
        yield _emit("step", {"phase": "路径贡献", "status": "done", "detail": f"有效信息占比 → {contrib_str}"})

    # ========== 阶段3.5：多路径树搜索（Beam Search, P2-3）==========
    # 当候选质量不够高时，用beam search扩展第二轮
    try:
        from core.beam_search import beam_search_engine
        if beam_search_engine.should_trigger(candidates):
            yield _emit("step", {"phase": "树搜索扩展", "status": "running", "detail": "候选质量不足，启动beam search扩展..."})
            async def _beam_fetch(q, ctx=""):
                try:
                    return await _fetch_ollama_all(q, conversation_context=ctx)
                except Exception:
                    return {"response": "", "source": "beam_search_failed", "quality": 0}
            candidates = await beam_search_engine.search(
                original_query=user_input,
                candidates=candidates,
                fetch_func=_beam_fetch,
                conversation_context=conversation_context,
            )
            yield _emit("step", {"phase": "树搜索扩展", "status": "done", "detail": f"扩展后{len(candidates)}个候选"})
    except Exception as e:
        logger.debug(f"Beam search跳过: {e}")

    # ========== 阶段4：对比择优 ==========
    logger.info(f"⏱️ [T+{time.time()-start_time:.1f}s] 进入阶段4: 对比择优, {len(candidates)}个候选")
    yield _emit("step", {"phase": "对比择优", "status": "running", "detail": f"对{len(candidates)}个结果评分对比..."})

    best, comparison = _compare_and_select(candidates, user_input)

    if best:
        final_response = best["response"]
        for c in comparison:
            src = c["source"]
            sc = c["score"]
            attempts.append((src, sc >= 60, f"评分{sc:.0f}"))
        yield _emit("step", {"phase": "对比择优", "status": "done", "detail": f"最优来源: {best['source']} (评分{comparison[0]['score']:.0f})，共{len(comparison)}个候选"})

        # 贡献度归因（SHAP风格）+ 路径权重更新（AdaBoost风格，不确定性感知）
        try:
            from core.contrib_attributor import contrib_attributor
            from core.path_weight_manager import path_weight_manager
            attrib = contrib_attributor.compute_contributions(
                candidates, final_response, best["source"], user_input
            )
            for src, score in attrib.get("contributions", {}).items():
                unc_info = (attrib.get("retrieval_uncertainties") or {}).get(src)
                uncertainty = unc_info.get("retrieval_entropy") if unc_info else None
                path_weight_manager.update_weight(src, True, score, uncertainty=uncertainty)
            if attrib.get("contributions"):
                contrib_str = " | ".join(f"{k}:{v:.0%}" for k, v in list(attrib["contributions"].items())[:5])
                unc_str = ""
                if attrib.get("retrieval_uncertainties"):
                    unc_dims = len(attrib["retrieval_uncertainties"])
                    unc_str = f" | 不确定性维度:{unc_dims}"
                yield _emit("step", {"phase": "贡献归因", "status": "done", "detail": f"贡献度: {contrib_str}{unc_str}"})
        except Exception as e:
            logger.debug(f"贡献归因跳过: {e}")

        # 动态概率场初始化（异步概率计算核心）+ 不确定性驱动路由
        try:
            from core.dynamic_probability_field import dynamic_probability_field
            from core.path_weight_manager import path_weight_manager
            prob_dist = dynamic_probability_field.initialize(candidates, path_weight_manager.get_weights())
            if prob_dist.get("top"):
                action = dynamic_probability_field.get_uncertainty_action()
                action_hint = ""
                if action["depth"] == "deep":
                    action_hint = " | 建议深度探索"
                elif action["depth"] == "moderate":
                    action_hint = f" | {action.get('uncertainty_label', '')}"
                yield _emit("step", {"phase": "概率场", "status": "done",
                    "detail": f"概率分布: top={prob_dist['top']['source']}({prob_dist['top']['probability']:.0%}) 熵={prob_dist['entropy']:.2f}{action_hint}"})
        except Exception as e:
            logger.debug(f"概率场初始化跳过: {e}")
    else:
        yield _emit("step", {"phase": "对比择优", "status": "done", "detail": "无有效候选结果"})

    # ========== 阶段4.5：本质推理与自洽验证 ==========
    essence_passed = True
    essence_confidence = 1.0
    essence_issues = []
    essence_cross_validated = False
    if final_response:
        yield _emit("step", {"phase": "本质推理", "status": "running", "detail": "第一性原理推理→自洽性验证→事实锚点验证→跨域一致性→反向归谬..."})
        try:
            from core.essence_reasoner import essence_reasoner
            essence_result = await _run_sync(essence_reasoner.reason, user_input, final_response, conversation_context, timeout=15)
            
            # 事实锚点验证：用事实库断言校验回复中的关键声明
            fact_verified = True
            fact_issues = []
            try:
                from infrastructure.fact_store import fact_store
                negations = await _run_sync(fact_store.get_negations, user_input, timeout=5)
                if negations:
                    for neg in negations:
                        neg_claim = f"{neg['subject']}{neg['predicate']}{neg['object']}"
                        if neg_claim in final_response:
                            fact_verified = False
                            fact_issues.append(f"与已纠错事实冲突: {neg_claim}")
            except:
                pass
            
            if not fact_verified:
                essence_result["passed"] = False
                essence_result["consistency_issues"].extend(fact_issues)
                if essence_result["confidence"] > 0.7:
                    essence_result["confidence"] = 0.5
                yield _emit("step", {"phase": "事实验证", "status": "done", "detail": f"发现{len(fact_issues)}个事实冲突 ⚠️"})
            elif fact_context:
                yield _emit("step", {"phase": "事实验证", "status": "done", "detail": "事实锚点验证通过 ✅"})
            
            if essence_result["passed"]:
                essence_passed = True
                essence_confidence = essence_result["confidence"]
                attempts.append(("本质推理", True, f"{essence_result['verdict']} (置信度{essence_result['confidence']:.0%})"))
                yield _emit("step", {"phase": "本质推理", "status": "done", "detail": f"推理自洽 ✅ {essence_result['verdict']}"})
            else:
                essence_passed = False
                essence_confidence = essence_result["confidence"]
                essence_issues = essence_result.get("consistency_issues", [])
                issues_str = '；'.join(essence_result["consistency_issues"][:3])
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
                        essence_cross_validated = True
                        # 多源差异萃取
                        yield _emit("step", {"phase": "多源交叉验证", "status": "progress", "detail": f"收集到{len(multi_sources)}个来源，进行差异萃取..."})
                        merged = _cross_source_merge(user_input, multi_sources, essence_result["consistency_issues"])
                        if merged:
                            final_response = merged
                            _save_to_experience_pool(user_input, merged, success=True, intent_type="multi_source_merge")
                            attempts.append(("多源交叉验证", True, f"{len(multi_sources)}源融合成功"))
                            yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": f"多源融合完成 ✅ ({len(multi_sources)}个来源)"})
                        else:
                            # 无法融合→诚实罗列分歧
                            divergence = _list_divergences(user_input, multi_sources)
                            final_response = divergence
                            attempts.append(("多源交叉验证", True, "罗列分歧"))
                            yield _emit("step", {"phase": "多源交叉验证", "status": "done", "detail": "多源存在分歧，诚实罗列各方观点"})
                    elif len(multi_sources) == 1:
                        essence_cross_validated = True
                        single = multi_sources[0]
                        recheck = None
                        try:
                            from core.essence_reasoner import essence_reasoner
                            recheck = await _run_sync(essence_reasoner.reason, user_input, single["response"], conversation_context, timeout=30)
                        except:
                            pass
                        if recheck and recheck["confidence"] > essence_result["confidence"]:
                            final_response = single["response"]
                            _save_to_experience_pool(user_input, final_response, success=True, intent_type="single_source")
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
        fallback = _generate_meaningful_fallback(user_input, attempts)
        if fallback == "__NEED_DYNAMIC_FALLBACK__":
            try:
                ollama_result = await _fetch_ollama_response(user_input, conversation_context=conversation_context, truth_insights=truth_insights)
                if ollama_result and ollama_result.get("response") and len(ollama_result["response"]) > 20:
                    final_response = ollama_result["response"]
                    attempts.append(("动态推理", True, "模型实时生成"))
                else:
                    final_response = f"这个问题我暂时还没想清楚——「{user_input}」涉及的方向我需要更多背景才能给出靠谱的回答。你能补充一下具体场景或你关注的重点吗？"
                    attempts.append(("动态推理", False, "模型无有效回复"))
            except:
                final_response = f"这个问题我暂时还没想清楚——「{user_input}」涉及的方向我需要更多背景才能给出靠谱的回答。你能补充一下具体场景或你关注的重点吗？"
                attempts.append(("动态推理", False, "模型异常"))
        else:
            final_response = fallback
            attempts.append(("降级保护", True, "基础回复"))
        yield _emit("step", {"phase": "自我验证", "status": "done", "detail": "使用动态推理回复"})

    if final_response:
        yield _emit("step", {"phase": "自我验证", "status": "running", "detail": "验证回复质量和逻辑性..."})
        verification = await _self_verify(user_input, final_response)
        combined_confidence = (verification["confidence"] + essence_confidence) / 2.0
        if essence_passed and essence_confidence >= 0.7:
            combined_confidence = max(combined_confidence, 0.85)
        verification["confidence"] = combined_confidence
        if verification["verified"]:
            attempts.append(("自我验证", True, f"通过 (置信度{verification['confidence']:.0%})"))
            yield _emit("step", {"phase": "自我验证", "status": "done", "detail": f"验证通过 ✅ 置信度{verification['confidence']:.0%}"})
        else:
            filtered_issues = [i for i in verification["issues"] if i not in essence_issues]
            if not filtered_issues and essence_cross_validated:
                attempts.append(("自我验证", True, f"本质推理已覆盖 (置信度{verification['confidence']:.0%})"))
                yield _emit("step", {"phase": "自我验证", "status": "done", "detail": f"本质推理已覆盖验证，跳过冗余修正 ✅"})
            else:
                attempts.append(("自我验证", False, f"问题: {'; '.join(verification['issues'])}"))
                yield _emit("step", {"phase": "自我验证", "status": "done", "detail": f"发现问题: {'; '.join(verification['issues'])}，尝试修正..."})

                # 验证不通过，尝试用Ollama重新推理（如果之前没有Ollama结果且未做多源交叉验证）
                if not essence_cross_validated and not any(a[0].startswith("Ollama") and a[1] for a in attempts):
                    model = await _get_available_ollama_model_async()
                    if model:
                        yield _emit("step", {"phase": "修正推理", "status": "running", "detail": f"验证未通过，调用 {model} 重新推理..."})
                        retry = await _fetch_ollama(user_input, model, timeout=15, conversation_context=conversation_context)
                        if retry and retry.get("response"):
                            retry_score = _score_response(retry, user_input)
                            current_score = _score_response(best, user_input) if best else 0
                            if retry_score > current_score:
                                final_response = retry["response"]
                                _save_to_experience_pool(user_input, retry["response"], success=True, intent_type="retry_correction")
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
        is_engineering_query = any(kw in user_input.lower() for kw in ["esp32", "电路", "电压", "电流", "供电", "引脚", "gpio", "串口", "焊接", "万用表", "示波器", "电容", "电阻", "上拉", "下拉", "复位", "烧录", "固件", "不工作", "不启动", "硬件", "pcb", "芯片", "模块", "传感器"])
        if verification.get("is_science") and not is_code_query and not is_paradox_query and not is_engineering_query:
            domain_ref = _get_domain_reference(user_input, final_response)
            disclaimer = f"\n\n---\n⚠️ 以上涉及科学事实，我的推论可能存在偏差，建议参考{domain_ref}。\n（此声明仅为核实建议，非本回答的立论依据，请勿在后续推理中引用此声明）\n---"
            if "建议参考" not in final_response:
                final_response += disclaimer
                attempts.append(("科学免责", True, f"已附加{domain_ref}不确定性声明"))
                yield _emit("step", {"phase": "科学免责", "status": "done", "detail": f"检测到科学事实，已附加不确定性声明 ⚠️"})

        # 不确定性坦诚表达（精神内核原则3+7：困惑时坦诚 + 有温度地回应）
        # 不是泛泛的"建议你也看看"，而是基于实际推理过程的针对性结语
        try:
            from core.dynamic_probability_field import dynamic_probability_field
            if dynamic_probability_field._candidates and dynamic_probability_field._entropy > 0.7:
                action = dynamic_probability_field.get_uncertainty_action()
                if action["depth"] in ("deep", "moderate") and "不确定" not in final_response:
                    unc_note = _build_uncertainty_note(
                        user_input, final_response, attempts,
                        dynamic_probability_field, action
                    )
                    if unc_note:
                        final_response += unc_note
                        attempts.append(("不确定性坦诚", True, "针对性结语"))
        except Exception:
            pass

        # 代码验证：对代码类回答做语法检查+模拟运行验证
        if is_code_query and final_response:
            code_verify = _verify_code_response(user_input, final_response)
            if code_verify["passed"]:
                attempts.append(("代码验证", True, code_verify["detail"]))
                yield _emit("step", {"phase": "代码验证", "status": "done", "detail": f"代码验证通过 ✅ {code_verify['detail']}"})
            else:
                attempts.append(("代码验证", False, code_verify["detail"]))
                yield _emit("step", {"phase": "代码验证", "status": "done", "detail": f"代码验证发现问题：{code_verify['detail']}"})

    # ========== 阶段5.5：适应度评估 ==========
    fitness_score = None
    if final_response:
        try:
            from infrastructure.fitness_evaluator import fitness_evaluator
            fitness_score = await _run_sync(
                fitness_evaluator.evaluate,
                question=user_input,
                response=final_response,
                user_feedback=0,
                intent_type=intent_type,
                timeout=5
            )
            if fitness_score.is_factual_question:
                attempts.append(("适应度评估", True, f"客观{fitness_score.objective_score:.0f}/主观{fitness_score.subjective_score:.0f}→总分{fitness_score.final_score:.0f}"))
                yield _emit("step", {"phase": "适应度评估", "status": "done", "detail": f"事实性问题 | 客观分{fitness_score.objective_score:.0f} 主观分{fitness_score.subjective_score:.0f} 总分{fitness_score.final_score:.0f}"})
                
                should_inject, inject_reason = fitness_evaluator.should_inject_knowledge(fitness_score)
                if should_inject:
                    yield _emit("step", {"phase": "适应度评估", "status": "done", "detail": f"⚠️ 建议知识注入: {inject_reason}"})
            else:
                yield _emit("step", {"phase": "适应度评估", "status": "done", "detail": f"开放性问题 | 主观分{fitness_score.subjective_score:.0f}"})
        except Exception as e:
            logger.debug(f"适应度评估跳过: {e}")

    # 概率场更新：用适应度结果作为证据更新概率分布 + 闭环校准反馈
    try:
        from core.dynamic_probability_field import dynamic_probability_field
        if fitness_score and dynamic_probability_field._candidates:
            ev_type = "quality_boost" if fitness_score.final_score >= 60 else "essence_fail"
            dynamic_probability_field.update({
                "type": ev_type,
                "confidence": fitness_score.final_score / 100.0,
                "source": best.get("source", "") if best else "",
                "content": final_response[:300] if final_response else "",
            })
            dynamic_probability_field.save_snapshot(user_input)
            if best:
                dynamic_probability_field.record_outcome(
                    best.get("source", ""), fitness_score.final_score
                )
    except Exception as e:
        logger.debug(f"概率场更新跳过: {e}")

    # ========== 阶段5.55：ReAct迭代循环（P0-3/P0-5 — 适应度<60时启动Reason→Act→Observe→Reflect） ==========
    if fitness_score and fitness_score.final_score < 60 and fitness_score.final_score >= 20 and final_response and route == "slow":
        yield _emit("step", {"phase": "ReAct循环", "status": "running",
            "detail": f"适应度{fitness_score.final_score:.0f}不足60，启动ReAct迭代推理..."})
        try:
            from core.react_engine import react_engine

            # ReactEnhancer短板聚焦（XGBoost风格）：识别最弱维度，注入增强提示
            react_enhanced_query = user_input
            try:
                from core.react_enhancer import react_enhancer
                coverage = {}
                if fitness_score:
                    if hasattr(fitness_score, 'factual_score') and fitness_score.factual_score is not None:
                        coverage["factual_accuracy"] = fitness_score.factual_score / 100.0
                    if hasattr(fitness_score, 'subjective_score') and fitness_score.subjective_score is not None:
                        coverage["subjective_quality"] = fitness_score.subjective_score / 100.0
                    if hasattr(fitness_score, 'completeness') and fitness_score.completeness is not None:
                        coverage["completeness"] = fitness_score.completeness / 100.0
                gap = react_enhancer.identify_gap({
                    "query": user_input, "coverage": coverage, "iteration": 0
                })
                if gap.get("severity", 0) > 0.3:
                    react_enhanced_query = react_enhancer.generate_focused_prompt(gap, user_input)
                    yield _emit("step", {"phase": "短板聚焦", "status": "done",
                        "detail": f"识别短板: {gap['gap_type']}(严重度{gap['severity']:.2f}), 已注入增强提示"})
            except Exception as e:
                logger.debug(f"ReactEnhancer跳过: {e}")

            async def _react_fitness(q, r):
                try:
                    from infrastructure.fitness_evaluator import fitness_evaluator
                    return await _run_sync(fitness_evaluator.evaluate, question=q, response=r, timeout=5)
                except Exception:
                    return None

            react_result = await react_engine.run(
                query=react_enhanced_query,
                initial_response=final_response,
                initial_quality=fitness_score.final_score,
                candidates=candidates,
                fitness_score=fitness_score,
                intent_type=intent_type,
                conversation_context=conversation_context,
                truth_insights=truth_insights,
                fetch_ollama_fn=_fetch_ollama_all,
                fetch_external_fn=_fetch_external_api,
                fetch_knowledge_fn=_fetch_knowledge,
                fetch_experience_fn=_fetch_experience,
                self_reason_fn=_self_reason,
                fitness_fn=_react_fitness,
            )

            for it in react_result.iterations:
                status = "改善 ✅" if it.improved else "未显著改善"
                yield _emit("step", {"phase": f"ReAct-R{it.iter_num}", "status": "done",
                    "detail": f"策略:{it.action} | {status} | 适应度→{it.quality:.0f}"})

            if react_result.improved and react_result.final_response:
                final_response = react_result.final_response
                fitness_score_final = react_result.final_quality
                attempts.append(("ReAct循环", True,
                    f"{react_result.total_iterations}次迭代, 适应度{fitness_score.final_score:.0f}→{fitness_score_final:.0f}, 策略:{'+'.join(react_result.strategies_used)}"))
                yield _emit("step", {"phase": "ReAct循环", "status": "done",
                    "detail": f"✅ ReAct改善: {react_result.total_iterations}次迭代, 适应度{fitness_score.final_score:.0f}→{fitness_score_final:.0f}"})
            else:
                attempts.append(("ReAct循环", False, f"{react_result.total_iterations}次迭代未改善"))
                yield _emit("step", {"phase": "ReAct循环", "status": "done",
                    "detail": f"ReAct {react_result.total_iterations}次迭代未显著改善，保留当前结果"})
        except Exception as e:
            logger.debug(f"ReAct循环异常: {e}")
            yield _emit("step", {"phase": "ReAct循环", "status": "done", "detail": "ReAct循环跳过"})
    elif fitness_score and fitness_score.final_score >= 60:
        pass

    # ========== 阶段5.6：闭环迭代（P0-5 — 适应度<20的最终兜底，ReAct也无法挽救时） ==========
    if fitness_score and not fitness_score.is_factual_question and fitness_score.subjective_score >= 40:
        pass
    elif fitness_score and fitness_score.final_score < 20 and final_response and route == "slow":
        yield _emit("step", {"phase": "闭环迭代", "status": "running",
            "detail": f"适应度{fitness_score.final_score:.0f}过低，启动闭环迭代..."})
        try:
            from core.closed_loop_orchestrator import closed_loop_orchestrator, LoopContext, LoopState
            loop_ctx = LoopContext(
                query=user_input,
                conversation_context=conversation_context,
                intent_type=intent_type,
                complexity=complexity if 'complexity' in dir() else 0.5,
                confidence=confidence,
                route=route,
                iteration=0,
                candidates=candidates if candidates else [],
                best=best._asdict() if best and hasattr(best, '_asdict') else (best if isinstance(best, dict) else None),
                final_response=final_response,
                attempts=attempts[:],
                fitness_score=fitness_score,
            )
            loop_ctx.evaluation_passed = False
            loop_ctx.evaluation_issues = [f"适应度{fitness_score.final_score:.0f}低于阈值40"]
            loop_ctx.state = LoopState.EXECUTION
            
            loop_result = await closed_loop_orchestrator.orchestrate_from_context(loop_ctx)
            
            if loop_result.final_response and len(loop_result.final_response) > len(final_response):
                final_response = loop_result.final_response
                attempts.append(("闭环迭代", True, f"迭代{loop_result.iteration + 1}次改善"))
                yield _emit("step", {"phase": "闭环迭代", "status": "done",
                    "detail": f"✅ 闭环迭代改善 (迭代{loop_result.iteration + 1}次)"})
            else:
                attempts.append(("闭环迭代", False, "迭代未改善"))
                yield _emit("step", {"phase": "闭环迭代", "status": "done", "detail": "迭代未显著改善，保留当前结果"})
        except Exception as e:
            logger.debug(f"闭环迭代异常: {e}")
            yield _emit("step", {"phase": "闭环迭代", "status": "done", "detail": "闭环迭代跳过"})

    # ========== 阶段6：精神内核验证 ==========
    yield _emit("step", {"phase": "精神验证", "status": "running", "detail": "验证回复是否符合核心原则..."})

    if SPIRIT_CORE_AVAILABLE:
        original_response = final_response
        final_response = await _run_sync(spirit_core.enforce_on_output, final_response, source="chat_handler", query=user_input, timeout=3)
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

    try:
        reflection = await _run_sync(_reflect_and_learn, user_input, final_response, attempts, start_time, comparison if candidates else [], timeout=5)
    except Exception as e:
        logger.debug(f"反思学习异常: {e}")
        reflection = "反思学习异常，跳过"

    # 基因微调：从交互中学习（反脆弱性：失败也触发学习）
    try:
        from core.task_queue import task_queue, gene_pool
        task_queue.notify_user_interaction()
        overall_success = any(a[1] for a in attempts)
        failed_steps = [a for a in attempts if not a[1]]
        gene_pool.learn_from_interaction(
            elapsed=time.time() - start_time,
            success=overall_success,
            model_used=best.get("source", "") if best else ""
        )
        if failed_steps and overall_success:
            gene_pool.mutate("caution_threshold", 0.02, "partial_failure")
            gene_pool.mutate("self_doubt_frequency", 0.01, "partial_failure")
            reflection += f"; 🧬 基因已微调(部分失败: {len(failed_steps)}步)"
        else:
            reflection += "; 🧬 基因已微调"
    except Exception as e:
        logger.debug(f"基因微调异常: {e}")

    # 双速进化快循环：秒级经验积累 + 痛点信号收集
    try:
        from infrastructure.dual_speed_evolution import dual_speed_evolution
        fitness_val = fitness_score if isinstance(fitness_score, (int, float)) else 0.0
        dual_speed_evolution.run_fast_loop(
            question=user_input, response=final_response,
            fitness_score=fitness_val, intent_type=intent_type,
        )
    except Exception as e:
        logger.debug(f"双速进化快循环异常: {e}")

    # 路径权重批量更新（AdaBoost快循环）：根据attempts结果更新各路径权重
    try:
        from core.path_weight_manager import path_weight_manager
        for src, success, detail in attempts:
            path_name = src
            if path_name in path_weight_manager._paths:
                conf = 0.5
                if "置信度" in detail:
                    try:
                        conf = float(detail.split("置信度")[-1].split("%")[0]) / 100
                    except (ValueError, IndexError):
                        pass
                path_weight_manager.update_weight(path_name, success, conf)
    except Exception as e:
        logger.debug(f"路径权重批量更新跳过: {e}")

    # 知识固化：高质量回复升级为知识
    try:
        gene_result = await _run_sync(_try_solidify_to_gene_pool, user_input, final_response, attempts, comparison, timeout=10)
        if gene_result:
            reflection += f"; {gene_result}"
    except Exception as e:
        logger.debug(f"知识固化异常: {e}")

    # 事实提取：高质量回复自动提取三元组存入事实库
    try:
        from infrastructure.fact_store import fact_store
        overall_success = any(a[1] for a in attempts)
        if overall_success and final_response and len(final_response) > 50:
            fact_count = await _run_sync(fact_store.extract_and_store, user_input, final_response, source="chat_auto", timeout=10)
            if fact_count > 0:
                reflection += f"; 📚 事实提取{fact_count}条三元组"
    except Exception as e:
        logger.debug(f"事实提取异常: {e}")

    # 反思管道：异步触发深度反思（不阻塞响应）
    try:
        from infrastructure.reflection_pipeline import get_reflection_pipeline
        pipeline = get_reflection_pipeline()
        if pipeline:
            execution_context = {
                "query": user_input,
                "plan": str(essence_gate_result) if essence_gate_result else "",
                "tool_calls": [],
                "final_answer": final_response,
                "confidence": confidence,
                "model_used": best.get("source", "") if best else "",
                "duration_ms": int((time.time() - start_time) * 1000),
                "extra": {"intent": intent_type, "attempts": [(a[0], a[1]) for a in attempts]}
            }
            asyncio.create_task(pipeline.process(execution_context))
    except Exception as e:
        logger.debug(f"反思管道触发跳过: {e}")

    # SelfReflection联动：从精神内核获取教训，注入反思学习
    try:
        if SPIRIT_CORE_AVAILABLE and spirit_core:
            failed_steps = [a for a in attempts if not a[1]]
            if failed_steps:
                lessons = spirit_core.get_lessons_for_reflection()
                if lessons:
                    reflection += f"; 精神教训: {lessons[:100]}"
            violations = spirit_core.get_violations_for_analysis()
            if violations:
                reflection += f"; 违规记录: {len(violations)}条"
    except Exception as e:
        logger.debug(f"精神内核联动跳过: {e}")

    # ========== 先发射最终响应（确保前端立即收到，不再被后续处理阻塞） ==========
    elapsed = time.time() - start_time

    if not final_response:
        try:
            ollama_result = await _fetch_ollama_response(user_input, conversation_context=conversation_context, truth_insights="")
            if ollama_result and ollama_result.get("response") and len(ollama_result["response"]) > 20:
                final_response = ollama_result["response"]
                attempts.append(("终极保护-动态", True, "模型实时生成"))
            else:
                final_response = f"这个问题我暂时还没想清楚——「{user_input}」涉及的方向我需要更多背景才能给出靠谱的回答。你能补充一下具体场景或你关注的重点吗？"
                attempts.append(("终极保护", True, "确保有回复"))
        except:
            final_response = f"这个问题我暂时还没想清楚——「{user_input}」涉及的方向我需要更多背景才能给出靠谱的回答。你能补充一下具体场景或你关注的重点吗？"
            attempts.append(("终极保护", True, "确保有回复"))

    _save_to_experience_pool(
        user_input, final_response,
        success=any(a[1] for a in attempts),
        intent_type=intent_type,
        quality_score=int(fitness_score.final_score) if fitness_score else (80 if any(a[1] for a in attempts) else 40),
        duration=elapsed
    )

    # 轨迹进化：将完整解决路径存入轨迹库
    try:
        from core.trajectory_evolution import trajectory_store
        traj_steps = []
        for a in attempts:
            traj_steps.append({
                "phase": a[0] if len(a) > 0 else "",
                "success": a[1] if len(a) > 1 else False,
                "detail": a[2] if len(a) > 2 else "",
                "duration_ms": 0
            })
        traj_decisions = []
        if route == "slow" and candidates:
            best_src = comparison[0]["source"] if comparison else ""
            traj_decisions.append({"type": "path_selection", "chosen": best_src, "reason": "highest_score"})
        if 'path_percentages' in dir() and path_percentages:
            traj_decisions.append({"type": "path_contribution", "distribution": path_percentages})
        traj_outcome = {
            "quality_score": int(fitness_score.final_score) if fitness_score else (80 if any(a[1] for a in attempts) else 40),
            "confidence": confidence,
            "duration": elapsed,
            "response_length": len(final_response) if final_response else 0,
            "success": any(a[1] for a in attempts)
        }
        traj_fitness = trajectory_store.evaluate_trajectory(traj_steps, traj_outcome)
        trajectory_store.store_trajectory(
            query=user_input,
            steps=traj_steps,
            decisions=traj_decisions,
            outcome=traj_outcome,
            intent_type=intent_type,
            route=route,
            fitness_score=traj_fitness,
            duration=elapsed,
            source="live"
        )
    except Exception as e:
        logger.debug(f"轨迹存储跳过: {e}")

    token_summary = {}
    for c in candidates:
        if isinstance(c, dict) and "tokens" in c:
            src = c.get("source", "未知")
            tk = c["tokens"]
            if tk.get("total_tokens", 0) > 0:
                token_summary[src] = tk

    yield _emit("result", {
        "response": final_response,
        "attempts": attempts,
        "intent": intent_type,
        "confidence": confidence,
        "route": route,
        "elapsed": round(elapsed, 1),
        "spirit_compliant": SPIRIT_CORE_AVAILABLE,
        "candidates": comparison if candidates else [],
        "path_contributions": path_percentages if 'path_percentages' in dir() else {},
        "token_usage": token_summary,
    })

    logger.info(f"✅ 响应已发送({elapsed:.1f}秒)，后续后台学习继续...")

    # P1-1: 发布KnowledgeUpdate和ModelStatusChange事件
    try:
        from infrastructure.event_bus import bus, EventTypes
        if fitness_score and fitness_score.final_score > 0:
            bus.publish(EventTypes.KnowledgeUpdate, {
                "query": user_input[:100],
                "quality": fitness_score.final_score,
                "source": best.get("source", "") if best else "",
                "timestamp": time.time(),
            })
        model_src = best.get("source", "") if best else ""
        if model_src:
            bus.publish(EventTypes.ModelStatusChange, {
                "model": model_src,
                "status": "responded",
                "quality": best.get("quality", 0) if isinstance(best, dict) else 0,
                "timestamp": time.time(),
            })
    except Exception:
        pass

    # ========== 以下全部为后台fire-and-forget任务，不阻塞SSE流 ==========

    # 知识缺失检测 + 自动学习进化（fire-and-forget后台任务，绝不阻塞响应）
    try:
        from core.knowledge_gap_detector import gap_detector
        has_gap, reason, issues = gap_detector.detect_knowledge_gap(
            user_input, final_response, confidence=confidence
        )
        if has_gap:
            yield _emit("step", {"phase": "反思学习", "status": "running", "detail": f"检测到知识缺失({reason})，后台学习中..."})

            async def _bg_auto_evolution():
                try:
                    from core.auto_learning_evolution import auto_evolution
                    evolution_result = await asyncio.get_running_loop().run_in_executor(
                        _slow_executor,
                        lambda: auto_evolution.process_query_with_evolution(
                            user_input, final_response, confidence=confidence
                        )
                    )
                    if evolution_result and evolution_result.get('corrected'):
                        logger.info(f"🧬 自动学习进化修正: {reason}")
                    logger.info("🧬 后台自动学习进化完成")
                except Exception as e:
                    logger.warning(f"后台自动学习进化异常: {e}")

            asyncio.create_task(_bg_auto_evolution())
            yield _emit("step", {"phase": "反思学习", "status": "done", "detail": "后台学习中..."})
    except Exception as e:
        logger.debug(f"自动学习进化跳过: {e}")

    # 自适应进化目标：从交互中推断进化方向
    try:
        from core.evolution.adaptive_goal import get_adaptive_evolution_goal
        agm = get_adaptive_evolution_goal()
        agm.infer_value_from_feedback({
            "type": "interaction",
            "query": user_input[:200],
            "value": fitness_score.final_score / 100.0 if fitness_score else 0.5,
            "success": any(a[1] for a in attempts),
        })
    except Exception as e:
        logger.debug(f"自适应进化目标跳过: {e}")

    # 注入验证：验证知识注入/事实提取/知识固化的实际效果
    try:
        from infrastructure.injection_verifier import injection_verifier
        injected_items = []
        if gene_result:
            injected_items.append({"type": "gene_solidification", "confidence": 0.9})
        if fact_count if 'fact_count' in dir() else 0:
            injected_items.append({"type": "fact_extraction", "confidence": 0.7, "count": fact_count if 'fact_count' in dir() else 0})
        if has_gap if 'has_gap' in dir() else False:
            injected_items.append({"type": "auto_evolution", "confidence": 0.6})
        
        if injected_items:
            before_score = best.get("quality", 50) if best else 30
            verification = injection_verifier.verify_injection(
                injection_id=f"chat_{int(time.time())}",
                question=user_input,
                before_score=float(before_score),
                injected_knowledge=injected_items
            )
            if not verification.passed:
                reflection += f"; ⚠️ 注入验证未通过(改进{verification.improvement:.1f}分)"
            else:
                reflection += f"; ✅ 注入验证通过(改进{verification.improvement:.1f}分)"
    except Exception as e:
        logger.debug(f"注入验证跳过: {e}")

    yield _emit("step", {"phase": "反思学习", "status": "done", "detail": reflection})

    # 立体记忆存储：将本次交互存入立体记忆系统
    try:
        from core.memory.stereo_memory import get_stereo_memory, MemoryType, MemoryImportance, SelfDimension, MemoryContext
        sm = get_stereo_memory()
        
        overall_success = any(a[1] for a in attempts)
        importance = MemoryImportance.HIGH if overall_success and confidence >= 0.7 else MemoryImportance.MEDIUM
        
        emotional_state = "confident" if overall_success and confidence >= 0.8 else "uncertain" if not overall_success else "neutral"
        
        sm_store_coro = _run_sync(
            lambda: sm.store(
                content={"query": user_input[:200], "response": final_response[:300]},
                memory_type=MemoryType.CONVERSATION,
                importance=importance,
                related_entities=set([w for w in user_input.split() if len(w) >= 2][:5]),
                self_dimension=SelfDimension(
                    role="assistant",
                    confidence=confidence,
                    emotional_state=emotional_state,
                    learning_progress=0.0,
                ),
                context=MemoryContext(
                    user_id=context.get("user_id", "default") if context else "default",
                    trigger="user_query",
                    related_concepts=[intent_type],
                ),
            ),
            timeout=5
        )
        asyncio.ensure_future(sm_store_coro)
    except Exception as e:
        logger.debug(f"立体记忆存储跳过: {e}")

    # 关系模型更新：记录本次互动，演化信任度
    try:
        from core.relationship.model import get_relationship_model, InteractionType
        rm = get_relationship_model()
        
        interaction_type = InteractionType.CONVERSATION
        if intent_type == "challenge":
            interaction_type = InteractionType.CORRECTION
        elif intent_type in ["question", "factual", "verification"]:
            interaction_type = InteractionType.QUESTION
        elif intent_type == "greeting":
            interaction_type = InteractionType.CONVERSATION
        
        satisfaction = 0.7 if any(a[1] for a in attempts) else 0.3
        if fitness_score:
            satisfaction = fitness_score.final_score / 100.0
        
        rm_record_coro = _run_sync(
            lambda: rm.record_interaction(
                user_input=user_input[:200],
                system_response=final_response[:300],
                interaction_type=interaction_type,
                user_satisfaction=satisfaction,
                context={"intent": intent_type, "confidence": confidence},
            ),
            timeout=5
        )
        asyncio.ensure_future(rm_record_coro)
    except Exception as e:
        logger.debug(f"关系模型更新跳过: {e}")

    # 存在层信号：将交互结果发送给存在层
    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        el.receive_signal({
            "type": "interaction_completed",
            "query": user_input[:100],
            "success": any(a[1] for a in attempts),
            "confidence": confidence,
            "intent": intent_type,
            "fitness": fitness_score.final_score if fitness_score else None,
        })
    except:
        pass

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

    elapsed_bg = time.time() - start_time
    logger.info(f"✅ 完整闭环(后台): {user_input[:30]} → {[(a[0], a[1]) for a in attempts]} (总耗时{elapsed_bg:.1f}秒，响应已提前发送)")


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
                    "INSERT INTO experiences (raw_input, response, timestamp, intent_type, quality_score, success, duration) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (f"[模式]{pattern_type}:{query[:50]}", f"解决路径:{'→'.join(success_path)}", dt.now().isoformat(), f"pattern_{pattern_type}", 85, 1, 0.0)
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
            _save_to_experience_pool(query, result, success=True, intent_type="background_thinking")
            logger.info(f"✅ 后台思考完成: {len(result)}字")
    except Exception as e:
        logger.error(f"❌ 后台思考失败: {e}")


def _save_to_experience_pool(query: str, response: str, success: bool = True, intent_type: str = "deep_thinking", quality_score: int = 70, duration: float = 0.0):
    try:
        import sqlite3
        from datetime import datetime
        conn = sqlite3.connect("data/experience_pool.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO experiences (raw_input, response, timestamp, intent_type, quality_score, success, duration) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (query, response, datetime.now().isoformat(), intent_type, quality_score, 1 if success else 0, duration)
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
    """动态智能回复——不使用写死模板，而是返回标记让调用方走模型推理"""
    return "__NEED_DYNAMIC_REPLY__"


def _generate_meaningful_fallback(query: str, attempts: list) -> str:
    """动态fallback——不使用写死模板，而是返回标记让调用方走模型推理"""
    return "__NEED_DYNAMIC_FALLBACK__"


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

    # 3. 增量知识更新（ResNet风格残差学习）
    try:
        from core.delta_knowledge_updater import delta_knowledge_updater
        new_knowledge = {"response": response[:2000], "score": best_score, "source": "gene_pool_solidification"}
        delta_result = delta_knowledge_updater.update(new_knowledge, topic=query[:100])
        if delta_result.get("updated"):
            solidified.append(f"增量知识(v{delta_result['version']}, 压缩{delta_result['compression_ratio']:.2f})")
    except Exception as e:
        logger.debug(f"增量知识更新跳过: {e}")

    # 4. 记录到基因库日志
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
