"""
阶段4：文件结构和数据库测试
"""
import sys
import os
import sqlite3
sys.path.insert(0, ".")

print("╔════════════════════════════════════════════════════════╗")
print("║       阶段4：文件结构和数据库测试                      ║")
print("╚════════════════════════════════════════════════════════╝\n")

# 测试1：核心文件
print("测试1：核心文件检查")
core_files = [
    "core/spirit_core.py",
    "core/never_give_up.py",
    "core/cognitive_dispatcher.py",
    "core/metacognitive_executor.py",
    "core/orchestrator.py",
    "core/cognitive_loop.py"
]

core_passed = 0
for file in core_files:
    exists = os.path.exists(file)
    if exists:
        core_passed += 1
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} 不存在")

print(f"  总结: {core_passed}/{len(core_files)} 核心文件存在")

# 测试2：后端文件
print("\n测试2：后端文件检查")
backend_files = [
    "backend/main_fast.py",
    "backend/chat_handler.py"
]

backend_passed = 0
for file in backend_files:
    exists = os.path.exists(file)
    if exists:
        backend_passed += 1
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} 不存在")

print(f"  总结: {backend_passed}/{len(backend_files)} 后端文件存在")

# 测试3：数据目录
print("\n测试3：数据目录检查")
data_exists = os.path.exists("data")
print(f"  {'✅' if data_exists else '❌'} data目录存在")

if data_exists:
    data_files = os.listdir("data")
    print(f"  包含{len(data_files)}个文件/目录")
    for f in data_files[:10]:  # 只显示前10个
        print(f"     • {f}")

# 测试4：数据库
print("\n测试4：数据库检查")
databases = {
    "knowledge_store.db": "knowledge",
    "experience_pool.db": "experiences",
    "tasks.db": "tasks"
}

db_passed = 0
for db_file, table in databases.items():
    db_path = f"data/{db_file}"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            conn.close()
            db_passed += 1
            print(f"  ✅ {db_file}: {count}条记录")
        except Exception as e:
            print(f"  ⚠️ {db_file}: {str(e)[:30]}")
    else:
        print(f"  ❌ {db_file} 不存在")

print(f"  总结: {db_passed}/{len(databases)} 数据库可用")

# 测试5：配置文件
print("\n测试5：配置文件检查")
config_files = [
    "start.bat",
    "requirements.txt",
    ".gitignore"
]

config_passed = 0
for file in config_files:
    exists = os.path.exists(file)
    if exists:
        config_passed += 1
        print(f"  ✅ {file}")
    else:
        print(f"  ⚠️ {file} 不存在")

# 总结
print("\n" + "=" * 60)
total_checks = len(core_files) + len(backend_files) + 1 + len(databases) + len(config_files)
total_passed = core_passed + backend_passed + (1 if data_exists else 0) + db_passed + config_passed
print(f"✅ 阶段4测试完成: {total_passed}/{total_checks} 检查通过")
print("=" * 60)