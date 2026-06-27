"""
L5进化层测试
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.layers.l5_evolution import get_l5_evolution, EvolutionType


def test_l5_initialization():
    """测试L5初始化"""
    print("=" * 60)
    print("L5进化层初始化测试")
    print("=" * 60)
    
    l5 = get_l5_evolution()
    
    assert l5 is not None
    assert l5.reporter is not None
    assert l5.collector is not None
    assert l5.heartbeat is not None
    
    print("✅ L5初始化测试通过")


def test_default_genes():
    """测试默认基因"""
    print("\n" + "=" * 60)
    print("默认基因测试")
    print("=" * 60)
    
    l5 = get_l5_evolution()
    
    status = l5.get_evolution_status()
    
    print(f"\n基因池状态:")
    print(f"  总基因数: {len(status['genes'])}")
    
    for gid, gene in status['genes'].items():
        print(f"  - {gid}: {gene['name']} = {gene['value']:.3f} (阶段: {gene['stage']})")
    
    assert len(status['genes']) >= 10
    
    print("✅ 默认基因测试通过")


def test_record_experience():
    """测试经验记录"""
    print("\n" + "=" * 60)
    print("经验记录测试")
    print("=" * 60)
    
    l5 = get_l5_evolution()
    
    experience = {
        'user_input': '如何优化Python代码性能？',
        'validation_result': {
            'status': 'pass',
            'confidence': 0.85
        },
        'learning_result': {
            'knowledge_gained': 3
        },
        'processing_time_ms': 1500,
        'user_feedback': {
            'satisfaction': 0.8,
            'like': True
        }
    }
    
    result = l5.record_experience(experience)
    
    print(f"\n经验记录结果:")
    print(f"  成功: {result.success}")
    print(f"  进化类型: {result.evolution_type.value if hasattr(result.evolution_type, 'value') else result.evolution_type}")
    print(f"  适应度: {result.confidence:.3f}")
    print(f"  变更: {len(result.changes)}项")
    
    print(f"\n推理过程:")
    for r in result.reasoning[:5]:
        print(f"  - {r}")
    
    assert result.success is True
    
    print("✅ 经验记录测试通过")


def test_fitness_evaluation():
    """测试适应度评估"""
    print("\n" + "=" * 60)
    print("适应度评估测试")
    print("=" * 60)
    
    l5 = get_l5_evolution()
    
    for i in range(5):
        experience = {
            'user_input': f'测试问题{i+1}',
            'validation_result': {
                'status': 'pass' if i % 2 == 0 else 'partial',
                'confidence': 0.7 + i * 0.05
            },
            'learning_result': {
                'knowledge_gained': i
            },
            'processing_time_ms': 1000 + i * 200,
            'user_feedback': {
                'satisfaction': 0.6 + i * 0.05
            }
        }
        
        result = l5.record_experience(experience)
    
    status = l5.get_evolution_status()
    
    print(f"\n适应度状态:")
    print(f"  平均适应度: {status['fitness']['avg']:.3f}")
    print(f"  历史记录数: {status['fitness']['history_count']}")
    print(f"  总进化次数: {status['stats']['total_evolutions']}")
    
    assert status['fitness']['history_count'] >= 5
    
    print("✅ 适应度评估测试通过")


def test_gene_evolution():
    """测试基因演化"""
    print("\n" + "=" * 60)
    print("基因演化测试")
    print("=" * 60)
    
    l5 = get_l5_evolution()
    
    initial_status = l5.get_evolution_status()
    initial_genes = initial_status['genes'].copy()
    
    for i in range(10):
        experience = {
            'user_input': f'演化测试{i+1}',
            'validation_result': {
                'status': 'pass',
                'confidence': 0.8
            },
            'learning_result': {
                'knowledge_gained': 2
            },
            'processing_time_ms': 1200,
            'user_feedback': {
                'satisfaction': 0.75
            }
        }
        
        l5.record_experience(experience)
    
    final_status = l5.get_evolution_status()
    
    print(f"\n基因演化对比:")
    print(f"  初始代数: {initial_status['state']['generation']}")
    print(f"  最终代数: {final_status['state']['generation']}")
    print(f"  基因演化次数: {final_status['stats']['gene_evolutions']}")
    
    print(f"\n基因值变化:")
    for gid in list(initial_genes.keys())[:3]:
        init_val = initial_genes[gid]['value']
        final_val = final_status['genes'][gid]['value']
        print(f"  {gid}: {init_val:.3f} → {final_val:.3f}")
    
    print("✅ 基因演化测试通过")


def test_skill_formation():
    """测试技能形成"""
    print("\n" + "=" * 60)
    print("技能形成测试")
    print("=" * 60)
    
    l5 = get_l5_evolution()
    
    for i in range(6):
        experience = {
            'user_input': '如何优化Python代码性能？',
            'validation_result': {
                'status': 'pass',
                'confidence': 0.85
            },
            'learning_result': {
                'knowledge_gained': 1
            },
            'processing_time_ms': 1000,
            'user_feedback': {
                'satisfaction': 0.8
            }
        }
        
        result = l5.record_experience(experience)
    
    status = l5.get_evolution_status()
    
    print(f"\n技能形成结果:")
    print(f"  技能数量: {status['skills_count']}")
    print(f"  技能形成次数: {status['stats']['skills_formed']}")
    print(f"  反射形成次数: {status['stats']['reflexes_formed']}")
    
    print("✅ 技能形成测试通过")


def test_get_gene_value():
    """测试获取基因值"""
    print("\n" + "=" * 60)
    print("获取基因值测试")
    print("=" * 60)
    
    l5 = get_l5_evolution()
    
    gene_value = l5.get_gene_value('G001')
    
    print(f"\n基因G001值: {gene_value:.3f}")
    
    assert gene_value is not None
    assert 0.1 <= gene_value <= 0.9
    
    print("✅ 获取基因值测试通过")


def test_get_evolution_status():
    """测试获取进化状态"""
    print("\n" + "=" * 60)
    print("进化状态测试")
    print("=" * 60)
    
    l5 = get_l5_evolution()
    
    experience = {
        'user_input': '状态测试',
        'validation_result': {
            'status': 'pass',
            'confidence': 0.8
        },
        'learning_result': {
            'knowledge_gained': 1
        },
        'processing_time_ms': 1000,
        'user_feedback': {}
    }
    
    l5.record_experience(experience)
    
    status = l5.get_evolution_status()
    
    print(f"\n进化状态:")
    print(f"  层: {status['layer']}")
    print(f"  总进化次数: {status['stats']['total_evolutions']}")
    print(f"  平均适应度: {status['fitness']['avg']:.3f}")
    print(f"  基因数: {len(status['genes'])}")
    print(f"  技能数: {status['skills_count']}")
    print(f"  相邻层状态: {status['neighbor_status']}")
    
    assert status['layer'] == 'L5'
    assert status['stats']['total_evolutions'] >= 1
    
    print("✅ 进化状态测试通过")


def test_evolution_type_enum():
    """测试进化类型枚举"""
    print("\n" + "=" * 60)
    print("进化类型枚举测试")
    print("=" * 60)
    
    print(f"\n进化类型:")
    print(f"  GENE: {EvolutionType.GENE.value}")
    print(f"  SKILL: {EvolutionType.SKILL.value}")
    print(f"  REFLEX: {EvolutionType.REFLEX.value}")
    print(f"  ABSTRACTION: {EvolutionType.ABSTRACTION.value}")
    print(f"  ADAPTATION: {EvolutionType.ADAPTATION.value}")
    
    assert EvolutionType.GENE.value == "gene"
    assert EvolutionType.SKILL.value == "skill"
    
    print("✅ 进化类型枚举测试通过")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("L5进化层完整测试")
    print("=" * 60)
    
    try:
        test_l5_initialization()
        test_default_genes()
        test_record_experience()
        test_fitness_evaluation()
        test_gene_evolution()
        test_skill_formation()
        test_get_gene_value()
        test_get_evolution_status()
        test_evolution_type_enum()
        
        print("\n" + "=" * 60)
        print("✅ 所有L5进化层测试通过!")
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
