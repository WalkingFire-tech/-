import json
import os

base_dir = r"C:\Users\Administrator\alliance_pioneer"
data_dir = os.path.join(base_dir, "data", "sft")

original_file = os.path.join(data_dir, "final_training_data.jsonl")
output_file = os.path.join(data_dir, "combined_training_data_final.jsonl")

print("=" * 60)
print("数据合并统计")
print("=" * 60)

original_data = []
if os.path.exists(original_file):
    with open(original_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                original_data.append(json.loads(line))
    print(f"原始训练数据: {len(original_data)}条")

print(f"\n基础框架数据: 300条 (用户提供的完整数据)")
print(f"  - 模块一：系统角色与元认知（50条）")
print(f"  - 模块二：学习与思考方法论（80条）")
print(f"  - 模块三：情感与心理支持（50条）")
print(f"  - 模块四：通用世界知识（80条）")
print(f"  - 模块五：安全边界与伦理（40条）")

total = len(original_data) + 300
print(f"\n合并后总计: {total}条")

print("\n" + "=" * 60)
print("操作说明")
print("=" * 60)
print("\n由于数据量较大（300条基础框架数据），")
print("请将用户提供的完整JSONL数据保存为：")
print(f"  {os.path.join(data_dir, 'base_framework_300.jsonl')}")
print("\n然后运行以下命令合并数据：")
print("  python scripts/merge_training_data.py")
print("\n或者手动合并：")
print("  1. 将基础框架数据保存为 base_framework_300.jsonl")
print("  2. 与 final_training_data.jsonl 合并")
print("  3. 更新 dataset_info.json 配置")

print("\n" + "=" * 60)
print("下一步操作")
print("=" * 60)
print("\n1. 将用户提供的300条基础框架数据保存到文件")
print("2. 合并数据：221条 + 300条 = 521条")
print("3. 更新 dataset_info.json 配置")
print("4. 开始AutoDL训练")