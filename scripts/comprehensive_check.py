"""
综合路径检查 - 验证所有文件路径和引用
"""
import os
from pathlib import Path

print("=" * 70)
print("综合路径检查")
print("=" * 70)
print()

all_ok = True

# 1. 检查目录结构
print("[1/6] 检查目录结构...")
required_dirs = [
    "frontend",
    "backend",
    "core",
    "infrastructure",
    "tools",
    "meta",
    "adapters",
    "data",
    "logs",
    "config",
]

for d in required_dirs:
    if Path(d).exists():
        print(f"  ✓ {d}/")
    else:
        print(f"  ✗ {d}/ 不存在")
        all_ok = False

# 2. 检查关键文件
print("\n[2/6] 检查关键文件...")
key_files = {
    "前端主页": "frontend/index.html",
    "前端样式": "frontend/styles.css",
    "前端逻辑": "frontend/app.js",
    "后端主文件": "backend/main.py",
    "最小化应用": "minimal_app.py",
    "编排器": "core/orchestrator.py",
    "反思管道": "infrastructure/reflection_pipeline.py",
    "经验池": "infrastructure/experience_pool.py",
    "模型归纳": "meta/induction.py",
    "工具注册": "tools/registry.py",
}

for name, path in key_files.items():
    if Path(path).exists():
        print(f"  ✓ {name}: {path}")
    else:
        print(f"  ✗ {name}: {path} 不存在")
        all_ok = False

# 3. 检查数据库文件
print("\n[3/6] 检查数据库文件...")
db_files = [
    "data/experience_pool.db",
    "data/learning_rules.db",
    "logs/campfire_log.db",
]

for db in db_files:
    if Path(db).exists():
        size = Path(db).stat().st_size
        print(f"  ✓ {db} ({size:,} 字节)")
    else:
        print(f"  ✗ {db} 不存在")
        all_ok = False

# 4. 检查配置文件
print("\n[4/6] 检查配置文件...")
config_files = [
    "config/reflex_rules.yaml",
]

for config in config_files:
    if Path(config).exists():
        print(f"  ✓ {config}")
    else:
        print(f"  ✗ {config} 不存在")
        all_ok = False

# 5. 检查__init__.py
print("\n[5/6] 检查__init__.py文件...")
init_dirs = [
    "core",
    "infrastructure",
    "tools",
    "meta",
    "adapters",
    "adapters/llm",
    "adapters/input",
    "adapters/ui",
    "core/layers",
]

for d in init_dirs:
    init_file = Path(d) / "__init__.py"
    if init_file.exists():
        print(f"  ✓ {d}/__init__.py")
    else:
        print(f"  ✗ {d}/__init__.py 不存在")
        all_ok = False

# 6. 检查前端资源引用
print("\n[6/6] 检查前端资源引用...")
index_html = Path("frontend/index.html")
if index_html.exists():
    content = index_html.read_text(encoding='utf-8')
    
    # 检查CSS引用
    if '/frontend/styles.css' in content:
        if Path('frontend/styles.css').exists():
            print("  ✓ CSS引用正确")
        else:
            print("  ✗ CSS文件不存在")
            all_ok = False
    
    # 检查JS引用
    if '/frontend/app.js' in content:
        if Path('frontend/app.js').exists():
            print("  ✓ JS引用正确")
        else:
            print("  ✗ JS文件不存在")
            all_ok = False

# 总结
print("\n" + "=" * 70)
if all_ok:
    print("✅ 所有路径检查通过")
    print("\n可以启动服务:")
    print("  python minimal_app.py")
    print("  或")
    print("  START.bat")
else:
    print("❌ 存在路径问题，请检查上述错误")
print("=" * 70)