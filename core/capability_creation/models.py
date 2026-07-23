import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class ExecutionResult:
    success: bool
    output: str = ""
    error: str = ""
    attempts: int = 0
    code_history: List[str] = field(default_factory=list)
    auto_installed: List[str] = field(default_factory=list)
    duration_ms: float = 0.0


class CapabilityGap:
    def __init__(self, query: str, gap_type: str, detail: str):
        self.query = query
        self.gap_type = gap_type
        self.detail = detail
        self.timestamp = datetime.now().isoformat()
        self.resolved = False
        self.solution = ""


class CreationAttempt:
    def __init__(self, query: str, method: str):
        self.query = query
        self.method = method
        self.start_time = time.time()
        self.success = False
        self.result = ""
        self.error = ""
        self.duration_ms = 0

    def finish(self, success: bool, result: str = "", error: str = ""):
        self.success = success
        self.result = result
        self.error = error
        self.duration_ms = (time.time() - self.start_time) * 1000