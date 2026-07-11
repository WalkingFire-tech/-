import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from loguru import logger


class AuditLogger:
    """
    认知审计日志——记录"系统以为自己理解了什么" vs "实际发生了什么"。
    通过回溯日志来修正认知，解决"做了也不明白意义"的问题。
    """

    LOG_PATH = Path("data/audit_logs.jsonl")

    @classmethod
    def _ensure_dir(cls):
        cls.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def log(cls, user_query: str, normalized_intent: Dict,
            execution_result: Any, reflection: Dict, error: Exception = None):
        cls._ensure_dir()

        entry = {
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query[:200],
            "normalized_entity": normalized_intent.get("standard_entity"),
            "detected_intent": normalized_intent.get("intent_type") or normalized_intent.get("intent"),
            "reflection_status": reflection.get("status", "unknown") if isinstance(reflection, dict) else str(reflection),
            "reflection_reason": reflection.get("reason") if isinstance(reflection, dict) else None,
            "suggested_action": reflection.get("suggested_action") if isinstance(reflection, dict) else None,
            "output_preview": str(execution_result)[:200] if execution_result else None,
            "error": str(error)[:200] if error else None,
            "learning_triggered": (reflection.get("status", "pass") != "pass") if isinstance(reflection, dict) else False,
        }

        try:
            with open(cls.LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug(f"审计日志写入失败: {e}")

        if entry["learning_triggered"]:
            logger.warning(f"[认知审计] 偏差发现: {entry['reflection_reason']}")

    @classmethod
    def get_recent_failures(cls, limit: int = 20) -> list:
        if not cls.LOG_PATH.exists():
            return []
        entries = []
        try:
            with open(cls.LOG_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("learning_triggered"):
                            entries.append(entry)
                    except Exception:
                        pass
        except Exception:
            pass
        return entries[-limit:]