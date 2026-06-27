"""
合并所有训练数据
"""

import json
from pathlib import Path

base_dir = Path(__file__).parent.parent
data_dir = base_dir / "data" / "sft"

print("=" * 70)
print("合并所有训练数据")
print("=" * 70)

# ============================================================
# 1. 合并九个模块数据为闭环进化数据
# ============================================================

print("\n📦 合并闭环进化数据（九个模块）...\n")

module_files = [
    "Module 1 Metacognition Activator.jsonl",
    "Module 2 Problem Decomposition and Task Scheduling.jsonl",
    "Module 3 Tool Invocation and Execution.jsonl",
    "Module 4 Adaptive Learning Engine.jsonl",
    "Module 5 Continual Learning Agent.jsonl",
    "Module 6 Basic Command Line Operations.jsonl",
    "Module 7 AI Script Generator .jsonl",
    "Module 8 Multi-Agent Code Synthesis.jsonl",
    "Module 9 Script Security Risk Assessment.jsonl",
]

closed_loop_data = []
for module_file in module_files:
    file_path = data_dir / module_file
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            count = 0
            for line in f:
                if line.strip():
                    closed_loop_data.append(json.loads(line))
                    count += 1
        print(f"  ✅ {module_file} ({count} 条)")
    else:
        print(f"  ❌ {module_file} (不存在)")

# 保存闭环进化数据
closed_loop_file = data_dir / "closed_loop_system_complete.jsonl"
with open(closed_loop_file, 'w', encoding='utf-8') as f:
    for item in closed_loop_data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"\n  💾 已保存: closed_loop_system_complete.jsonl ({len(closed_loop_data)} 条)")

# ============================================================
# 2. 合并所有数据
# ============================================================

print("\n" + "=" * 70)
print("📦 合并所有训练数据...\n")

all_data = []

# 原始训练数据
original_file = data_dir / "final_training_data.jsonl"
if original_file.exists():
    with open(original_file, 'r', encoding='utf-8') as f:
        count = 0
        for line in f:
            if line.strip():
                all_data.append(json.loads(line))
                count += 1
    print(f"  ✅ 原始训练数据 ({count} 条)")

# 基础框架数据
base_framework_file = data_dir / "base_framework_300.jsonl"
if base_framework_file.exists():
    with open(base_framework_file, 'r', encoding='utf-8') as f:
        count = 0
        for line in f:
            if line.strip():
                all_data.append(json.loads(line))
                count += 1
    print(f"  ✅ 基础框架数据 ({count} 条)")

# 闭环进化数据
print(f"  ✅ 闭环进化数据 ({len(closed_loop_data)} 条)")
all_data.extend(closed_loop_data)

# 保存合并后的数据
combined_file = data_dir / "combined_all_training_data.jsonl"
with open(combined_file, 'w', encoding='utf-8') as f:
    for item in all_data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"\n  💾 已保存: combined_all_training_data.jsonl ({len(all_data)} 条)")

# ============================================================
# 3. 数据质量验证
# ============================================================

print("\n" + "=" * 70)
print("📊 数据质量验证")
print("=" * 70)

valid_count = 0
invalid_count = 0
total_output_len = 0
total_instruction_len = 0

for item in all_data:
    if "instruction" in item and "output" in item:
        valid_count += 1
        total_output_len += len(item.get("output", ""))
        total_instruction_len += len(item.get("instruction", ""))
    else:
        invalid_count += 1

avg_output_len = total_output_len / valid_count if valid_count > 0 else 0
avg_instruction_len = total_instruction_len / valid_count if valid_count > 0 else 0

print(f"\n  总数据量: {len(all_data)} 条")
print(f"  有效数据: {valid_count} 条")
print(f"  无效数据: {invalid_count} 条")
print(f"  平均问题长度: {avg_instruction_len:.1f} 字符")
print(f"  平均回答长度: {avg_output_len:.1f} 字符")

# ============================================================
# 4. 更新配置文件
# ============================================================

print("\n" + "=" * 70)
print("📝 更新配置文件")
print("=" * 70)

dataset_info = {
    "alliance_pioneer": {
        "file_name": "sft/final_training_data.jsonl",
        "formatting": "sharegpt",
        "columns": {
            "instruction": "instruction",
            "input": "input",
            "output": "output"
        }
    },
    "base_framework": {
        "file_name": "sft/base_framework_300.jsonl",
        "formatting": "sharegpt",
        "columns": {
            "instruction": "instruction",
            "input": "input",
            "output": "output"
        }
    },
    "closed_loop_system": {
        "file_name": "sft/closed_loop_system_complete.jsonl",
        "formatting": "sharegpt",
        "columns": {
            "instruction": "instruction",
            "input": "input",
            "output": "output"
        }
    },
    "combined_all": {
        "file_name": "sft/combined_all_training_data.jsonl",
        "formatting": "sharegpt",
        "columns": {
            "instruction": "instruction",
            "input": "input",
            "output": "output"
        }
    }
}

dataset_info_path = base_dir / "data" / "dataset_info.json"
with open(dataset_info_path, 'w', encoding='utf-8') as f:
    json.dump(dataset_info, f, indent=2, ensure_ascii=False)

print(f"\n  ✅ 配置文件已更新: data/dataset_info.json")

# ============================================================
# 5. 总结
# ============================================================

print("\n" + "=" * 70)
print("🎉 数据准备完成！")
print("=" * 70)

print(f"""
数据统计：
  原始训练数据: 221 条
  基础框架数据: 253 条
  闭环进化数据: {len(closed_loop_data)} 条
  ─────────────────────
  总计: {len(all_data)} 条

输出文件：
  📄 data/sft/closed_loop_system_complete.jsonl
  📄 data/sft/combined_all_training_data.jsonl
  📄 data/dataset_info.json

下一步操作：
  1. 将以下文件上传到AutoDL：
     - data/sft/combined_all_training_data.jsonl
     - data/dataset_info.json
  
  2. 在AutoDL中运行训练：
     llamafactory-cli train config/train_closed_loop_lora.yaml
  
  3. 预计训练时间：20-30分钟
  4. 预计成本：¥1-1.5
""")