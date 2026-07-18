from dataclasses import dataclass, field, replace
from typing import Dict, List, Any, Optional, Tuple


@dataclass
class OrchestratorState:
    user_input: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    intent_type: str = "unknown"
    route: str = "slow"
    confidence: float = 0.5
    model: str = "unknown"
    final_response: Optional[str] = None
    attempts: List[Tuple[str, bool, str]] = field(default_factory=list)
    failed_steps: List[Dict] = field(default_factory=list)
    methodology: Dict[str, Any] = field(default_factory=dict)
    truth_insights: str = ""
    cbnr_context: Dict[str, Any] = field(default_factory=dict)
    rule_actions: List[str] = field(default_factory=list)
    chat_session_id: Optional[str] = None
    start_time: float = 0.0
    candidates: List[Dict] = field(default_factory=list)
    best: Optional[Dict] = None
    fitness_score: Any = None
    comparison: List[Dict] = field(default_factory=list)
    essence_issues: List[str] = field(default_factory=list)
    essence_passed: bool = True
    essence_confidence: float = 1.0
    essence_cross_validated: bool = False
    events: List[Dict] = field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 5
    tool_calls_log: List[Dict] = field(default_factory=list)

    def with_update(self, **kwargs) -> "OrchestratorState":
        return replace(self, **kwargs)

    def add_attempt(self, source: str, success: bool, detail: str = "") -> "OrchestratorState":
        new_attempts = self.attempts + [(source, success, detail)]
        return replace(self, attempts=new_attempts)

    def add_event(self, event_type: str, data: Dict) -> "OrchestratorState":
        new_events = self.events + [{"type": event_type, "data": data}]
        return replace(self, events=new_events)

    def set_response(self, response: str, **kwargs) -> "OrchestratorState":
        updates = {"final_response": response}
        updates.update(kwargs)
        return replace(self, **updates)

    def update_methodology(self, patch: Dict[str, Any]) -> "OrchestratorState":
        new_methodology = {**self.methodology, **patch}
        return replace(self, methodology=new_methodology)

    def record_failure(self, step: str, detail: str) -> "OrchestratorState":
        new_failed = self.failed_steps + [{"step": step, "detail": detail}]
        return replace(self, failed_steps=new_failed)

    def overall_success(self) -> bool:
        return any(a[1] for a in self.attempts)