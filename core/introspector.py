"""
系统内省监控服务 - 轻量级异常检测与内省报告

基于现有基础设施（health_monitor + scheduled_tasks + event_bus），
不依赖core/layers/的复杂依赖链。

核心能力：
1. 异常检测：检测子系统退化、数据闭环断裂、资源异常
2. 内省报告：定期生成系统健康度评估
3. 自动修复建议：基于异常类型给出修复建议

设计原则：
- 轻量级：不引入新依赖，复用现有模块
- 非侵入：不修改主流程，通过event_bus发布事件
- 可恢复：检测到异常时给出建议，不自动执行破坏性操作
"""

import json
import time
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path
from infrastructure.database_manager import DatabaseManager

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class AnomalySeverity(Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    OBSERVATION = "observation"


class AnomalyCategory(Enum):
    RESOURCE = "resource"
    DATA_LOOP = "data_loop"
    SUBSYSTEM = "subsystem"
    PERFORMANCE = "performance"


@dataclass
class Anomaly:
    id: str
    title: str
    description: str
    severity: AnomalySeverity
    category: AnomalyCategory
    detected_at: str
    metric_name: str = ""
    metric_value: Any = None
    threshold: Any = None
    suggestion: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "detected_at": self.detected_at,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "suggestion": self.suggestion,
        }


@dataclass
class IntrospectionReport:
    generated_at: str
    overall_health: float
    anomaly_count: int
    critical_count: int
    major_count: int
    minor_count: int
    subsystem_status: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[Dict] = field(default_factory=list)
    trends: Dict[str, str] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


class SystemIntrospector:
    """系统内省监控 - 轻量级异常检测与内省报告"""

    HISTORY_FILE = "data/introspection_history.json"
    MAX_HISTORY = 50

    def __init__(self):
        self._anomalies: List[Anomaly] = []
        self._history: List[Dict] = []
        self._last_check_time = 0
        self._check_count = 0
        self._lock = threading.Lock()
        self._load_history()

    def _load_history(self):
        try:
            p = Path(self.HISTORY_FILE)
            if p.exists():
                with open(p, 'r', encoding='utf-8') as f:
                    self._history = json.load(f)
        except Exception:
            self._history = []

    def _save_history(self):
        try:
            p = Path(self.HISTORY_FILE)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(self._history[-self.MAX_HISTORY:], f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def run_check(self) -> IntrospectionReport:
        self._check_count += 1
        now = datetime.now().isoformat()
        new_anomalies = []

        new_anomalies.extend(self._check_resource())
        new_anomalies.extend(self._check_data_loops())
        new_anomalies.extend(self._check_subsystems())
        new_anomalies.extend(self._check_performance())
        new_anomalies.extend(self._check_alignment())

        with self._lock:
            self._anomalies = [a for a in self._anomalies
                               if a.severity in (AnomalySeverity.CRITICAL, AnomalySeverity.MAJOR)
                               and (datetime.now() - datetime.fromisoformat(a.detected_at)).total_seconds() < 3600]
            self._anomalies.extend(new_anomalies)

        critical = sum(1 for a in self._anomalies if a.severity == AnomalySeverity.CRITICAL)
        major = sum(1 for a in self._anomalies if a.severity == AnomalySeverity.MAJOR)
        minor = sum(1 for a in self._anomalies if a.severity == AnomalySeverity.MINOR)

        health = max(0.0, 1.0 - critical * 0.3 - major * 0.1 - minor * 0.03)

        report = IntrospectionReport(
            generated_at=now,
            overall_health=round(health, 3),
            anomaly_count=len(self._anomalies),
            critical_count=critical,
            major_count=major,
            minor_count=minor,
            anomalies=[a.to_dict() for a in self._anomalies],
            recommendations=self._generate_recommendations(),
        )

        self._history.append({
            "timestamp": now,
            "health": health,
            "anomaly_count": len(self._anomalies),
            "critical": critical,
        })
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]
        self._save_history()

        if new_anomalies:
            for a in new_anomalies:
                log_fn = logger.warning if a.severity in (AnomalySeverity.CRITICAL, AnomalySeverity.MAJOR) else logger.info
                log_fn(f"内省检测: [{a.severity.value}] {a.title} - {a.description}")

        self._last_check_time = time.time()
        return report

    def _check_resource(self) -> List[Anomaly]:
        anomalies = []
        try:
            from core.resource_awareness.health_monitor import get_health_monitor
            hm = get_health_monitor()
            snap = hm.check()
            if snap.memory_usage > 0.85:
                anomalies.append(Anomaly(
                    id=f"res_mem_{int(time.time())}",
                    title="内存使用率过高",
                    description=f"内存使用率{snap.memory_usage:.1%}，超过85%阈值",
                    severity=AnomalySeverity.CRITICAL if snap.memory_usage > 0.9 else AnomalySeverity.MAJOR,
                    category=AnomalyCategory.RESOURCE,
                    detected_at=datetime.now().isoformat(),
                    metric_name="memory_usage",
                    metric_value=round(snap.memory_usage, 3),
                    threshold=0.85,
                    suggestion="检查是否有内存泄漏，考虑重启服务",
                ))
            if snap.thread_count > 70:
                anomalies.append(Anomaly(
                    id=f"res_thr_{int(time.time())}",
                    title="线程数过多",
                    description=f"活跃线程{snap.thread_count}个，超过70阈值",
                    severity=AnomalySeverity.MAJOR,
                    category=AnomalyCategory.RESOURCE,
                    detected_at=datetime.now().isoformat(),
                    metric_name="thread_count",
                    metric_value=snap.thread_count,
                    threshold=70,
                    suggestion="检查后台任务是否过多，考虑减少并行度",
                ))
        except Exception:
            pass
        return anomalies

    def _check_data_loops(self) -> List[Anomaly]:
        anomalies = []
        try:
            conn = DatabaseManager.get("data/experience_pool.db")._get_conn()
            cur = conn.execute("SELECT COUNT(*) FROM experiences WHERE success = 0")
            fail_count = cur.fetchone()[0]
            cur2 = conn.execute("SELECT COUNT(*) FROM experiences")
            total = cur2.fetchone()[0]
            if total > 0 and fail_count / total > 0.5:
                anomalies.append(Anomaly(
                    id=f"data_exp_{int(time.time())}",
                    title="经验池失败率过高",
                    description=f"经验池失败率{fail_count/total:.1%}({fail_count}/{total})",
                    severity=AnomalySeverity.MAJOR,
                    category=AnomalyCategory.DATA_LOOP,
                    detected_at=datetime.now().isoformat(),
                    metric_name="experience_failure_rate",
                    metric_value=round(fail_count / total, 3),
                    threshold=0.5,
                    suggestion="检查推理路径配置，可能需要调整模型或搜索策略",
                ))
        except Exception:
            pass

        try:
            conn = DatabaseManager.get("data/rule_store.db")._get_conn()
            cur = conn.execute("SELECT COUNT(*) FROM rules WHERE apply_count > 0")
            active = cur.fetchone()[0]
            cur2 = conn.execute("SELECT COUNT(*) FROM rules WHERE status = 'active'")
            total_active = cur2.fetchone()[0]
            if total_active > 0 and active / total_active < 0.1:
                anomalies.append(Anomaly(
                    id=f"data_rule_{int(time.time())}",
                    title="规则使用率过低",
                    description=f"活跃规则中使用率<10%: {active}/{total_active}",
                    severity=AnomalySeverity.MINOR,
                    category=AnomalyCategory.DATA_LOOP,
                    detected_at=datetime.now().isoformat(),
                    metric_name="rule_usage_rate",
                    metric_value=round(active / total_active, 3),
                    threshold=0.1,
                    suggestion="检查规则条件是否过于严格，或context变量是否缺失",
                ))
        except Exception:
            pass

        return anomalies

    def _check_subsystems(self) -> List[Anomaly]:
        anomalies = []
        try:
            from core.resource_awareness.background_controller import get_background_controller
            bc = get_background_controller()
            paused = bc.get_paused_tasks()
            if len(paused) >= 3:
                anomalies.append(Anomaly(
                    id=f"subsys_bg_{int(time.time())}",
                    title="多个后台任务被暂停",
                    description=f"已暂停任务: {', '.join(paused)}",
                    severity=AnomalySeverity.MAJOR,
                    category=AnomalyCategory.SUBSYSTEM,
                    detected_at=datetime.now().isoformat(),
                    metric_name="paused_background_tasks",
                    metric_value=len(paused),
                    threshold=3,
                    suggestion="系统可能处于保守/紧急模式，检查资源状态",
                ))
        except Exception:
            pass

        try:
            from infrastructure.vector_retriever import _ST_AVAILABLE
            if not _ST_AVAILABLE:
                anomalies.append(Anomaly(
                    id=f"subsys_vec_{int(time.time())}",
                    title="语义检索不可用",
                    description="sentence_transformers模型未加载，使用TF-IDF降级",
                    severity=AnomalySeverity.MINOR,
                    category=AnomalyCategory.SUBSYSTEM,
                    detected_at=datetime.now().isoformat(),
                    metric_name="semantic_search_available",
                    metric_value=False,
                    threshold=True,
                    suggestion="检查模型文件是否完整，或DirectEncoder是否正常",
                ))
        except Exception:
            pass

        return anomalies

    def _check_performance(self) -> List[Anomaly]:
        anomalies = []
        try:
            conn = DatabaseManager.get("data/experience_pool.db")._get_conn()
            cur = conn.execute(
                "SELECT AVG(duration) FROM experiences WHERE timestamp > datetime('now', '-1 hour')"
            )
            avg_duration = cur.fetchone()[0]
            if avg_duration and avg_duration > 30:
                anomalies.append(Anomaly(
                    id=f"perf_dur_{int(time.time())}",
                    title="平均响应时间过长",
                    description=f"近1小时平均响应时间{avg_duration:.1f}秒",
                    severity=AnomalySeverity.MAJOR if avg_duration > 60 else AnomalySeverity.MINOR,
                    category=AnomalyCategory.PERFORMANCE,
                    detected_at=datetime.now().isoformat(),
                    metric_name="avg_response_duration",
                    metric_value=round(avg_duration, 1),
                    threshold=30,
                    suggestion="检查Ollama并发控制、模型加载时间、网络延迟",
                ))
        except Exception:
            pass
        return anomalies

    def _generate_recommendations(self) -> List[str]:
        recs = []
        critical = [a for a in self._anomalies if a.severity == AnomalySeverity.CRITICAL]
        major = [a for a in self._anomalies if a.severity == AnomalySeverity.MAJOR]

        if any(a.category == AnomalyCategory.RESOURCE for a in critical):
            recs.append("资源严重不足，建议立即检查内存/线程使用情况")
        if any(a.category == AnomalyCategory.DATA_LOOP for a in major):
            recs.append("数据闭环异常，建议检查经验池/规则库的写入-读取链路")
        if any(a.category == AnomalyCategory.SUBSYSTEM for a in major):
            recs.append("子系统退化，建议检查后台任务状态和模型可用性")
        if any(a.category == AnomalyCategory.PERFORMANCE for a in major):
            recs.append("性能退化，建议检查Ollama状态和网络连接")

        if not recs and not critical and not major:
            recs.append("系统运行正常，无异常")

        return recs

    def _check_alignment(self) -> List[Anomaly]:
        anomalies = []
        try:
            from core.alignment_guard import get_alignment_guard
            guard = get_alignment_guard()
            stats = guard.get_stats()
            open_deviations = stats.get("open", 0)
            if open_deviations > 0:
                anomalies.append(Anomaly(
                    id=f"align_{int(time.time())}",
                    title=f"存在{open_deviations}个未修正的思想偏离",
                    description=f"偏离类型分布: {stats.get('by_type', {})}",
                    severity=AnomalySeverity.MAJOR if open_deviations > 3 else AnomalySeverity.MINOR,
                    category=AnomalyCategory.SUBSYSTEM,
                    detected_at=datetime.now().isoformat(),
                    metric_name="open_alignment_deviations",
                    metric_value=open_deviations,
                    threshold=0,
                    suggestion="检查ALIGNMENT_CHARTER.md中的偏离记录，制定修正方案",
                ))
        except Exception:
            pass
        return anomalies

    def get_status(self) -> Dict:
        with self._lock:
            return {
                "last_check": datetime.fromtimestamp(self._last_check_time).isoformat() if self._last_check_time else "never",
                "check_count": self._check_count,
                "active_anomalies": len(self._anomalies),
                "critical": sum(1 for a in self._anomalies if a.severity == AnomalySeverity.CRITICAL),
                "major": sum(1 for a in self._anomalies if a.severity == AnomalySeverity.MAJOR),
                "minor": sum(1 for a in self._anomalies if a.severity == AnomalySeverity.MINOR),
                "history_size": len(self._history),
            }

    def get_recent_anomalies(self, limit: int = 20) -> List[Dict]:
        with self._lock:
            return [a.to_dict() for a in self._anomalies[-limit:]]

    def get_health_trend(self, hours: int = 24) -> List[Dict]:
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        return [h for h in self._history if h.get("timestamp", "") >= cutoff]


_introspector_instance = None


def get_introspector() -> SystemIntrospector:
    global _introspector_instance
    if _introspector_instance is None:
        _introspector_instance = SystemIntrospector()
    return _introspector_instance