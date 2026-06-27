"""
混合多源训练数据
"""
import json
from pathlib import Path
from typing import List, Dict
import random

def load_jsonl(file_path: str) -> List[Dict]:
    """加载JSONL文件"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def mix_datasets(
    sources: Dict[str, float],
    output_file: str,
    shuffle: bool = True,
    seed: int = 42
):
    """
    混合多个数据集
    
    Args:
        sources: 数据源路径和比例，如 {'data/a.jsonl': 0.5, 'data/b.jsonl': 0.5}
        output_file: 输出文件路径
        shuffle: 是否打乱顺序
        seed: 随机种子
    """
    random.seed(seed)
    
    all_data = []
    
    for file_path, ratio in sources.items():
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️ 文件不存在: {file_path}")
            continue
        
        data = load_jsonl(file_path)
        sample_size = int(len(data) * ratio)
        sampled = random.sample(data, min(sample_size, len(data)))
        
        all_data.extend(sampled)
        print(f"  {path.name}: {len(sampled)}/{len(data)}条 (比例{ratio})")
    
    if shuffle:
        random.shuffle(all_data)
    
    # 保存
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"\n✅ 混合完成: {output_path}")
    print(f"   总计: {len(all_data)}条")
    
    return len(all_data)


def create_mixed_dataset():
    """创建混合数据集"""
    print("=" * 60)
    print("混合多源训练数据")
    print("=" * 60)
    
    # 数据源配置
    sources = {
        # 专属知识（优先级高）
        'data/sft/merged_training_data.jsonl': 1.0,  # 全部使用
        'data/generated/generated_training_data.jsonl': 1.0,  # 全部使用
        
        # 自定义高质量数据
        'data/custom/metacognition_qa.jsonl': 1.0,  # 元认知数据
        'data/custom/key_technical_domains_qa.jsonl': 1.0,  # 关键技术领域数据
        'data/custom/interaction_scenarios_qa.jsonl': 1.0,  # 交互场景数据
        'data/custom/ethics_boundaries_qa.jsonl': 1.0,  # 伦理与边界数据
        'data/custom/self_reflection_qa.jsonl': 1.0,  # 自我反思数据
        'data/custom/communication_framework_qa.jsonl': 1.0,  # 对话沟通框架数据
        'data/custom/cognitive_bias_qa.jsonl': 1.0,  # 认知偏差数据
        'data/custom/systems_thinking_qa.jsonl': 1.0,  # 系统思维数据
        'data/custom/logic_science_method_qa.jsonl': 1.0,  # 基础逻辑与科学方法数据
        'data/custom/creative_expression_qa.jsonl': 1.0,  # 实用创造与表达框架数据
        'data/custom/learning_methods_qa.jsonl': 1.0,  # 学习方法数据（费曼技巧、MECE）
        
        # 外部数据集（按比例采样）
        'data/external/alpaca_zh_sample.jsonl': 0.8,  # 使用80%
        'data/external/coig_cqia_sample.jsonl': 0.8,
        'data/external/sharegpt_sample.jsonl': 0.8,
    }
    
    print("\n数据源配置:")
    for source, ratio in sources.items():
        path = Path(source)
        if path.exists():
            data = load_jsonl(source)
            print(f"  ✅ {path.name}: {len(data)}条 × {ratio}")
        else:
            print(f"  ⚠️ {path.name}: 不存在")
    
    print("\n开始混合...")
    count = mix_datasets(
        sources=sources,
        output_file='data/sft/final_training_data.jsonl',
        shuffle=True,
        seed=42
    )
    
    return count


def analyze_dataset(file_path: str):
    """分析数据集"""
    data = load_jsonl(file_path)
    
    print(f"\n📊 数据集分析: {Path(file_path).name}")
    print("=" * 60)
    print(f"总数量: {len(data)}条")
    
    # 统计instruction长度
    inst_lengths = [len(item.get('instruction', '')) for item in data]
    print(f"Instruction长度: 平均{sum(inst_lengths)/len(inst_lengths):.1f}字符")
    
    # 统计output长度
    out_lengths = [len(item.get('output', '')) for item in data]
    print(f"Output长度: 平均{sum(out_lengths)/len(out_lengths):.1f}字符")
    
    # 检查是否有input
    with_input = sum(1 for item in data if item.get('input'))
    print(f"包含Input: {with_input}/{len(data)}条")
    
    # 检查来源
    sources = {}
    for item in data:
        src = item.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1
    
    if len(sources) > 1:
        print(f"数据来源: {sources}")


if __name__ == "__main__":
    # 先下载外部数据
    print("准备外部数据...")
    import subprocess
    subprocess.run(['python', 'scripts/download_datasets.py'], check=False)
    
    # 生成基于知识库的数据
    print("\n生成知识库数据...")
    subprocess.run(['python', 'scripts/generate_training_data.py'], check=False)
    
    # 混合数据集
    count = create_mixed_dataset()
    
    # 分析最终数据集
    analyze_dataset('data/sft/final_training_data.jsonl')
    
    print("\n" + "=" * 60)
    print("✅ 训练数据准备完成！")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 查看数据: data/sft/final_training_data.jsonl")
    print("  2. 开始训练: llamafactory-cli webui")
    print("  3. 或直接训练: python scripts/run_lora_training.py")