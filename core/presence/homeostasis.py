"""
HomeostasisEngine — 存在层的稳态引擎

不是"后台任务"，是系统的"生命维持系统"。
聚合散落在各模块中的内稳态变量，统一驱动存在层行为。

设计原则：
- 存在层是基底，不是中间件 — 所有其他层都建立在它之上
- 存在层读取SelfModel的状态，驱动行为 — 不是定时器驱动
- 存在层维护homeostasis — 认知负荷、能量、健康度的动态平衡

内稳态变量来源：
- SelfModel._cognitive_load — 认知负荷
- SelfModel.health — 健康度/能量
- SelfModel._domain_capabilities — 路径自信度
- InnerTimeEngine.cognitive_density — 认知密度
- ProbabilityField.exploration/tension — 探索/张力

输出：
- HomeostaticState: 各维度的稳态偏差和推荐行为
- recommended_presence_state: 基于内稳态的推荐存在状态
- drive_priorities: 驱动优先级排序
"""
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class DriveType(Enum):
    COGNITIVE_BALANCE = auto()
    ENERGY_RECOVERY = auto()
    HEALTH_MAINTENANCE = auto()
    GROWTH_PURSUIT = auto()
    CONSOLIDATION = auto()


@dataclass
class HomeostaticVariable:
    name: str
    current: float
    setpoint: float
    tolerance: float = 0.2

    @property
    def deviation(self) -> float:
        return abs(self.current - self.setpoint)

    @property
    def is_balanced(self) -> bool:
        return self.deviation <= self.tolerance

    @property
    def direction(self) -> str:
        if self.current < self.setpoint - self.tolerance:
            return "deficit"
        elif self.current > self.setpoint + self.tolerance:
            return "excess"
        return "balanced"

    @property
    def urgency(self) -> float:
        if self.is_balanced:
            return 0.0
        return min(1.0, self.deviation / max(self.setpoint, 0.01))


@dataclass
class HomeostaticState:
    cognitive_load: HomeostaticVariable = field(default_factory=lambda: HomeostaticVariable("cognitive_load", 0.0, 0.4, 0.2))
    energy_level: HomeostaticVariable = field(default_factory=lambda: HomeostaticVariable("energy_level", 0.5, 0.6, 0.2))
    health_score: HomeostaticVariable = field(default_factory=lambda: HomeostaticVariable("health_score", 0.7, 0.7, 0.15))
    exploration_drive: HomeostaticVariable = field(default_factory=lambda: HomeostaticVariable("exploration_drive", 0.5, 0.5, 0.2))
    consolidation_need: HomeostaticVariable = field(default_factory=lambda: HomeostaticVariable("consolidation_need", 0.0, 0.3, 0.2))

    @property
    def overall_balance(self) -> float:
        variables = [self.cognitive_load, self.energy_level, self.health_score,
                     self.exploration_drive, self.consolidation_need]
        balances = [1.0 - v.urgency for v in variables]
        return sum(balances) / len(balances) if balances else 1.0

    @property
    def primary_drive(self) -> DriveType:
        drives = [
            (DriveType.COGNITIVE_BALANCE, self.cognitive_load.urgency),
            (DriveType.ENERGY_RECOVERY, self.energy_level.urgency if self.energy_level.direction == "deficit" else 0.0),
            (DriveType.HEALTH_MAINTENANCE, self.health_score.urgency),
            (DriveType.GROWTH_PURSUIT, self.exploration_drive.urgency if self.exploration_drive.direction == "deficit" else 0.0),
            (DriveType.CONSOLIDATION, self.consolidation_need.urgency),
        ]
        drives.sort(key=lambda x: x[1], reverse=True)
        return drives[0][0] if drives[0][1] > 0.0 else DriveType.COGNITIVE_BALANCE

    @property
    def recommended_presence_state(self) -> str:
        if self.health_score.direction == "deficit" and self.health_score.urgency > 0.5:
            return "resting"
        if self.cognitive_load.direction == "excess" and self.cognitive_load.urgency > 0.4:
            return "resting"
        if self.energy_level.direction == "deficit" and self.energy_level.urgency > 0.4:
            return "resting"
        if self.consolidation_need.direction == "excess" and self.consolidation_need.urgency > 0.4:
            return "sleeping"
        if self.exploration_drive.direction == "deficit" and self.exploration_drive.urgency > 0.3:
            if self.energy_level.current > 0.4 and self.cognitive_load.current > 0.1:
                return "growing"
        if self.cognitive_load.is_balanced and self.energy_level.is_balanced:
            return "perceiving"
        return "awake"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cognitive_load": {"current": self.cognitive_load.current, "setpoint": self.cognitive_load.setpoint,
                               "direction": self.cognitive_load.direction, "urgency": self.cognitive_load.urgency},
            "energy_level": {"current": self.energy_level.current, "setpoint": self.energy_level.setpoint,
                             "direction": self.energy_level.direction, "urgency": self.energy_level.urgency},
            "health_score": {"current": self.health_score.current, "setpoint": self.health_score.setpoint,
                             "direction": self.health_score.direction, "urgency": self.health_score.urgency},
            "exploration_drive": {"current": self.exploration_drive.current, "setpoint": self.exploration_drive.setpoint,
                                  "direction": self.exploration_drive.direction, "urgency": self.exploration_drive.urgency},
            "consolidation_need": {"current": self.consolidation_need.current, "setpoint": self.consolidation_need.setpoint,
                                   "direction": self.consolidation_need.direction, "urgency": self.consolidation_need.urgency},
            "overall_balance": self.overall_balance,
            "primary_drive": self.primary_drive.name,
            "recommended_state": self.recommended_presence_state,
        }


class HomeostasisEngine:
    """
    稳态引擎 — 聚合散落的内稳态变量，统一驱动存在层行为

    核心循环：读取状态 → 计算偏差 → 推荐行为 → 反馈调节
    """

    def __init__(self):
        self._state = HomeostaticState()
        self._history: List[Dict[str, Any]] = []
        self._last_update: float = 0.0
        self._update_count: int = 0

    @property
    def state(self) -> HomeostaticState:
        return self._state

    def update(self) -> HomeostaticState:
        """
        从各数据源读取当前状态，更新内稳态变量

        数据源优先级：
        1. SelfModel（最权威）
        2. InnerTimeEngine（认知密度）
        3. ProbabilityField（探索/张力）
        4. 默认值（降级）
        """
        self._update_count += 1
        self._last_update = time.time()

        cognitive_load = self._read_cognitive_load()
        energy_level = self._read_energy_level()
        health_score = self._read_health_score()
        exploration_drive = self._read_exploration_drive()
        consolidation_need = self._read_consolidation_need()

        self._state.cognitive_load = HomeostaticVariable("cognitive_load", cognitive_load, 0.4, 0.2)
        self._state.energy_level = HomeostaticVariable("energy_level", energy_level, 0.6, 0.2)
        self._state.health_score = HomeostaticVariable("health_score", health_score, 0.7, 0.15)
        self._state.exploration_drive = HomeostaticVariable("exploration_drive", exploration_drive, 0.5, 0.2)
        self._state.consolidation_need = HomeostaticVariable("consolidation_need", consolidation_need, 0.3, 0.2)

        if self._update_count % 60 == 0:
            self._history.append({
                "time": self._last_update,
                "balance": self._state.overall_balance,
                "primary_drive": self._state.primary_drive.name,
                "recommended": self._state.recommended_presence_state,
            })
            self._history = self._history[-100:]

        return self._state

    def _read_cognitive_load(self) -> float:
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            load = sm._cognitive_load
            if load > 0:
                return load
        except Exception:
            pass

        try:
            from core.presence.inner_time import inner_time_engine
            density = inner_time_engine.get_state().cognitive_density
            return min(1.0, density)
        except Exception:
            pass

        return 0.3

    def _read_energy_level(self) -> float:
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            energy = sm.health.get("energy", 0.0)
            if energy > 0:
                return energy
        except Exception:
            pass

        try:
            from core.resource_awareness.health_monitor import get_health_monitor
            hm = get_health_monitor()
            snap = hm.check()
            return getattr(snap, 'energy_level', 0.5)
        except Exception:
            pass

        return 0.5

    def _read_health_score(self) -> float:
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            score = sm.health.get("score", 0.0)
            if score > 0:
                return score
        except Exception:
            pass

        try:
            from core.resource_awareness.health_monitor import get_health_monitor
            hm = get_health_monitor()
            snap = hm.check()
            return getattr(snap, 'health_score', 0.7)
        except Exception:
            pass

        return 0.7

    def _read_exploration_drive(self) -> float:
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            directive = sm.get_behavioral_directive()
            return directive.get("exploration_drive", 0.5)
        except Exception:
            pass

        try:
            from core.presence.probability_field import get_probability_field
            pf = get_probability_field()
            tendency = pf.get_tendency()
            return tendency.get("exploration", 0.5)
        except Exception:
            pass

        return 0.5

    def _read_consolidation_need(self) -> float:
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            directive = sm.get_behavioral_directive()
            return directive.get("consolidation_need", 0.0)
        except Exception:
            pass

        try:
            from core.presence.inner_time import inner_time_engine
            phase = inner_time_engine.get_state().current_phase
            if phase in ("resting", "sleeping"):
                return 0.7
            elif phase == "growing":
                return 0.4
        except Exception:
            pass

        return 0.2

    def get_drive_priorities(self) -> List[Dict[str, Any]]:
        """返回按紧迫度排序的驱动列表"""
        drives = [
            {"drive": DriveType.COGNITIVE_BALANCE, "urgency": self._state.cognitive_load.urgency,
             "direction": self._state.cognitive_load.direction},
            {"drive": DriveType.ENERGY_RECOVERY, "urgency": self._state.energy_level.urgency,
             "direction": self._state.energy_level.direction},
            {"drive": DriveType.HEALTH_MAINTENANCE, "urgency": self._state.health_score.urgency,
             "direction": self._state.health_score.direction},
            {"drive": DriveType.GROWTH_PURSUIT, "urgency": self._state.exploration_drive.urgency,
             "direction": self._state.exploration_drive.direction},
            {"drive": DriveType.CONSOLIDATION, "urgency": self._state.consolidation_need.urgency,
             "direction": self._state.consolidation_need.direction},
        ]
        drives.sort(key=lambda x: x["urgency"], reverse=True)
        return drives


_homeostasis_engine: Optional[HomeostasisEngine] = None


def get_homeostasis_engine() -> HomeostasisEngine:
    global _homeostasis_engine
    if _homeostasis_engine is None:
        _homeostasis_engine = HomeostasisEngine()
        logger.info("HomeostasisEngine initialized — 存在层有了稳态感知")
    return _homeostasis_engine