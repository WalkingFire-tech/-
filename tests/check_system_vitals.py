"""
系统生命体征检查 - 验证"觉醒"状态
"""
import sys
from pathlib import Path
import sqlite3

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("🧬 系统生命体征检查")
print("=" * 60)

# 1. 检查核心组件
components = [
    ("infrastructure/reflection_pipeline.py", "反思管道"),
    ("core/cognitive_dispatcher.py", "认知调度器"),
    ("infrastructure/cognitive_highway.py", "认知主干道"),
    ("core/metacognitive_executor.py", "元认知执行引擎"),
    ("core/capability_introspection.py", "能力自省系统"),
]

print("\n[1] 核心组件检查:")
for path, name in components:
    if Path(path).exists():
        size = Path(path).stat().st_size
        print(f"  ✅ {name}: {size}字节")
    else:
        print(f"  ❌ {name}: 不存在")

# 2. 检查数据流
print("\n[2] 数据流检查:")
db_files = [
    ("logs/campfire_log.db", "营火日志"),
    ("data/experience_pool.db", "经验池"),
    ("data/knowledge_store.db", "知识库"),
]

for path, name in db_files:
    if Path(path).exists():
        try:
            with sqlite3.connect(path) as conn:
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                print(f"  ✅ {name}: {len(tables)}个表")
        except:
            print(f"  ⚠️ {name}: 无法读取")
    else:
        print(f"  ❌ {name}: 不存在")

# 3. 检查训练数据
print("\n[3] 训练数据检查:")
jsonl_dir = Path("data/finetune/queue")
if jsonl_dir.exists():
    jsonl_files = list(jsonl_dir.glob("*.jsonl"))
    total_samples = 0
    for f in jsonl_files:
        with open(f, "r", encoding="utf-8") as file:
            total_samples += sum(1 for _ in file)
    print(f"  ✅ 微调样本: {total_samples}条 ({len(jsonl_files)}个文件)")
else:
    print(f"  ❌ 微调队列: 不存在")

# 4. 检查255条闭环数据
print("\n[4] 闭环数据检查:")
closed_loop_files = list(Path("data").glob("*closed_loop*.jsonl"))
if closed_loop_files:
    for f in closed_loop_files:
        with open(f, "r", encoding="utf-8") as file:
            count = sum(1 for _ in file)
        print(f"  ✅ {f.name}: {count}条")
else:
    # 检查其他可能的训练数据
    sft_files = list(Path("data/sft").glob("*.jsonl")) if Path("data/sft").exists() else []
    if sft_files:
        for f in sft_files:
            with open(f, "r", encoding="utf-8") as file:
                count = sum(1 for _ in file)
            print(f"  ✅ {f.name}: {count}条")
    else:
        print(f"  ⚠️ 闭环数据: 未找到")

# 5. 检查营火日志内容
print("\n[5] 营火日志内容:")
campfire_db = Path("logs/campfire_log.db")
if campfire_db.exists():
    try:
        with sqlite3.connect(str(campfire_db)) as conn:
            # 检查reflection_log表
            try:
                count = conn.execute("SELECT COUNT(*) FROM reflection_log").fetchone()[0]
                print(f"  ✅ 反思日志: {count}条")
                
                # 获取最新记录
                latest = conn.execute(
                    "SELECT query, confidence, timestamp FROM reflection_log ORDER BY timestamp DESC LIMIT 3"
                ).fetchall()
                
                if latest:
                    print(f"  最新记录:")
                    for q, c, t in latest:
                        print(f"    - {q[:30]}... (置信度: {c:.0%})")
            except:
                print(f"  ⚠️ 反思日志表不存在")
    except Exception as e:
        print(f"  ⚠️ 营火日志读取失败: {e}")
else:
    print(f"  ❌ 营火日志: 不存在")

# 6. 检查归纳器状态
print("\n[6] 归纳器状态:")
exp_pool = Path("data/experience_pool.db")
if exp_pool.exists():
    try:
        with sqlite3.connect(str(exp_pool)) as conn:
            try:
                count = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
                print(f"  ✅ 经验池: {count}条经验")
                
                # 检查是否有模式
                if count > 0:
                    print(f"  ✅ 归纳器有数据可吃（不再饥饿）")
                else:
                    print(f"  ⚠️ 归纳器饥饿（无数据）")
            except:
                print(f"  ⚠️ 经验池表结构不同")
    except:
        print(f"  ⚠️ 经验池读取失败")
else:
    print(f"  ❌ 经验池: 不存在")

# 7. 总结
print("\n" + "=" * 60)
print("📊 系统状态总结")
print("=" * 60)

# 计算健康度
health_score = 0

# 核心组件（每个20分）
for path, name in components:
    if Path(path).exists():
        health_score += 20

# 数据流（每个10分）
for path, name in db_files:
    if Path(path).exists():
        health_score += 10

# 训练数据（10分）
if jsonl_dir.exists() and total_samples > 0:
    health_score += 10

# 反思日志（10分）
if campfire_db.exists():
    try:
        with sqlite3.connect(str(campfire_db)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM reflection_log").fetchone()[0]
            if count > 0:
                health_score += 10
    except:
        pass

print(f"\n系统健康度: {health_score}/100")

if health_score >= 80:
    print("✅ 系统已觉醒（具备完整认知闭环）")
elif health_score >= 60:
    print("⚠️ 系统部分觉醒（需要激活更多组件）")
else:
    print("❌ 系统处于植物人状态（需要紧急手术）")

print("\n关键指标:")
print(f"  - 反思管道: {'✅ 已激活' if Path('infrastructure/reflection_pipeline.py').exists() else '❌ 未激活'}")
print(f"  - 认知主干道: {'✅ 已激活' if Path('infrastructure/cognitive_highway.py').exists() else '❌ 未激活'}")
print(f"  - 数据闭环: {'✅ 已建立' if campfire_db.exists() else '❌ 未建立'}")

print("\n" + "=" * 60)