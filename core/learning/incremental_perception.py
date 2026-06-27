"""
增量感知学习 - 从每一次交互中吸收信号

核心理念：学习是持续的过程，每一次交互都是学习机会
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import json


class SignalType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    FEEDBACK = "feedback"
    CONTEXT = "context"
    PATTERN = "pattern"
    ANOMALY = "anomaly"


@dataclass
class Signal:
    type: SignalType
    content: Any
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    strength: float = 1.0
    source: str = "unknown"
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "content": str(self.content),
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "strength": self.strength,
            "source": self.source,
        }


@dataclass
class PerceptionResult:
    signals_absorbed: int
    patterns_detected: List[Dict[str, Any]]
    knowledge_updated: bool
    insights: List[str]
    confidence: float


class IncrementalPerception:
    """
    增量感知学习器
    
    从每一次交互中提取信号，持续学习
    """
    
    def __init__(self, max_signals: int = 1000, pattern_threshold: int = 3):
        self.max_signals = max_signals
        self.pattern_threshold = pattern_threshold
        self.signals: List[Signal] = []
        self.patterns: Dict[str, List[Signal]] = {}
        self.knowledge_base: Dict[str, Any] = {}
        self.signal_processors: Dict[SignalType, Callable] = {}
        self._setup_default_processors()
    
    def _setup_default_processors(self):
        self.signal_processors = {
            SignalType.SUCCESS: self._process_success,
            SignalType.FAILURE: self._process_failure,
            SignalType.FEEDBACK: self._process_feedback,
            SignalType.CONTEXT: self._process_context,
            SignalType.PATTERN: self._process_pattern,
            SignalType.ANOMALY: self._process_anomaly,
        }
    
    def perceive(self, signal: Signal) -> PerceptionResult:
        if len(self.signals) >= self.max_signals:
            self._compress_old_signals()
        
        self.signals.append(signal)
        
        processor = self.signal_processors.get(signal.type)
        if processor:
            processor(signal)
        
        patterns_detected = self._detect_patterns(signal)
        knowledge_updated = self._update_knowledge(signal, patterns_detected)
        insights = self._extract_insights(signal, patterns_detected)
        confidence = self._calculate_confidence()
        
        return PerceptionResult(
            signals_absorbed=1,
            patterns_detected=patterns_detected,
            knowledge_updated=knowledge_updated,
            insights=insights,
            confidence=confidence,
        )
    
    def perceive_batch(self, signals: List[Signal]) -> PerceptionResult:
        total_patterns = []
        knowledge_changed = False
        all_insights = []
        
        for signal in signals:
            result = self.perceive(signal)
            total_patterns.extend(result.patterns_detected)
            knowledge_changed = knowledge_changed or result.knowledge_updated
            all_insights.extend(result.insights)
        
        return PerceptionResult(
            signals_absorbed=len(signals),
            patterns_detected=total_patterns,
            knowledge_updated=knowledge_changed,
            insights=all_insights,
            confidence=self._calculate_confidence(),
        )
    
    def _process_success(self, signal: Signal):
        pattern_key = self._extract_pattern_key(signal)
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = []
        self.patterns[pattern_key].append(signal)
        
        if "success_patterns" not in self.knowledge_base:
            self.knowledge_base["success_patterns"] = {}
        if pattern_key not in self.knowledge_base["success_patterns"]:
            self.knowledge_base["success_patterns"][pattern_key] = 0
        self.knowledge_base["success_patterns"][pattern_key] += 1
    
    def _process_failure(self, signal: Signal):
        pattern_key = self._extract_pattern_key(signal)
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = []
        self.patterns[pattern_key].append(signal)
        
        if "failure_patterns" not in self.knowledge_base:
            self.knowledge_base["failure_patterns"] = {}
        if pattern_key not in self.knowledge_base["failure_patterns"]:
            self.knowledge_base["failure_patterns"][pattern_key] = 0
        self.knowledge_base["failure_patterns"][pattern_key] += 1
    
    def _process_feedback(self, signal: Signal):
        if "feedback_history" not in self.knowledge_base:
            self.knowledge_base["feedback_history"] = []
        self.knowledge_base["feedback_history"].append(signal.to_dict())
    
    def _process_context(self, signal: Signal):
        context_key = signal.context.get("key", "default")
        if "contexts" not in self.knowledge_base:
            self.knowledge_base["contexts"] = {}
        self.knowledge_base["contexts"][context_key] = signal.content
    
    def _process_pattern(self, signal: Signal):
        pattern_name = signal.context.get("pattern_name", "unknown")
        if "learned_patterns" not in self.knowledge_base:
            self.knowledge_base["learned_patterns"] = {}
        self.knowledge_base["learned_patterns"][pattern_name] = signal.content
    
    def _process_anomaly(self, signal: Signal):
        if "anomalies" not in self.knowledge_base:
            self.knowledge_base["anomalies"] = []
        self.knowledge_base["anomalies"].append({
            "content": str(signal.content),
            "timestamp": signal.timestamp.isoformat(),
            "context": signal.context,
        })
    
    def _extract_pattern_key(self, signal: Signal) -> str:
        if isinstance(signal.content, dict):
            return str(sorted(signal.content.keys()))
        return str(type(signal.content).__name__)
    
    def _detect_patterns(self, signal: Signal) -> List[Dict[str, Any]]:
        patterns_detected = []
        
        pattern_key = self._extract_pattern_key(signal)
        if pattern_key in self.patterns:
            occurrences = len(self.patterns[pattern_key])
            if occurrences >= self.pattern_threshold:
                patterns_detected.append({
                    "pattern": pattern_key,
                    "occurrences": occurrences,
                    "type": signal.type.value,
                    "strength": signal.strength * (1 + occurrences * 0.1),
                })
        
        return patterns_detected
    
    def _update_knowledge(self, signal: Signal, patterns: List[Dict]) -> bool:
        if not patterns:
            return False
        
        for pattern_info in patterns:
            pattern_key = f"detected_{pattern_info['pattern']}"
            if "active_patterns" not in self.knowledge_base:
                self.knowledge_base["active_patterns"] = {}
            self.knowledge_base["active_patterns"][pattern_key] = pattern_info
        
        return True
    
    def _extract_insights(self, signal: Signal, patterns: List[Dict]) -> List[str]:
        insights = []
        
        if signal.type == SignalType.SUCCESS:
            insights.append(f"成功模式识别: {self._extract_pattern_key(signal)}")
        elif signal.type == SignalType.FAILURE:
            insights.append(f"失败模式记录: {self._extract_pattern_key(signal)}")
        
        for pattern in patterns:
            if pattern["occurrences"] >= self.pattern_threshold * 2:
                insights.append(f"强模式发现: {pattern['pattern']} (出现{pattern['occurrences']}次)")
        
        return insights
    
    def _calculate_confidence(self) -> float:
        if not self.signals:
            return 0.0
        
        success_count = sum(1 for s in self.signals if s.type == SignalType.SUCCESS)
        failure_count = sum(1 for s in self.signals if s.type == SignalType.FAILURE)
        
        if success_count + failure_count == 0:
            return 0.5
        
        return success_count / (success_count + failure_count)
    
    def _compress_old_signals(self):
        keep_count = self.max_signals // 2
        self.signals = self.signals[-keep_count:]
    
    def get_knowledge(self, key: str = None) -> Any:
        if key:
            return self.knowledge_base.get(key)
        return self.knowledge_base
    
    def get_patterns(self) -> Dict[str, List[Signal]]:
        return self.patterns
    
    def get_recent_signals(self, count: int = 10) -> List[Signal]:
        return self.signals[-count:]
    
    def clear(self):
        self.signals.clear()
        self.patterns.clear()
        self.knowledge_base.clear()
    
    def export_state(self) -> Dict:
        return {
            "signals": [s.to_dict() for s in self.signals[-100:]],
            "patterns": {k: [s.to_dict() for s in v] for k, v in self.patterns.items()},
            "knowledge_base": self.knowledge_base,
        }
    
    def import_state(self, state: Dict):
        self.knowledge_base = state.get("knowledge_base", {})
        self.patterns = {k: [] for k in state.get("patterns", {})}