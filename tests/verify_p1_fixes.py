"""
验证P1修复
"""
import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

print("=" * 60)
print("P1修复验证")
print("=" * 60)

# 测试1: charter_executor数据库字段修复
print("\n[测试1] charter_executor数据库字段修复")
try:
    import sqlite3
    
    # 测试parallel_calls表查询
    conn = sqlite3.connect('data/scheduler_stats.db')
    cursor = conn.execute('''
        SELECT COUNT(*), MAX(start_time)
        FROM parallel_calls
        WHERE start_time >= datetime('now', '-7 days')
    ''')
    result = cursor.fetchone()
    conn.close()
    print(f"  ✓ parallel_calls查询成功: {result}")
    
    # 测试decompositions表查询
    conn = sqlite3.connect('data/task_decomposition.db')
    cursor = conn.execute('''
        SELECT COUNT(*), MAX(timestamp)
        FROM decompositions
        WHERE timestamp >= datetime('now', '-7 days')
    ''')
    result = cursor.fetchone()
    conn.close()
    print(f"  ✓ decompositions查询成功: {result}")
    
    print("  ✅ 数据库字段修复验证通过")
    
except Exception as e:
    print(f"  ❌ 数据库字段测试失败: {e}")
    import traceback
    traceback.print_exc()

# 测试2: counterfactual_simulator导入修复
print("\n[测试2] counterfactual_simulator导入修复")
try:
    from infrastructure.model_capability import model_capability
    
    # 测试方法是否存在
    assert hasattr(model_capability, 'score_model_for_task'), "缺少score_model_for_task方法"
    assert hasattr(model_capability, 'update_capability'), "缺少update_capability方法"
    print("  ✓ model_capability方法检查通过")
    
    # 测试反事实模拟器的apply_insights方法
    from infrastructure.counterfactual_simulator import CounterfactualSimulator
    simulator = CounterfactualSimulator()
    
    # 添加一个测试洞察
    simulator.insights['test_task'] = [{
        'type': 'model_preference',
        'recommendation': '对于test_task任务，优先使用 mindchat',
        'confidence': 0.6,
        'timestamp': '2026-01-01T00:00:00'
    }]
    
    # 尝试应用洞察
    applied = simulator.apply_insights()
    print(f"  ✓ apply_insights执行成功，应用了{applied}条洞察")
    
    print("  ✅ 反事实模拟器修复验证通过")
    
except Exception as e:
    print(f"  ❌ 反事实模拟器测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("P1修复验证完成")
print("=" * 60)