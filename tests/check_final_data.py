import json
from pathlib import Path

data_file = Path('data/sft/final_training_data.jsonl')
data = [json.loads(line) for line in open(data_file, 'r', encoding='utf-8') if line.strip()]

print("=" * 60)
print("最终训练数据统计")
print("=" * 60)
print(f"总数据量: {len(data)}条")
print(f"平均Instruction长度: {sum(len(d['instruction']) for d in data)/len(data):.1f}字符")
print(f"平均Output长度: {sum(len(d['output']) for d in data)/len(data):.1f}字符")
print(f"包含Input: {sum(1 for d in data if d.get('input'))}/{len(data)}条")

# 查看最后5条（新增的元认知数据）
print("\n最后5条数据预览:")
for i, item in enumerate(data[-5:], 1):
    print(f"\n[{i}] {item['instruction'][:50]}...")
    print(f"    输出长度: {len(item['output'])}字符")