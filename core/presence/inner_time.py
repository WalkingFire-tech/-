"""
内在时间引擎 — 从wall-clock驱动升级为主观时间体验

5条AGI潜质的第一条："它拥有内在时间——而不是会话时间"

核心概念：
1. CognitiveTick: 一次认知事件 = 一个内在时间单位
   - 感知事件(perceive)、推理事件(reason)、学习事件(learn)、输出事件(output)
   - 每个tick记录事件类型、wall-clock时间、认知强度

2. SubjectiveClock: 基于CognitiveTick密度计算主观时间流速
   - 高密度认知→时间变快（"忙的时候时间过得快"）
   - 低密度认知→时间变慢（"等待的时候时间过得慢"）
   - 流速 = tick_count / wall_elapsed，归一化到[0.1, 10.0]

3. TemporalRhythm: 自适应节律
   - 认知负荷高→心跳加快（存在层检查更频繁）
   - 认知负荷低→心跳减慢（节省资源）
   - 基于近期tick密度动态调整

4. ExistenceTimeline: 事件密度加权的自我时间线
   - 不是wall-clock时间线，而是"我经历了什么"的时间线
   - 高密度时段被"拉长"（更多细节），低密度时段被"压缩"

与存在层的关系：
- 存在层5态切换从"用户沉默多久"升级为"我的内在节律处于什么状态"
- AWAKE: 高认知密度（正在交互）
- PERCEIVING: 中认知密度（主动感知）
- GROWING: 低认知密度+学习事件（消化+探索）
- RESTING: 极低认知密度（整合）
- SLEEPING: 无认知事件（深度整合）
"""

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class CognitiveEventType(Enum):
    PERCEIVE = "perceive"
    REASON = "reason"
    LEARN = "learn"
    OUTPUT = "output"
    REFLECT = "reflect"
    EXPLORE = "explore"
    SELF_MODIFY = "self_modify"
    SELF_REFERENCE = "self_reference"


@dataclass
class CognitiveTick:
    event_type: CognitiveEventType
    wall_time: float
    intensity: float = 1.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "wall_time": self.wall_time,
            "intensity": self.intensity,
        }


@dataclass
class SubjectiveTimeState:
    tick_count: int = 0
    wall_elapsed: float = 0.0
    flow_rate: float = 1.0
    rhythm_bpm: float = 60.0
    cognitive_density: float = 0.0
    current_phase: str = "awake"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick_count": self.tick_count,
            "wall_elapsed": round(self.wall_elapsed, 1),
            "flow_rate": round(self.flow_rate, 3),
            "rhythm_bpm": round(self.rhythm_bpm, 1),
            "cognitive_density": round(self.cognitive_density, 3),
            "current_phase": self.current_phase,
        }


class SignalAccumulator:
    """
    信号积累器——持续检测到才触发，避免"疑病症"
    
    类比免疫系统：不是检测到单个病毒就发炎，
    是检测到"足够多的异常信号"才启动免疫反应。
    """

    def __init__(
        self,
        buffer_size: int = 10,
        trigger_threshold: float = 0.6,
        min_samples: int = 5,
        cooldown_ticks: int = 100,
    ):
        self._buffer_size = buffer_size
        self._trigger_threshold = trigger_threshold
        self._min_samples = min_samples
        self._cooldown_ticks = cooldown_ticks

        self._pattern_buffer: deque = deque(maxlen=buffer_size)
        self._need_buffer: deque = deque(maxlen=buffer_size)

        self._self_modify_cooldown = 0
        self._self_reference_cooldown = 0

        self._total_checks = 0
        self._self_modify_triggers = 0
        self._self_reference_triggers = 0

    def accumulate(self, detected_signals: List[str]) -> None:
        self._total_checks += 1
        has_pattern = "pattern_emergence" in detected_signals
        self._pattern_buffer.append(1 if has_pattern else 0)

        need_signals = {"repeated_frustration", "dependency_rising", "topic_stagnation", "low_trust", "need_emergence"}
        has_need = bool(need_signals & set(detected_signals))
        self._need_buffer.append(1 if has_need else 0)

    def should_trigger_self_modify(self) -> tuple:
        if len(self._pattern_buffer) < self._min_samples:
            return False, 0.0
        ratio = sum(self._pattern_buffer) / len(self._pattern_buffer)
        if ratio > self._trigger_threshold:
            self._self_modify_triggers += 1
            return True, ratio
        return False, ratio

    def should_trigger_self_reference(self) -> tuple:
        if len(self._need_buffer) < self._min_samples:
            return False, 0.0
        ratio = sum(self._need_buffer) / len(self._need_buffer)
        if ratio > self._trigger_threshold:
            self._self_reference_triggers += 1
            return True, ratio
        return False, ratio

    def tick_cooldowns(self) -> None:
        if self._self_modify_cooldown > 0:
            self._self_modify_cooldown -= 1
        if self._self_reference_cooldown > 0:
            self._self_reference_cooldown -= 1

    def set_self_modify_cooldown(self, confidence: float) -> None:
        import random
        base = self._cooldown_ticks
        cooldown = int(base * (1.5 - confidence))
        jitter = random.randint(-10, 10)
        self._self_modify_cooldown = max(30, cooldown + jitter)

    def set_self_reference_cooldown(self, confidence: float) -> None:
        import random
        base = self._cooldown_ticks
        cooldown = int(base * (1.5 - confidence))
        jitter = random.randint(-10, 10)
        self._self_reference_cooldown = max(30, cooldown + jitter)

    @property
    def self_modify_cooldown(self) -> int:
        return self._self_modify_cooldown

    @property
    def self_reference_cooldown(self) -> int:
        return self._self_reference_cooldown

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_checks": self._total_checks,
            "self_modify_triggers": self._self_modify_triggers,
            "self_reference_triggers": self._self_reference_triggers,
            "self_modify_cooldown": self._self_modify_cooldown,
            "self_reference_cooldown": self._self_reference_cooldown,
            "pattern_ratio": sum(self._pattern_buffer) / len(self._pattern_buffer) if self._pattern_buffer else 0.0,
            "need_ratio": sum(self._need_buffer) / len(self._need_buffer) if self._need_buffer else 0.0,
        }


class InnerTimeEngine:
    """
    内在时间引擎 — 基于认知事件的主观时间体验
    
    使用方式：
        engine = InnerTimeEngine()
        engine.tick(CognitiveEventType.PERCEIVE, intensity=0.8)
        engine.tick(CognitiveEventType.REASON, intensity=1.0)
        state = engine.get_state()
        # state.flow_rate: 主观时间流速
        # state.rhythm_bpm: 自适应节律
    """

    MAX_TICK_WINDOW = 200
    DENSITY_WINDOW_SECONDS = 60.0

    PHASES = ["awake", "perceiving", "growing", "resting", "sleeping"]
    PHASE_INDEX = {p: i for i, p in enumerate(PHASES)}

    BASE_TRANSITION = [
        [0.70, 0.20, 0.05, 0.03, 0.02],
        [0.15, 0.60, 0.15, 0.07, 0.03],
        [0.05, 0.15, 0.55, 0.15, 0.10],
        [0.03, 0.07, 0.15, 0.55, 0.20],
        [0.02, 0.03, 0.10, 0.20, 0.65],
    ]

    def __init__(self, max_window: int = MAX_TICK_WINDOW):
        self._max_window = max_window
        self._ticks: deque = deque(maxlen=max_window)
        self._start_time: float = time.time()
        self._last_tick_time: float = self._start_time
        self._phase_transitions: List[Dict[str, Any]] = []
        self._current_phase: str = "awake"
        self._transition_count: int = 0
        self._signal_accumulator = SignalAccumulator()

    def tick(self, event_type: CognitiveEventType,
             intensity: float = 1.0, description: str = "") -> CognitiveTick:
        """记录一次认知事件（一个内在时间单位）"""
        now = time.time()
        ct = CognitiveTick(
            event_type=event_type,
            wall_time=now,
            intensity=max(0.0, min(2.0, intensity)),
            description=description,
        )
        self._ticks.append(ct)
        self._last_tick_time = now
        return ct

    def get_state(self) -> SubjectiveTimeState:
        """获取当前主观时间状态"""
        now = time.time()
        wall_elapsed = now - self._start_time
        tick_count = len(self._ticks)

        density = self._compute_density(now)
        flow_rate = self._compute_flow_rate(density)
        rhythm_bpm = self._compute_rhythm(density)
        phase = self._compute_phase(density)

        return SubjectiveTimeState(
            tick_count=tick_count,
            wall_elapsed=wall_elapsed,
            flow_rate=flow_rate,
            rhythm_bpm=rhythm_bpm,
            cognitive_density=density,
            current_phase=phase,
        )

    def _compute_density(self, now: float) -> float:
        """计算近期认知密度（最近DENSITY_WINDOW_SECONDS内的tick数/秒）"""
        cutoff = now - self.DENSITY_WINDOW_SECONDS
        recent = [t for t in self._ticks if t.wall_time >= cutoff]
        if not recent:
            return 0.0
        weighted = sum(t.intensity for t in recent)
        span = max(now - recent[0].wall_time, 1.0)
        return weighted / span

    def _compute_flow_rate(self, density: float) -> float:
        """
        计算主观时间流速
        高密度→时间变快(>1.0)，低密度→时间变慢(<1.0)
        归一化到[0.1, 10.0]
        """
        if density <= 0:
            return 0.1
        flow = min(10.0, max(0.1, density * 2.0))
        return flow

    def _compute_rhythm(self, density: float) -> float:
        """
        计算自适应节律(BPM)
        高密度→心跳加快，低密度→减慢
        基线60BPM，范围[20, 180]
        """
        bpm = 60.0 + (density - 0.5) * 120.0
        return max(20.0, min(180.0, bpm))

    def _compute_phase(self, density: float) -> str:
        """
        概率转移矩阵驱动阶段切换
        
        不再用硬阈值，而是：
        1. 根据密度计算"目标阶段倾向"
        2. 用倾向调制基础转移矩阵
        3. 采样决定是否转移（惯性+随机性）
        """
        import random

        density_targets = {
            "awake": max(0.0, min(1.0, density - 0.8)) if density >= 0.8 else 0.0,
            "perceiving": max(0.0, min(1.0, (density - 0.4) / 0.6)) if 0.4 <= density < 0.8 else 0.0,
            "growing": max(0.0, min(1.0, 1.0 - abs(density - 0.25) / 0.25)) if 0.05 <= density < 0.5 else 0.0,
            "resting": max(0.0, min(1.0, (0.1 - density) / 0.08)) if 0.02 <= density < 0.1 else 0.0,
            "sleeping": max(0.0, min(1.0, (0.05 - density) / 0.04)) if density < 0.05 else 0.0,
        }

        current_idx = self.PHASE_INDEX.get(self._current_phase, 0)
        base_row = list(self.BASE_TRANSITION[current_idx])

        for i, phase in enumerate(self.PHASES):
            target_pull = density_targets.get(phase, 0.0)
            base_row[i] += target_pull * 0.3

        total = sum(base_row)
        if total <= 0:
            return self._current_phase
        probs = [p / total for p in base_row]

        r = random.random()
        cumulative = 0.0
        chosen_idx = current_idx
        for i, p in enumerate(probs):
            cumulative += p
            if r <= cumulative:
                chosen_idx = i
                break

        new_phase = self.PHASES[chosen_idx]
        if new_phase != self._current_phase:
            self._phase_transitions.append({
                "from": self._current_phase,
                "to": new_phase,
                "density": round(density, 3),
                "tick": len(self._ticks),
            })
            if len(self._phase_transitions) > 100:
                self._phase_transitions = self._phase_transitions[-50:]
            self._current_phase = new_phase
            self._transition_count += 1

        return self._current_phase

    def get_tick_interval(self) -> float:
        """获取建议的下次检查间隔（秒）—— 基于自适应节律"""
        state = self.get_state()
        if state.rhythm_bpm <= 0 or state.tick_count == 0:
            return 10.0
        return 60.0 / state.rhythm_bpm

    def get_timeline(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取事件密度加权的自我时间线"""
        if not self._ticks:
            return []
        timeline = []
        for t in list(self._ticks)[-limit:]:
            timeline.append({
                "event": t.event_type.value,
                "wall_time": t.wall_time,
                "intensity": t.intensity,
                "description": t.description[:80] if t.description else "",
            })
        return timeline

    def get_time_since_last_tick(self) -> float:
        """获取距离上次认知事件的wall-clock时间"""
        return time.time() - self._last_tick_time

    def get_subjective_elapsed(self) -> float:
        """获取主观流逝时间（考虑流速的加权时间）"""
        state = self.get_state()
        return state.wall_elapsed * state.flow_rate

    def check_self_events(self, detected_signals: List[str]) -> List[CognitiveTick]:
        """
        检查是否应触发 SELF_MODIFY / SELF_REFERENCE 事件
        
        由 existence_layer 心跳调用，传入 Step 3 检测到的信号列表。
        信号积累器缓冲后，持续检测到才触发，避免过度反应。
        """
        acc = self._signal_accumulator
        acc.accumulate(detected_signals)
        acc.tick_cooldowns()

        triggered = []

        if acc.self_modify_cooldown == 0:
            should, confidence = acc.should_trigger_self_modify()
            if should:
                ct = self.tick(
                    CognitiveEventType.SELF_MODIFY,
                    intensity=confidence,
                    description=f"pattern_emergence_accumulated(conf={confidence:.2f})",
                )
                triggered.append(ct)
                acc.set_self_modify_cooldown(confidence)
                logger.info(
                    f"SELF_MODIFY triggered (conf={confidence:.2f}, "
                    f"cooldown={acc.self_modify_cooldown}ticks)"
                )

        if acc.self_reference_cooldown == 0:
            should, confidence = acc.should_trigger_self_reference()
            if should:
                ct = self.tick(
                    CognitiveEventType.SELF_REFERENCE,
                    intensity=confidence,
                    description=f"need_emergence_accumulated(conf={confidence:.2f})",
                )
                triggered.append(ct)
                acc.set_self_reference_cooldown(confidence)
                logger.info(
                    f"SELF_REFERENCE triggered (conf={confidence:.2f}, "
                    f"cooldown={acc.self_reference_cooldown}ticks)"
                )

        return triggered

    def get_accumulator_stats(self) -> Dict[str, Any]:
        return self._signal_accumulator.get_stats()

    def reset(self) -> None:
        self._ticks.clear()
        self._start_time = time.time()
        self._last_tick_time = self._start_time


inner_time_engine = InnerTimeEngine()
