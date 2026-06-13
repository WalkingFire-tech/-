"""
初始化知识库 - 注入基础知识
"""
from infrastructure.knowledge_injector import knowledge_injector

# 注入基础知识
knowledge_items = [
    {
        "question": "什么是联盟拓荒者？",
        "answer": "联盟拓荒者是一个生产级自我进化数字生命体系统，具备自我感知、自我对比、自我完善、自我进化、自我保护、理解用户、决策透明等能力。",
        "intent_type": "question",
        "source": "system_init"
    },
    {
        "question": "你的核心能力有哪些？",
        "answer": "我的核心能力包括：\n1. 意图识别（code/question/meta/calculation等）\n2. 模型路由（根据任务类型选择最佳模型）\n3. 经验复用（知识库检索）\n4. 失败学习（归纳总结）\n5. 健康监控（APHI仪表盘）\n6. 反事实模拟（探索更优决策）\n7. 情绪推断（理解用户状态）",
        "intent_type": "question",
        "source": "system_init"
    },
    {
        "question": "APHI是什么？",
        "answer": "APHI（Alliance Pioneer Health Index）是联盟拓荒者健康度指数，综合评估系统的能力覆盖率、任务成功率、资源可用性、进化活力、用户满意度等5个维度，得分范围0-100。",
        "intent_type": "question",
        "source": "system_init"
    },
    {
        "question": "如何使用数学计算器？",
        "answer": "直接输入数学表达式即可，例如：\n- 计算圆周率前100位\n- 计算 123 * 456\n- 求解方程 x^2 - 5x + 6 = 0\n系统会自动识别并调用高精度计算器。",
        "intent_type": "calculation",
        "source": "system_init"
    },
    {
        "question": "五层防御机制是什么？",
        "answer": "五层防御机制包括：\n第1层：工具优先调用（精确答案）\n第2层：任务智能分解（复杂任务）\n第3层：知识库检索（经验复用）\n第4层：主动用户求助（坦诚限制）\n第5层：失败学习机制（归纳总结）",
        "intent_type": "question",
        "source": "system_init"
    },
    {
        "question": "如何查看决策日志？",
        "answer": "输入命令 `:why` 可以查看最近一次决策的原因和过程，包括模型选择、置信度评估、降级原因等详细信息。",
        "intent_type": "question",
        "source": "system_init"
    },
]

print("="*60)
print("初始化知识库")
print("="*60)

for item in knowledge_items:
    knowledge_injector.inject_knowledge(
        question=item["question"],
        answer=item["answer"],
        source=item["source"],
        intent_type=item["intent_type"],
        metadata={"quality": 90, "verified": True}
    )
    print(f"✅ 注入: {item['question'][:30]}...")

print("\n" + "="*60)
print("知识库初始化完成")
print("="*60)

print(f"\n✅ 已注入 {len(knowledge_items)} 条知识")