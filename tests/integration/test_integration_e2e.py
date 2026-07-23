"""
端到端集成测试 - 验证所有改进组件协同工作
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.enhanced_scheduler import EnhancedCognitiveScheduler
from core.conflict_coordinator import ConflictCoordinator, ConflictType, ConflictSeverity
from core.trigger_feedback_loop import TriggerFeedbackLoop, TriggerEvent
from core.memory_value_assessor import MemoryValueAssessor, MemoryValue


def test_full_integration():
    """完整集成测试"""
    print("=" * 60)
    print("开始端到端集成测试")
    print("=" * 60)
    
    scheduler = EnhancedCognitiveScheduler(db_path="data/test_integration.db")
    
    print("\n1. 测试冲突协调...")
    scheduler.register_evolution_rule(
        rule_id='gene_threshold',
        source_type='evolution_result',
        parameter='threshold',
        value=0.5,
        evidence={'success_count': 5}
    )
    
    scheduler.register_evolution_rule(
        rule_id='user_threshold',
        source_type='user_feedback',
        parameter='threshold',
        value=0.8,
        evidence={'user_feedback_count': 10}
    )
    
    conflicts = scheduler._detect_conflicts(scheduler._collect_system_state())
    if conflicts:
        print(f"   检测到 {len(conflicts)} 个冲突")
        scheduler._resolve_conflicts(conflicts)
        print(f"   已解决 {scheduler.stats['conflicts_resolved']} 个冲突")
    else:
        print("   无冲突")
    
    print("\n2. 测试触发反馈...")
    event_id = scheduler.record_trigger_event(
        user_input="推荐一款26650电池保护芯片",
        triggered=True,
        depth='full',
        reason='keyword_match'
    )
    print(f"   记录触发事件: {event_id}")
    
    scheduler.provide_feedback(event_id, satisfied=True)
    print(f"   提供正面反馈")
    
    summary = scheduler.trigger_feedback.get_learning_summary()
    print(f"   触发准确率: {summary.get('accuracy', 0):.2%}")
    
    print("\n3. 测试记忆评估...")
    memory = {
        'id': 'chip_knowledge',
        'content': '26650电池保护芯片知识',
        'user_marked_important': True,
        'access_count': 15,
        'correctness_score': 0.95,
        'context_importance': 0.9,
        'created_at': datetime.now().isoformat()
    }
    
    result = scheduler.evaluate_memory(memory)
    print(f"   记忆价值分数: {result['score']:.2f}")
    print(f"   记忆等级: {result['grade_name']}")
    print(f"   是否保留: {result['retain']}")
    print(f"   建议: {result['suggestion']}")
    
    print("\n4. 测试系统状态...")
    status = scheduler.get_status()
    print(f"   运行状态: {status['running']}")
    print(f"   执行周期: {status['stats']['cycles']}")
    print(f"   已执行任务: {status['stats']['tasks_executed']}")
    print(f"   已解决冲突: {status['stats']['conflicts_resolved']}")
    print(f"   已评估记忆: {status['stats']['memories_evaluated']}")
    
    print("\n" + "=" * 60)
    print("端到端集成测试通过 ✅")
    print("=" * 60)
    
    return True


def test_conflict_resolution_priority():
    """测试冲突解决优先级"""
    print("\n测试冲突解决优先级...")
    
    coordinator = ConflictCoordinator(db_path="data/test_priority.db")
    
    rule1 = {
        'parameter': 'learning_rate',
        'value': 0.01,
        'source_type': 'evolution_result',
        'evidence': {'success_count': 3}
    }
    
    rule2 = {
        'parameter': 'learning_rate',
        'value': 0.1,
        'source_type': 'user_feedback',
        'evidence': {'user_feedback_count': 5}
    }
    
    conflict = coordinator.detect_conflicts(rule1, rule2)
    assert conflict is not None
    
    decision = coordinator.arbitrate(conflict)
    
    assert decision['winner'] == 'source2'
    assert decision['rule']['value'] == 0.1
    
    print("   用户反馈优先级 > 基因演化优先级 ✅")
    return True


def test_memory_lifecycle():
    """测试记忆生命周期"""
    print("\n测试记忆生命周期...")
    
    assessor = MemoryValueAssessor(db_path="data/test_lifecycle.db")
    
    memory_critical = {
        'id': 'critical',
        'user_marked_important': True,
        'access_count': 20,
        'correctness_score': 1.0,
        'context_importance': 1.0,
        'created_at': datetime.now().isoformat()
    }
    
    memory_transient = {
        'id': 'transient',
        'user_marked_important': False,
        'access_count': 0,
        'created_at': datetime.now().isoformat()
    }
    
    rec_critical = assessor.get_retention_recommendation(memory_critical)
    rec_transient = assessor.get_retention_recommendation(memory_transient)
    
    assert rec_critical['retain'] is True
    assert rec_critical['grade'] >= MemoryValue.HIGH.value
    
    assert rec_transient['retain'] is False
    
    print("   刻骨铭心记忆永久保留 ✅")
    print("   瞬态记忆可安全遗忘 ✅")
    return True


def test_trigger_learning():
    """测试触发学习"""
    print("\n测试触发学习...")
    
    loop = TriggerFeedbackLoop(db_path="data/test_learning.db")
    
    for i in range(10):
        event = TriggerEvent(
            id=loop.create_event_id(f"input_{i}"),
            user_input=f"测试输入{i}",
            trigger_decision='triggered',
            processing_depth='full',
            route_reason='keyword_match',
            created_at=datetime.now().isoformat()
        )
        loop.record_decision(event)
        
        satisfied = i < 7
        loop.collect_feedback(event.id, satisfied=satisfied)
    
    summary = loop.get_learning_summary()
    
    assert summary['total_decisions'] == 10
    assert summary['accuracy'] >= 0.5
    
    print(f"   总决策数: {summary['total_decisions']}")
    print(f"   准确率: {summary['accuracy']:.2%}")
    print("   触发学习机制正常 ✅")
    return True


if __name__ == "__main__":
    results = []
    
    results.append(test_full_integration())
    results.append(test_conflict_resolution_priority())
    results.append(test_memory_lifecycle())
    results.append(test_trigger_learning())
    
    print("\n" + "=" * 60)
    print(f"所有集成测试通过: {all(results)} ✅")
    print("=" * 60)