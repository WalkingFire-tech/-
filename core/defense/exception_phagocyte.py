"""
L3 异常处理层 - 异常吞噬 (Exception Phagocyte)

类比：巨噬细胞——吞噬并消化异物
- 捕获异常，防止未处理异常导致系统崩溃
- 异常分类与归档
- 从异常中提取教训
"""
import traceback
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime


class ExceptionPhagocyte:
    MAX_DIGESTED = 500
    CRITICAL_EXCEPTIONS = {"SystemExit", "KeyboardInterrupt", "MemoryError"}

    def __init__(self):
        self._digested: List[dict] = []
        self._exception_counts: Dict[str, int] = {}
        self._suppressed_count = 0

    def swallow(self, exception: Exception, context: str = "", module: str = "") -> dict:
        exc_type = type(exception).__name__
        if exc_type in self.CRITICAL_EXCEPTIONS:
            raise exception
        record = {
            "type": exc_type,
            "message": str(exception)[:500],
            "context": context[:200],
            "module": module,
            "timestamp": datetime.now().isoformat(),
        }
        self._digested.append(record)
        if len(self._digested) > self.MAX_DIGESTED:
            self._digested = self._digested[-self.MAX_DIGESTED:]
        self._exception_counts[exc_type] = self._exception_counts.get(exc_type, 0) + 1
        self._suppressed_count += 1
        logger.debug(f"🧬 异常吞噬: [{module}]{exc_type}: {str(exception)[:80]}")
        return record

    def swallow_and_return(self, exception: Exception, fallback=None, context: str = "", module: str = ""):
        self.swallow(exception, context, module)
        return fallback

    def get_frequent_exceptions(self, limit: int = 10) -> List[dict]:
        sorted_exc = sorted(self._exception_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"type": t, "count": c} for t, c in sorted_exc[:limit]]

    def get_recent(self, limit: int = 20) -> List[dict]:
        return self._digested[-limit:]

    def get_stats(self) -> dict:
        return {
            "total_suppressed": self._suppressed_count,
            "unique_types": len(self._exception_counts),
            "frequent": self.get_frequent_exceptions(5),
        }

    def extract_lessons(self, limit: int = 10) -> List[dict]:
        lessons = []
        seen = set()
        for record in reversed(self._digested):
            key = f"{record['type']}:{record.get('module', '')}"
            if key not in seen:
                seen.add(key)
                lessons.append({
                    "exception_type": record["type"],
                    "module": record.get("module", ""),
                    "sample_message": record["message"][:100],
                    "occurrence_count": self._exception_counts.get(record["type"], 0),
                })
            if len(lessons) >= limit:
                break
        return lessons

    def clear(self):
        self._digested.clear()
        self._exception_counts.clear()
        self._suppressed_count = 0


exception_phagocyte = ExceptionPhagocyte()