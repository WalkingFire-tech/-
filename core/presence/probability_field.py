"""
概率场漂移引擎 — 系统的"神经系统"

核心机制：带呼吸节律的连续漂移
- 均值漂移 = 信号驱动 + 自然回归 + 呼吸振荡
- 方差漂移 = 信号响应 + 自然回归 + 呼吸振荡(相位偏移)
- 信号记忆衰减：信号消失后影响指数衰减，不是立即归零
- 呼吸节律：即使无信号，概率场也在自然波动

与inner_time的关系：
- inner_time提供cognitive_density作为概率场的外部信号
- 概率场的phase标签替代inner_time的硬阈值phase判断
- 概率场的sample()输出驱动执行概率
"""

import math
import time
import random
from dataclasses import dataclass, field
from collections import deque
from typing import Dict, List, Optional, Tuple
from enum import Enum, auto

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class FieldPhase(Enum):
    INHALE = auto()
    EXHALE = auto()
    HOLD = auto()
    RELEASE = auto()
    BREATH = auto()


@dataclass
class ProbabilityFieldConfig:
    alpha: float = 0.02
    beta: float = 0.003
    gamma: float = 0.01
    delta: float = 0.003
    mu_0: float = 0.5
    sigma_0: float = 0.15
    rho: float = 0.02
    omega: float = 0.1
    phase_offset: float = 0.0
    memory_decay: float = 0.95
    noise_std: float = 0.01
    min_mean: float = 0.1
    max_mean: float = 0.9
    min_variance: float = 0.05
    max_variance: float = 0.5


class ProbabilityFieldDrift:
    """
    概率场漂移引擎
    
    均值演化: dmu/dt = alpha*(s - mu) + beta*(mu0 - mu) + rho*sin(omega*t)
    方差演化: dsigma2/dt = gamma*(|s| - sigma2) + delta*(sigma0 - sigma2) + 0.3*rho*sin(omega*t + pi/4)
    """

    def __init__(self, config: Optional[ProbabilityFieldConfig] = None):
        self.config = config or ProbabilityFieldConfig()
        self.mean = self.config.mu_0
        self.variance = self.config.sigma_0
        self.entropy = self._calc_entropy()
        self.t = 0.0
        self.signal_memory = 0.0
        self.phase_state = FieldPhase.BREATH
        self.history: List[Dict] = []
        self.max_history = 2000
        self.update_count = 0
        self.last_update = time.time()
        self._auto_tuner: Optional[AutoTuningEngine] = None

    def _calc_entropy(self) -> float:
        return -0.5 * math.log(self.variance + 0.001)

    def update(self, signal: Optional[float] = None, dt: Optional[float] = None) -> Dict:
        now = time.time()
        if dt is None:
            dt = max(0.01, now - self.last_update)
        self.last_update = now
        self.t += dt
        self.update_count += 1

        if signal is not None:
            self.signal_memory = self.signal_memory * self.config.memory_decay + signal * (1 - self.config.memory_decay)
        else:
            self.signal_memory *= self.config.memory_decay ** dt

        effective_signal = self.signal_memory

        epsilon = random.gauss(0, self.config.noise_std * math.sqrt(dt))
        eta = random.gauss(0, self.config.noise_std * 0.5 * math.sqrt(dt))

        breath = self.config.rho * math.sin(self.config.omega * self.t + self.config.phase_offset)

        signal_term = self.config.alpha * (effective_signal - self.mean) * dt
        recovery_term = self.config.beta * (self.config.mu_0 - self.mean) * dt
        breath_term = breath * 0.8 * dt
        self.mean += signal_term + recovery_term + breath_term + epsilon

        var_signal = self.config.gamma * (abs(effective_signal) - self.variance) * dt
        var_recovery = self.config.delta * (self.config.sigma_0 - self.variance) * dt
        var_breath = 0.3 * breath * dt
        self.variance += var_signal + var_recovery + var_breath + eta

        self.mean = max(self.config.min_mean, min(self.config.max_mean, self.mean))
        self.variance = max(self.config.min_variance, min(self.config.max_variance, self.variance))

        self.entropy = self._calc_entropy()
        self._update_phase()

        record = {
            "t": self.t,
            "signal": effective_signal,
            "mean": self.mean,
            "variance": self.variance,
            "entropy": self.entropy,
            "phase": self.phase_state.name,
            "breath": breath,
        }
        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]

        if self._auto_tuner:
            self._auto_tuner.record_update(signal, self.mean, self.variance)
            if self.update_count % 60 == 0:
                self._auto_tuner.tune(self)

        return record

    def _update_phase(self):
        if len(self.history) < 2:
            self.phase_state = FieldPhase.BREATH
            return
        prev = self.history[-2]
        cur = self.history[-1]
        dm = cur["mean"] - prev["mean"]
        dv = cur["variance"] - prev["variance"]
        if dm > 0.005 and dv > 0.002:
            self.phase_state = FieldPhase.INHALE
        elif dm < -0.005 and dv < -0.002:
            self.phase_state = FieldPhase.EXHALE
        elif abs(dm) < 0.002 and abs(dv) < 0.001:
            self.phase_state = FieldPhase.HOLD
        else:
            self.phase_state = FieldPhase.RELEASE

    def sample(self) -> float:
        return random.gauss(self.mean, math.sqrt(max(0.01, self.variance)))

    def sample_probability(self) -> float:
        return max(0.0, min(1.0, self.mean))

    def get_tendency(self) -> Dict[str, float]:
        return {
            "exploration": self.mean,
            "stability": 1 - self.mean,
            "tension": self.variance,
            "entropy": self.entropy,
            "activity": self.mean * self.variance,
            "phase": self.phase_state.name,
        }

    def get_status(self) -> Dict:
        status = {
            "mean": round(self.mean, 4),
            "variance": round(self.variance, 4),
            "entropy": round(self.entropy, 4),
            "phase": self.phase_state.name,
            "signal_memory": round(self.signal_memory, 4),
            "update_count": self.update_count,
            "tendency": self.get_tendency(),
        }
        if self._auto_tuner:
            status["auto_tuner"] = self._auto_tuner.get_status()
        return status

    def get_breath_metrics(self) -> Dict:
        if len(self.history) < 5:
            return {"phase": self.phase_state.name, "breath_active": self.config.rho > 0.01}
        recent = self.history[-5:]
        means = [h["mean"] for h in recent]
        variances = [h["variance"] for h in recent]
        return {
            "mean_amplitude": max(means) - min(means),
            "variance_amplitude": max(variances) - min(variances),
            "phase": self.phase_state.name,
            "breath_active": self.config.rho > 0.01,
        }

    def predict_future(self, steps: int = 10, signal: Optional[float] = None) -> List[Dict]:
        predictions = []
        m = self.mean
        v = self.variance
        for i in range(steps):
            s = signal if signal is not None else self.signal_memory
            m += self.config.alpha * (s - m) + self.config.beta * (self.config.mu_0 - m)
            v += self.config.gamma * (abs(s) - v) + self.config.delta * (self.config.sigma_0 - v)
            m = max(self.config.min_mean, min(self.config.max_mean, m))
            v = max(self.config.min_variance, min(self.config.max_variance, v))
            predictions.append({"mean": m, "variance": v, "entropy": -0.5 * math.log(v + 0.001)})
        return predictions

    def reset(self):
        self.mean = self.config.mu_0
        self.variance = self.config.sigma_0
        self.entropy = self._calc_entropy()
        self.t = 0.0
        self.signal_memory = 0.0
        self.history = []
        self.update_count = 0
        self.phase_state = FieldPhase.BREATH


class ExperiencePoolConsolidator:
    def __init__(self, db_path: str = "data/experience_pool.db"):
        self.db_path = db_path
        self.consolidation_count = 0
        self.last_consolidation = time.time()

    def consolidate(self, intensity: float = 1.0) -> Dict[str, int]:
        results = {"deduped": 0, "compressed": 0, "expired": 0, "active_count": 0}
        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get(self.db_path)

            limit = max(10, int(50 * intensity))

            low_quality = db.query(
                "SELECT id, raw_input, quality_score FROM experiences WHERE quality_score < 30 AND timestamp < datetime('now', '-7 days') ORDER BY timestamp ASC LIMIT ?",
                (limit,)
            )
            if low_quality:
                ids = [str(r[0]) for r in low_quality]
                placeholders = ",".join(["?"] * len(ids))
                db.execute(f"DELETE FROM experiences WHERE id IN ({placeholders})", ids, commit=True)
                results["compressed"] = len(low_quality)

            db.execute(
                "DELETE FROM experiences WHERE timestamp < datetime('now', '-90 days') AND quality_score < 20 LIMIT ?",
                (limit,), commit=True
            )
            results["expired"] = 0

            count_row = db.query_one("SELECT COUNT(*) FROM experiences")
            results["active_count"] = count_row[0] if count_row else 0

            self.consolidation_count += 1
            self.last_consolidation = time.time()
        except Exception as e:
            logger.debug(f"经验池整理跳过: {e}")
        return results


class PathWeightDecay:
    def __init__(self, half_life: float = 3600.0):
        self.half_life = half_life
        self.last_decay = time.time()
        self.decay_count = 0

    def decay(self) -> Dict[str, int]:
        results = {"decayed": 0, "total": 0}
        try:
            from core.path_weight_manager import path_weight_manager
            now = time.time()
            elapsed = now - self.last_decay
            decay_factor = 0.5 ** (elapsed / self.half_life)
            for path_name in list(path_weight_manager._paths.keys()):
                pw = path_weight_manager._paths[path_name]
                pw.weight = max(0.01, pw.weight * decay_factor)
                results["decayed"] += 1
            results["total"] = len(path_weight_manager._paths)
            self.last_decay = now
            self.decay_count += 1
        except Exception:
            pass
        return results


@dataclass
class PerformanceMetrics:
    responsiveness: float = 0.0
    stability: float = 0.0
    efficiency: float = 0.0
    prediction_accuracy: float = 0.0

    def overall_score(self) -> float:
        return (
            self.responsiveness * 0.3
            + self.stability * 0.3
            + self.efficiency * 0.2
            + self.prediction_accuracy * 0.2
        )


@dataclass
class ParameterSnapshot:
    timestamp: float
    alpha: float
    beta: float
    gamma: float
    delta: float
    performance: PerformanceMetrics
    trigger_reason: str


class ParameterEvolutionLog:
    def __init__(self, max_history: int = 1000):
        self.history: deque = deque(maxlen=max_history)
        self.update_count = 0

    def record(self, snapshot: ParameterSnapshot):
        self.history.append(snapshot)
        self.update_count += 1

    def get_trend(self, param_name: str, window: int = 10) -> float:
        if len(self.history) < window:
            return 0.0
        recent = list(self.history)[-window:]
        values = [getattr(s, param_name) for s in recent]
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        return numerator / denominator if denominator != 0 else 0.0

    def get_correlation(self, param_name: str, metric_name: str, window: int = 20) -> float:
        if len(self.history) < window:
            return 0.0
        recent = list(self.history)[-window:]
        params = [getattr(s, param_name) for s in recent]
        metrics = [getattr(s.performance, metric_name) for s in recent]
        n = len(params)
        mean_p = sum(params) / n
        mean_m = sum(metrics) / n
        cov = sum((p - mean_p) * (m - mean_m) for p, m in zip(params, metrics))
        std_p = math.sqrt(sum((p - mean_p) ** 2 for p in params))
        std_m = math.sqrt(sum((m - mean_m) ** 2 for m in metrics))
        return cov / (std_p * std_m) if std_p * std_m != 0 else 0.0


class AutoTuningEngine:
    PARAM_BOUNDS = {
        "alpha": (0.001, 0.1),
        "beta": (0.0001, 0.01),
        "gamma": (0.001, 0.05),
        "delta": (0.0001, 0.01),
    }

    def __init__(
        self,
        current_params: Dict[str, float],
        tuning_interval: float = 3600.0,
        min_updates: int = 100,
        step_size: float = 0.1,
    ):
        self.params = current_params.copy()
        self.tuning_interval = tuning_interval
        self.min_updates = min_updates
        self.step_size = step_size
        self.evolution_log = ParameterEvolutionLog()
        self._signal_history: deque = deque(maxlen=10000)
        self._performance_history: deque = deque(maxlen=1000)
        self.last_tuning_time = time.time()
        self.tuning_count = 0
        self.best_performance = 0.0
        self.best_params = current_params.copy()

    def record_update(self, signal: Optional[float], mean: float, variance: float):
        self._signal_history.append({
            "t": time.time(),
            "signal": signal,
            "mean": mean,
            "variance": variance,
        })

    def should_tune(self, update_count: int) -> bool:
        if update_count < self.min_updates:
            return False

        time_based = time.time() - self.last_tuning_time >= self.tuning_interval

        emergency = False
        if len(self._performance_history) >= 20:
            recent = list(self._performance_history)[-20:]
            recent_avg = sum(p.overall_score() for p in recent) / len(recent)
            if self.best_performance > 0 and recent_avg < self.best_performance * 0.8:
                emergency = True

        stable_period = True
        if len(self._signal_history) >= 50:
            recent_signals = sum(1 for s in list(self._signal_history)[-50:] if s.get("signal") is not None)
            stable_period = recent_signals < 10

        return (time_based and stable_period) or (emergency and stable_period)

    def tune(self, field: "ProbabilityFieldDrift") -> Optional[Dict[str, float]]:
        if not self.should_tune(field.update_count):
            return None

        current_perf = self._calculate_performance(field)
        gradients = self._estimate_gradients()
        candidate = self._generate_candidate(gradients)

        current_score = current_perf.overall_score()
        if current_score < self.best_performance * 0.95 and self.tuning_count > 0:
            logger.debug(f"自调优棘轮门控: score={current_score:.3f} < best={self.best_performance:.3f}*0.95, 阻止")
            return None

        old_params = self.params.copy()
        self.params = candidate
        field.config.alpha = candidate["alpha"]
        field.config.beta = candidate["beta"]
        field.config.gamma = candidate["gamma"]
        field.config.delta = candidate["delta"]

        param_delta = sum(
            abs(candidate[k] - old_params[k]) / max(old_params[k], 1e-6)
            for k in old_params
        ) / len(old_params)
        if param_delta > 0.3:
            field.mean = field.mean * 0.7 + field.config.mu_0 * 0.3
            field.variance = field.variance * 0.7 + field.config.sigma_0 * 0.3
            field.entropy = field._calc_entropy()
            logger.info(f"🌊 软着陆: 参数变化{param_delta:.0%}, mean/variance向基线收敛")

        snapshot = ParameterSnapshot(
            timestamp=time.time(),
            alpha=candidate["alpha"],
            beta=candidate["beta"],
            gamma=candidate["gamma"],
            delta=candidate["delta"],
            performance=current_perf,
            trigger_reason=f"auto_tune_{self.tuning_count}",
        )
        self.evolution_log.record(snapshot)

        if current_score > self.best_performance:
            self.best_performance = current_score
            self.best_params = candidate.copy()

        self.tuning_count += 1
        self.last_tuning_time = time.time()

        logger.info(
            f"🌊 概率场自调优 #{self.tuning_count}: "
            f"α={old_params['alpha']:.4f}→{candidate['alpha']:.4f}, "
            f"β={old_params['beta']:.4f}→{candidate['beta']:.4f}, "
            f"γ={old_params['gamma']:.4f}→{candidate['gamma']:.4f}, "
            f"δ={old_params['delta']:.4f}→{candidate['delta']:.4f}, "
            f"score={current_score:.3f}"
        )
        return candidate

    def _calculate_performance(self, field: "ProbabilityFieldDrift") -> PerformanceMetrics:
        responsiveness = self._calc_responsiveness()
        stability = self._calc_stability()
        efficiency = self._calc_efficiency()
        prediction_accuracy = self._calc_prediction_accuracy(field)
        perf = PerformanceMetrics(
            responsiveness=responsiveness,
            stability=stability,
            efficiency=efficiency,
            prediction_accuracy=prediction_accuracy,
        )
        self._performance_history.append(perf)
        return perf

    def _calc_responsiveness(self) -> float:
        responses = []
        history = list(self._signal_history)
        for i in range(1, len(history)):
            if history[i].get("signal") is not None:
                prev_mean = history[i - 1].get("mean", 0.5)
                curr_mean = history[i].get("mean", 0.5)
                responses.append(abs(curr_mean - prev_mean))
        if not responses:
            return 0.5
        avg = sum(responses[-50:]) / min(50, len(responses))
        return min(1.0, avg * 10)

    def _calc_stability(self) -> float:
        no_signal_means = []
        for h in self._signal_history:
            if h.get("signal") is None:
                no_signal_means.append(h.get("mean", 0.5))
        if len(no_signal_means) < 5:
            return 0.5
        recent = no_signal_means[-50:]
        m = sum(recent) / len(recent)
        var = sum((x - m) ** 2 for x in recent) / len(recent)
        return max(0.0, 1.0 - var * 1000)

    def _calc_efficiency(self) -> float:
        total_signals = sum(1 for h in self._signal_history if h.get("signal") is not None)
        if total_signals == 0:
            return 0.5
        total_updates = len(self._signal_history)
        ratio = total_updates / total_signals if total_signals > 0 else 0
        if 5 <= ratio <= 50:
            return 1.0 - abs(ratio - 20) / 50
        return max(0.0, 0.5 - abs(ratio - 20) / 100)

    def _calc_prediction_accuracy(self, field: "ProbabilityFieldDrift") -> float:
        if len(field.history) < 10:
            return 0.5
        recent = field.history[-20:]
        predicted = field.predict_future(steps=1)
        if not predicted:
            return 0.5
        pred_mean = predicted[0]["mean"]
        actual_mean = recent[-1]["mean"]
        error = abs(pred_mean - actual_mean)
        return max(0.0, 1.0 - error * 10)

    def _estimate_gradients(self) -> Dict[str, float]:
        gradients = {}
        for param_name in ["alpha", "beta", "gamma", "delta"]:
            corr = self.evolution_log.get_correlation(param_name, "overall_score", window=20)
            if abs(corr) < 0.05:
                if self.tuning_count < 5:
                    corr = random.uniform(-0.3, 0.3)
                else:
                    corr = 0.0
            gradients[param_name] = corr
        return gradients

    def _generate_candidate(self, gradients: Dict[str, float]) -> Dict[str, float]:
        candidate = self.params.copy()
        for param_name, gradient in gradients.items():
            adjustment = self.step_size * gradient * self.params[param_name]
            candidate[param_name] += adjustment
            lo, hi = self.PARAM_BOUNDS[param_name]
            candidate[param_name] = max(lo, min(hi, candidate[param_name]))
        return candidate

    def get_status(self) -> Dict:
        return {
            "current_params": {k: round(v, 5) for k, v in self.params.items()},
            "best_params": {k: round(v, 5) for k, v in self.best_params.items()},
            "best_performance": round(self.best_performance, 3),
            "tuning_count": self.tuning_count,
            "samples_collected": len(self._signal_history),
            "next_tuning_in": max(0, round(self.tuning_interval - (time.time() - self.last_tuning_time))),
            "evolution_trend": {
                p: round(self.evolution_log.get_trend(p, window=10), 5)
                for p in ["alpha", "beta", "gamma", "delta"]
            },
        }


_probability_field: Optional[ProbabilityFieldDrift] = None


def get_probability_field() -> ProbabilityFieldDrift:
    global _probability_field
    if _probability_field is None:
        _probability_field = ProbabilityFieldDrift()
        initial_params = {
            "alpha": _probability_field.config.alpha,
            "beta": _probability_field.config.beta,
            "gamma": _probability_field.config.gamma,
            "delta": _probability_field.config.delta,
        }
        _probability_field._auto_tuner = AutoTuningEngine(initial_params)
        logger.info("🌊 概率场漂移引擎已创建 — 系统有了呼吸节律（含自调优）")
    return _probability_field