"""
自我感知模块 (Self Perception Module) - 优化版

核心理念：系统持续感知自身状态
- 不是被动地被查询
- 而是主动地感知自己

核心能力：
1. 健康度评估 - 系统整体健康状态
2. 置信度评估 - 对当前知识的信心
3. 能量水平 - 系统活力
4. 知识增长 - 学习进度
5. 关系健康 - 与用户的关系状态
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import threading
import time

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class HealthIndicator(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class SystemHealth:
    """系统健康状态"""
    indicator: HealthIndicator
    score: float
    issues: List[str]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConfidenceAssessment:
    """置信度评估"""
    overall: float
    by_domain: Dict[str, float]
    recent_trend: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SelfPerceptionResult:
    """自我感知结果"""
    health_score: float
    confidence_level: float
    energy_level: float
    knowledge_growth: float
    relationship_health: float
    timestamp: datetime = field(default_factory=datetime.now)


class SelfPerceptionModule:
    """
    自我感知模块
    
    让系统持续感知自身状态
    """
    
    def __init__(self):
        self.health_history: List[SystemHealth] = []
        self.confidence_history: List[ConfidenceAssessment] = []
        self.energy_history: List[float] = []
        
        self.knowledge_metrics = {
            "total_knowledge": 0,
            "recent_additions": 0,
            "validation_rate": 0.0,
        }
        
        self.relationship_metrics = {
            "trust_level": 0.8,
            "interaction_count": 0,
            "positive_rate": 0.8,
        }
        
        self.subsystem_health = {
            "cognitive_loop": True,
            "learning_mechanisms": True,
            "knowledge_network": True,
            "rhythm_controller": True,
            "memory_system": True,
            "existence_layer": True,
        }
        
        self.running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        logger.info("👁️ 自我感知模块已初始化")
    
    def start(self):
        """启动监控"""
        if self.running:
            return
        
        self.running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        logger.info("👁️ 自我感知监控已启动")
    
    def stop(self):
        """停止监控"""
        self.running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3)
        logger.info("👁️ 自我感知监控已停止")
    
    def is_running(self) -> bool:
        """检查是否运行中"""
        return self.running and (self._monitor_thread is not None and self._monitor_thread.is_alive())
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self.perceive()
                time.sleep(30)
            except Exception as e:
                logger.error(f"自我感知监控错误: {e}")
                time.sleep(60)
    
    def perceive(self) -> SelfPerceptionResult:
        """
        执行自我感知
        
        返回完整的自我感知结果
        """
        health = self._assess_health()
        confidence = self._assess_confidence()
        energy = self._assess_energy()
        knowledge = self._assess_knowledge_growth()
        relationship = self._assess_relationship()
        
        return SelfPerceptionResult(
            health_score=health.score,
            confidence_level=confidence.overall,
            energy_level=energy,
            knowledge_growth=knowledge,
            relationship_health=relationship,
        )
    
    def _assess_health(self) -> SystemHealth:
        """评估系统健康度"""
        issues = []
        recommendations = []
        
        healthy_count = sum(1 for v in self.subsystem_health.values() if v)
        total_count = len(self.subsystem_health)
        
        for name, healthy in self.subsystem_health.items():
            if not healthy:
                issues.append(f"{name} 异常")
                recommendations.append(f"检查并修复 {name}")
        
        if healthy_count == total_count:
            indicator = HealthIndicator.EXCELLENT
            score = 1.0
        elif healthy_count >= total_count * 0.8:
            indicator = HealthIndicator.GOOD
            score = 0.8
        elif healthy_count >= total_count * 0.6:
            indicator = HealthIndicator.FAIR
            score = 0.6
        elif healthy_count >= total_count * 0.4:
            indicator = HealthIndicator.POOR
            score = 0.4
        else:
            indicator = HealthIndicator.CRITICAL
            score = 0.2
        
        health = SystemHealth(
            indicator=indicator,
            score=score,
            issues=issues,
            recommendations=recommendations,
        )
        
        self.health_history.append(health)
        if len(self.health_history) > 50:
            self.health_history = self.health_history[-25:]
        
        return health
    
    def _assess_confidence(self) -> ConfidenceAssessment:
        """评估置信度"""
        by_domain = {
            "knowledge": 0.7,
            "reasoning": 0.75,
            "recommendation": 0.65,
            "general": 0.7,
        }
        
        overall = sum(by_domain.values()) / len(by_domain)
        
        if len(self.confidence_history) >= 2:
            recent = self.confidence_history[-1].overall
            if overall > recent + 0.05:
                trend = "improving"
            elif overall < recent - 0.05:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        assessment = ConfidenceAssessment(
            overall=overall,
            by_domain=by_domain,
            recent_trend=trend,
        )
        
        self.confidence_history.append(assessment)
        if len(self.confidence_history) > 50:
            self.confidence_history = self.confidence_history[-25:]
        
        return assessment
    
    def _assess_energy(self) -> float:
        """评估能量水平"""
        base_energy = 0.8
        
        if len(self.health_history) > 0:
            health_factor = self.health_history[-1].score
        else:
            health_factor = 1.0
        
        knowledge_factor = min(1.0, self.knowledge_metrics.get("total_knowledge", 0) / 100)
        
        energy = base_energy * health_factor * (0.7 + 0.3 * knowledge_factor)
        
        self.energy_history.append(energy)
        if len(self.energy_history) > 100:
            self.energy_history = self.energy_history[-50:]
        
        return energy
    
    def _assess_knowledge_growth(self) -> float:
        """评估知识增长"""
        total = self.knowledge_metrics.get("total_knowledge", 0)
        recent = self.knowledge_metrics.get("recent_additions", 0)
        
        if total == 0:
            return 0.0
        
        growth_rate = recent / max(total, 1)
        
        return min(1.0, growth_rate * 10)
    
    def _assess_relationship(self) -> float:
        """评估关系健康"""
        trust = self.relationship_metrics.get("trust_level", 0.5)
        positive_rate = self.relationship_metrics.get("positive_rate", 0.5)
        
        relationship_health = trust * 0.6 + positive_rate * 0.4
        
        return relationship_health
    
    def update_knowledge_metrics(self, metrics: Dict[str, Any]):
        """更新知识指标"""
        self.knowledge_metrics.update(metrics)
    
    def update_relationship_metrics(self, metrics: Dict[str, Any]):
        """更新关系指标"""
        self.relationship_metrics.update(metrics)
    
    def report_subsystem_status(self, subsystem: str, healthy: bool):
        """报告子系统状态"""
        self.subsystem_health[subsystem] = healthy
        
        if not healthy:
            logger.warning(f"⚠️ 子系统 {subsystem} 报告异常")
    
    def get_current_perception(self) -> Optional[SelfPerceptionResult]:
        """获取当前感知结果"""
        if self.health_history and self.confidence_history:
            health = self.health_history[-1]
            confidence = self.confidence_history[-1]
            energy = self.energy_history[-1] if self.energy_history else 0.7
            
            return SelfPerceptionResult(
                health_score=health.score,
                confidence_level=confidence.overall,
                energy_level=energy,
                knowledge_growth=self._assess_knowledge_growth(),
                relationship_health=self._assess_relationship(),
            )
        
        return None
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        if not self.health_history:
            return {"status": "no_data"}
        
        recent = self.health_history[-1]
        
        return {
            "indicator": recent.indicator.value,
            "score": recent.score,
            "issues": recent.issues,
            "recommendations": recent.recommendations,
            "subsystems": self.subsystem_health,
            "timestamp": recent.timestamp.isoformat(),
        }


_self_perception_module: Optional[SelfPerceptionModule] = None


def get_self_perception_module() -> SelfPerceptionModule:
    """获取全局自我感知模块实例"""
    global _self_perception_module
    if _self_perception_module is None:
        _self_perception_module = SelfPerceptionModule()
    return _self_perception_module


def start_self_perception():
    """启动自我感知"""
    module = get_self_perception_module()
    module.start()
    return module
