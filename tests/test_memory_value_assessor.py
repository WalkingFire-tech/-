"""
测试记忆价值评估器
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory_value_assessor import (
    MemoryValueAssessor,
    MemoryValue,
    MemoryItem
)


def test_initialization():
    """测试初始化"""
    db_path = "data/test_memory_assessor.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)
    
    assessor = MemoryValueAssessor(db_path=db_path)
    
    assert assessor is not None
    assert assessor.db_path == db_path
    assert isinstance(assessor.weights, dict)
    assert isinstance(assessor.thresholds, dict)
    print("✅ 初始化测试通过")


def test_evaluate_access_frequency():
    """测试访问频率评估"""
    db_path = "data/test_memory_access.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    assessor = MemoryValueAssessor(db_path=db_path)
    
    memory_0 = {'access_count': 0}
    memory_1 = {'access_count': 1}
    memory_5 = {'access_count': 5}
    memory_20 = {'access_count': 20}
    
    score_0 = assessor._evaluate_access_frequency(memory_0)
    score_1 = assessor._evaluate_access_frequency(memory_1)
    score_5 = assessor._evaluate_access_frequency(memory_5)
    score_20 = assessor._evaluate_access_frequency(memory_20)
    
    assert score_0 == 0.0
    assert score_1 == 0.3
    assert score_5 == 0.7
    assert score_20 == 1.0
    print("✅ 访问频率评估测试通过")


def test_evaluate_user_marked():
    """测试用户标记评估"""
    db_path = "data/test_memory_marked.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    assessor = MemoryValueAssessor(db_path=db_path)
    
    memory_marked = {'user_marked_important': True}
    memory_not_marked = {'user_marked_important': False}
    
    score_marked = assessor._evaluate_user_marked(memory_marked)
    score_not_marked = assessor._evaluate_user_marked(memory_not_marked)
    
    assert score_marked == 1.0
    assert score_not_marked == 0.0
    print("✅ 用户标记评估测试通过")


def test_evaluate_recency():
    """测试时效性评估"""
    db_path = "data/test_memory_recency.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    assessor = MemoryValueAssessor(db_path=db_path)
    
    memory_today = {'created_at': datetime.now()}
    memory_week = {'created_at': datetime.now() - timedelta(days=5)}
    memory_month = {'created_at': datetime.now() - timedelta(days=20)}
    memory_old = {'created_at': datetime.now() - timedelta(days=100)}
    
    score_today = assessor._evaluate_recency(memory_today)
    score_week = assessor._evaluate_recency(memory_week)
    score_month = assessor._evaluate_recency(memory_month)
    score_old = assessor._evaluate_recency(memory_old)
    
    assert score_today >= 0.8
    assert score_week >= 0.5
    assert score_month >= 0.3
    assert score_old <= 0.3
    print("✅ 时效性评估测试通过")


def test_get_value_grade():
    """测试价值等级判定"""
    db_path = "data/test_memory_grade.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    assessor = MemoryValueAssessor(db_path=db_path)
    
    grade_critical = assessor.get_value_grade(0.90)
    grade_high = assessor.get_value_grade(0.70)
    grade_medium = assessor.get_value_grade(0.50)
    grade_low = assessor.get_value_grade(0.25)
    grade_transient = assessor.get_value_grade(0.10)
    
    assert grade_critical == MemoryValue.CRITICAL
    assert grade_high == MemoryValue.HIGH
    assert grade_medium == MemoryValue.MEDIUM
    assert grade_low == MemoryValue.LOW
    assert grade_transient == MemoryValue.TRANSIENT
    print("✅ 价值等级判定测试通过")


def test_should_retain():
    """测试保留决策"""
    db_path = "data/test_memory_retain.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    assessor = MemoryValueAssessor(db_path=db_path)
    
    memory_critical = {'user_marked_important': True}
    memory_high = {'access_count': 10, 'correctness_score': 0.9}
    memory_low = {'access_count': 0, 'created_at': datetime.now() - timedelta(days=100)}
    
    retain_critical = assessor.should_retain(memory_critical)
    retain_high = assessor.should_retain(memory_high)
    retain_low = assessor.should_retain(memory_low)
    
    assert retain_critical is True
    assert retain_high is True
    assert retain_low is False
    print("✅ 保留决策测试通过")


def test_get_retention_recommendation():
    """测试保留建议"""
    db_path = "data/test_memory_recommend.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    assessor = MemoryValueAssessor(db_path=db_path)
    
    memory = {
        'user_marked_important': True,
        'access_count': 5,
        'correctness_score': 0.9,
        'context_importance': 0.8,
        'created_at': datetime.now()
    }
    
    recommendation = assessor.get_retention_recommendation(memory)
    
    assert 'score' in recommendation
    assert 'grade' in recommendation
    assert 'retain' in recommendation
    assert 'action' in recommendation
    assert 'suggestion' in recommendation
    assert recommendation['retain'] is True
    print("✅ 保留建议测试通过")


def test_save_and_report():
    """测试保存和报告"""
    db_path = "data/test_memory_save.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    assessor = MemoryValueAssessor(db_path=db_path)
    
    memory1 = {
        'id': 'mem_1',
        'content': '重要记忆',
        'memory_type': 'important',
        'user_marked_important': True,
        'access_count': 10,
        'created_at': datetime.now().isoformat()
    }
    
    memory2 = {
        'id': 'mem_2',
        'content': '普通记忆',
        'memory_type': 'general',
        'access_count': 1,
        'created_at': datetime.now().isoformat()
    }
    
    assessor.save_memory(memory1)
    assessor.save_memory(memory2)
    
    report = assessor.get_memory_report(limit=10)
    
    assert report['total_memories'] == 2
    assert 'by_grade' in report
    assert 'top_memories' in report
    print("✅ 保存和报告测试通过")


def test_memory_assessor_complete():
    """完整流程测试"""
    db_path = "data/test_memory_complete.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    assessor = MemoryValueAssessor(db_path=db_path)
    
    memory_important = {
        'id': 'critical_memory',
        'content': '这是刻骨铭心的记忆',
        'memory_type': 'critical',
        'user_marked_important': True,
        'access_count': 20,
        'correctness_score': 1.0,
        'context_importance': 1.0,
        'created_at': datetime.now().isoformat()
    }
    
    memory_normal = {
        'id': 'normal_memory',
        'content': '这是普通记忆',
        'memory_type': 'general',
        'access_count': 3,
        'correctness_score': 0.8,
        'context_importance': 0.5,
        'created_at': datetime.now().isoformat()
    }
    
    memory_transient = {
        'id': 'transient_memory',
        'content': '这是临时记忆',
        'memory_type': 'temporary',
        'access_count': 0,
        'correctness_score': 0.5,
        'context_importance': 0.2,
        'created_at': (datetime.now() - timedelta(days=100)).isoformat()
    }
    
    assessor.save_memory(memory_important)
    assessor.save_memory(memory_normal)
    assessor.save_memory(memory_transient)
    
    rec_important = assessor.get_retention_recommendation(memory_important)
    rec_normal = assessor.get_retention_recommendation(memory_normal)
    rec_transient = assessor.get_retention_recommendation(memory_transient)
    
    assert rec_important['retain'] is True
    assert rec_important['grade'] == MemoryValue.CRITICAL.value
    
    assert rec_normal['retain'] is True
    assert rec_normal['grade'] >= MemoryValue.MEDIUM.value
    
    assert rec_transient['retain'] is False
    assert rec_transient['grade'] <= MemoryValue.LOW.value
    
    report = assessor.get_memory_report()
    assert report['total_memories'] == 3
    
    print("✅ 记忆价值评估器完整测试通过")


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试记忆价值评估器")
    print("=" * 60)
    
    test_initialization()
    test_evaluate_access_frequency()
    test_evaluate_user_marked()
    test_evaluate_recency()
    test_get_value_grade()
    test_should_retain()
    test_get_retention_recommendation()
    test_save_and_report()
    test_memory_assessor_complete()
    
    print("=" * 60)
    print("所有测试通过 ✅")
    print("=" * 60)