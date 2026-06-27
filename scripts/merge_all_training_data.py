"""
训练数据合并脚本
将所有训练数据合并为一个完整的训练集

使用方法：
1. 将你的300条基础框架数据保存到 data/sft/base_framework_300.jsonl
2. 将你的255条闭环进化数据保存到 data/sft/closed_loop_system_complete.jsonl
3. 运行此脚本：python scripts/merge_all_training_data.py
"""

import json
import os
from pathlib import Path

base_dir = Path(__file__).parent.parent
data_dir = base_dir / "data" / "sft"

print("=" * 70)
print("训练数据合并工具")
print("=" * 70)

# 定义数据源
data_sources = {
    "原始训练数据": {
        "file": "final_training_data.jsonl",
        "expected": 221,
        "required": True
    },
    "基础框架数据": {
        "file": "base_framework_300.jsonl",
        "expected": 300,
        "required": True
    },
    "闭环进化数据": {
        "file": "closed_loop_system_complete.jsonl",
        "expected": 255,
        "required": True
    }
}

# 检查各数据源
print("\n📁 数据源检查：\n")
all_ready = True
total_expected = 0
total_actual = 0

for name, info in data_sources.items():
    file_path = data_dir / info["file"]
    expected = info["expected"]
    total_expected += expected
    
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            actual = sum(1 for _ in f)
        total_actual += actual
        
        if actual == expected:
            print(f"  ✅ {name}")
            print(f"     文件: {info['file']}")
            print(f"     条数: {actual} 条（符合预期）\n")
        else:
            print(f"  ⚠️  {name}")
            print(f"     文件: {info['file']}")
            print(f"     条数: {actual} 条（预期 {expected} 条）\n")
    else:
        print(f"  ❌ {name}")
        print(f"     文件: {info['file']}")
        print(f"     状态: 文件不存在\n")
        if info["required"]:
            all_ready = False

print("-" * 70)
print(f"\n📊 统计：")
print(f"  预期总条数: {total_expected} 条")
print(f"  实际总条数: {total_actual} 条")

# 如果所有数据都准备好了，进行合并
if all_ready:
    print("\n" + "=" * 70)
    print("开始合并数据...")
    print("=" * 70)
    
    output_file = data_dir / "combined_all_training_data.jsonl"
    all_data = []
    
    for name, info in data_sources.items():
        file_path = data_dir / info["file"]
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    all_data.append(json.loads(line))
        print(f"  ✓ 已加载 {name}")
    
    # 保存合并后的数据
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n✅ 合并完成！")
    print(f"   输出文件: {output_file}")
    print(f"   总条数: {len(all_data)} 条")
    
    # 验证数据质量
    print("\n📋 数据质量验证：")
    
    # 检查数据格式
    valid_count = 0
    invalid_count = 0
    avg_output_len = 0
    
    for item in all_data:
        if "instruction" in item and "output" in item:
            valid_count += 1
            avg_output_len += len(item.get("output", ""))
        else:
            invalid_count += 1
    
    avg_output_len = avg_output_len / valid_count if valid_count > 0 else 0
    
    print(f"  有效数据: {valid_count} 条")
    print(f"  无效数据: {invalid_count} 条")
    print(f"  平均输出长度: {avg_output_len:.1f} 字符")
    
    # 更新dataset_info.json
    print("\n📝 更新配置文件...")
    dataset_info_path = base_dir / "data" / "dataset_info.json"
    
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
    
    with open(dataset_info_path, 'w', encoding='utf-8') as f:
        json.dump(dataset_info, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ 配置文件已更新: {dataset_info_path}")
    
    print("\n" + "=" * 70)
    print("🎉 数据准备完成！")
    print("=" * 70)
    print("\n下一步操作：")
    print("1. 将以下文件上传到AutoDL：")
    print("   - data/sft/combined_all_training_data.jsonl")
    print("   - data/dataset_info.json")
    print("   - config/train_closed_loop_lora.yaml")
    print("\n2. 在AutoDL中运行训练：")
    print("   llamafactory-cli train config/train_closed_loop_lora.yaml")
    print("\n3. 预计训练时间：20-30分钟")
    print("4. 预计成本：¥1-1.5")
    
else:
    print("\n" + "=" * 70)
    print("⚠️  数据尚未完全准备好")
    print("=" * 70)
    print("\n请按以下步骤操作：")
    print("\n1. 创建基础框架数据文件：")
    print("   文件路径: data/sft/base_framework_300.jsonl")
    print("   预期条数: 300条")
    print("   内容说明: 系统角色、方法论、情感支持、世界知识、伦理边界")
    print("\n2. 创建闭环进化数据文件：")
    print("   文件路径: data/sft/closed_loop_system_complete.jsonl")
    print("   预期条数: 255条")
    print("   内容说明: 元认知、问题拆解、工具调用、评估反思、自我进化")
    print("\n3. 数据格式示例：")
    print('   {"instruction": "问题内容", "input": "", "output": "回答内容"}')
    print("\n4. 准备完成后，重新运行此脚本。")
    print("\n💡 提示：")
    print("   - 你之前提供的300条基础框架数据需要保存为JSONL格式")
    print("   - 你之前提供的255条闭环进化数据需要保存为JSONL格式")
    print("   - 如果数据已经准备好，请确保文件名和路径正确")