"""
认知节奏控制器 - 根据不同学习阶段动态调整节奏

核心理念：学习有节奏，不同阶段需要不同策略
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum


class LearningPhase(Enum):
    EXPLORATION = "exploration"
    CONSOLIDATION = "consolidation"
    MASTERY = "mastery"
    ADAPTATION = "adaptation"
    INNOVATION = "innovation"


class LearningState(Enum):
    ACTIVE = "active"
    RESTING = "resting"
    REFLECTING = "reflecting"
    INTEGRATING = "integrating"


@dataclass
class RhythmConfig:
    phase: LearningPhase
    intensity: float
    frequency: float
    rest_periods: List[timedelta]
    reflection_interval: timedelta
    adaptation_threshold: float


@dataclass
class StateSnapshot:
    state: LearningState
    phase: LearningPhase
    energy_level: float
    focus_score: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RhythmAdjustment:
    old_phase: LearningPhase
    new_phase: LearningPhase
    reason: str
    confidence: float
    actions: List[str]


class CognitiveRhythmController:
    """
    认知节奏控制器
    
    动态调整学习节奏，优化认知效率
    """
    
    def __init__(self):
        self.current_phase = LearningPhase.EXPLORATION
        self.current_state = LearningState.ACTIVE
        self.energy_level = 1.0
        self.focus_score = 0.5
        
        self.phase_configs: Dict[LearningPhase, RhythmConfig] = {}
        self._setup_default_configs()
        
        self.state_history: List[StateSnapshot] = []
        self.phase_transitions: List[RhythmAdjustment] = []
        
        self.learning_metrics: Dict[str, List[float]] = {
            "success_rate": [],
            "error_rate": [],
            "discovery_rate": [],
            "integration_rate": [],
        }
        
        self.last_rest: datetime = datetime.now()
        self.last_reflection: datetime = datetime.now()
        self.session_start: datetime = datetime.now()
    
    def _setup_default_configs(self):
        self.phase_configs = {
            LearningPhase.EXPLORATION: RhythmConfig(
                phase=LearningPhase.EXPLORATION,
                intensity=0.8,
                frequency=1.0,
                rest_periods=[timedelta(minutes=15), timedelta(minutes=30)],
                reflection_interval=timedelta(minutes=20),
                adaptation_threshold=0.3,
            ),
            LearningPhase.CONSOLIDATION: RhythmConfig(
                phase=LearningPhase.CONSOLIDATION,
                intensity=0.6,
                frequency=0.8,
                rest_periods=[timedelta(minutes=10), timedelta(minutes=20)],
                reflection_interval=timedelta(minutes=15),
                adaptation_threshold=0.5,
            ),
            LearningPhase.MASTERY: RhythmConfig(
                phase=LearningPhase.MASTERY,
                intensity=0.7,
                frequency=0.9,
                rest_periods=[timedelta(minutes=20), timedelta(minutes=40)],
                reflection_interval=timedelta(minutes=25),
                adaptation_threshold=0.7,
            ),
            LearningPhase.ADAPTATION: RhythmConfig(
                phase=LearningPhase.ADAPTATION,
                intensity=0.5,
                frequency=0.6,
                rest_periods=[timedelta(minutes=5), timedelta(minutes=15)],
                reflection_interval=timedelta(minutes=10),
                adaptation_threshold=0.4,
            ),
            LearningPhase.INNOVATION: RhythmConfig(
                phase=LearningPhase.INNOVATION,
                intensity=0.9,
                frequency=1.2,
                rest_periods=[timedelta(minutes=30), timedelta(minutes=60)],
                reflection_interval=timedelta(minutes=30),
                adaptation_threshold=0.6,
            ),
        }
    
    def tick(self) -> StateSnapshot:
        self._record_state()
        
        self._update_energy()
        
        if self._should_rest():
            self.current_state = LearningState.RESTING
            self._apply_rest()
        elif self._should_reflect():
            self.current_state = LearningState.REFLECTING
            self._apply_reflection()
        elif self._should_integrate():
            self.current_state = LearningState.INTEGRATING
            self._apply_integration()
        else:
            self.current_state = LearningState.ACTIVE
        
        adjustment = self._check_phase_transition()
        if adjustment:
            self.phase_transitions.append(adjustment)
        
        return StateSnapshot(
            state=self.current_state,
            phase=self.current_phase,
            energy_level=self.energy_level,
            focus_score=self.focus_score,
        )
    
    def _record_state(self) -> None:
        snapshot = StateSnapshot(
            state=self.current_state,
            phase=self.current_phase,
            energy_level=self.energy_level,
            focus_score=self.focus_score,
        )
        self.state_history.append(snapshot)
        
        if len(self.state_history) > 1000:
            self.state_history = self.state_history[-500:]
    
    def _update_energy(self) -> None:
        if self.current_state == LearningState.RESTING:
            self.energy_level = min(1.0, self.energy_level + 0.1)
        elif self.current_state == LearningState.ACTIVE:
            config = self.phase_configs[self.current_phase]
            self.energy_level = max(0.1, self.energy_level - config.intensity * 0.05)
        
        recent_success = self._get_recent_metric("success_rate", 10)
        recent_error = self._get_recent_metric("error_rate", 10)
        
        if recent_success > 0.7:
            self.focus_score = min(1.0, self.focus_score + 0.05)
        if recent_error > 0.3:
            self.focus_score = max(0.1, self.focus_score - 0.1)
    
    def _should_rest(self) -> bool:
        config = self.phase_configs[self.current_phase]
        
        if self.energy_level < 0.3:
            return True
        
        time_since_rest = datetime.now() - self.last_rest
        min_rest_period = min(config.rest_periods)
        
        if time_since_rest > min_rest_period * 2:
            return True
        
        return False
    
    def _should_reflect(self) -> bool:
        config = self.phase_configs[self.current_phase]
        
        time_since_reflection = datetime.now() - self.last_reflection
        
        if time_since_reflection > config.reflection_interval:
            return True
        
        if len(self.state_history) > 0:
            recent_states = self.state_history[-20:]
            active_count = sum(1 for s in recent_states if s.state == LearningState.ACTIVE)
            if active_count >= 15:
                return True
        
        return False
    
    def _should_integrate(self) -> bool:
        discovery_rate = self._get_recent_metric("discovery_rate", 10)
        
        if discovery_rate > 0.5:
            return True
        
        if self.current_phase == LearningPhase.EXPLORATION:
            success_rate = self._get_recent_metric("success_rate", 20)
            if success_rate > 0.6:
                return True
        
        return False
    
    def _apply_rest(self) -> None:
        self.energy_level = min(1.0, self.energy_level + 0.2)
        self.last_rest = datetime.now()
    
    def _apply_reflection(self) -> None:
        self.focus_score = min(1.0, self.focus_score + 0.1)
        self.last_reflection = datetime.now()
    
    def _apply_integration(self) -> None:
        self.energy_level = max(0.3, self.energy_level - 0.1)
    
    def _check_phase_transition(self) -> Optional[RhythmAdjustment]:
        config = self.phase_configs[self.current_phase]
        
        success_rate = self._get_recent_metric("success_rate", 20)
        error_rate = self._get_recent_metric("error_rate", 20)
        discovery_rate = self._get_recent_metric("discovery_rate", 20)
        
        new_phase = None
        reason = ""
        actions = []
        
        if self.current_phase == LearningPhase.EXPLORATION:
            if success_rate > config.adaptation_threshold:
                new_phase = LearningPhase.CONSOLIDATION
                reason = "探索阶段成功率达标，进入巩固阶段"
                actions = ["整理发现的知识", "建立初步连接", "识别模式"]
        
        elif self.current_phase == LearningPhase.CONSOLIDATION:
            if success_rate > config.adaptation_threshold and error_rate < 0.2:
                new_phase = LearningPhase.MASTERY
                reason = "巩固阶段稳定，进入精通阶段"
                actions = ["深化理解", "优化策略", "建立直觉"]
            elif discovery_rate > 0.5:
                new_phase = LearningPhase.EXPLORATION
                reason = "发现新领域，回到探索阶段"
                actions = ["探索新领域", "收集新信息"]
        
        elif self.current_phase == LearningPhase.MASTERY:
            if error_rate > 0.3:
                new_phase = LearningPhase.ADAPTATION
                reason = "遇到新挑战，进入适应阶段"
                actions = ["调整策略", "学习新方法"]
            elif success_rate > 0.9:
                new_phase = LearningPhase.INNOVATION
                reason = "精通达成，进入创新阶段"
                actions = ["探索边界", "尝试创新", "突破限制"]
        
        elif self.current_phase == LearningPhase.ADAPTATION:
            if success_rate > config.adaptation_threshold:
                new_phase = LearningPhase.CONSOLIDATION
                reason = "适应成功，回到巩固阶段"
                actions = ["巩固新技能", "整合经验"]
        
        elif self.current_phase == LearningPhase.INNOVATION:
            if error_rate > 0.4:
                new_phase = LearningPhase.ADAPTATION
                reason = "创新遇到困难，回到适应阶段"
                actions = ["调整方向", "学习新方法"]
        
        if new_phase:
            old_phase = self.current_phase
            self.current_phase = new_phase
            return RhythmAdjustment(
                old_phase=old_phase,
                new_phase=new_phase,
                reason=reason,
                confidence=success_rate,
                actions=actions,
            )
        
        return None
    
    def record_metric(self, metric_name: str, value: float) -> None:
        if metric_name in self.learning_metrics:
            self.learning_metrics[metric_name].append(value)
            
            if len(self.learning_metrics[metric_name]) > 100:
                self.learning_metrics[metric_name] = self.learning_metrics[metric_name][-50:]
    
    def _get_recent_metric(self, metric_name: str, count: int) -> float:
        if metric_name not in self.learning_metrics:
            return 0.0
        
        values = self.learning_metrics[metric_name][-count:]
        
        if not values:
            return 0.0
        
        return sum(values) / len(values)
    
    def get_current_intensity(self) -> float:
        config = self.phase_configs[self.current_phase]
        
        intensity = config.intensity * self.energy_level * self.focus_score
        
        if self.current_state == LearningState.RESTING:
            intensity *= 0.3
        elif self.current_state == LearningState.REFLECTING:
            intensity *= 0.5
        
        return intensity
    
    def get_recommended_actions(self) -> List[str]:
        config = self.phase_configs[self.current_phase]
        actions = []
        
        if self.current_state == LearningState.ACTIVE:
            if self.current_phase == LearningPhase.EXPLORATION:
                actions = ["尝试新方法", "收集信息", "识别模式"]
            elif self.current_phase == LearningPhase.CONSOLIDATION:
                actions = ["整理知识", "建立连接", "验证理解"]
            elif self.current_phase == LearningPhase.MASTERY:
                actions = ["优化策略", "深化理解", "建立直觉"]
            elif self.current_phase == LearningPhase.ADAPTATION:
                actions = ["调整方法", "学习新技能", "适应变化"]
            elif self.current_phase == LearningPhase.INNOVATION:
                actions = ["突破边界", "尝试创新", "探索未知"]
        
        elif self.current_state == LearningState.RESTING:
            actions = ["休息恢复", "整理思绪"]
        
        elif self.current_state == LearningState.REFLECTING:
            actions = ["反思经验", "总结教训", "规划下一步"]
        
        elif self.current_state == LearningState.INTEGRATING:
            actions = ["整合知识", "建立体系", "形成整体"]
        
        return actions
    
    def force_phase(self, phase: LearningPhase, reason: str = "") -> None:
        old_phase = self.current_phase
        self.current_phase = phase
        
        self.phase_transitions.append(RhythmAdjustment(
            old_phase=old_phase,
            new_phase=phase,
            reason=reason or "手动切换",
            confidence=1.0,
            actions=[],
        ))
    
    def get_phase_progress(self) -> Dict[str, Any]:
        success_rate = self._get_recent_metric("success_rate", 50)
        error_rate = self._get_recent_metric("error_rate", 50)
        
        config = self.phase_configs[self.current_phase]
        
        progress = success_rate / config.adaptation_threshold if config.adaptation_threshold > 0 else 0
        
        return {
            "current_phase": self.current_phase.value,
            "current_state": self.current_state.value,
            "progress": min(1.0, progress),
            "energy_level": self.energy_level,
            "focus_score": self.focus_score,
            "intensity": self.get_current_intensity(),
            "success_rate": success_rate,
            "error_rate": error_rate,
        }
    
    def get_session_summary(self) -> Dict[str, Any]:
        session_duration = datetime.now() - self.session_start
        
        phase_counts = {}
        for snapshot in self.state_history:
            phase = snapshot.phase.value
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
        
        return {
            "duration_seconds": session_duration.total_seconds(),
            "total_ticks": len(self.state_history),
            "phase_distribution": phase_counts,
            "phase_transitions": len(self.phase_transitions),
            "average_energy": (
                sum(s.energy_level for s in self.state_history) / len(self.state_history)
                if self.state_history else 0
            ),
            "average_focus": (
                sum(s.focus_score for s in self.state_history) / len(self.state_history)
                if self.state_history else 0
            ),
        }
    
    def update_phase_config(self, phase: LearningPhase, config: RhythmConfig) -> None:
        self.phase_configs[phase] = config
    
    def reset(self) -> None:
        self.current_phase = LearningPhase.EXPLORATION
        self.current_state = LearningState.ACTIVE
        self.energy_level = 1.0
        self.focus_score = 0.5
        self.state_history.clear()
        self.phase_transitions.clear()
        for metric in self.learning_metrics:
            self.learning_metrics[metric].clear()
        self.last_rest = datetime.now()
        self.last_reflection = datetime.now()
        self.session_start = datetime.now()