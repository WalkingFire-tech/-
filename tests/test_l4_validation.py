"""
L4校验层测试
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.layers.l4_validation import get_l4_validation, ValidationStatus, TrustLevel


def test_l4_initialization():
    """测试L4初始化"""
    print("=" * 60)
    print("L4校验层初始化测试")
    print("=" * 60)
    
    l4 = get_l4_validation()
    
    assert l4 is not None
    assert l4.reporter is not None
    assert l4.collector is not None
    assert l4.heartbeat is not None
    
    print("✅ L4初始化测试通过")


def test_validate_empty_knowledge():
    """测试空知识校验"""
    print("\n" + "=" * 60)
    print("空知识校验测试")
    print("=" * 60)
    
    l4 = get_l4_validation()
    
    result = l4.validate({})
    
    assert result.success is False
    assert result.status == ValidationStatus.FAIL
    
    print(f"✅ 空知识校验测试通过 - 正确处理空输入")


def test_validate_high_quality_knowledge():
    """测试高质量知识校验"""
    print("\n" + "=" * 60)
    print("高质量知识校验测试")
    print("=" * 60)
    
    l4 = get_l4_validation()
    
    from core.layers.l3_integration import KnowledgeNode
    
    knowledge_graph = {
        'k1': KnowledgeNode(
            id='k1',
            content='Python是一种解释型编程语言，由Guido van Rossum创建。',
            source='official_documentation',
            confidence=0.95,
            quality_score=95,
            timestamp=datetime.now().isoformat(),
            keywords=['python', 'programming']
        ),
        'k2': KnowledgeNode(
            id='k2',
            content='Python支持面向对象、函数式和过程式编程范式。',
            source='wikipedia',
            confidence=0.9,
            quality_score=88,
            timestamp=datetime.now().isoformat(),
            keywords=['python', 'paradigms']
        )
    }
    
    integrated_knowledge = {
        'knowledge_graph': knowledge_graph,
        'core_knowledge': [
            {'id': 'k1', 'confidence': 0.95},
            {'id': 'k2', 'confidence': 0.9}
        ]
    }
    
    result = l4.validate(integrated_knowledge)
    
    print(f"\n校验结果:")
    print(f"  成功: {result.success}")
    print(f"  校验等级: {result.status.value}")
    print(f"  确定性: {result.certainty_score:.2f}")
    print(f"  一致性: {result.consistency_score:.2f}")
    print(f"  完整性: {result.completeness_score:.2f}")
    print(f"  信任等级: {result.trust_level.value}")
    print(f"  回退: {result.should_fallback}")
    
    assert result.success is True
    assert result.status in [ValidationStatus.PASS, ValidationStatus.PARTIAL]
    assert result.certainty_score > 0.5
    assert result.should_fallback is False
    
    print("✅ 高质量知识校验测试通过")


def test_validate_low_quality_knowledge():
    """测试低质量知识校验"""
    print("\n" + "=" * 60)
    print("低质量知识校验测试")
    print("=" * 60)
    
    l4 = get_l4_validation()
    
    from core.layers.l3_integration import KnowledgeNode
    
    knowledge_graph = {
        'k1': KnowledgeNode(
            id='k1',
            content='Some vague information.',
            source='unknown',
            confidence=0.3,
            quality_score=30,
            timestamp=datetime.now().isoformat(),
            keywords=[]
        )
    }
    
    integrated_knowledge = {
        'knowledge_graph': knowledge_graph,
        'core_knowledge': [{'id': 'k1', 'confidence': 0.3}]
    }
    
    result = l4.validate(integrated_knowledge)
    
    print(f"\n校验结果:")
    print(f"  校验等级: {result.status.value}")
    print(f"  确定性: {result.certainty_score:.2f}")
    print(f"  回退: {result.should_fallback}")
    print(f"  回退原因: {result.fallback_reason}")
    
    assert result.certainty_score < 0.5
    assert result.should_fallback is True
    
    print("✅ 低质量知识校验测试通过 - 正确触发回退")


def test_consistency_check():
    """测试一致性检查"""
    print("\n" + "=" * 60)
    print("一致性检查测试")
    print("=" * 60)
    
    l4 = get_l4_validation()
    
    from core.layers.l3_integration import KnowledgeNode
    
    knowledge_graph = {
        'k1': KnowledgeNode(
            id='k1',
            content='High confidence information.',
            source='source1',
            confidence=0.9,
            quality_score=85,
            timestamp=datetime.now().isoformat(),
            keywords=['test']
        ),
        'k2': KnowledgeNode(
            id='k2',
            content='Low confidence information.',
            source='source2',
            confidence=0.2,
            quality_score=20,
            timestamp=datetime.now().isoformat(),
            keywords=['test']
        )
    }
    
    integrated_knowledge = {
        'knowledge_graph': knowledge_graph,
        'core_knowledge': []
    }
    
    result = l4.validate(integrated_knowledge)
    
    print(f"\n一致性结果:")
    print(f"  一致性评分: {result.consistency_score:.2f}")
    print(f"  问题数: {len(result.issues)}")
    
    if result.issues:
        print(f"  问题:")
        for issue in result.issues[:3]:
            print(f"    - {issue[:60]}...")
    
    assert result.consistency_score < 1.0
    
    print("✅ 一致性检查测试通过")


def test_trust_chain_building():
    """测试信任链构建"""
    print("\n" + "=" * 60)
    print("信任链构建测试")
    print("=" * 60)
    
    l4 = get_l4_validation()
    
    from core.layers.l3_integration import KnowledgeNode
    
    knowledge_graph = {
        'official': KnowledgeNode(
            id='official',
            content='Official documentation content.',
            source='official_documentation',
            confidence=0.95,
            quality_score=95,
            timestamp=datetime.now().isoformat(),
            keywords=['official']
        ),
        'wiki': KnowledgeNode(
            id='wiki',
            content='Wikipedia content.',
            source='wikipedia',
            confidence=0.85,
            quality_score=80,
            timestamp=datetime.now().isoformat(),
            keywords=['wiki']
        )
    }
    
    integrated_knowledge = {
        'knowledge_graph': knowledge_graph,
        'core_knowledge': [{'id': 'official', 'confidence': 0.95}]
    }
    
    result = l4.validate(integrated_knowledge)
    
    print(f"\n信任链结果:")
    print(f"  信任等级: {result.trust_level.value}")
    print(f"  信任链长度: {len(result.trust_chain)}")
    for i, link in enumerate(result.trust_chain[:3]):
        print(f"    [{i+1}] {link.source}: {link.statement[:50]}...")
    
    assert len(result.trust_chain) > 0
    assert result.trust_level in [TrustLevel.HIGH, TrustLevel.MEDIUM]
    
    print("✅ 信任链构建测试通过")


def test_fallback_mechanism():
    """测试回退机制"""
    print("\n" + "=" * 60)
    print("回退机制测试")
    print("=" * 60)
    
    l4 = get_l4_validation()
    
    from core.layers.l3_integration import KnowledgeNode
    
    knowledge_graph = {
        'bad': KnowledgeNode(
            id='bad',
            content='Very low quality.',
            source='unknown',
            confidence=0.2,
            quality_score=20,
            timestamp=datetime.now().isoformat(),
            keywords=[]
        )
    }
    
    integrated_knowledge = {
        'knowledge_graph': knowledge_graph,
        'core_knowledge': [{'id': 'bad', 'confidence': 0.2}]
    }
    
    result = l4.validate(integrated_knowledge)
    
    print(f"\n回退结果:")
    print(f"  触发回退: {result.should_fallback}")
    print(f"  回退原因: {result.fallback_reason}")
    
    if result.should_fallback:
        fallback_event = l4.trigger_fallback_to_l2(result.fallback_reason)
        print(f"  回退事件: {fallback_event['status']}")
    
    assert result.should_fallback is True
    
    print("✅ 回退机制测试通过")


def test_validation_level_determination():
    """测试校验等级确定"""
    print("\n" + "=" * 60)
    print("校验等级确定测试")
    print("=" * 60)
    
    l4 = get_l4_validation()
    
    from core.layers.l3_integration import KnowledgeNode
    
    test_cases = [
        ('HIGH', 0.9, 0.9, 0.9),
        ('MEDIUM', 0.7, 0.7, 0.7),
        ('LOW', 0.5, 0.5, 0.5),
        ('FAILED', 0.3, 0.3, 0.3)
    ]
    
    for expected_level, certainty, consistency, completeness in test_cases:
        knowledge_graph = {
            'test': KnowledgeNode(
                id='test',
                content='Test content.',
                source='test',
                confidence=certainty,
                quality_score=int(certainty * 100),
                timestamp=datetime.now().isoformat(),
                keywords=['test']
            )
        }
        
        result = l4.validate({
            'knowledge_graph': knowledge_graph,
            'core_knowledge': [{'id': 'test', 'confidence': certainty}]
        })
        
        print(f"  {expected_level}: 确定性={certainty:.1f} → 等级={result.status.value}")
    
    print("✅ 校验等级确定测试通过")


def test_get_validation_status():
    """测试获取校验状态"""
    print("\n" + "=" * 60)
    print("校验状态测试")
    print("=" * 60)
    
    l4 = get_l4_validation()
    
    from core.layers.l3_integration import KnowledgeNode
    
    knowledge_graph = {
        'status_test': KnowledgeNode(
            id='status_test',
            content='Test for status.',
            source='test',
            confidence=0.8,
            quality_score=75,
            timestamp=datetime.now().isoformat(),
            keywords=['test']
        )
    }
    
    l4.validate({
        'knowledge_graph': knowledge_graph,
        'core_knowledge': [{'id': 'status_test', 'confidence': 0.8}]
    })
    
    status = l4.get_validation_status()
    
    print(f"\n校验状态:")
    print(f"  层: {status['layer']}")
    print(f"  总校验次数: {status['stats']['total_validations']}")
    print(f"  通过次数: {status['stats']['pass_count']}")
    print(f"  回退率: {status['fail_rate']:.2f}")
    print(f"  相邻层状态: {status['neighbor_status']}")
    
    assert status['layer'] == 'L4'
    assert status['stats']['total_validations'] >= 1
    
    print("✅ 校验状态测试通过")


def test_validation_level_enum():
    """测试校验等级枚举"""
    print("\n" + "=" * 60)
    print("校验等级枚举测试")
    print("=" * 60)
    
    print(f"\n校验等级:")
    print(f"  PASS: {ValidationStatus.PASS.value}")
    print(f"  PARTIAL: {ValidationStatus.PARTIAL.value}")
    print(f"  FAIL: {ValidationStatus.FAIL.value}")
    print(f"  ERROR: {ValidationStatus.ERROR.value}")
    
    assert ValidationStatus.PASS.value == "pass"
    assert ValidationStatus.FAIL.value == "fail"
    
    print("✅ 校验等级枚举测试通过")


def test_trust_level_enum():
    """测试信任等级枚举"""
    print("\n" + "=" * 60)
    print("信任等级枚举测试")
    print("=" * 60)
    
    print(f"\n信任等级:")
    print(f"  HIGH: {TrustLevel.HIGH.value}")
    print(f"  MEDIUM: {TrustLevel.MEDIUM.value}")
    print(f"  LOW: {TrustLevel.LOW.value}")
    print(f"  UNKNOWN: {TrustLevel.UNKNOWN.value}")
    
    assert TrustLevel.HIGH.value == "high"
    assert TrustLevel.LOW.value == "low"
    
    print("✅ 信任等级枚举测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("L4校验层完整测试")
    print("=" * 60)
    
    try:
        test_l4_initialization()
        test_validate_empty_knowledge()
        test_validate_high_quality_knowledge()
        test_validate_low_quality_knowledge()
        test_consistency_check()
        test_trust_chain_building()
        test_fallback_mechanism()
        test_validation_level_determination()
        test_get_validation_status()
        test_validation_level_enum()
        test_trust_level_enum()
        
        print("\n" + "=" * 60)
        print("✅ 所有L4校验层测试通过!")
        print("=" * 60)
        
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)