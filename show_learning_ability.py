"""
展示系统的自我学习能力
"""
import sqlite3
from pathlib import Path

print("=" * 70)
print("联盟拓荒者自我学习能力展示")
print("=" * 70)

# 1. 学习规则统计
print("\n【1. 学习规则来源统计】")
try:
    conn = sqlite3.connect('learning_rules.db')
    
    # 总规则数
    cur = conn.execute('SELECT COUNT(*) FROM learning_rules')
    total = cur.fetchone()[0]
    
    # 按来源统计
    cur = conn.execute('''
        SELECT source, COUNT(*) 
        FROM learning_rules 
        GROUP BY source
    ''')
    by_source = cur.fetchall()
    
    # 活跃规则
    cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
    active = cur.fetchone()[0]
    
    conn.close()
    
    print(f"  总规则数: {total}")
    print(f"  活跃规则: {active}")
    print(f"\n  按来源分布:")
    for source, count in by_source:
        print(f"    - {source}: {count}条")
        
except Exception as e:
    print(f"  错误: {e}")

# 2. 经验池统计
print("\n【2. 经验池学习统计】")
try:
    conn = sqlite3.connect('experience_pool.db')
    
    # 总经验数
    cur = conn.execute('SELECT COUNT(*) FROM experiences')
    total = cur.fetchone()[0]
    
    # 成功经验
    cur = conn.execute('SELECT COUNT(*) FROM experiences WHERE success=1')
    success = cur.fetchone()[0]
    
    # 最近学习的经验
    cur = conn.execute('''
        SELECT intent_type, model_name, quality_score
        FROM experiences
        ORDER BY timestamp DESC
        LIMIT 5
    ''')
    recent = cur.fetchall()
    
    conn.close()
    
    print(f"  总经验数: {total}")
    print(f"  成功经验: {success} ({success/total*100:.1f}%)")
    print(f"\n  最近学习:")
    for intent, model, quality in recent:
        print(f"    - {intent} → {model} (质量: {quality})")
        
except Exception as e:
    print(f"  错误: {e}")

# 3. 能力矩阵更新统计
print("\n【3. 能力矩阵学习统计】")
try:
    conn = sqlite3.connect('data/capability_matrix.db')
    
    # 模型数量
    cur = conn.execute('SELECT COUNT(DISTINCT model_name) FROM model_capabilities')
    models = cur.fetchone()[0]
    
    # 更新次数
    cur = conn.execute('SELECT COUNT(*) FROM model_capabilities')
    updates = cur.fetchone()[0]
    
    conn.close()
    
    print(f"  已学习模型: {models}个")
    print(f"  能力更新次数: {updates}次")
    
except Exception as e:
    print(f"  错误: {e}")

# 4. 反事实模拟统计
print("\n【4. 反事实模拟学习统计】")
try:
    conn = sqlite3.connect('counterfactual_history.db')
    
    # 模拟次数
    cur = conn.execute('SELECT COUNT(*) FROM counterfactual_records')
    simulations = cur.fetchone()[0]
    
    # 发现改进机会
    cur = conn.execute('SELECT COUNT(*) FROM counterfactual_records WHERE gap > 10')
    improvements = cur.fetchone()[0]
    
    conn.close()
    
    print(f"  模拟次数: {simulations}")
    print(f"  发现改进机会: {improvements}次")
    
except Exception as e:
    print(f"  (数据库不存在或为空)")

# 5. 用户反馈学习
print("\n【5. 用户反馈学习统计】")
try:
    conn = sqlite3.connect('experience_pool.db')
    
    # 正面反馈
    cur = conn.execute('SELECT COUNT(*) FROM experiences WHERE user_feedback > 0')
    positive = cur.fetchone()[0]
    
    # 负面反馈
    cur = conn.execute('SELECT COUNT(*) FROM experiences WHERE user_feedback < 0')
    negative = cur.fetchone()[0]
    
    conn.close()
    
    print(f"  正面反馈: {positive}次")
    print(f"  负面反馈: {negative}次")
    print(f"  反馈驱动学习: {'是' if negative > 0 else '否'}")
    
except Exception as e:
    print(f"  错误: {e}")

print("\n" + "=" * 70)
print("自我学习机制总结")
print("=" * 70)
print("""
系统通过以下途径完善自我：

1. 经验学习：每次交互都存储到经验池
2. 归纳学习：定期从经验池挖掘模式生成规则
3. 反事实学习：模拟"如果用其他模型会怎样"
4. 用户反馈学习：负面反馈触发规则降级
5. 在线反思：低质量立即生成改进规则
6. 能力更新：根据表现动态调整能力矩阵

学习闭环：经验 → 归纳 → 规则 → 应用 → 反馈 → 更新 → 再学习
""")