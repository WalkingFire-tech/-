"""
测试冲突协调器
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.conflict_coordinator import (
    ConflictCoordinator,
    Conflict,
    ConflictType,
    ConflictSeverity,
    EvolutionRule
)


def test_initialization():
    """测试初始化"""
    db_path = "data/test_conflict_coordinator.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    
    coordinator = ConflictCoordinator(db_path=db_path)
    
    assert coordinator is not None
    assert coordinator.db_path == db_path
    assert isinstance(coordinator.conflict_history, list)
    assert isinstance(coordinator.applied_rules, dict)
    print("✅ 初始化测试通过")


def test_priority_table():
    """测试优先级表"""
    db_path = "data/test_conflict_priority.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    coordinator = ConflictCoordinator(db_path=db_path)
    
    assert coordinator.PRIORITY_TABLE['user_feedback'] == 100
    assert coordinator.PRIORITY_TABLE['safe_guard'] == 90
    assert coordinator.PRIORITY_TABLE['philosophy_rule'] == 85
    assert coordinator.PRIORITY_TABLE['default_config'] == 40
    print("✅ 优先级表测试通过")


def test_detect_parameter_conflict():
    """测试参数冲突检测"""
    db_path = "data/test_conflict_param.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    coordinator = ConflictCoordinator(db_path=db_path)
    
    rule1 = {
        'parameter': 'learning_rate',
        'value': 0.01,
        'source_type': 'evolution_result'
    }
    
    rule2 = {
        'parameter': 'learning_rate',
        'value': 0.1,
        'source_type': 'learning_rule'
    }
    
    conflict = coordinator.detect_conflicts(rule1, rule2)
    
    assert conflict is not None
    assert conflict.type == ConflictType.GENE_RULE
    assert conflict.severity == ConflictSeverity.HIGH
    assert 'learning_rate' in conflict.description
    print("✅ 参数冲突检测测试通过")


def test_arbitrate_by_priority():
    """测试按优先级仲裁"""
    db_path = "data/test_conflict_priority_arb.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    coordinator = ConflictCoordinator(db_path=db_path)
    
    rule1 = {
        'parameter': 'threshold',
        'value': 0.5,
        'source_type': 'user_feedback',
        'evidence': {}
    }
    
    rule2 = {
        'parameter': 'threshold',
        'value': 0.8,
        'source_type': 'learning_rule',
        'evidence': {}
    }
    
    conflict = coordinator.detect_conflicts(rule1, rule2)
    assert conflict is not None
    
    decision = coordinator.arbitrate(conflict)
    
    assert decision['winner'] == 'source1'
    assert '优先级更高' in decision['reason']
    assert decision['rule']['value'] == 0.5
    print("✅ 优先级仲裁测试通过")


def test_arbitrate_by_evidence():
    """测试按证据仲裁（优先级相同时）"""
    db_path = "data/test_conflict_evidence.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    coordinator = ConflictCoordinator(db_path=db_path)
    
    rule1 = {
        'parameter': 'threshold',
        'value': 0.5,
        'source_type': 'learning_rule',
        'evidence': {
            'user_feedback_count': 3,
            'success_count': 2
        }
    }
    
    rule2 = {
        'parameter': 'threshold',
        'value': 0.8,
        'source_type': 'learning_rule',
        'evidence': {
            'user_feedback_count': 1,
            'success_count': 1
        }
    }
    
    conflict = coordinator.detect_conflicts(rule1, rule2)
    assert conflict is not None
    
    decision = coordinator.arbitrate(conflict)
    
    assert decision['winner'] == 'source1'
    assert '证据更充分' in decision['reason']
    print("✅ 证据仲裁测试通过")


def test_conflict_coordinator_complete():
    """完整流程测试"""
    db_path = "data/test_conflict_complete.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    if os.path.exists(db_path):
        os.remove(db_path)
    
    coordinator = ConflictCoordinator(db_path=db_path)
    
    rule1 = EvolutionRule(
        rule_id='gene_rule_1',
        source_type='evolution_result',
        parameter='learning_rate',
        value=0.01,
        priority=70,
        applied_at=datetime.now().isoformat(),
        evidence={'success_count': 3, 'data_points': 50}
    )
    
    rule2 = EvolutionRule(
        rule_id='user_rule_1',
        source_type='user_feedback',
        parameter='learning_rate',
        value=0.1,
        priority=100,
        applied_at=datetime.now().isoformat(),
        evidence={'user_feedback_count': 5}
    )
    
    coordinator.register_rule(rule1)
    coordinator.register_rule(rule2)
    
    conflict = coordinator.detect_conflicts(
        {'parameter': 'learning_rate', 'value': 0.01, 'source_type': 'evolution_result', 'evidence': {}},
        {'parameter': 'learning_rate', 'value': 0.1, 'source_type': 'user_feedback', 'evidence': {}}
    )
    
    assert conflict is not None
    
    coordinator.save_conflict(conflict)
    coordinator.conflict_history.append(conflict)
    
    decision = coordinator.arbitrate(conflict)
    
    assert decision['winner'] == 'source2'
    assert decision['rule']['value'] == 0.1
    
    stats = coordinator.get_conflict_stats()
    assert stats['total_conflicts'] >= 1
    
    print("✅ 冲突协调器完整测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试冲突协调器")
    print("=" * 60)
    
    test_initialization()
    test_priority_table()
    test_detect_parameter_conflict()
    test_arbitrate_by_priority()
    test_arbitrate_by_evidence()
    test_conflict_coordinator_complete()
    
    print("=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)