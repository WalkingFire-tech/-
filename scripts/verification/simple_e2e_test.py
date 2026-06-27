"""
简化端到端测试 - 不启动服务
"""
import sys
import os
import sqlite3

sys.path.insert(0, '.')

print("=" * 70)
print("联盟拓荒者 - 端到端测试（无服务启动）")
print("=" * 70)
print()

passed = 0
failed = 0

# 1. 前端文件检查
print("[1/8] 前端文件检查...")
frontend_files = [
    "frontend/index.html",
    "frontend/styles.css",
    "frontend/app.js",
    "frontend/learning_dashboard.html",
    "frontend/knowledge_panel.html",
]

for f in frontend_files:
    exists = os.path.exists(f)
    status = "✓" if exists else "✗"
    print(f"  {status} {f}")
    if exists:
        passed += 1
    else:
        failed += 1

# 2. 后端文件检查
print("\n[2/8] 后端文件检查...")
backend_files = [
    "backend/main.py",
    "backend/__init__.py",
]

for f in backend_files:
    exists = os.path.exists(f)
    status = "✓" if exists else "✗"
    print(f"  {status} {f}")
    if exists:
        passed += 1
    else:
        failed += 1

# 3. 核心模块检查
print("\n[3/8] 核心模块检查...")
core_files = [
    "core/orchestrator.py",
    "core/cognitive_dispatcher.py",
    "core/metacognitive_executor.py",
    "core/canary_evaluator.py",
    "core/sleep_consolidator.py",
]

for f in core_files:
    exists = os.path.exists(f)
    status = "✓" if exists else "✗"
    print(f"  {status} {f}")
    if exists:
        passed += 1
    else:
        failed += 1

# 4. 基础设施检查
print("\n[4/8] 基础设施检查...")
infra_files = [
    "infrastructure/reflection_pipeline.py",
    "infrastructure/quick_reflex.py",
    "infrastructure/config_manager.py",
    "infrastructure/experience_pool.py",
]

for f in infra_files:
    exists = os.path.exists(f)
    status = "✓" if exists else "✗"
    print(f"  {status} {f}")
    if exists:
        passed += 1
    else:
        failed += 1

# 5. 数据库检查
print("\n[5/8] 数据库检查...")
dbs = [
    ("经验池", "data/experience_pool.db"),
    ("学习规则", "data/learning_rules.db"),
    ("反思日志", "logs/campfire_log.db"),
]

for name, path in dbs:
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchone()[0]
        conn.close()
        print(f"  ✓ {name}: {tables}张表")
        passed += 1
    else:
        print(f"  ✗ {name}: 不存在")
        failed += 1

# 6. 数据质量检查
print("\n[6/8] 数据质量检查...")
try:
    conn = sqlite3.connect("data/experience_pool.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM experiences")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM experiences WHERE success > 0")
    success_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT AVG(success) FROM experiences")
    avg_success = cursor.fetchone()[0] or 0
    
    conn.close()
    
    print(f"  ✓ 总经验: {total}")
    print(f"  ✓ 成功经验: {success_count}")
    print(f"  ✓ 平均成功率: {avg_success:.2%}")
    passed += 1
except Exception as e:
    print(f"  ✗ 数据质量检查失败: {e}")
    failed += 1

# 7. 核心导入测试
print("\n[7/8] 核心导入测试...")
try:
    from core.layers.l1_perception_enhanced import L1PerceptionLayer
    from core.layers.l2_learning import L2LearningLayer
    from core.learning.feedback_loop import LearningFeedbackLoop
    from core.orchestrator import SystemOrchestrator
    
    print("  ✓ L1PerceptionLayer")
    print("  ✓ L2LearningLayer")
    print("  ✓ LearningFeedbackLoop")
    print("  ✓ SystemOrchestrator")
    passed += 1
except Exception as e:
    print(f"  ✗ 导入失败: {e}")
    failed += 1

# 8. 配置文件检查
print("\n[8/8] 配置文件检查...")
config_files = [
    "config/reflex_rules.yaml",
]

for f in config_files:
    exists = os.path.exists(f)
    status = "✓" if exists else "✗"
    print(f"  {status} {f}")
    if exists:
        passed += 1
    else:
        failed += 1

# 总结
print("\n" + "=" * 70)
print(f"测试结果: ✅ {passed} 通过, ❌ {failed} 失败")
print("=" * 70)

if failed == 0:
    print("\n✅ 所有端到端测试通过！")
    print("\n启动服务:")
    print("  python start.py")
    print("\n访问地址:")
    print("  http://localhost:8000/")
    sys.exit(0)
else:
    print(f"\n❌ {failed} 个测试失败")
    sys.exit(1)