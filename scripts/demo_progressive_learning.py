# -*- coding: utf-8 -*-
"""
测试完整的渐进式学习流程

演示：
1. 用户提问
2. 系统检索即时学习库
3. 发现知识缺口时主动询问
4. 用户纠错
5. 即时学习（秒级生效）
6. 下次提问时直接使用新知识
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.instant_learning import InstantLearningSystem

def demonstrate_progressive_learning():
    """演示渐进式学习"""
    print("="*70)
    print("🧠 渐进式学习演示 - 不训练也能进化")
    print("="*70)
    print()
    
    # 创建即时学习系统
    system = InstantLearningSystem()
    
    # ========== 场景1: 用户提问，系统检索知识库 ==========
    print("场景1: 用户提问")
    print("-"*70)
    question1 = "什么是深度学习的特点？"
    print(f"用户: {question1}")
    
    # 检索知识
    knowledge, confidence = system.retrieve_knowledge(question1)
    
    if knowledge:
        print(f"系统: 我从知识库中找到以下信息：")
        for k in knowledge[:2]:
            print(f"   - {k['assertion'][:100]}...")
        print(f"   [置信度: {confidence:.2f}]")
    else:
        print(f"系统: ⚠️ 我目前对这个问题还不够了解。")
        print(f"       您能告诉我正确的理解吗？我会立即记住。")
    
    print()
    
    # ========== 场景2: 用户纠错，系统即时学习 ==========
    print("场景2: 用户纠错")
    print("-"*70)
    print(f"用户: 深度学习的特点包括：")
    print(f"      1. 自动特征提取")
    print(f"      2. 端到端学习")
    print(f"      3. 层次化表示学习")
    print(f"      4. 数据驱动与规模效应")
    print(f"      5. 可扩展性")
    
    # 即时学习
    correction = """深度学习的特点包括：
1. 自动特征提取：传统机器学习需要人工设计特征，而深度学习能够自动从原始数据中学习有用的特征表示。
2. 端到端学习：模型可以直接从原始输入映射到最终输出，无需中间的手工特征工程步骤。
3. 层次化表示学习：通过多层非线性变换，数据被转化为越来越抽象和语义化的表示。
4. 数据驱动与规模效应：深度学习的性能随着数据量的增加而持续提升。
5. 可扩展性：Transformer架构在GPU/TPU上具有优异的并行计算能力。"""
    
    result = system.learn_instantly(
        concept="深度学习的特点",
        assertion=correction,
        source='user_correction'
    )
    
    print(f"\n系统: ✅ 已记住！下次我会直接使用这个答案。")
    print(f"       [动作: {result['action']}, 时间: {result['timestamp'][:19]}]")
    
    print()
    
    # ========== 场景3: 用户再次提问，系统使用新知识 ==========
    print("场景3: 用户再次提问")
    print("-"*70)
    question2 = "深度学习有哪些特点？"
    print(f"用户: {question2}")
    
    # 检索知识
    knowledge, confidence = system.retrieve_knowledge(question2)
    
    if knowledge:
        print(f"系统: 根据我的知识库：")
        print(f"       {knowledge[0]['assertion'][:200]}...")
        print(f"       [置信度: {confidence:.2f}, 来源: {knowledge[0]['source']}]")
        print(f"       ✅ 无需重新训练，知识已即时生效！")
    else:
        print(f"系统: ⚠️ 我还是不太确定...")
    
    print()
    
    # ========== 场景4: 批量学习 ==========
    print("场景4: 批量学习")
    print("-"*70)
    
    knowledge_items = [
        {
            'concept': 'Transformer架构的核心创新',
            'assertion': 'Transformer的核心创新包括：自注意力机制、多头注意力、位置编码、并行计算优势。',
            'source': 'user_correction'
        },
        {
            'concept': '迁移学习的原理',
            'assertion': '迁移学习通过预训练-微调范式实现，将通用知识转化为特定领域的专用能力。',
            'source': 'user_correction'
        },
        {
            'concept': '梯度消失问题',
            'assertion': '梯度消失是指在训练深层神经网络时，梯度在反向传播过程中逐层衰减。解决方案包括使用ReLU激活函数和残差连接。',
            'source': 'user_correction'
        }
    ]
    
    batch_result = system.batch_learn(knowledge_items)
    
    print(f"用户: 我要一次性告诉你多个知识点...")
    print(f"系统: ✅ 批量学习完成！")
    print(f"       - 新增: {batch_result['inserted']} 条")
    print(f"       - 更新: {batch_result['updated']} 条")
    
    print()
    
    # ========== 场景5: 知识统计 ==========
    print("场景5: 知识统计")
    print("-"*70)
    
    stats = system.get_knowledge_stats()
    
    print(f"系统: 📊 当前知识库状态：")
    print(f"       - 总知识数: {stats['total_facts']} 条")
    print(f"       - 平均置信度: {stats['avg_confidence']:.2f}")
    print(f"       - 按来源分布: {stats['by_source']}")
    print(f"       - 最近学习: {stats['recent_learning'][0]['concept'] if stats['recent_learning'] else '无'}")
    
    print()
    print("="*70)
    print("✅ 渐进式学习演示完成")
    print()
    print("💡 核心理念：")
    print("   1. 用户纠错 → 立即写入知识库（秒级生效）")
    print("   2. 下次提问 → 直接检索并使用新知识")
    print("   3. 无需重新训练 → 真正的渐进式学习")
    print("   4. 周期性训练 → 仅在需要提升推理能力时进行")
    print("="*70)


if __name__ == "__main__":
    demonstrate_progressive_learning()