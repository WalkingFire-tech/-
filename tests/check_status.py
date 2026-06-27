"""
检查系统当前状态
"""
import sqlite3

conn = sqlite3.connect("data/knowledge_store.db")

print("\n" + "="*60)
print("📊 系统当前状态")
print("="*60)

# 知识库
cursor = conn.execute("SELECT COUNT(*) FROM knowledge_items")
knowledge = cursor.fetchone()[0]
print(f"\n知识库: {knowledge}条")

# 经验池
cursor = conn.execute("SELECT COUNT(*) FROM experiences")
experience = cursor.fetchone()[0]
print(f"经验池: {experience}条")

# 学习规则
cursor = conn.execute("SELECT COUNT(*) FROM learning_rules")
rules = cursor.fetchone()[0]
print(f"学习规则: {rules}条")

# 意图分布
print("\n意图分布:")
cursor = conn.execute("""
    SELECT intent_type, COUNT(*) as cnt, AVG(quality_score) as avg_q
    FROM experiences
    GROUP BY intent_type
    ORDER BY cnt DESC
    LIMIT 10
""")
for intent, cnt, avg_q in cursor.fetchall():
    print(f"  {intent}: {cnt}次, 平均质量: {avg_q:.1f}")

# 最近学习规则
print("\n最近学习规则:")
cursor = conn.execute("""
    SELECT trigger_pattern, action, confidence, source
    FROM learning_rules
    ORDER BY created_at DESC
    LIMIT 5
""")
rules_list = cursor.fetchall()
if rules_list:
    for i, (pattern, action, conf, source) in enumerate(rules_list, 1):
        print(f"\n规则{i}:")
        print(f"  触发: {pattern[:50]}...")
        print(f"  动作: {action[:50]}...")
        print(f"  置信度: {conf:.2f}, 来源: {source}")
else:
    print("  暂无学习规则")

# 模型统计
print("\n模型使用统计:")
cursor = conn.execute("""
    SELECT model_used, COUNT(*) as cnt, AVG(quality_score) as avg_q
    FROM experiences
    WHERE model_used IS NOT NULL
    GROUP BY model_used
    ORDER BY cnt DESC
    LIMIT 5
""")
for model, cnt, avg_q in cursor.fetchall():
    print(f"  {model}: {cnt}次, 平均质量: {avg_q:.1f}")

conn.close()

print("\n" + "="*60)
print("📈 进化建议")
print("="*60)

if experience < 20:
    print(f"\n⚠️ 经验不足 ({experience}/20)")
    print("建议: 继续对话积累经验")
elif rules < 3:
    print(f"\n⚠️ 规则较少 ({rules}/3)")
    print("建议: 系统会自动归纳，请继续对话")
else:
    print("\n✅ 系统已具备学习能力")
    print(f"  - 经验充足: {experience}条")
    print(f"  - 规则生成: {rules}条")
    print("  - 可触发归纳总结")

print("\n💡 操作建议:")
print("  1. 在前端继续对话")
print("  2. 提问各种类型的问题")
print("  3. 系统会自动学习和进化")
print("  4. 定期运行此脚本查看进度")