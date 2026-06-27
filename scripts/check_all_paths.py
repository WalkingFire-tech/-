"""
全面路径检查 - 检查所有可能的路径问题
"""
import os
import glob

print("=" * 70)
print("全面路径检查")
print("=" * 70)
print()

issues = []

# 1. 检查data目录下的数据库是否存在
print("[1/5] 检查数据库文件...")
db_files = [
    "data/experience_pool.db",
    "data/learning_rules.db",
    "data/knowledge_store.db",
]

for db in db_files:
    if os.path.exists(db):
        print(f"  ✓ {db}")
    else:
        print(f"  ✗ {db} 不存在")
        issues.append(f"数据库缺失: {db}")

# 2. 检查logs目录
print("\n[2/5] 检查日志文件...")
log_files = [
    "logs/campfire_log.db",
]

for log in log_files:
    if os.path.exists(log):
        print(f"  ✓ {log}")
    else:
        print(f"  ✗ {log} 不存在")
        issues.append(f"日志文件缺失: {log}")

# 3. 检查config目录
print("\n[3/5] 检查配置文件...")
config_files = [
    "config/reflex_rules.yaml",
]

for config in config_files:
    if os.path.exists(config):
        print(f"  ✓ {config}")
    else:
        print(f"  ✗ {config} 不存在")
        issues.append(f"配置文件缺失: {config}")

# 4. 检查__init__.py文件
print("\n[4/5] 检查__init__.py文件...")
init_dirs = [
    "meta",
    "adapters",
    "adapters/llm",
    "adapters/input",
    "adapters/ui",
    "core",
    "tools",
    "infrastructure",
    "core/layers",
]

for dir_path in init_dirs:
    init_file = os.path.join(dir_path, "__init__.py")
    if os.path.exists(init_file):
        print(f"  ✓ {init_file}")
    else:
        print(f"  ✗ {init_file} 不存在")
        issues.append(f"__init__.py缺失: {init_file}")

# 5. 检查移动后的脚本是否有正确的路径设置
print("\n[5/5] 检查移动后的脚本...")
verification_scripts = glob.glob("scripts/verification/*.py")

for script in verification_scripts:
    with open(script, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # 检查是否有sys.path设置
    has_path_setup = 'sys.path.insert' in content or 'sys.path.append' in content
    
    if has_path_setup:
        print(f"  ✓ {os.path.basename(script)}")
    else:
        print(f"  ⚠ {os.path.basename(script)} - 缺少sys.path设置")

# 总结
print("\n" + "=" * 70)
if issues:
    print(f"发现 {len(issues)} 个问题:")
    for issue in issues:
        print(f"  ✗ {issue}")
else:
    print("✅ 所有路径检查通过")
print("=" * 70)