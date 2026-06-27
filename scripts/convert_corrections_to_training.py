"""
将纠错数据转换为训练数据格式并合并到训练集
"""
import json
from pathlib import Path
from datetime import datetime

def convert_corrections_to_training_data(corrections_file, output_file, training_file):
    """
    将纠错数据转换为Alpaca格式并合并到训练数据集
    """
    # 读取纠错数据
    with open(corrections_file, 'r', encoding='utf-8') as f:
        corrections_data = json.load(f)
    
    # 转换为训练格式
    new_training_data = []
    for correction in corrections_data['corrections']:
        training_item = {
            "instruction": correction['question'],
            "input": "",
            "output": correction['correct_answer'],
            "source": "user_correction",
            "category": correction.get('category', 'general'),
            "date": corrections_data['correction_session']
        }
        new_training_data.append(training_item)
    
    # 读取现有训练数据
    existing_data = []
    with open(training_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                existing_data.append(json.loads(line))
    
    # 合并数据
    all_data = existing_data + new_training_data
    
    # 写入合并后的数据
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    # 统计信息
    print(f"✅ 转换完成！")
    print(f"   - 纠错数据: {len(new_training_data)} 条")
    print(f"   - 原有数据: {len(existing_data)} 条")
    print(f"   - 合并后总计: {len(all_data)} 条")
    print(f"   - 输出文件: {output_file}")
    
    # 按类别统计
    categories = {}
    for item in new_training_data:
        cat = item.get('category', 'general')
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\n📊 新增数据类别分布:")
    for cat, count in categories.items():
        print(f"   - {cat}: {count} 条")
    
    return len(all_data)

if __name__ == "__main__":
    base_dir = Path(__file__).parent.parent
    
    corrections_file = base_dir / "data" / "corrections" / "correction_2026-06-27.json"
    training_file = base_dir / "data" / "sft" / "combined_all_training_data.jsonl"
    output_file = base_dir / "data" / "sft" / "combined_all_training_data_v2.jsonl"
    
    total = convert_corrections_to_training_data(corrections_file, output_file, training_file)
    
    print(f"\n🎯 下一步：当数据达到1000条时，可以启动第二轮LoRA微调")
    print(f"   当前进度: {total}/1000 ({total/10:.1f}%)")