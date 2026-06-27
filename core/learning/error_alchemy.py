"""
失败的炼金术 - 从每次错误中提炼黄金

核心理念：错误不是失败，而是优化的原料
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum


class ErrorCategory(Enum):
    LOGIC = "logic"
    DATA = "data"
    RESOURCE = "resource"
    TIMING = "timing"
    CONFIGURATION = "configuration"
    EXTERNAL = "external"
    UNKNOWN = "unknown"


class LearningSignalType(Enum):
    AVOID_PATTERN = "avoid_pattern"
    RETRY_STRATEGY = "retry_strategy"
    FALLBACK_OPTION = "fallback_option"
    PRECONDITION = "precondition"
    POSTCONDITION = "postcondition"


@dataclass
class LearningSignal:
    type: LearningSignalType
    content: Any
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)
    source_error_id: str = ""


@dataclass
class ErrorRecord:
    error_id: str
    category: ErrorCategory
    message: str
    stack_trace: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution: str = ""


@dataclass
class AlchemyResult:
    error_id: str
    signals_extracted: List[LearningSignal]
    patterns_found: List[str]
    lessons_learned: int
    gold_extracted: bool


class ErrorAlchemy:
    """
    失败的炼金术
    
    从错误中提取学习信号，转化为优化知识
    """
    
    def __init__(self):
        self.error_records: Dict[str, ErrorRecord] = {}
        self.learned_patterns: Dict[str, List[ErrorRecord]] = {}
        self.avoid_patterns: Dict[str, Dict] = {}
        self.retry_strategies: Dict[str, Callable] = {}
        self.fallback_options: Dict[str, Any] = {}
        self.preconditions: Dict[str, List[Callable]] = {}
        self._setup_default_strategies()
    
    def _setup_default_strategies(self):
        self.retry_strategies = {
            "resource": lambda ctx: {"max_retries": 3, "backoff": "exponential"},
            "timing": lambda ctx: {"delay": 1.0, "jitter": True},
            "external": lambda ctx: {"timeout": 30, "fallback": True},
        }
    
    def record_error(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
    ) -> str:
        error_id = f"err_{datetime.now().strftime('%Y%m%d%H%M%S')}_{id(error)}"
        
        category = self._categorize_error(error)
        
        record = ErrorRecord(
            error_id=error_id,
            category=category,
            message=str(error),
            stack_trace=self._extract_stack_trace(error),
            context=context or {},
        )
        
        self.error_records[error_id] = record
        
        pattern_key = self._extract_pattern_key(error, category)
        if pattern_key not in self.learned_patterns:
            self.learned_patterns[pattern_key] = []
        self.learned_patterns[pattern_key].append(record)
        
        return error_id
    
    def alchemize(self, error_id: str) -> AlchemyResult:
        if error_id not in self.error_records:
            return AlchemyResult(
                error_id=error_id,
                signals_extracted=[],
                patterns_found=[],
                lessons_learned=0,
                gold_extracted=False,
            )
        
        record = self.error_records[error_id]
        signals = []
        patterns_found = []
        lessons_count = 0
        
        avoid_signal = self._extract_avoid_pattern(record)
        if avoid_signal:
            signals.append(avoid_signal)
            patterns_found.append("avoid_pattern")
            lessons_count += 1
        
        retry_signal = self._extract_retry_strategy(record)
        if retry_signal:
            signals.append(retry_signal)
            patterns_found.append("retry_strategy")
            lessons_count += 1
        
        fallback_signal = self._extract_fallback_option(record)
        if fallback_signal:
            signals.append(fallback_signal)
            patterns_found.append("fallback_option")
            lessons_count += 1
        
        precondition_signal = self._extract_precondition(record)
        if precondition_signal:
            signals.append(precondition_signal)
            patterns_found.append("precondition")
            lessons_count += 1
        
        gold_extracted = lessons_count > 0
        
        return AlchemyResult(
            error_id=error_id,
            signals_extracted=signals,
            patterns_found=patterns_found,
            lessons_learned=lessons_count,
            gold_extracted=gold_extracted,
        )
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        error_name = type(error).__name__
        error_msg = str(error).lower()
        
        if "value" in error_name.lower() or "type" in error_name.lower():
            return ErrorCategory.LOGIC
        elif "data" in error_msg or "format" in error_msg:
            return ErrorCategory.DATA
        elif "memory" in error_msg or "resource" in error_msg:
            return ErrorCategory.RESOURCE
        elif "timeout" in error_msg or "timing" in error_msg:
            return ErrorCategory.TIMING
        elif "config" in error_msg:
            return ErrorCategory.CONFIGURATION
        elif "connection" in error_msg or "network" in error_msg:
            return ErrorCategory.EXTERNAL
        
        return ErrorCategory.UNKNOWN
    
    def _extract_stack_trace(self, error: Exception) -> str:
        import traceback
        return "".join(traceback.format_exception(type(error), error, error.__traceback__))
    
    def _extract_pattern_key(self, error: Exception, category: ErrorCategory) -> str:
        return f"{category.value}_{type(error).__name__}"
    
    def _extract_avoid_pattern(self, record: ErrorRecord) -> Optional[LearningSignal]:
        pattern_key = f"avoid_{record.category.value}_{record.message[:50]}"
        
        if pattern_key not in self.avoid_patterns:
            self.avoid_patterns[pattern_key] = {
                "message": record.message,
                "category": record.category.value,
                "occurrences": 1,
                "contexts": [record.context],
            }
        else:
            self.avoid_patterns[pattern_key]["occurrences"] += 1
            self.avoid_patterns[pattern_key]["contexts"].append(record.context)
        
        occurrences = self.avoid_patterns[pattern_key]["occurrences"]
        confidence = min(1.0, 0.3 + occurrences * 0.1)
        
        return LearningSignal(
            type=LearningSignalType.AVOID_PATTERN,
            content={
                "pattern": record.message,
                "category": record.category.value,
            },
            confidence=confidence,
            source_error_id=record.error_id,
        )
    
    def _extract_retry_strategy(self, record: ErrorRecord) -> Optional[LearningSignal]:
        category_key = record.category.value
        
        if category_key in self.retry_strategies:
            strategy = self.retry_strategies[category_key](record.context)
            return LearningSignal(
                type=LearningSignalType.RETRY_STRATEGY,
                content=strategy,
                confidence=0.7,
                context={"category": category_key},
                source_error_id=record.error_id,
            )
        
        return None
    
    def _extract_fallback_option(self, record: ErrorRecord) -> Optional[LearningSignal]:
        if record.category in [ErrorCategory.EXTERNAL, ErrorCategory.RESOURCE]:
            return LearningSignal(
                type=LearningSignalType.FALLBACK_OPTION,
                content={
                    "action": "use_cached_or_default",
                    "category": record.category.value,
                },
                confidence=0.6,
                source_error_id=record.error_id,
            )
        
        return None
    
    def _extract_precondition(self, record: ErrorRecord) -> Optional[LearningSignal]:
        if record.category == ErrorCategory.DATA:
            return LearningSignal(
                type=LearningSignalType.PRECONDITION,
                content={
                    "check": "validate_input",
                    "category": record.category.value,
                },
                confidence=0.8,
                source_error_id=record.error_id,
            )
        
        return None
    
    def resolve_error(self, error_id: str, resolution: str) -> bool:
        if error_id not in self.error_records:
            return False
        
        self.error_records[error_id].resolved = True
        self.error_records[error_id].resolution = resolution
        return True
    
    def get_avoid_patterns(self) -> Dict[str, Dict]:
        return self.avoid_patterns
    
    def get_error_patterns(self) -> Dict[str, List[ErrorRecord]]:
        return self.learned_patterns
    
    def get_unresolved_errors(self) -> List[ErrorRecord]:
        return [
            record for record in self.error_records.values()
            if not record.resolved
        ]
    
    def get_lessons_learned(self) -> Dict[str, Any]:
        return {
            "total_errors": len(self.error_records),
            "resolved_errors": sum(1 for r in self.error_records.values() if r.resolved),
            "avoid_patterns": len(self.avoid_patterns),
            "error_categories": {
                cat.value: sum(
                    1 for r in self.error_records.values()
                    if r.category == cat
                )
                for cat in ErrorCategory
            },
        }
    
    def add_retry_strategy(
        self,
        category: str,
        strategy: Callable[[Dict], Dict],
    ) -> None:
        self.retry_strategies[category] = strategy
    
    def add_fallback_option(self, category: str, option: Any) -> None:
        self.fallback_options[category] = option
    
    def export_state(self) -> Dict:
        return {
            "error_count": len(self.error_records),
            "avoid_patterns": self.avoid_patterns,
            "lessons": self.get_lessons_learned(),
        }