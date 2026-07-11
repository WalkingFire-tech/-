from enum import Enum
from typing import Dict, Any, Optional
from loguru import logger


class FailureCategory(Enum):
    PARAM_EXTRACTION_FAILED = "参数提取失败"
    INTENT_TYPE_MISMATCH = "意图类型不匹配"
    OUTPUT_EMPTY = "执行成功但返回空数据"
    TIMEOUT = "执行超时"
    FORMAT_ERROR = "返回格式无法解析"
    SEMANTIC_MISMATCH = "语义偏差(答非所问)"
    ENTITY_ALIAS_MISSING = "实体别名缺失"


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
            return FailureCategory.SEMANTIC_MISMATCH

        if execution_error:
            err_str = str(execution_error).lower()
            if "timeout" in err_str or "超时" in err_str:
                return FailureCategory.TIMEOUT
            if "format" in err_str or "parse" in err_str or "解析" in err_str:
                return FailureCategory.FORMAT_ERROR

        if ref_status == "empty_data":
            return FailureCategory.OUTPUT_EMPTY

        return FailureCategory.SEMANTIC_MISMATCH

    @classmethod
    def get_learning_prompt(cls, category: FailureCategory, user_query: str) -> str:
        prompts = {
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
        }
        return prompts.get(category, f"未知失败类型，需人工介入分析: {user_query}")

    @classmethod
    def record_failure(cls, category: FailureCategory, user_query: str, context: Dict = None):
        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/failure_classifier.db")
            db.execute('''CREATE TABLE IF NOT EXISTS failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, user_query TEXT, context TEXT,
                learning_prompt TEXT, timestamp TEXT
            )''', commit=True)
            prompt = cls.get_learning_prompt(category, user_query)
            import json
            from datetime import datetime
            db.execute(
                'INSERT INTO failures (category, user_query, context, learning_prompt, timestamp) VALUES (?, ?, ?, ?, ?)',
                (category.value, user_query[:200], json.dumps(context or {}, ensure_ascii=False)[:500],
                 prompt[:500], datetime.now().isoformat()),
                commit=True
            )
            logger.info(f"📋 失败分类记录: {category.value} | query='{user_query[:30]}'")
        except Exception as e:
            logger.debug(f"失败分类记录写入跳过: {e}")