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

    def __init__(self, max_window: int = MAX_TICK_WINDOW):
        self._max_window = max_window
        self._ticks: deque = deque(maxlen=max_window)
        self._start_time: float = time.time()
        self._last_tick_time: float = self._start_time
        self._phase_transitions: List[Dict[str, Any]] = []

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
        根据认知密度计算内在阶段
        替代存在层的wall-clock沉默时长判断
        """
        if density >= 1.0:
            return "awake"
        elif density >= 0.5:
            return "perceiving"
        elif density >= 0.2:
            return "growing"
        elif density >= 0.05:
            return "resting"
        else:
            return "sleeping"

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

    def reset(self) -> None:
        self._ticks.clear()
        self._start_time = time.time()
        self._last_tick_time = self._start_time


inner_time_engine = InnerTimeEngine()