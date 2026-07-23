"""
元控制治理器 — 防止元控制层过度活跃导致系统震荡

核心问题：bayesian_optimizer/active_learner/self_reflector 三个元控制组件
缺乏频率控制、幅度限制和回滚机制，可能导致：
1. 参数震荡（优化器频繁大幅调整）
2. 提问疲劳（主动学习无节制骚扰用户）
3. 规则爆炸（反思器高频生成pending规则）

设计原则：
- 复用 AdaptiveGovernor 的冷却+硬约束模式
- 复用 StrategyParams 的幅度限制模式
- 复用 LoopMixin 的降级门控模式
- 不改变现有组件接口，通过审批门控注入治理
"""

import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class AdjustmentRecord:
    __slots__ = ("timestamp", "component", "adjustment", "approved", "reason")

    def __init__(self, timestamp, component, adjustment, approved, reason):
        self.timestamp = timestamp
        self.component = component
        self.adjustment = adjustment
        self.approved = approved
        self.reason = reason


class MetaControlGovernor:
    """元控制治理器：统一管理三个元控制组件的调整行为"""

    STABLE = "stable"
    CAUTIOUS = "cautious"
    FROZEN = "frozen"
    RECOVERING = "recovering"

    STATE_PERMISSIONS = {
        "stable": ["bayesian_optimizer", "self_reflector", "active_learner"],
        "cautious": ["self_reflector"],
        "frozen": [],
        "recovering": ["self_reflector"],
    }

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._state = self.STABLE
        self._state_entered_at = datetime.now()
        self._state_history: List[Dict] = []
        self._consecutive_rejections_total = 0
        self._recent_success_rate = 1.0

        self._adjustment_history: List[AdjustmentRecord] = []
        self._max_history = 500
        self._param_snapshots: Dict[str, Dict[str, float]] = {}
        self._last_adjustment_time: Dict[str, datetime] = {}
        self._rejection_counts: Dict[str, int] = {}
        self._session_question_counts: Dict[str, int] = {}

        self._min_intervals: Dict[str, timedelta] = {
            "bayesian_optimizer": timedelta(hours=24),
            "self_reflector": timedelta(minutes=30),
            "active_learner": timedelta(minutes=5),
        }

        self._max_magnitudes: Dict[str, float] = {
            "bayesian_optimizer": 0.15,
            "self_reflector": 1.0,
            "active_learner": 1.0,
        }

        self._cooldown_after_rejection: Dict[str, timedelta] = {
            "active_learner": timedelta(minutes=10),
        }

        self._max_questions_per_session = 3
        self._consecutive_rejection_limit = 3
        self._oscillation_window = 10
        self._oscillation_threshold = 0.7

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = MetaControlGovernor()
        return cls._instance

    def approve_adjustment(self, component: str, proposed: Dict[str, float],
                           context: Dict = None) -> Dict[str, Any]:
        """审批调整请求 — bayesian_optimizer 和 self_reflector 使用"""
        result = {"approved": True, "clamped": {}, "reason": ""}

        if component not in self.STATE_PERMISSIONS.get(self._state, []):
            result["approved"] = False
            result["reason"] = f"治理器状态={self._state}，不允许{component}调整"
            return result

        now = datetime.now()

        min_interval = self._min_intervals.get(component, timedelta(minutes=30))
        last_time = self._last_adjustment_time.get(component)
        if last_time and (now - last_time) < min_interval:
            elapsed = (now - last_time).total_seconds()
            minimum = min_interval.total_seconds()
            result["approved"] = False
            result["reason"] = f"冷却中: 距上次调整{elapsed:.0f}s < 最小间隔{minimum:.0f}s"
            self._record(now, component, proposed, False, result["reason"])
            return result

        if self._is_oscillating(component):
            result["approved"] = False
            result["reason"] = "检测到参数震荡，冻结调整"
            self._record(now, component, proposed, False, result["reason"])
            return result

        max_mag = self._max_magnitudes.get(component, 1.0)
        clamped = {}
        for key, new_val in proposed.items():
            old_val = self._param_snapshots.get(component, {}).get(key, new_val)
            delta = abs(new_val - old_val)
            if delta > max_mag:
                if new_val > old_val:
                    clamped[key] = old_val + max_mag
                else:
                    clamped[key] = old_val - max_mag
                result["clamped"][key] = {"original": new_val, "clamped": clamped[key]}

        if clamped:
            result["approved"] = True
            result["reason"] = f"调整幅度超限，已钳位({len(clamped)}个参数)"
            proposed.update(clamped)

        self._param_snapshots.setdefault(component, {}).update(proposed)
        self._last_adjustment_time[component] = now
        self._record(now, component, proposed, True, result["reason"])
        return result

    def approve_question(self, session_id: str, user_rejected_last: bool = False) -> Dict[str, Any]:
        """审批提问请求 — active_learner 使用"""
        result = {"approved": True, "reason": ""}

        if "active_learner" not in self.STATE_PERMISSIONS.get(self._state, []):
            result["approved"] = False
            result["reason"] = f"治理器状态={self._state}，不允许主动学习提问"
            return result

        count = self._session_question_counts.get(session_id, 0)
        if count >= self._max_questions_per_session:
            result["approved"] = False
            result["reason"] = f"本会话已提问{count}次，达到上限{self._max_questions_per_session}"
            return result

        if user_rejected_last:
            rejections = self._rejection_counts.get(session_id, 0)
            if rejections >= self._consecutive_rejection_limit:
                result["approved"] = False
                result["reason"] = f"用户已连续拒绝{rejections}次，停止提问"
                return result

        self._session_question_counts[session_id] = count + 1
        return result

    def record_user_rejection(self, session_id: str):
        """记录用户拒绝"""
        self._rejection_counts[session_id] = self._rejection_counts.get(session_id, 0) + 1

    def record_user_acceptance(self, session_id: str):
        """记录用户接受，重置拒绝计数"""
        self._rejection_counts[session_id] = 0

    def snapshot_params(self, component: str, params: Dict[str, float]):
        """保存参数快照（用于回滚）"""
        self._param_snapshots[component] = dict(params)

    def rollback_params(self, component: str) -> Optional[Dict[str, float]]:
        """回滚到上次快照"""
        snapshot = self._param_snapshots.get(component)
        if snapshot:
            logger.warning(f"元控制回滚: {component} 参数恢复到快照值")
            return dict(snapshot)
        return None

    def reset_session(self, session_id: str):
        """重置会话计数（新会话时调用）"""
        self._session_question_counts.pop(session_id, None)
        self._rejection_counts.pop(session_id, None)

    def _is_oscillating(self, component: str) -> bool:
        """检测参数震荡"""
        recent = [
            r for r in self._adjustment_history[-self._oscillation_window * 2:]
            if r.component == component and r.approved
        ]
        if len(recent) < 4:
            return False

        recent_half = recent[-(len(recent) // 2):]
        direction_changes = 0
        for i in range(1, len(recent_half)):
            prev = recent_half[i - 1].adjustment
            curr = recent_half[i].adjustment
            for key in prev:
                if key in curr:
                    if (curr[key] - prev[key]) * (-1 if i % 2 == 0 else 1) < 0:
                        direction_changes += 1
                        break

        if len(recent_half) > 0:
            change_rate = direction_changes / len(recent_half)
            return change_rate > self._oscillation_threshold

        return False

    def _record(self, timestamp, component, adjustment, approved, reason):
        self._adjustment_history.append(
            AdjustmentRecord(timestamp, component, dict(adjustment), approved, reason)
        )
        if len(self._adjustment_history) > self._max_history:
            self._adjustment_history = self._adjustment_history[-self._max_history:]

    def get_status(self) -> Dict[str, Any]:
        """获取治理器状态"""
        return {
            "state": self._state,
            "state_entered_at": self._state_entered_at.isoformat(),
            "state_history_count": len(self._state_history),
            "total_adjustments": len(self._adjustment_history),
            "approved": sum(1 for r in self._adjustment_history if r.approved),
            "rejected": sum(1 for r in self._adjustment_history if not r.approved),
            "components_tracked": list(self._param_snapshots.keys()),
            "active_sessions": len(self._session_question_counts),
            "last_adjustments": {
                comp: t.isoformat() for comp, t in self._last_adjustment_time.items()
            },
        }

    @property
    def current_state(self) -> str:
        return self._state

    def transition_to(self, new_state: str, reason: str = ""):
        """状态转换 — 必须记录原因"""
        if new_state not in self.STATE_PERMISSIONS:
            logger.warning(f"无效状态: {new_state}")
            return
        old_state = self._state
        self._state_history.append({
            "from": old_state,
            "to": new_state,
            "reason": reason,
            "time": datetime.now().isoformat(),
        })
        self._state = new_state
        self._state_entered_at = datetime.now()
        logger.info(f"治理器状态转换: {old_state} → {new_state} ({reason})")

    def allowed_operations(self) -> List[str]:
        """当前状态允许的操作"""
        return self.STATE_PERMISSIONS.get(self._state, [])

    def can_run(self, component: str) -> bool:
        """检查组件是否允许运行"""
        return component in self.STATE_PERMISSIONS.get(self._state, [])

    def update_system_health(self, success_rate: float, user_satisfaction: float = 1.0):
        """根据系统健康指标更新状态"""
        self._recent_success_rate = success_rate

        if self._state == self.STABLE:
            if success_rate < 0.5 or user_satisfaction < 0.4:
                self.transition_to(self.CAUTIOUS, f"成功率{success_rate:.0%}/满意度{user_satisfaction:.0%}下降")
        elif self._state == self.CAUTIOUS:
            if success_rate < 0.3 or user_satisfaction < 0.2:
                self.transition_to(self.FROZEN, f"成功率{success_rate:.0%}/满意度{user_satisfaction:.0%}严重下降")
            elif success_rate > 0.7 and user_satisfaction > 0.6:
                self.transition_to(self.STABLE, f"成功率{success_rate:.0%}/满意度{user_satisfaction:.0%}恢复")
        elif self._state == self.FROZEN:
            if (datetime.now() - self._state_entered_at) > timedelta(hours=24):
                self.transition_to(self.RECOVERING, "冻结24小时，尝试恢复")
        elif self._state == self.RECOVERING:
            if success_rate > 0.7 and user_satisfaction > 0.6:
                self.transition_to(self.STABLE, "恢复期指标正常，回到稳定")
            elif success_rate < 0.4:
                self.transition_to(self.FROZEN, "恢复期指标恶化，重新冻结")


meta_governor = MetaControlGovernor.get_instance()