"""
L2 监控感知层 - 异常模式识别 (Anomaly Detector)

类比：免疫系统——识别非自身模式
- 基于统计的异常检测（Z-score）
- 基于模式的异常检测（频率、序列）
- 异常评分与告警
"""
import time
import math
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime


class AnomalyDetector:
    MIN_SAMPLES = 10
    ZSCORE_THRESHOLD = 2.5
    RATE_SPIKE_THRESHOLD = 3.0

    def __init__(self):
        self._baselines: Dict[str, dict] = {}
        self._anomalies: List[dict] = []

    def _update_baseline(self, name: str, value: float):
        if name not in self._baselines:
            self._baselines[name] = {"values": [], "count": 0, "sum": 0, "sum_sq": 0}
        b = self._baselines[name]
        b["values"].append(value)
        b["count"] += 1
        b["sum"] += value
        b["sum_sq"] += value * value
        if len(b["values"]) > 1000:
            b["values"] = b["values"][-500:]

    def check(self, name: str, value: float) -> Optional[dict]:
        self._update_baseline(name, value)
        b = self._baselines[name]
        if b["count"] < self.MIN_SAMPLES:
            return None
        mean = b["sum"] / b["count"]
        variance = (b["sum_sq"] / b["count"]) - (mean * mean)
        std = math.sqrt(max(variance, 0))
        if std < 1e-9:
            return None
        z_score = abs(value - mean) / std
        if z_score > self.ZSCORE_THRESHOLD:
            anomaly = {
                "metric": name,
                "value": value,
                "mean": round(mean, 4),
                "std": round(std, 4),
                "z_score": round(z_score, 2),
                "direction": "high" if value > mean else "low",
                "timestamp": datetime.now().isoformat(),
            }
            self._anomalies.append(anomaly)
            if len(self._anomalies) > 500:
                self._anomalies = self._anomalies[-500:]
            logger.warning(f"🔍 异常检测: {name}={value:.2f} (均值={mean:.2f}, Z={z_score:.1f})")
            return anomaly
        return None

    def check_rate_spike(self, name: str, current_rate: float, baseline_rate: float) -> Optional[dict]:
        if baseline_rate < 1e-9:
            return None
        ratio = current_rate / baseline_rate
        if ratio > self.RATE_SPIKE_THRESHOLD:
            anomaly = {
                "metric": f"{name}_rate",
                "value": current_rate,
                "baseline": baseline_rate,
                "ratio": round(ratio, 2),
                "type": "rate_spike",
                "timestamp": datetime.now().isoformat(),
            }
            self._anomalies.append(anomaly)
            logger.warning(f"🔍 速率异常: {name} 当前={current_rate:.2f} 基线={baseline_rate:.2f} 比率={ratio:.1f}x")
            return anomaly
        return None

    def get_anomalies(self, limit: int = 20) -> List[dict]:
        return self._anomalies[-limit:]

    def get_baselines(self) -> dict:
        result = {}
        for name, b in self._baselines.items():
            if b["count"] >= self.MIN_SAMPLES:
                mean = b["sum"] / b["count"]
                variance = (b["sum_sq"] / b["count"]) - (mean * mean)
                result[name] = {
                    "mean": round(mean, 4),
                    "std": round(math.sqrt(max(variance, 0)), 4),
                    "samples": b["count"],
                }
        return result


anomaly_detector = AnomalyDetector()