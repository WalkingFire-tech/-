"""
测试触发反馈回路
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.trigger_feedback_loop import (
    TriggerFeedbackLoop,
    TriggerEvent
)


def test_initialization():
    """测试初始化"""
    db_path = "data/test_trigger_feedback.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    
    loop = TriggerFeedbackLoop(db_path=db_path)
    
    assert loop is not None
    assert loop.db_path == db_path
    assert isinstance(loop.stats, dict)
    assert isinstance(loop.pattern_weights, dict)
    print("✅ 初始化测试通过")


def test_record_decision():
    """测试记录决策"""
    db_path = "data/test_trigger_record.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    loop = TriggerFeedbackLoop(db_path=db_path)
    
    event = TriggerEvent(
        id=loop.create_event_id("测试输入"),
        user_input="这是一个测试输入",
        trigger_decision='triggered',
        processing_depth='full',
        route_reason='keyword_match',
        created_at=datetime.now().isoformat()
    )
    
    loop.record_decision(event)
    
    assert loop.stats['total_decisions'] == 1
    print("✅ 记录决策测试通过")


def test_collect_feedback():
    """测试收集反馈"""
    db_path = "data/test_trigger_collect.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    loop = TriggerFeedbackLoop(db_path=db_path)
    
    event = TriggerEvent(
        id=loop.create_event_id("测试输入"),
        user_input="这是一个测试输入",
        trigger_decision='triggered',
        processing_depth='full',
        route_reason='keyword_match',
        created_at=datetime.now().isoformat()
    )
    
    loop.record_decision(event)
    
    loop.collect_feedback(event.id, satisfied=True)
    
    assert loop.stats['true_positives'] == 1
    print("✅ 收集反馈测试通过")


def test_false_positive_detection():
    """测试误报检测"""
    db_path = "data/test_trigger_fp.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    loop = TriggerFeedbackLoop(db_path=db_path)
    
    event = TriggerEvent(
        id=loop.create_event_id("测试输入"),
        user_input="这是一个简单问题",
        trigger_decision='triggered',
        processing_depth='full',
        route_reason='keyword_match',
        created_at=datetime.now().isoformat()
    )
    
    loop.record_decision(event)
    
    loop.collect_feedback(event.id, satisfied=False, correction_needed=True)
    
    assert loop.stats['false_positives'] == 1
    print("✅ 误报检测测试通过")


def test_pattern_extraction():
    """测试模式提取"""
    db_path = "data/test_trigger_pattern.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    loop = TriggerFeedbackLoop(db_path=db_path)
    
    assert loop._extract_pattern("whitelist matched") == 'whitelist_match'
    assert loop._extract_pattern("keyword found") == 'keyword_match'
    assert loop._extract_pattern("semantic similarity") == 'semantic_match'
    assert loop._extract_pattern("intent detected") == 'intent_match'
    assert loop._extract_pattern("state based") == 'state_match'
    assert loop._extract_pattern("") == 'unknown'
    print("✅ 模式提取测试通过")


def test_learning_summary():
    """测试学习摘要"""
    db_path = "data/test_trigger_summary.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    loop = TriggerFeedbackLoop(db_path=db_path)
    
    for i in range(5):
        event = TriggerEvent(
            id=loop.create_event_id(f"测试输入{i}"),
            user_input=f"测试输入{i}",
            trigger_decision='triggered',
            processing_depth='full',
            route_reason='keyword_match',
            created_at=datetime.now().isoformat()
        )
        loop.record_decision(event)
        loop.collect_feedback(event.id, satisfied=True)
    
    summary = loop.get_learning_summary()
    
    assert summary['total_decisions'] == 5
    assert 'accuracy' in summary
    assert 'precision' in summary
    assert 'recall' in summary
    print("✅ 学习摘要测试通过")


def test_trigger_feedback_complete():
    """完整流程测试"""
    db_path = "data/test_trigger_complete.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    loop = TriggerFeedbackLoop(db_path=db_path)
    
    event1 = TriggerEvent(
        id=loop.create_event_id("推荐芯片"),
        user_input="推荐一款芯片",
        trigger_decision='triggered',
        processing_depth='full',
        route_reason='keyword_match',
        created_at=datetime.now().isoformat()
    )
    loop.record_decision(event1)
    loop.collect_feedback(event1.id, satisfied=True)
    
    event2 = TriggerEvent(
        id=loop.create_event_id("简单问题"),
        user_input="你好",
        trigger_decision='triggered',
        processing_depth='full',
        route_reason='keyword_match',
        created_at=datetime.now().isoformat()
    )
    loop.record_decision(event2)
    loop.collect_feedback(event2.id, satisfied=False, correction_needed=True)
    
    event3 = TriggerEvent(
        id=loop.create_event_id("复杂问题"),
        user_input="分析系统架构",
        trigger_decision='not_triggered',
        processing_depth='none',
        route_reason='state_match',
        created_at=datetime.now().isoformat()
    )
    loop.record_decision(event3)
    loop.collect_feedback(event3.id, satisfied=False, correction_needed=True, actual_need='full')
    
    summary = loop.get_learning_summary()
    
    assert summary['total_decisions'] == 3
    assert summary['confusion_matrix']['true_positives'] == 1
    assert summary['confusion_matrix']['false_positives'] == 1
    assert summary['confusion_matrix']['false_negatives'] == 1
    
    print("✅ 触发反馈回路完整测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试触发反馈回路")
    print("=" * 60)
    
    test_initialization()
    test_record_decision()
    test_collect_feedback()
    test_false_positive_detection()
    test_pattern_extraction()
    test_learning_summary()
    test_trigger_feedback_complete()
    
    print("=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)