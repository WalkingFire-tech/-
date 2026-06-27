"""
测试增强版认知调度器
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.enhanced_scheduler import (
    EnhancedCognitiveScheduler,
    TaskPriority
)


def test_initialization():
    """测试初始化"""
    db_path = "data/test_enhanced_scheduler.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    assert scheduler is not None
    assert scheduler.conflict_coordinator is not None
    assert scheduler.trigger_feedback is not None
    assert scheduler.memory_assessor is not None
    assert scheduler.running is False
    print("✅ 初始化测试通过")


def test_collect_system_state():
    """测试收集系统状态"""
    db_path = "data/test_scheduler_state.db"
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    state = scheduler._collect_system_state()
    
    assert 'timestamp' in state
    assert 'health' in state
    assert 'knowledge' in state
    assert 'memory' in state
    assert 'conflicts' in state
    assert 'trigger' in state
    print("✅ 收集系统状态测试通过")


def test_select_tasks():
    """测试选择任务"""
    db_path = "data/test_scheduler_tasks.db"
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    state = {
        'health': {'status': 'healthy'},
        'trigger': {'accuracy': 0.8},
        'memory': {'total': 50}
    }
    
    tasks = scheduler._select_tasks(state)
    
    assert len(tasks) > 0
    assert all('name' in task and 'priority' in task for task in tasks)
    print("✅ 选择任务测试通过")


def test_task_priority():
    """测试任务优先级排序"""
    db_path = "data/test_scheduler_priority.db"
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    state = {
        'health': {'status': 'unhealthy'},
        'trigger': {'accuracy': 0.5},
        'memory': {'total': 150}
    }
    
    tasks = scheduler._select_tasks(state)
    
    for i in range(len(tasks) - 1):
        assert tasks[i]['priority'].value >= tasks[i+1]['priority'].value
    print("✅ 任务优先级排序测试通过")


def test_register_evolution_rule():
    """测试注册进化规则"""
    db_path = "data/test_scheduler_rule.db"
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    scheduler.register_evolution_rule(
        rule_id='test_rule_1',
        source_type='user_feedback',
        parameter='learning_rate',
        value=0.1,
        evidence={'user_feedback_count': 5}
    )
    
    assert 'test_rule_1' in scheduler.conflict_coordinator.applied_rules
    print("✅ 注册进化规则测试通过")


def test_record_trigger_event():
    """测试记录触发事件"""
    db_path = "data/test_scheduler_trigger.db"
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    event_id = scheduler.record_trigger_event(
        user_input="测试输入",
        triggered=True,
        depth='full',
        reason='keyword_match'
    )
    
    assert event_id is not None
    assert len(event_id) == 12
    assert scheduler.trigger_feedback.stats['total_decisions'] == 1
    print("✅ 记录触发事件测试通过")


def test_provide_feedback():
    """测试提供反馈"""
    db_path = "data/test_scheduler_feedback.db"
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    event_id = scheduler.record_trigger_event(
        user_input="测试输入",
        triggered=True,
        depth='full',
        reason='keyword_match'
    )
    
    scheduler.provide_feedback(event_id, satisfied=True)
    
    assert scheduler.trigger_feedback.stats['true_positives'] == 1
    print("✅ 提供反馈测试通过")


def test_evaluate_memory():
    """测试评估记忆"""
    db_path = "data/test_scheduler_memory.db"
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    memory = {
        'id': 'test_memory',
        'content': '测试记忆',
        'user_marked_important': True,
        'access_count': 10,
        'created_at': datetime.now().isoformat()
    }
    
    result = scheduler.evaluate_memory(memory)
    
    assert 'score' in result
    assert 'grade' in result
    assert 'retain' in result
    assert result['retain'] is True
    print("✅ 评估记忆测试通过")


def test_calculate_interval():
    """测试计算间隔"""
    db_path = "data/test_scheduler_interval.db"
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    state_healthy = {'health': {'status': 'healthy'}, 'conflicts': {'active_conflicts': 0}}
    state_unhealthy = {'health': {'status': 'unhealthy'}, 'conflicts': {'active_conflicts': 0}}
    state_conflicts = {'health': {'status': 'healthy'}, 'conflicts': {'active_conflicts': 5}}
    
    interval_healthy = scheduler._calculate_interval(state_healthy)
    interval_unhealthy = scheduler._calculate_interval(state_unhealthy)
    interval_conflicts = scheduler._calculate_interval(state_conflicts)
    
    assert interval_healthy == 60
    assert interval_unhealthy == 10
    assert interval_conflicts == 30
    print("✅ 计算间隔测试通过")


def test_get_status():
    """测试获取状态"""
    db_path = "data/test_scheduler_status.db"
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    status = scheduler.get_status()
    
    assert 'running' in status
    assert 'stats' in status
    assert 'conflicts' in status
    assert 'trigger' in status
    assert 'memory' in status
    print("✅ 获取状态测试通过")


def test_enhanced_scheduler_complete():
    """完整流程测试"""
    db_path = "data/test_enhanced_complete.db"
    scheduler = EnhancedCognitiveScheduler(db_path=db_path)
    
    scheduler.register_evolution_rule(
        rule_id='gene_rule',
        source_type='evolution_result',
        parameter='threshold',
        value=0.5,
        evidence={'success_count': 3}
    )
    
    scheduler.register_evolution_rule(
        rule_id='user_rule',
        source_type='user_feedback',
        parameter='threshold',
        value=0.8,
        evidence={'user_feedback_count': 5}
    )
    
    active_rules = scheduler._get_active_rules()
    assert len(active_rules) >= 2
    
    state = scheduler._collect_system_state()
    conflicts = scheduler._detect_conflicts(state)
    
    if conflicts:
        scheduler._resolve_conflicts(conflicts)
        assert scheduler.stats['conflicts_resolved'] > 0
    
    event_id = scheduler.record_trigger_event(
        user_input="推荐芯片",
        triggered=True,
        depth='full',
        reason='keyword_match'
    )
    scheduler.provide_feedback(event_id, satisfied=True)
    
    memory = {
        'id': 'important_memory',
        'content': '重要记忆',
        'user_marked_important': True,
        'access_count': 20,
        'created_at': datetime.now().isoformat()
    }
    result = scheduler.evaluate_memory(memory)
    assert result['retain'] is True
    
    status = scheduler.get_status()
    assert status['stats']['tasks_executed'] >= 0
    
    print("✅ 增强版认知调度器完整测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试增强版认知调度器")
    print("=" * 60)
    
    test_initialization()
    test_collect_system_state()
    test_select_tasks()
    test_task_priority()
    test_register_evolution_rule()
    test_record_trigger_event()
    test_provide_feedback()
    test_evaluate_memory()
    test_calculate_interval()
    test_get_status()
    test_enhanced_scheduler_complete()
    
    print("=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)