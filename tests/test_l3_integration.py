"""
L3整合层测试
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.layers.l3_integration import get_l3_integration, KnowledgeRelation


def test_l3_initialization():
    """测试L3初始化"""
    print("=" * 60)
    print("L3整合层初始化测试")
    print("=" * 60)
    
    l3 = get_l3_integration()
    
    assert l3 is not None
    assert l3.reporter is not None
    assert l3.collector is not None
    assert l3.heartbeat is not None
    
    print("✅ L3初始化测试通过")


def test_integrate_empty_knowledge():
    """测试空知识整合"""
    print("\n" + "=" * 60)
    print("空知识整合测试")
    print("=" * 60)
    
    l3 = get_l3_integration()
    
    result = l3.integrate([])
    
    assert result.success is True
    assert result.total_nodes == 0
    assert result.core_knowledge == []
    
    print(f"✅ 空知识整合测试通过 - 正确处理空输入")


def test_integrate_single_knowledge():
    """测试单条知识整合"""
    print("\n" + "=" * 60)
    print("单条知识整合测试")
    print("=" * 60)
    
    l3 = get_l3_integration()
    
    knowledge = [{
        'id': 'single',
        'answer': '这是一条测试知识',
        'source': 'test',
        'confidence': 0.8,
        'quality_score': 75
    }]
    
    result = l3.integrate(knowledge)
    
    print(f"\n整合结果:")
    print(f"  成功: {result.success}")
    print(f"  节点数: {result.total_nodes}")
    print(f"  核心知识: {len(result.core_knowledge)}条")
    print(f"  置信度: {result.confidence:.2f}")
    
    assert result.success is True
    assert result.total_nodes == 1
    assert len(result.core_knowledge) == 1
    assert result.confidence > 0
    
    print("✅ 单条知识整合测试通过")


def test_integrate_multiple_knowledge():
    """测试多条知识整合"""
    print("\n" + "=" * 60)
    print("多条知识整合测试")
    print("=" * 60)
    
    l3 = get_l3_integration()
    
    knowledge = [
        {
            'id': 'k1',
            'answer': 'Python是一种解释型、面向对象的编程语言，支持多种编程范式。',
            'source': 'official_documentation',
            'confidence': 0.9,
            'quality_score': 90
        },
        {
            'id': 'k2',
            'answer': 'Python is an interpreted, object-oriented programming language.',
            'source': 'wikipedia',
            'confidence': 0.85,
            'quality_score': 80
        },
        {
            'id': 'k3',
            'answer': 'Python不支持编译，只能解释执行。',
            'source': 'forum',
            'confidence': 0.6,
            'quality_score': 50
        },
        {
            'id': 'k4',
            'answer': 'Python 3.0发布于2008年，引入了许多新特性。',
            'source': 'blog',
            'confidence': 0.75,
            'quality_score': 70
        }
    ]
    
    result = l3.integrate(knowledge)
    
    print(f"\n整合结果:")
    print(f"  成功: {result.success}")
    print(f"  节点数: {result.total_nodes}")
    print(f"  核心知识: {len(result.core_knowledge)}条")
    print(f"  冲突解决: {result.resolved_conflicts}个")
    print(f"  置信度: {result.confidence:.2f}")
    print(f"\n推理过程:")
    for r in result.reasoning:
        print(f"  - {r}")
    
    assert result.success is True
    assert result.total_nodes == 4
    assert len(result.core_knowledge) > 0
    assert result.confidence > 0
    
    print("✅ 多条知识整合测试通过")


def test_conflict_detection():
    """测试冲突检测"""
    print("\n" + "=" * 60)
    print("冲突检测测试")
    print("=" * 60)
    
    l3 = get_l3_integration()
    
    knowledge = [
        {
            'id': 'conflict1',
            'answer': 'Python is the best language for everything.',
            'source': 'enthusiast',
            'confidence': 0.9,
            'quality_score': 40
        },
        {
            'id': 'conflict2',
            'answer': 'Python is not suitable for high-performance computing.',
            'source': 'expert',
            'confidence': 0.85,
            'quality_score': 85
        }
    ]
    
    result = l3.integrate(knowledge)
    
    print(f"\n冲突检测结果:")
    print(f"  节点数: {result.total_nodes}")
    print(f"  冲突解决: {result.resolved_conflicts}个")
    print(f"  警告: {result.warnings}")
    
    assert result.success is True
    assert result.total_nodes == 2
    
    print("✅ 冲突检测测试通过")


def test_relation_discovery():
    """测试关系发现"""
    print("\n" + "=" * 60)
    print("关系发现测试")
    print("=" * 60)
    
    l3 = get_l3_integration()
    
    knowledge = [
        {
            'id': 'r1',
            'answer': 'Machine learning is a subset of artificial intelligence.',
            'source': 'textbook',
            'confidence': 0.95,
            'quality_score': 90
        },
        {
            'id': 'r2',
            'answer': 'Deep learning is a subset of machine learning.',
            'source': 'textbook',
            'confidence': 0.95,
            'quality_score': 90
        },
        {
            'id': 'r3',
            'answer': 'Neural networks are the foundation of deep learning.',
            'source': 'documentation',
            'confidence': 0.9,
            'quality_score': 85
        }
    ]
    
    result = l3.integrate(knowledge)
    
    print(f"\n关系发现结果:")
    print(f"  节点数: {result.total_nodes}")
    
    total_relations = sum(len(node.relations) for node in result.knowledge_graph.values())
    print(f"  发现关系: {total_relations}条")
    
    for node_id, node in result.knowledge_graph.items():
        if node.relations:
            print(f"\n  节点 {node_id[:20]}... 的关系:")
            for target_id, relation in node.relations[:3]:
                print(f"    → {target_id[:20]}... ({relation.value})")
    
    assert result.success is True
    
    print("✅ 关系发现测试通过")


def test_source_authority():
    """测试来源权威性"""
    print("\n" + "=" * 60)
    print("来源权威性测试")
    print("=" * 60)
    
    l3 = get_l3_integration()
    
    knowledge = [
        {
            'id': 'official',
            'answer': 'The function returns None on error.',
            'source': 'official_documentation',
            'confidence': 0.7,
            'quality_score': 60
        },
        {
            'id': 'unofficial',
            'answer': 'The function returns an empty string on error.',
            'source': 'random_blog',
            'confidence': 0.7,
            'quality_score': 60
        }
    ]
    
    result = l3.integrate(knowledge)
    
    print(f"\n来源权威性结果:")
    print(f"  冲突解决: {result.resolved_conflicts}个")
    
    official_node = result.knowledge_graph.get('official')
    unofficial_node = result.knowledge_graph.get('unofficial')
    
    if official_node and unofficial_node:
        print(f"  官方来源置信度: {official_node.confidence:.2f}")
        print(f"  非官方来源置信度: {unofficial_node.confidence:.2f}")
    
    assert result.success is True
    
    print("✅ 来源权威性测试通过")


def test_get_integration_status():
    """测试获取整合状态"""
    print("\n" + "=" * 60)
    print("整合状态测试")
    print("=" * 60)
    
    l3 = get_l3_integration()
    
    knowledge = [{
        'id': 'status_test',
        'answer': 'Test knowledge for status',
        'source': 'test',
        'confidence': 0.8,
        'quality_score': 75
    }]
    
    l3.integrate(knowledge)
    
    status = l3.get_integration_status()
    
    print(f"\n整合状态:")
    print(f"  层: {status['layer']}")
    print(f"  总整合次数: {status['stats']['total_integrations']}")
    print(f"  缓存节点数: {status['cached_nodes']}")
    print(f"  相邻层状态: {status['neighbor_status']}")
    
    assert status['layer'] == 'L3'
    assert status['stats']['total_integrations'] >= 1
    
    print("✅ 整合状态测试通过")


def test_knowledge_node_serialization():
    """测试知识节点序列化"""
    print("\n" + "=" * 60)
    print("知识节点序列化测试")
    print("=" * 60)
    
    l3 = get_l3_integration()
    
    knowledge = [{
        'id': 'serialize_test',
        'answer': 'This is a test knowledge item for serialization testing purposes.',
        'source': 'test',
        'confidence': 0.85,
        'quality_score': 80
    }]
    
    result = l3.integrate(knowledge)
    
    assert result.success is True
    
    for node in result.knowledge_graph.values():
        node_dict = node.to_dict()
        
        print(f"\n序列化结果:")
        print(f"  ID: {node_dict['id']}")
        print(f"  内容预览: {node_dict['content'][:50]}...")
        print(f"  来源: {node_dict['source']}")
        print(f"  置信度: {node_dict['confidence']}")
        
        assert 'id' in node_dict
        assert 'content' in node_dict
        assert 'confidence' in node_dict
    
    print("✅ 知识节点序列化测试通过")


def test_knowledge_relation_enum():
    """测试知识关系枚举"""
    print("\n" + "=" * 60)
    print("知识关系枚举测试")
    print("=" * 60)
    
    print(f"\n关系类型:")
    print(f"  SUPPORTS: {KnowledgeRelation.SUPPORTS.value}")
    print(f"  CONTRADICTS: {KnowledgeRelation.CONTRADICTS.value}")
    print(f"  EXTENDS: {KnowledgeRelation.EXTENDS.value}")
    print(f"  SPECIFIES: {KnowledgeRelation.SPECIFIES.value}")
    print(f"  GENERALIZES: {KnowledgeRelation.GENERALIZES.value}")
    print(f"  UNRELATED: {KnowledgeRelation.UNRELATED.value}")
    
    assert KnowledgeRelation.SUPPORTS.value == "supports"
    assert KnowledgeRelation.CONTRADICTS.value == "contradicts"
    
    print("✅ 知识关系枚举测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("L3整合层完整测试")
    print("=" * 60)
    
    try:
        test_l3_initialization()
        test_integrate_empty_knowledge()
        test_integrate_single_knowledge()
        test_integrate_multiple_knowledge()
        test_conflict_detection()
        test_relation_discovery()
        test_source_authority()
        test_get_integration_status()
        test_knowledge_node_serialization()
        test_knowledge_relation_enum()
        
        print("\n" + "=" * 60)
        print("✅ 所有L3整合层测试通过!")
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
