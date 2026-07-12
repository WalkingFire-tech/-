from enum import Enum
from typing import Dict, Any, Optional, List
from loguru import logger


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
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/failure_classifier.db")
            db.execute('''CREATE TABLE IF NOT EXISTS failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, user_query TEXT, context TEXT,
                learning_prompt TEXT, timestamp TEXT,
                severity TEXT, layer TEXT
            )''', commit=True)
            try:
                db.execute('ALTER TABLE failures ADD COLUMN severity TEXT', commit=True)
            except Exception:
                pass
            try:
                db.execute('ALTER TABLE failures ADD COLUMN layer TEXT', commit=True)
            except Exception:
                pass
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
    def get_failure_patterns(cls, limit: int = 20) -> List[Dict]:
        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/failure_classifier.db")
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
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/failure_classifier.db")
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
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/failure_classifier.db")
            rows = db.query(
                "SELECT severity, COUNT(*) as cnt FROM failures GROUP BY severity"
            )
            return {r["severity"]: r["cnt"] for r in rows}
        except Exception as e:
            logger.warning(f"严重度统计跳过: {e}")
            return {}
