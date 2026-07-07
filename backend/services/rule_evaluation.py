import time
from loguru import logger

from backend.services.path_handlers._shared import _run_sync
from infrastructure.database_manager import DatabaseManager

_RULES_DB = "data/learning_rules.db"

_INTENT_TYPE_MAP = {
    "greeting": "chat", "confirmation": "chat", "simple_query": "question",
    "complex_query": "code", "learning_trigger": "question",
    "challenge": "verification", "history_query": "memory",
}


def evaluate_rules(user_input: str, intent_type: str, model_name: str = "unknown") -> list:
    rule_actions = []
    try:
        from infrastructure.rule_matcher import RuleMatcher
        mapped_type = _INTENT_TYPE_MAP.get(intent_type, intent_type)
        rule_ctx = {
            "intent_type": intent_type,
            "intent_type_legacy": mapped_type,
            "raw_input": user_input,
            "model": model_name,
        }
        matcher = RuleMatcher()
        db = DatabaseManager.get(_RULES_DB)
        rows = db.query(
            "SELECT id, condition, action, status FROM learning_rules "
            "WHERE status IN ('active','trial') ORDER BY priority ASC, confidence DESC"
        )
        for row in rows:
            try:
                if matcher.evaluate_condition(row["condition"], rule_ctx):
                    db.execute(
                        "UPDATE learning_rules SET apply_count=apply_count+1, last_applied=? WHERE id=?",
                        (time.time(), row["id"]),
                        commit=True,
                    )
                    rule_actions.append(row["action"])
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"规则匹配统计失败: {e}")
    return rule_actions


async def evaluate_rules_async(user_input: str, intent_type: str, model_name: str = "unknown") -> list:
    return await _run_sync(evaluate_rules, user_input, intent_type, model_name, timeout=5, phase="规则匹配")
