"""
系统评估报告生成器
"""
import sys
import sqlite3
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

print("=" * 70)
print("联盟拓荒者系统评估报告")
print("=" * 70)
print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 70)

# 1. 经验池统计
print("\n【1. 经验池统计】")
try:
    conn = sqlite3.connect('experience_pool.db')
    cur = conn.execute('SELECT COUNT(*) FROM experiences')
    total = cur.fetchone()[0]
    
    cur = conn.execute('SELECT COUNT(*) FROM experiences WHERE success=1')
    success = cur.fetchone()[0]
    
    cur = conn.execute('SELECT AVG(quality_score) FROM experiences')
    avg_quality = cur.fetchone()[0] or 0
    
    cur = conn.execute('''
        SELECT intent_type, COUNT(*), AVG(quality_score)
        FROM experiences
        GROUP BY intent_type
        ORDER BY COUNT(*) DESC
    ''')
    by_intent = cur.fetchall()
    conn.close()
    
    print(f"  经验总数: {total}")
    print(f"  成功率: {success/total*100:.1f}%" if total > 0 else "  成功率: N/A")
    print(f"  平均质量: {avg_quality:.1f}/100")
    print(f"\n  按意图分布:")
    for intent, count, quality in by_intent[:5]:
        print(f"    - {intent}: {count}次, 平均质量 {quality:.1f}")
except Exception as e:
    print(f"  错误: {e}")

# 2. 学习规则统计
print("\n【2. 学习规则统计】")
try:
    conn = sqlite3.connect('learning_rules.db')
    cur = conn.execute('SELECT COUNT(*) FROM learning_rules')
    total = cur.fetchone()[0]
    
    cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
    active = cur.fetchone()[0]
    
    cur = conn.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
    pending = cur.fetchone()[0]
    conn.close()
    
    print(f"  规则总数: {total}")
    print(f"  活跃规则: {active}")
    print(f"  待激活规则: {pending}")
except Exception as e:
    print(f"  错误: {e}")

# 3. 系统健康度
print("\n【3. 系统健康度】")
try:
    from infrastructure.health_dashboard import health_dashboard
    aphi = health_dashboard.calculate_aphi()
    
    print(f"  APHI得分: {aphi['aphi']:.2f}/100")
    print(f"  运行模式: {aphi['mode']}")
    print(f"  能力覆盖率: {aphi.get('capability_coverage', 0)*100:.1f}%")
    
    # 各维度得分
    if 'dimensions' in aphi:
        print(f"\n  各维度得分:")
        for dim, score in aphi['dimensions'].items():
            print(f"    - {dim}: {score:.1f}")
except Exception as e:
    print(f"  错误: {e}")

# 4. 模型统计
print("\n【4. 模型统计】")
try:
    conn = sqlite3.connect('data/model_stats.db')
    cur = conn.execute('''
        SELECT model_name, COUNT(*), AVG(duration), AVG(quality)
        FROM model_calls
        GROUP BY model_name
        ORDER BY COUNT(*) DESC
    ''')
    models = cur.fetchall()
    conn.close()
    
    print(f"  已使用模型: {len(models)}个")
    for model, calls, duration, quality in models:
        print(f"    - {model}: {calls}次, 平均耗时 {duration:.2f}s, 平均质量 {quality:.1f}")
except Exception as e:
    print(f"  错误: {e}")

# 5. 修复记录
print("\n【5. 已完成修复】")
fixes = [
    ("P0-1", "并行调度异步调用错误", "✅"),
    ("P0-2", "反事实模拟异步调用错误", "✅"),
    ("P0-3", "规则匹配缺少raw_input变量", "✅"),
    ("P1-1", "charter_executor数据库字段缺失", "✅"),
    ("P1-2", "counterfactual_simulator导入错误", "✅"),
    ("P1-3", "资源超限警告频繁", "✅"),
    ("P2-1", "前端undefined请求", "✅"),
]

for level, issue, status in fixes:
    print(f"  [{level}] {issue}: {status}")

# 6. 改进记录
print("\n【6. 已实现改进】")
improvements = [
    ("动态模型发现", "安装aiohttp，启用自动发现Ollama模型"),
    ("模型热加载API", "新增5个API端点支持动态添加/移除模型"),
    ("健康检查优化", "添加连续超限检测，避免瞬时波动误报"),
    ("异步调用修复", "使用nest_asyncio正确处理事件循环"),
]

for feature, desc in improvements:
    print(f"  ✓ {feature}: {desc}")

print("\n" + "=" * 70)
print("评估完成")
print("=" * 70)