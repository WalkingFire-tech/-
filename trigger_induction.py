"""
手动触发归纳总结并显示结果
"""
import sys
sys.path.insert(0, ".")

from meta.induction import induction_scheduler
import sqlite3

print("\n" + "="*60)
print("🧬 触发归纳总结")
print("="*60)

# 检查经验数据
conn = sqlite3.connect("data/knowledge_store.db")
cursor = conn.execute("SELECT COUNT(*) FROM experiences")
exp_count = cursor.fetchone()[0]

print(f"\n经验数据: {exp_count}条")

if exp_count < 10:
    print("⚠️ 经验不足，无法归纳")
    conn.close()
    sys.exit(0)

# 显示部分经验
print("\n最近经验:")
cursor = conn.execute("""
    SELECT intent_type, response, quality_score, success
    FROM experiences
    ORDER BY timestamp DESC
    LIMIT 10
""")
for intent, response, quality, success in cursor.fetchall():
    response_text = response[:40] if response else "无"
    print(f"  [{intent}] {response_text}... (质量:{quality}, 成功:{success})")

conn.close()

# 触发归纳
print("\n" + "="*60)
print("开始归纳...")
print("="*60)

try:
    result = induction_scheduler.run_induction(days=7)
    
    print("\n✅ 归纳完成")
    print(f"结果: {result}")
    
except Exception as e:
    print(f"\n❌ 归纳失败: {e}")
    
    # 尝试直接调用模式挖掘
    print("\n尝试直接模式挖掘...")
    try:
        from meta.induction import pattern_miner
        
        patterns = pattern_miner.mine_patterns()
        
        if patterns:
            print(f"\n✅ 发现 {len(patterns)} 个模式:")
            for i, p in enumerate(patterns, 1):
                print(f"\n模式{i}:")
                print(f"  {p}")
        else:
            print("\n⚠️ 未发现显著模式")
            print("\n原因分析:")
            print("  - 经验数据可能过于分散")
            print("  - 需要更多重复或相似的问题")
            print("  - 质量分数差异不够明显")
            
    except Exception as e2:
        print(f"模式挖掘也失败: {e2}")

# 检查学习规则
print("\n" + "="*60)
print("📊 当前学习规则")
print("="*60)

conn = sqlite3.connect("data/knowledge_store.db")
cursor = conn.execute("""
    SELECT trigger_pattern, action, confidence, source, created_at
    FROM learning_rules
    ORDER BY confidence DESC
    LIMIT 10
""")
rules = cursor.fetchall()

if rules:
    print(f"\n共 {len(rules)} 条规则:")
    for i, (pattern, action, conf, source, created) in enumerate(rules, 1):
        print(f"\n规则{i} (置信度: {conf:.2f}):")
        print(f"  触发: {pattern[:60]}")
        print(f"  动作: {action[:60]}")
        print(f"  来源: {source}")
else:
    print("\n暂无学习规则")

conn.close()

print("\n" + "="*60)
print("💡 建议")
print("="*60)
print("\n要触发成功的归纳总结，需要:")
print("  1. 更多重复或相似的问题")
print("  2. 明显的质量差异（高分 vs 低分）")
print("  3. 不同意图类型的对比")
print("\n操作建议:")
print("  - 继续对话，提问相似问题")
print("  - 对好回答点赞，差回答点踩")
print("  - 系统会自动发现模式并生成规则")