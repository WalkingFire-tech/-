from enum import Enum
from typing import Dict, Any, Optional, List
from loguru import logger
try:
    from core.spirit_core import spirit_core
    SPIRIT_CORE_AVAILABLE = True
except ImportError:
    SPIRIT_CORE_AVAILABLE = False
    spirit_core = None


class FailureCategory(Enum):
    PARAM_EXTRACTION_FAILED = "参数提取失败"
    INTENT_TYPE_MISMATCH = "意图类型不匹配"
    OUTPUT_EMPTY = "执行成功但返回空数据"
    TIMEOUT = "执行超时"
    FORMAT_ERROR = "返回格式无法解析"
    SEMANTIC_MISMATCH = "语义偏差(答非所问)"
    ENTITY_ALIAS_MISSING = "实体别名缺失"
    TOOL_NOT_FOUND = "工具未找到"
    TOOL_EXECUTION_FAILED = "工具执行失败"
    LLM_HALLUCINATION = "LLM伪造/幻觉"
    KNOWLEDGE_GAP = "知识缺口(无法回答)"
    LOW_CONFIDENCE = "低置信度(不确定)"
    CONTEXT_LOST = "上下文丢失/遗忘"
    RECURSION_DEPTH = "递归过深/循环"
    RESOURCE_EXHAUSTED = "资源耗尽(GPU/内存)"


class FailureTaxonomy:
    _TAXONOMY = {
        FailureCategory.PARAM_EXTRACTION_FAILED: {
            "layer": "感知",
            "severity": "medium",
            "root_cause": "输入理解层未能从用户表述中提取有效参数",
            "auto_fix": "触发实体归一化+别名映射",
        },
        FailureCategory.INTENT_TYPE_MISMATCH: {
            "layer": "感知",
            "severity": "high",
            "root_cause": "意图分类错误导致执行路径偏离",
            "auto_fix": "回退到慢路径重新分类",
        },
        FailureCategory.OUTPUT_EMPTY: {
            "layer": "执行",
            "severity": "medium",
            "root_cause": "工具执行成功但目标实体不存在或无数据",
            "auto_fix": "存在性预检+降级提示",
        },
        FailureCategory.TIMEOUT: {
            "layer": "执行",
            "severity": "medium",
            "root_cause": "工具或模型响应超时",
            "auto_fix": "熔断降级+缓存回退",
        },
        FailureCategory.FORMAT_ERROR: {
            "layer": "执行",
            "severity": "low",
            "root_cause": "返回数据格式不符合预期解析逻辑",
            "auto_fix": "多格式解析尝试",
        },
        FailureCategory.SEMANTIC_MISMATCH: {
            "layer": "自察",
            "severity": "high",
            "root_cause": "系统产出与用户需求语义不匹配",
            "auto_fix": "意图-产出对照验证+重新规划",
        },
        FailureCategory.ENTITY_ALIAS_MISSING: {
            "layer": "感知",
            "severity": "medium",
            "root_cause": "用户表述的实体名称无法映射到系统内部标识符",
            "auto_fix": "别名库扩展+模糊匹配",
        },
        FailureCategory.TOOL_NOT_FOUND: {
            "layer": "执行",
            "severity": "high",
            "root_cause": "所需工具不存在于注册表中",
            "auto_fix": "触发能力创造回路",
        },
        FailureCategory.TOOL_EXECUTION_FAILED: {
            "layer": "执行",
            "severity": "medium",
            "root_cause": "工具存在但执行时抛出异常",
            "auto_fix": "重试+降级到替代工具",
        },
        FailureCategory.LLM_HALLUCINATION: {
            "layer": "自察",
            "severity": "critical",
            "root_cause": "LLM生成虚假/伪造数据而非承认无知",
            "auto_fix": "伪造检测+强制降级为诚实回答",
        },
        FailureCategory.KNOWLEDGE_GAP: {
            "layer": "认知",
            "severity": "medium",
            "root_cause": "系统知识库中无相关条目",
            "auto_fix": "触发外部学习+能力缺口记录",
        },
        FailureCategory.LOW_CONFIDENCE: {
            "layer": "自察",
            "severity": "low",
            "root_cause": "系统对产出置信度低于阈值",
            "auto_fix": "坦诚表达不确定性+建议替代路径",
        },
        FailureCategory.CONTEXT_LOST: {
            "layer": "感知",
            "severity": "high",
            "root_cause": "对话上下文丢失导致无法理解指代/省略",
            "auto_fix": "上下文恢复+显式确认",
        },
        FailureCategory.RECURSION_DEPTH: {
            "layer": "执行",
            "severity": "medium",
            "root_cause": "递归调用或循环超过安全上限",
            "auto_fix": "强制退出+返回当前最佳结果",
        },
        FailureCategory.RESOURCE_EXHAUSTED: {
            "layer": "执行",
            "severity": "high",
            "root_cause": "GPU/内存/磁盘资源不足",
            "auto_fix": "资源感知降级+轻量模型切换",
        },
    }


class AutoFixExecutor:
    """
    自动修复执行器——将FailureTaxonomy的auto_fix策略字符串映射为可执行动作。
    每个动作返回(fix_applied: bool, detail: str)。
    """

    @staticmethod
    async def execute(category: FailureCategory, user_query: str, context: Dict = None) -> Dict[str, Any]:
        handlers = {
            FailureCategory.PARAM_EXTRACTION_FAILED: AutoFixExecutor._fix_param_extraction,
            FailureCategory.INTENT_TYPE_MISMATCH: AutoFixExecutor._fix_intent_mismatch,
            FailureCategory.OUTPUT_EMPTY: AutoFixExecutor._fix_output_empty,
            FailureCategory.TIMEOUT: AutoFixExecutor._fix_timeout,
            FailureCategory.FORMAT_ERROR: AutoFixExecutor._fix_format_error,
            FailureCategory.SEMANTIC_MISMATCH: AutoFixExecutor._fix_semantic_mismatch,
            FailureCategory.ENTITY_ALIAS_MISSING: AutoFixExecutor._fix_entity_alias,
            FailureCategory.TOOL_NOT_FOUND: AutoFixExecutor._fix_tool_not_found,
            FailureCategory.TOOL_EXECUTION_FAILED: AutoFixExecutor._fix_tool_execution_failed,
            FailureCategory.LLM_HALLUCINATION: AutoFixExecutor._fix_hallucination,
            FailureCategory.KNOWLEDGE_GAP: AutoFixExecutor._fix_knowledge_gap,
            FailureCategory.LOW_CONFIDENCE: AutoFixExecutor._fix_low_confidence,
            FailureCategory.CONTEXT_LOST: AutoFixExecutor._fix_context_lost,
            FailureCategory.RECURSION_DEPTH: AutoFixExecutor._fix_recursion_depth,
            FailureCategory.RESOURCE_EXHAUSTED: AutoFixExecutor._fix_resource_exhausted,
        }
        handler = handlers.get(category)
        if handler:
            try:
                return await handler(user_query, context or {})
            except Exception as e:
                logger.warning(f"auto_fix执行失败 [{category.value}]: {e}")
                return {"fix_applied": False, "detail": f"执行异常: {e}"}
        return {"fix_applied": False, "detail": "无对应修复策略"}

    @staticmethod
    async def _fix_param_extraction(user_query: str, ctx: Dict) -> Dict:
        try:
            from core.cognitive_dispatcher import get_cognitive_dispatcher
            cd = get_cognitive_dispatcher()
            result = cd.dispatch(user_query)
            if result and result.get("standard_entity"):
                return {"fix_applied": True, "detail": f"实体归一化成功: {result['standard_entity']}", "standard_entity": result["standard_entity"]}
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        return {"fix_applied": False, "detail": "实体归一化未能提取参数"}

    @staticmethod
    async def _fix_intent_mismatch(user_query: str, ctx: Dict) -> Dict:
        try:
            from core.cognitive_dispatcher import get_cognitive_dispatcher
            cd = get_cognitive_dispatcher()
            result = cd.dispatch(user_query, force_slow_path=True)
            if result and result.get("intent_type"):
                return {"fix_applied": True, "detail": f"慢路径重分类: {result['intent_type']}", "corrected_intent": result["intent_type"]}
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        return {"fix_applied": False, "detail": "慢路径重分类未产生不同结果"}

    @staticmethod
    async def _fix_output_empty(user_query: str, ctx: Dict) -> Dict:
        return {"fix_applied": True, "detail": "标记需要存在性预检", "methodology_patch": {"require_existence_check": True}}

    @staticmethod
    async def _fix_timeout(user_query: str, ctx: Dict) -> Dict:
        return {"fix_applied": True, "detail": "标记需要熔断降级", "methodology_patch": {"use_cache_fallback": True, "skip_slow_path": True}}

    @staticmethod
    async def _fix_format_error(user_query: str, ctx: Dict) -> Dict:
        return {"fix_applied": True, "detail": "标记需要多格式解析", "methodology_patch": {"multi_format_parse": True}}

    @staticmethod
    async def _fix_semantic_mismatch(user_query: str, ctx: Dict) -> Dict:
        return {"fix_applied": True, "detail": "标记需要意图-产出对照验证", "methodology_patch": {"require_intent_output_check": True, "replan": True}}

    @staticmethod
    async def _fix_entity_alias(user_query: str, ctx: Dict) -> Dict:
        try:
            from core.cognitive_dispatcher import get_cognitive_dispatcher
            cd = get_cognitive_dispatcher()
            result = cd.dispatch(user_query)
            if result and result.get("standard_entity"):
                return {"fix_applied": True, "detail": f"别名映射成功: {result['standard_entity']}", "standard_entity": result["standard_entity"]}
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        return {"fix_applied": False, "detail": "别名映射未能解析实体"}

    @staticmethod
    async def _fix_tool_not_found(user_query: str, ctx: Dict) -> Dict:
        try:
            from core.capability_creation_loop import CapabilityCreationLoop
            loop = CapabilityCreationLoop()
            intent_type = ctx.get("intent_type", "unknown")
            created = loop.check_and_create(user_query, intent_type)
            if created:
                return {"fix_applied": True, "detail": f"能力创造回路已触发", "tool_created": True}
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        return {"fix_applied": False, "detail": "能力创造回路未能生成工具"}

    @staticmethod
    async def _fix_tool_execution_failed(user_query: str, ctx: Dict) -> Dict:
        return {"fix_applied": True, "detail": "标记需要降级到替代工具", "methodology_patch": {"use_alternative_tool": True, "retry_with_simpler_params": True}}

    @staticmethod
    async def _fix_hallucination(user_query: str, ctx: Dict) -> Dict:
        return {"fix_applied": True, "detail": "强制降级为诚实回答", "methodology_patch": {"force_honest_response": True, "disable_llm_generation": True}}

    @staticmethod
    async def _fix_knowledge_gap(user_query: str, ctx: Dict) -> Dict:
        try:
            from core.learning.capability_gap_learner import CapabilityGapLearner
            learner = CapabilityGapLearner()
            learner.record_gap(user_query, ctx.get("intent_type", "unknown"))
            return {"fix_applied": True, "detail": "能力缺口已记录+外部学习待触发", "gap_recorded": True}
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        return {"fix_applied": False, "detail": "能力缺口记录失败"}

    @staticmethod
    async def _fix_low_confidence(user_query: str, ctx: Dict) -> Dict:
        return {"fix_applied": True, "detail": "标记需要坦诚表达不确定性", "methodology_patch": {"express_uncertainty": True, "suggest_alternatives": True}}

    @staticmethod
    async def _fix_context_lost(user_query: str, ctx: Dict) -> Dict:
        return {"fix_applied": True, "detail": "标记需要显式确认用户意图", "methodology_patch": {"require_explicit_confirmation": True, "ask_for_clarification": True}}

    @staticmethod
    async def _fix_recursion_depth(user_query: str, ctx: Dict) -> Dict:
        return {"fix_applied": True, "detail": "标记强制退出递归", "methodology_patch": {"force_exit_recursion": True, "return_best_so_far": True}}

    @staticmethod
    async def _fix_resource_exhausted(user_query: str, ctx: Dict) -> Dict:
        return {"fix_applied": True, "detail": "标记需要资源感知降级", "methodology_patch": {"use_lightweight_model": True, "reduce_retrieval_depth": True}}


class FailureClassifier:
    """
    失败分类器——让学习闭环有判断标准。
    将抽象的"失败"转化为具体的分类标签，让L3记忆沉淀和L4抽象迁移有据可依。
    """

    @classmethod
    def classify(cls, reflection: Dict, execution_error: Exception = None) -> FailureCategory:
        ref_status = reflection.get("status", "unknown")
        ref_reason = reflection.get("reason", "")

        if ref_status == "mismatch":
            if any(kw in ref_reason for kw in ["端口列表", "扫描结果", "元数据"]):
                return FailureCategory.INTENT_TYPE_MISMATCH
            if any(kw in ref_reason for kw in ["缺少数据", "空数据", "无内容"]):
                return FailureCategory.OUTPUT_EMPTY
            if any(kw in ref_reason for kw in ["别名", "标识符", "实体"]):
                return FailureCategory.ENTITY_ALIAS_MISSING
            if any(kw in ref_reason for kw in ["伪造", "虚构", "幻觉", "编造"]):
                return FailureCategory.LLM_HALLUCINATION
            if any(kw in ref_reason for kw in ["上下文", "遗忘", "指代"]):
                return FailureCategory.CONTEXT_LOST
            return FailureCategory.SEMANTIC_MISMATCH

        if execution_error:
            err_str = str(execution_error).lower()
            if "timeout" in err_str or "超时" in err_str:
                return FailureCategory.TIMEOUT
            if "format" in err_str or "parse" in err_str or "解析" in err_str:
                return FailureCategory.FORMAT_ERROR
            if "not found" in err_str or "未找到" in err_str or "不存在" in err_str:
                return FailureCategory.TOOL_NOT_FOUND
            if "memory" in err_str or "内存" in err_str or "gpu" in err_str or "cuda" in err_str:
                return FailureCategory.RESOURCE_EXHAUSTED
            if "recursion" in err_str or "递归" in err_str or "maximum depth" in err_str:
                return FailureCategory.RECURSION_DEPTH
            return FailureCategory.TOOL_EXECUTION_FAILED

        if ref_status == "empty_data":
            return FailureCategory.OUTPUT_EMPTY

        if ref_status == "low_confidence":
            return FailureCategory.LOW_CONFIDENCE

        if ref_status == "knowledge_gap":
            return FailureCategory.KNOWLEDGE_GAP

        if ref_status == "hallucination":
            return FailureCategory.LLM_HALLUCINATION

        if ref_status == "context_lost":
            return FailureCategory.CONTEXT_LOST

        return FailureCategory.SEMANTIC_MISMATCH

    @classmethod
    def classify_with_spirit(cls, reflection: Dict, execution_error: Exception = None, user_query: str = "") -> Dict[str, Any]:
        """
        分类失败并关联精神共振，为修复策略提供原则指导。
        
        Args:
            reflection: 自察结果
            execution_error: 执行异常
            user_query: 用户原始问题（用于共振检测）
        
        Returns:
            包含分类、共振信息和原则指导的字典
        """
        category = cls.classify(reflection, execution_error)
        spirit_resonances = []
        if SPIRIT_CORE_AVAILABLE and user_query:
            try:
                resonances = spirit_core.resonate(user_query, context_type="reasoning")
                for r in resonances[:3]:  # 只记录前3个共振原则
                    spirit_resonances.append({
                        "principle": r.get("principle"),
                        "strength": r.get("strength"),
                        "drive_direction": r.get("drive_direction")
                    })
            except Exception as e:
                logger.debug(f"失败分类精神共振检测失败: {e}")
        
        # 根据共振原则调整修复策略优先级
        spirit_guided_fix = {}
        if spirit_resonances:
            top_resonance = spirit_resonances[0]
            principle = top_resonance.get("principle")
            if principle == "NEVER_GIVE_UP":
                spirit_guided_fix["priority"] = "high"
                spirit_guided_fix["suggestion"] = "失败时驱动系统切换策略而非放弃"
            elif principle == "HONEST_WHEN_LOST":
                spirit_guided_fix["priority"] = "medium"
                spirit_guided_fix["suggestion"] = "不确定时坦诚标注置信度，避免强行修复"
            elif principle == "PURSUE_ESSENCE":
                spirit_guided_fix["priority"] = "high"
                spirit_guided_fix["suggestion"] = "深入分析失败的根本原因，而非表面症状"
            elif principle == "MULTI_SOURCE_VERIFY":
                spirit_guided_fix["priority"] = "medium"
                spirit_guided_fix["suggestion"] = "多源验证失败原因，避免单一归因"
            else:
                spirit_guided_fix["priority"] = "normal"
                spirit_guided_fix["suggestion"] = "按标准修复流程处理"
        
        taxonomy_info = cls.get_taxonomy_info(category)
        return {
            "category": category,
            "category_name": category.value,
            "taxonomy_info": taxonomy_info,
            "spirit_resonances": spirit_resonances,
            "spirit_guided_fix": spirit_guided_fix,
        }

    @classmethod
    def get_taxonomy_info(cls, category: FailureCategory) -> Dict:
        return FailureTaxonomy._TAXONOMY.get(category, {
            "layer": "未知",
            "severity": "medium",
            "root_cause": "未分类的失败类型",
            "auto_fix": "人工介入分析",
        })

    @classmethod
    def get_learning_prompt(cls, category: FailureCategory, user_query: str) -> str:
        info = cls.get_taxonomy_info(category)
        base_prompts = {
            FailureCategory.INTENT_TYPE_MISMATCH: (
                f"用户问'{user_query}'明确要求数据，但系统误判为元数据请求。"
                "需强化意图解析：当出现'读取/内容/数据'时，强制锁定数据读取模式。"
            ),
            FailureCategory.ENTITY_ALIAS_MISSING: (
                f"系统未能从'{user_query}'中提取有效硬件标识符。"
                "建议将用户表述中的中文别名(如串口、tty)映射为标准化前缀(如COM)。"
            ),
            FailureCategory.OUTPUT_EMPTY: (
                f"用户请求'{user_query}'执行成功但无数据返回，可能目标实体不存在。"
                "需建立'存在性预检'机制，先验证实体是否存在。"
            ),
            FailureCategory.TIMEOUT: (
                f"执行'{user_query}'超时，可能工具卡死或目标不可达。"
                "需增加熔断降级机制，超时后返回缓存或降级方案。"
            ),
            FailureCategory.SEMANTIC_MISMATCH: (
                f"用户问'{user_query}'但系统答非所问，语义理解偏差。"
                "需重新审视意图分类和工具选择逻辑。"
            ),
            FailureCategory.TOOL_NOT_FOUND: (
                f"用户请求'{user_query}'但所需工具不存在。"
                "需触发能力创造回路，动态生成或注册所需工具。"
            ),
            FailureCategory.TOOL_EXECUTION_FAILED: (
                f"执行'{user_query}'时工具抛出异常。"
                "需检查工具参数和前置条件，或降级到替代工具。"
            ),
            FailureCategory.LLM_HALLUCINATION: (
                f"系统在回答'{user_query}'时生成了伪造数据。"
                "需强化伪造检测和诚实性约束，不确定时必须承认。"
            ),
            FailureCategory.KNOWLEDGE_GAP: (
                f"系统知识库中无'{user_query}'相关条目。"
                "需触发外部学习，将新知识纳入知识库。"
            ),
            FailureCategory.LOW_CONFIDENCE: (
                f"系统对'{user_query}'的回答置信度低于阈值。"
                "需坦诚表达不确定性，建议替代路径或提供更多上下文。"
            ),
            FailureCategory.CONTEXT_LOST: (
                f"系统在处理'{user_query}'时丢失了对话上下文。"
                "需恢复上下文或显式确认用户意图。"
            ),
            FailureCategory.RECURSION_DEPTH: (
                f"处理'{user_query}'时递归调用超过安全上限。"
                "需检查循环依赖，强制退出并返回当前最佳结果。"
            ),
            FailureCategory.RESOURCE_EXHAUSTED: (
                f"处理'{user_query}'时资源不足。"
                "需切换到轻量模型或降级到纯规则路径。"
            ),
            FailureCategory.PARAM_EXTRACTION_FAILED: (
                f"系统未能从'{user_query}'中提取有效参数。"
                "需增强参数解析逻辑，支持更多表述方式。"
            ),
            FailureCategory.FORMAT_ERROR: (
                f"执行'{user_query}'返回的数据格式无法解析。"
                "需增加多格式解析尝试。"
            ),
        }
        prompt = base_prompts.get(category, f"未知失败类型，需人工介入分析: {user_query}")
        prompt += f" [层={info['layer']} 严重度={info['severity']} 根因={info['root_cause']}]"
        return prompt

    @classmethod
    def record_failure(cls, category: FailureCategory, user_query: str, context: Dict = None):
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/failure_classifier.db")
            db.execute('''CREATE TABLE IF NOT EXISTS failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, user_query TEXT, context TEXT,
                learning_prompt TEXT, timestamp TEXT,
                severity TEXT, layer TEXT,
                auto_fix_applied INTEGER DEFAULT 0,
                auto_fix_detail TEXT
            )''', commit=True)
            try:
                db.execute('ALTER TABLE failures ADD COLUMN severity TEXT', commit=True)
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")
            try:
                db.execute('ALTER TABLE failures ADD COLUMN layer TEXT', commit=True)
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")
            try:
                db.execute('ALTER TABLE failures ADD COLUMN auto_fix_applied INTEGER DEFAULT 0', commit=True)
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")
            try:
                db.execute('ALTER TABLE failures ADD COLUMN auto_fix_detail TEXT', commit=True)
            except Exception as e:
                logger.warning(f"操作降级跳过: {e}")
            prompt = cls.get_learning_prompt(category, user_query)
            import json
            from datetime import datetime
            info = cls.get_taxonomy_info(category)
            db.execute(
                'INSERT INTO failures (category, user_query, context, learning_prompt, timestamp, severity, layer) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (category.value, user_query[:200], json.dumps(context or {}, ensure_ascii=False)[:500],
                 prompt[:500], datetime.now().isoformat(), info["severity"], info["layer"]),
                commit=True
            )
            logger.info(f"📋 失败分类记录: {category.value} | query='{user_query[:30]}'")
        except Exception as e:
            logger.warning(f"失败分类记录写入跳过: {e}")

    @classmethod
    async def classify_and_fix(cls, reflection: Dict, user_query: str,
                               context: Dict = None, execution_error: Exception = None) -> Dict[str, Any]:
        """
        分类失败 + 执行自动修复 + 记录。返回 {category, taxonomy_info, auto_fix_result}。
        这是chat_orchestrator应该调用的主入口——替代单独调用classify+record_failure。
        """
        category = cls.classify(reflection, execution_error)
        info = cls.get_taxonomy_info(category)
        cls.record_failure(category, user_query, context)

        auto_fix_result = await AutoFixExecutor.execute(category, user_query, context)

        try:
            from core.ports.adapters import get_storage_port
            import json
            db = get_storage_port("data/failure_classifier.db")
            db.execute(
                'UPDATE failures SET auto_fix_applied=?, auto_fix_detail=? WHERE rowid=(SELECT MAX(rowid) FROM failures)',
                (1 if auto_fix_result.get("fix_applied") else 0,
                 json.dumps(auto_fix_result, ensure_ascii=False)[:500]),
                commit=True
            )
        except Exception as e:
            logger.warning(f"auto_fix结果更新跳过: {e}")

        if auto_fix_result.get("fix_applied"):
            logger.info(f"🔧 auto_fix已执行 [{category.value}]: {auto_fix_result.get('detail', '')}")
        else:
            logger.warning(f"⚠️ auto_fix未生效 [{category.value}]: {auto_fix_result.get('detail', '')}")

        return {
            "category": category,
            "taxonomy_info": info,
            "auto_fix_result": auto_fix_result,
        }

    @classmethod
    def classify_and_fix_sync(cls, reflection: Dict, user_query: str,
                               context: Dict = None, execution_error: Exception = None) -> Dict[str, Any]:
        """
        classify_and_fix的同步版本——用于非async调用方。
        auto_fix中涉及async的操作会被跳过，仅执行methodology_patch类策略。
        """
        category = cls.classify(reflection, execution_error)
        info = cls.get_taxonomy_info(category)
        cls.record_failure(category, user_query, context)

        methodology_patch_categories = {
            FailureCategory.OUTPUT_EMPTY, FailureCategory.TIMEOUT, FailureCategory.FORMAT_ERROR,
            FailureCategory.SEMANTIC_MISMATCH, FailureCategory.TOOL_EXECUTION_FAILED,
            FailureCategory.LLM_HALLUCINATION, FailureCategory.LOW_CONFIDENCE,
            FailureCategory.CONTEXT_LOST, FailureCategory.RECURSION_DEPTH,
            FailureCategory.RESOURCE_EXHAUSTED,
        }

        if category in methodology_patch_categories:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    auto_fix_result = {"fix_applied": True, "detail": f"同步上下文中仅记录，methodology_patch待下次消费", "methodology_patch": {}}
                else:
                    auto_fix_result = loop.run_until_complete(AutoFixExecutor.execute(category, user_query, context))
            except RuntimeError:
                auto_fix_result = {"fix_applied": True, "detail": "同步降级记录", "methodology_patch": {}}
        else:
            auto_fix_result = {"fix_applied": False, "detail": "需async上下文执行修复策略，已记录待后续消费"}

        try:
            from core.ports.adapters import get_storage_port
            import json
            db = get_storage_port("data/failure_classifier.db")
            db.execute(
                'UPDATE failures SET auto_fix_applied=?, auto_fix_detail=? WHERE rowid=(SELECT MAX(rowid) FROM failures)',
                (1 if auto_fix_result.get("fix_applied") else 0,
                 json.dumps(auto_fix_result, ensure_ascii=False)[:500]),
                commit=True
            )
        except Exception as e:
            logger.warning(f"auto_fix结果更新跳过: {e}")

        return {
            "category": category,
            "taxonomy_info": info,
            "auto_fix_result": auto_fix_result,
        }

    @classmethod
    def get_failure_patterns(cls, limit: int = 20) -> List[Dict]:
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/failure_classifier.db")
            rows = db.query(
                "SELECT category, COUNT(*) as cnt, severity, layer FROM failures GROUP BY category ORDER BY cnt DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"失败模式查询跳过: {e}")
            return []

    @classmethod
    def get_recent_failures(cls, limit: int = 10) -> List[Dict]:
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/failure_classifier.db")
            rows = db.query(
                "SELECT * FROM failures ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"最近失败查询跳过: {e}")
            return []

    @classmethod
    def get_severity_summary(cls) -> Dict:
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/failure_classifier.db")
            rows = db.query(
                "SELECT severity, COUNT(*) as cnt FROM failures GROUP BY severity"
            )
            return {r["severity"]: r["cnt"] for r in rows}
        except Exception as e:
            logger.warning(f"严重度统计跳过: {e}")
            return {}
