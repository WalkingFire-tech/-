"""
添加种子知识数据
让系统能够回答基本问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.versioned_fact_store import VersionedFactStore

store = VersionedFactStore()

# 添加基础知识
seed_knowledge = [
    {
        "question": "什么是机器学习?",
        "subject": "机器学习",
        "predicate": "定义",
        "obj": "人工智能的一个分支，通过数据训练模型，使计算机能够从数据中学习规律并做出预测",
        "confidence": 0.9
    },
    {
        "question": "什么是深度学习?",
        "subject": "深度学习",
        "predicate": "定义",
        "obj": "机器学习的一种方法，使用多层神经网络进行特征学习和模式识别",
        "confidence": 0.9
    },
    {
        "question": "什么是人工智能?",
        "subject": "人工智能",
        "predicate": "定义",
        "obj": "计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统",
        "confidence": 0.9
    },
    {
        "question": "Python是什么?",
        "subject": "Python",
        "predicate": "定义",
        "obj": "一种高级编程语言，由Guido van Rossum于1991年创建，以简洁易读著称",
        "confidence": 0.9
    },
    {
        "question": "Python什么时候发布的?",
        "subject": "Python",
        "predicate": "发布时间",
        "obj": "1991年",
        "confidence": 0.95
    },
]

print("正在添加种子知识...")
for i, knowledge in enumerate(seed_knowledge, 1):
    id, action = store.add_assertion(
        question=knowledge["question"],
        subject=knowledge["subject"],
        predicate=knowledge["predicate"],
        obj=knowledge["obj"],
        source="seed",
        confidence=knowledge["confidence"],
        is_seed=True
    )
    print(f"  {i}. {knowledge['question'][:30]}... - {action}")

print(f"\n✅ 已添加 {len(seed_knowledge)} 条种子知识")

# 验证
stats = store.get_statistics()
print(f"\n事实库统计:")
print(f"  总断言: {stats['total']}")
print(f"  有效断言: {stats['active']}")
print(f"  种子数据: {stats['seeds']}")