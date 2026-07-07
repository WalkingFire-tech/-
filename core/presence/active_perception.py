"""
主动感知引擎 - 在用户空闲时主动感知状态变化

核心能力：
1. 在用户沉默时持续感知用户的状态变化
2. 识别值得关注的模式（情绪变化、话题转移、需求变化）
3. 将感知结果传递给主动性引擎和关系模型

核心理念：
- 感知不需要用户输入，系统在空闲时主动进行
- 感知的目标是发现"值得关注的变化"
- 感知结果会驱动系统的主动行为
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class PerceptionSignal(Enum):
    EMOTION_SHIFT = "emotion_shift"
    TOPIC_SHIFT = "topic_shift"
    ACTIVITY_CHANGE = "activity_change"
    NEED_EMERGENCE = "need_emergence"
    RELATIONSHIP_MILESTONE = "relationship_milestone"
    SILENCE_BREAK = "silence_break"
    PATTERN_EMERGENCE = "pattern_emergence"


@dataclass
class PerceptionResult:
    signal: PerceptionSignal
    description: str
    confidence: float
    source: str
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "signal": self.signal.value,
            "description": self.description,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp,
            "details": self.details
        }


class ActivePerceptionEngine:
    """主动感知引擎"""

    def __init__(self):
        self._running = False
        self._thread = None
        self._perception_history: List[PerceptionResult] = []
        self._max_history = 200
        self._baseline_state: Dict = {}
        self._current_state: Dict = {}
        self._perception_interval = 120
        self._thresholds = {
            "emotion_shift": 0.3,
            "topic_shift": 0.4,
            "activity_shift": 0.3,
            "trust_milestone": 0.7,
            "intimacy_milestone": 0.6
        }
        self._stats = {
            "total_perceptions": 0,
            "significant_signals": 0,
            "by_signal": {},
            "last_perception": None,
            "last_signal_time": None
        }
        self._stereo_store = None
        self._relationship_model = None
        self._gap_growth = None
        
        # 神经形态感知：感觉适应 + 注意力聚焦
        self._stimulus_history: Dict[str, List[float]] = {}
        self._adaptation_rates: Dict[str, float] = {
            "emotion_shift": 0.95,
            "topic_shift": 0.97,
            "activity_change": 0.95,
            "need_emergence": 0.93,
            "silence_break": 0.98,
            "pattern_emergence": 0.90,
        }
        self._novelty_boost = 1.5
        self._max_stimulus_memory = 20
        
        logger.info("👁️ 主动感知引擎已创建（含神经形态适应）")

    def start(self) -> None:
        if self._running:
            logger.warning("主动感知引擎已在运行")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._perception_loop,
            daemon=True,
            name="ActivePerceptionEngine"
        )
        self._thread.start()
        logger.info("👁️ 主动感知引擎已启动")

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("👁️ 主动感知引擎已停止")

    def is_running(self) -> bool:
        return self._running and self._thread and self._thread.is_alive()

    def _perception_loop(self) -> None:
        while self._running:
            try:
                current = self._collect_current_state()
                self._current_state = current

                if self._baseline_state:
                    signals = self._detect_signals(current, self._baseline_state)
                    for signal in signals:
                        self._handle_signal(signal)

                self._update_baseline(current)
                time.sleep(self._perception_interval)

            except Exception as e:
                logger.error(f"主动感知循环异常: {e}")
                time.sleep(60)

    def _collect_current_state(self) -> Dict:
        state = {
            "timestamp": datetime.now().isoformat(),
            "emotion": "neutral",
            "topic": "unknown",
            "activity_level": 0.5,
            "trust": 0.5,
            "intimacy": 0.3,
            "dependency": 0.2,
            "recent_topics": [],
            "conversation_count": 0,
            "last_interaction": None,
            "silence_duration": 0
        }

        try:
            if self._stereo_store is None:
                from core.memory.stereo_memory import get_stereo_memory
                self._stereo_store = get_stereo_memory()
            
            recent = self._stereo_store.get_recent(3)
            if recent:
                last_msg = recent[-1]
                last_content = getattr(last_msg, 'content', '') or getattr(last_msg, 'response', '') or ''
                state["emotion"] = self._infer_emotion(last_content)
        except Exception:
            pass

        try:
            if self._relationship_model is None:
                from core.relationship.model import get_relationship_model
                self._relationship_model = get_relationship_model()
            
            metrics = self._relationship_model.get_metrics()
            state["trust"] = metrics.get("trust", 0.5)
            state["intimacy"] = metrics.get("intimacy", 0.3)
            state["dependency"] = metrics.get("dependency", 0.2)
            state["activity_level"] = (state["trust"] + state["intimacy"]) / 2
        except Exception as e:
            logger.debug(f"获取关系状态失败: {e}")

        try:
            if self._stereo_store is None:
                from core.memory.stereo_memory import get_stereo_memory
                self._stereo_store = get_stereo_memory()
            
            recent = self._stereo_store.get_recent(10)
            topics = [m.topic for m in recent if m.topic and m.topic != "general"]
            state["recent_topics"] = topics
            if topics:
                state["topic"] = topics[-1]
            state["conversation_count"] = len(recent)
        except Exception as e:
            logger.debug(f"获取记忆失败: {e}")

        return state

    def _detect_signals(self, current: Dict, baseline: Dict) -> List[PerceptionResult]:
        signals = []
        
        emotion_signal = self._detect_emotion_shift(current, baseline)
        if emotion_signal:
            signals.append(emotion_signal)

        topic_signal = self._detect_topic_shift(current, baseline)
        if topic_signal:
            signals.append(topic_signal)

        activity_signal = self._detect_activity_shift(current, baseline)
        if activity_signal:
            signals.append(activity_signal)

        milestone_signal = self._detect_relationship_milestone(current, baseline)
        if milestone_signal:
            signals.append(milestone_signal)

        silence_signal = self._detect_silence_break(current, baseline)
        if silence_signal:
            signals.append(silence_signal)

        # 神经形态适应：调整信号置信度
        adapted_signals = []
        for sig in signals:
            adapted_confidence = self._apply_neuromorphic_adaptation(sig.signal.value, sig.confidence)
            if adapted_confidence >= self._thresholds.get(sig.signal.value.replace("_shift", "_shift").replace("change", "shift"), 0.2):
                sig.confidence = adapted_confidence
                adapted_signals.append(sig)
            else:
                logger.debug(f"神经适应: {sig.signal.value} 被抑制 (adapted_conf={adapted_confidence:.2f})")

        return adapted_signals

    def _apply_neuromorphic_adaptation(self, signal_type: str, raw_confidence: float) -> float:
        history = self._stimulus_history.setdefault(signal_type, [])
        history.append(raw_confidence)
        if len(history) > self._max_stimulus_memory:
            history.pop(0)

        if len(history) < 2:
            return raw_confidence * self._novelty_boost

        adaptation_rate = self._adaptation_rates.get(signal_type, 0.90)
        recent_avg = sum(history[-5:]) / len(history[-5:])
        adapted = raw_confidence * (adaptation_rate ** len(history))

        if raw_confidence > recent_avg * 1.5:
            adapted *= self._novelty_boost

        return min(1.0, adapted)

    def _infer_emotion(self, text: str) -> str:
        if not text:
            return "neutral"
        text_lower = text.lower()
        emotion_patterns = {
            "positive": ["谢谢", "感谢", "好的", "太好了", "棒", "优秀", "完美", "喜欢", "开心", "happy", "great", "awesome", "thanks", "good"],
            "frustrated": ["不行", "失败", "错误", "bug", "崩溃", "烦", "郁闷", "郁闷", "frustrated", "annoying", "broken", "error", "fail"],
            "curious": ["为什么", "怎么", "如何", "什么", "为什么", "好奇", "why", "how", "what", "curious"],
            "urgent": ["紧急", "急", "马上", "立刻", "赶紧", "urgent", "asap", "hurry", "immediately"],
            "confused": ["不懂", "不明白", "困惑", "迷惑", "不理解", "confused", "don't understand", "unclear"],
        }
        for emotion, keywords in emotion_patterns.items():
            if any(kw in text_lower for kw in keywords):
                return emotion
        return "neutral"

    def _detect_emotion_shift(self, current: Dict, baseline: Dict) -> Optional[PerceptionResult]:
        current_emotion = current.get("emotion", "neutral")
        baseline_emotion = baseline.get("emotion", "neutral")

        if current_emotion != baseline_emotion and current_emotion != "neutral":
            if baseline_emotion == "neutral" or current_emotion != baseline_emotion:
                return PerceptionResult(
                    signal=PerceptionSignal.EMOTION_SHIFT,
                    description=f"用户情绪从 {baseline_emotion} 变为 {current_emotion}",
                    confidence=0.7,
                    source="active_perception",
                    timestamp=datetime.now().isoformat(),
                    details={"from": baseline_emotion, "to": current_emotion}
                )
        return None

    def _detect_topic_shift(self, current: Dict, baseline: Dict) -> Optional[PerceptionResult]:
        current_topics = set(current.get("recent_topics", [])[-5:])
        baseline_topics = set(baseline.get("recent_topics", [])[-5:])

        if current_topics and baseline_topics:
            union = current_topics | baseline_topics
            if not union:
                return None
            overlap = len(current_topics & baseline_topics) / len(union)

            if overlap < self._thresholds["topic_shift"]:
                new_topics = current_topics - baseline_topics
                if new_topics:
                    return PerceptionResult(
                        signal=PerceptionSignal.TOPIC_SHIFT,
                        description=f"话题发生变化: 新话题 {', '.join(list(new_topics)[:3])}",
                        confidence=0.8,
                        source="active_perception",
                        timestamp=datetime.now().isoformat(),
                        details={"old_topics": list(baseline_topics), "new_topics": list(current_topics)}
                    )
        return None

    def _detect_activity_shift(self, current: Dict, baseline: Dict) -> Optional[PerceptionResult]:
        current_activity = current.get("activity_level", 0.5)
        baseline_activity = baseline.get("activity_level", 0.5)

        if abs(current_activity - baseline_activity) > self._thresholds["activity_shift"]:
            direction = "增加" if current_activity > baseline_activity else "减少"
            return PerceptionResult(
                signal=PerceptionSignal.ACTIVITY_CHANGE,
                description=f"用户活跃度{direction}: {baseline_activity:.2f} → {current_activity:.2f}",
                confidence=0.6,
                source="active_perception",
                timestamp=datetime.now().isoformat(),
                details={"from": baseline_activity, "to": current_activity}
            )
        return None

    def _detect_relationship_milestone(self, current: Dict, baseline: Dict) -> Optional[PerceptionResult]:
        current_trust = current.get("trust", 0.5)
        baseline_trust = baseline.get("trust", 0.5)

        if current_trust >= self._thresholds["trust_milestone"] and baseline_trust < self._thresholds["trust_milestone"]:
            return PerceptionResult(
                signal=PerceptionSignal.RELATIONSHIP_MILESTONE,
                description=f"信任度达到较高水平 ({current_trust:.2f})",
                confidence=0.9,
                source="active_perception",
                timestamp=datetime.now().isoformat(),
                details={"trust": current_trust, "milestone": "trust_high"}
            )
        return None

    def _detect_silence_break(self, current: Dict, baseline: Dict) -> Optional[PerceptionResult]:
        """检测沉默打破（用户从长时间沉默中恢复）"""
        current_silence = current.get("silence_duration", 0)
        baseline_silence = baseline.get("silence_duration", 0)

        if baseline_silence > 600 and current_silence < 60:
            return PerceptionResult(
                signal=PerceptionSignal.SILENCE_BREAK,
                description="用户从长时间沉默中恢复",
                confidence=0.8,
                source="active_perception",
                timestamp=datetime.now().isoformat(),
                details={"silence_duration": baseline_silence, "reset": True}
            )
        return None

    def _handle_signal(self, signal: PerceptionResult) -> None:
        self._perception_history.append(signal)
        if len(self._perception_history) > self._max_history:
            self._perception_history = self._perception_history[-self._max_history:]

        self._stats["significant_signals"] += 1
        signal_type = signal.signal.value
        self._stats["by_signal"][signal_type] = self._stats["by_signal"].get(signal_type, 0) + 1
        self._stats["last_signal_time"] = datetime.now().isoformat()

        logger.info(f"👁️ 感知信号: {signal.description} (置信度: {signal.confidence:.2f})")

        try:
            from core.presence.existence_layer import get_existence_layer
            el = get_existence_layer()
            if hasattr(el, 'receive_perception_signal'):
                el.receive_perception_signal(signal.to_dict())
        except Exception:
            pass

        try:
            from core.task_queue import get_task_queue
            tq = get_task_queue()
            if signal.confidence > 0.7 and signal.signal in (PerceptionSignal.NEED_EMERGENCE, PerceptionSignal.EMOTION_SHIFT):
                tq.submit(
                    task_type="perception_driven",
                    payload={"signal": signal.to_dict(), "action": "proactive_check"},
                    priority=3,
                )
        except Exception:
            pass

    def _update_baseline(self, current: Dict) -> None:
        if not self._baseline_state:
            self._baseline_state = current.copy()
            return

        for key, value in current.items():
            if key in self._baseline_state and isinstance(value, (int, float)):
                self._baseline_state[key] = self._baseline_state[key] * 0.8 + value * 0.2
            elif key == "timestamp":
                self._baseline_state[key] = value
            else:
                if value and value != "unknown":
                    self._baseline_state[key] = value

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "perception_interval": self._perception_interval,
            "total_perceptions": self._stats["total_perceptions"],
            "significant_signals": self._stats["significant_signals"],
            "by_signal": self._stats["by_signal"],
            "last_perception": self._stats["last_perception"],
            "last_signal": self._stats["last_signal_time"]
        }

    def get_recent_perceptions(self, limit: int = 10) -> List[Dict]:
        return [p.to_dict() for p in self._perception_history[-limit:]]

    def get_stats(self) -> Dict:
        """获取详细统计"""
        return self._stats

    def user_interaction(self) -> None:
        """记录用户交互（由外部调用）"""
        self._stats["last_perception"] = datetime.now().isoformat()


_active_perception_engine: Optional[ActivePerceptionEngine] = None


def get_active_perception_engine() -> ActivePerceptionEngine:
    global _active_perception_engine
    if _active_perception_engine is None:
        _active_perception_engine = ActivePerceptionEngine()
    return _active_perception_engine


def start_active_perception() -> None:
    engine = get_active_perception_engine()
    if not engine.is_running():
        engine.start()


def stop_active_perception() -> None:
    engine = get_active_perception_engine()
    if engine.is_running():
        engine.stop()