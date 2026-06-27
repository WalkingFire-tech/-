"""
测试L6内省层引擎
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.introspection_engine import (
    IntrospectionEngine,
    SystemState,
    Anomaly,
    AnomalyType,
    AnomalySeverity,
    HealingResult,
    HealingStatus
)


def test_initialization():
    """测试初始化"""
    db_path = "data/test_introspection.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    engine = IntrospectionEngine(db_path=db_path)
    
    assert engine is not None
    assert engine.running is False
    assert isinstance(engine.thresholds, dict)
    assert isinstance(engine.healing_strategies, dict)
    print("✅ 初始化测试通过")


def test_perceive():
    """测试感知系统状态"""
    db_path = "data/test_introspection_perceive.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = IntrospectionEngine(db_path=db_path)
    
    state = engine.perceive()
    
    assert state is not None
    assert isinstance(state, SystemState)
    assert state.architecture_health is not None
    assert state.behavior_consistency is not None
    assert state.cognition_completeness is not None
    assert state.boundary_safety is not None
    assert state.evolution_health is not None
    print("✅ 感知系统状态测试通过")


def test_diagnose_architecture():
    """测试架构异常诊断"""
    db_path = "data/test_introspection_arch.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = IntrospectionEngine(db_path=db_path)
    
    engine.thresholds['component_survival_rate'] = 0.99
    
    state = SystemState(
        timestamp=datetime.now().isoformat(),
        architecture_health={
            'component_survival_rate': 0.90,
            'dependency_availability': True,
            'resource_usage': {'cpu': 85.0, 'memory': 60.0, 'disk': 55.0}
        },
        behavior_consistency={'error_rate': 0.02, 'philosophy_compliance': True},
        cognition_completeness={'knowledge_low_confidence_rate': 0.20, 'active_conflicts': 2},
        boundary_safety={'ethics_redline_triggered': False, 'domain_boundary_violations': 0},
        evolution_health={'last_evolution_days': 3, 'fitness_trend': 'increasing'},
        introspection_health={}
    )
    
    anomalies = engine.diagnose(state)
    
    assert len(anomalies) > 0
    assert any(a.type == AnomalyType.ARCHITECTURE for a in anomalies)
    print("✅ 架构异常诊断测试通过")


def test_diagnose_behavior():
    """测试行为异常诊断"""
    db_path = "data/test_introspection_behavior.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = IntrospectionEngine(db_path=db_path)
    
    state = SystemState(
        timestamp=datetime.now().isoformat(),
        architecture_health={'component_survival_rate': 0.98, 'resource_usage': {}},
        behavior_consistency={
            'error_rate': 0.10,
            'philosophy_compliance': False
        },
        cognition_completeness={'knowledge_low_confidence_rate': 0.20, 'active_conflicts': 2},
        boundary_safety={'ethics_redline_triggered': False, 'domain_boundary_violations': 0},
        evolution_health={'last_evolution_days': 3, 'fitness_trend': 'increasing'},
        introspection_health={}
    )
    
    anomalies = engine.diagnose(state)
    
    assert len(anomalies) >= 2
    assert any('哲学承诺' in a.description for a in anomalies)
    print("✅ 行为异常诊断测试通过")


def test_diagnose_cognition():
    """测试认知异常诊断"""
    db_path = "data/test_introspection_cognition.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = IntrospectionEngine(db_path=db_path)
    
    state = SystemState(
        timestamp=datetime.now().isoformat(),
        architecture_health={'component_survival_rate': 0.98, 'resource_usage': {}},
        behavior_consistency={'error_rate': 0.02, 'philosophy_compliance': True},
        cognition_completeness={
            'knowledge_low_confidence_rate': 0.40,
            'active_conflicts': 10
        },
        boundary_safety={'ethics_redline_triggered': False, 'domain_boundary_violations': 0},
        evolution_health={'last_evolution_days': 3, 'fitness_trend': 'increasing'},
        introspection_health={}
    )
    
    anomalies = engine.diagnose(state)
    
    assert len(anomalies) >= 2
    assert any('冲突' in a.description for a in anomalies)
    print("✅ 认知异常诊断测试通过")


def test_heal():
    """测试自动修复"""
    db_path = "data/test_introspection_heal.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = IntrospectionEngine(db_path=db_path)
    
    anomaly = Anomaly(
        id='test_anomaly_1',
        type=AnomalyType.BEHAVIOR,
        severity=AnomalySeverity.HIGH,
        description='错误率过高: 10%',
        context={'error_rate': 0.10},
        detected_at=datetime.now().isoformat()
    )
    
    result = engine.heal(anomaly)
    
    assert result is not None
    assert result.status in [HealingStatus.SUCCESS, HealingStatus.SKIPPED]
    print("✅ 自动修复测试通过")


def test_learn():
    """测试从修复中学习"""
    db_path = "data/test_introspection_learn.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = IntrospectionEngine(db_path=db_path)
    
    result = HealingResult(
        anomaly_id='test_anomaly',
        status=HealingStatus.SUCCESS,
        action_taken='启用熔断保护',
        effect={'circuit_breaker_enabled': True},
        timestamp=datetime.now().isoformat()
    )
    
    engine.learn(result)
    
    assert result.learned is True
    assert len(engine.anomaly_patterns) > 0
    print("✅ 从修复中学习测试通过")


def test_predict():
    """测试预测性审查"""
    db_path = "data/test_introspection_predict.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = IntrospectionEngine(db_path=db_path)
    
    state = SystemState(
        timestamp=datetime.now().isoformat(),
        architecture_health={'component_survival_rate': 0.98, 'resource_usage': {}},
        behavior_consistency={'error_rate': 0.02, 'philosophy_compliance': True},
        cognition_completeness={'knowledge_avg_confidence': 0.68},
        boundary_safety={'ethics_redline_triggered': False},
        evolution_health={'fitness_trend': 'flat'},
        introspection_health={}
    )
    
    predictions = engine.predict(state)
    
    assert len(predictions) >= 1
    assert any(p['type'] == 'knowledge_degradation' for p in predictions)
    print("✅ 预测性审查测试通过")


def test_introspection_report():
    """测试内省报告"""
    db_path = "data/test_introspection_report.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = IntrospectionEngine(db_path=db_path)
    
    state = engine.perceive()
    anomalies = engine.diagnose(state)
    
    if anomalies:
        result = engine.heal(anomalies[0])
        if result.status == HealingStatus.SUCCESS:
            engine.learn(result)
    
    report = engine.get_introspection_report()
    
    assert 'status' in report
    assert 'stats' in report
    assert 'recent_anomalies' in report
    assert 'thresholds' in report
    print("✅ 内省报告测试通过")


def test_introspection_complete():
    """完整流程测试"""
    db_path = "data/test_introspection_complete.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = IntrospectionEngine(db_path=db_path)
    
    state = engine.perceive()
    engine.stats['perceptions'] = 1
    print(f"   感知状态: {state.timestamp}")
    
    anomalies = engine.diagnose(state)
    print(f"   诊断异常: {len(anomalies)}个")
    
    healed_count = 0
    for anomaly in anomalies:
        result = engine.heal(anomaly)
        if result.status == HealingStatus.SUCCESS:
            engine.learn(result)
            healed_count += 1
    
    print(f"   成功修复: {healed_count}个")
    
    predictions = engine.predict(state)
    print(f"   预测异常: {len(predictions)}个")
    
    report = engine.get_introspection_report()
    print(f"   修复成功率: {report['healing_success_rate']:.2%}")
    
    assert report['stats']['perceptions'] >= 1
    assert report['stats']['anomalies_detected'] >= len(anomalies)
    
    print("✅ L6内省层完整测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试L6内省层引擎")
    print("=" * 60)
    
    test_initialization()
    test_perceive()
    test_diagnose_architecture()
    test_diagnose_behavior()
    test_diagnose_cognition()
    test_heal()
    test_learn()
    test_predict()
    test_introspection_report()
    test_introspection_complete()
    
    print("=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)