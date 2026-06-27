"""
测试学习闭环
"""
import sys
sys.path.insert(0, ".")

from core.learning_loop import check_and_learn, learning_loop

print("\n" + "="*60)
print("测试学习闭环")
print("="*60)

# 测试1: 检测能力不足
print("\n【测试1】检测能力不足")
gap_info = learning_loop.detect_capability_gap(
    question="西瓜为什么是圆的",
    answer=None,
    confidence=0.0,
    quality_score=0.0,
    error="无法回答"
)
print(f"能力不足: {gap_info['has_gap']}")
print(f"类型: {gap_info['gap_type']}")
print(f"严重程度: {gap_info['severity']}")
print(f"学习优先级: {gap_info['learning_priority']}")

# 测试2: 触发学习
print("\n【测试2】触发学习")
result = check_and_learn(
    question="西瓜为什么是圆的",
    answer=None,
    confidence=0.0,
    quality_score=0.0,
    error="无法回答"
)
print(f"学习成功: {result['success']}")
print(f"获得知识: {result['knowledge_gained']}条")
print(f"来源: {result.get('sources', [])[:2]}")
if result.get('analysis'):
    print(f"分析: {result['analysis'][:200]}...")

# 测试3: 质量不足触发学习
print("\n【测试3】质量不足触发学习")
result = check_and_learn(
    question="什么是机器学习",
    answer="机器学习是...",
    confidence=0.6,
    quality_score=40.0,
    error=None
)
print(f"学习成功: {result['success']}")
print(f"获得知识: {result['knowledge_gained']}条")

# 测试4: 检查知识库
print("\n【测试4】检查知识库")
import sqlite3
with sqlite3.connect("data/knowledge_store.db") as conn:
    cursor = conn.execute(
        "SELECT COUNT(*) FROM knowledge_items WHERE source = 'search_learned' OR source = 'analysis'"
    )
    learned_count = cursor.fetchone()[0]
    print(f"通过学习获得的知识: {learned_count}条")
    
    cursor = conn.execute(
        "SELECT question, source FROM knowledge_items WHERE source = 'search_learned' OR source = 'analysis' ORDER BY created_at DESC LIMIT 3"
    )
    recent = cursor.fetchall()
    print("\n最近学习的知识:")
    for q, s in recent:
        print(f"  - {q[:50]}... (来源: {s})")

print("\n" + "="*60)
print("✅ 学习闭环测试完成")
print("="*60)
print("\n学习闭环逻辑:")
print("1. 检测能力不足 (置信度低/质量差/失败)")
print("2. 触发搜索学习 (DuckDuckGo/Bing)")
print("3. 分析对比搜索结果")
print("4. 存储高质量知识")
print("5. 生成学习规则")
print("6. 下次遇到类似问题就能回答了")