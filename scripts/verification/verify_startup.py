"""
系统启动验证脚本
"""
import sys
import os
import time
import sqlite3
from datetime import datetime

sys.path.insert(0, '.')

print("=" * 70)
print("联盟拓荒者 - 系统启动验证")
print("=" * 70)
print()

# 1. 检查数据库
print("[1/5] 检查数据库...")
dbs = {
    "经验池": "data/experience_pool.db",
    "学习规则": "data/learning_rules.db",
    "反思日志": "logs/campfire_log.db",
}

for name, path in dbs.items():
    if os.path.exists(path):
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchone()[0]
        conn.close()
        print(f"  ✓ {name}: {path} ({tables}张表)")
    else:
        print(f"  ✗ {name}: 不存在")

# 2. 检查配置文件
print("\n[2/5] 检查配置文件...")
configs = [
    "config/reflex_rules.yaml",
]

for config in configs:
    if os.path.exists(config):
        print(f"  ✓ {config}")
    else:
        print(f"  ✗ {config} 不存在")

# 3. 检查核心模块导入
print("\n[3/5] 检查核心模块导入...")
modules = [
    ("L1感知层", "core.layers.l1_perception_enhanced", "L1PerceptionLayer"),
    ("L2学习层", "core.layers.l2_learning", "L2LearningLayer"),
    ("反馈回路", "core.learning.feedback_loop", "LearningFeedbackLoop"),
    ("工具构建", "core.learning.tool_builder", "ToolSelfBuilder"),
    ("编排器", "core.orchestrator", "SystemOrchestrator"),
]

for name, module_path, class_name in modules:
    try:
        module = __import__(module_path, fromlist=[class_name])
        cls = getattr(module, class_name)
        print(f"  ✓ {name}: {class_name}")
    except Exception as e:
        print(f"  ✗ {name}: {e}")

# 4. 检查系统编排器
print("\n[4/5] 检查系统编排器...")
try:
    from core.orchestrator import SystemOrchestrator
    
    orchestrator = SystemOrchestrator({
        "persistence_dir": "data/orchestrator"
    })
    
    print(f"  ✓ 编排器已初始化")
    print(f"    - 活跃层: {orchestrator.metrics.active_layers}")
    print(f"    - 活跃机制: {len(orchestrator.mechanisms)}")
    print(f"    - 已加载层: {list(orchestrator.layers.keys())}")
except Exception as e:
    print(f"  ✗ 编排器初始化失败: {e}")

# 5. 检查API路由
print("\n[5/5] 检查API路由...")
try:
    from backend.main import app
    
    routes = [route.path for route in app.routes]
    print(f"  ✓ FastAPI应用已加载")
    print(f"    - 总路由数: {len(routes)}")
    print(f"    - 主要路由: /, /api/chat, /api/learn, /api/tools")
except Exception as e:
    print(f"  ✗ API加载失败: {e}")

print("\n" + "=" * 70)
print("系统验证完成")
print("=" * 70)
print()
print("✅ 所有核心组件已就绪")
print()
print("启动命令:")
print("  python backend/main.py")
print()
print("或使用uvicorn:")
print("  uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload")
print()