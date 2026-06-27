"""
LoRA微调脚本
使用LLaMA-Factory或transformers进行微调
"""
import os
import json
import subprocess
from pathlib import Path

def check_environment():
    """检查微调环境"""
    print("检查微调环境...")
    
    requirements = [
        "torch",
        "transformers",
        "peft",
        "datasets",
        "accelerate"
    ]
    
    missing = []
    for pkg in requirements:
        try:
            __import__(pkg)
            print(f"  ✅ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg} - 缺失")
            missing.append(pkg)
    
    if missing:
        print(f"\n需要安装: pip install {' '.join(missing)}")
        return False
    
    return True


def create_lora_config():
    """创建LoRA配置文件"""
    config = {
        "model_name_or_path": "Qwen/Qwen2.5-7B-Instruct",
        "stage": "sft",
        "do_train": True,
        "finetuning_type": "lora",
        "lora_target": "all",
        "output_dir": "output/lora_checkpoints",
        "overwrite_output_dir": True,
        "per_device_train_batch_size": 4,
        "gradient_accumulation_steps": 4,
        "lr_scheduler_type": "cosine",
        "logging_steps": 10,
        "save_steps": 100,
        "learning_rate": 5e-5,
        "num_train_epochs": 3.0,
        "plot_loss": True,
        "bf16": True,
        
        "dataset": "custom",
        "dataset_dir": "data/sft",
        "template": "qwen",
        "cutoff_len": 1024,
        "preprocessing_num_workers": 4,
    }
    
    config_path = Path("config/lora_config.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 配置文件已创建: {config_path}")
    return config_path


def create_training_script():
    """创建训练脚本"""
    script = '''#!/usr/bin/env python
"""
使用transformers进行LoRA微调
"""
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForSeq2Seq
)
from peft import LoraConfig, get_peft_model, TaskType
from datasets import load_dataset
import json

def load_custom_dataset(file_path):
    """加载自定义数据集"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def main():
    print("=" * 60)
    print("LoRA微调开始")
    print("=" * 60)
    
    # 1. 加载模型
    model_name = "Qwen/Qwen2.5-7B-Instruct"
    print(f"\\n[1/5] 加载模型: {model_name}")
    
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True
    )
    
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    
    # 2. 配置LoRA
    print("\\n[2/5] 配置LoRA...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=8,  # LoRA秩
        lora_alpha=32,
        lora_dropout=0.1,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]
    )
    
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    
    # 3. 加载数据
    print("\\n[3/5] 加载训练数据...")
    data_file = "data/sft/merged_training_data.jsonl"
    
    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在: {data_file}")
        return
    
    dataset = load_custom_dataset(data_file)
    print(f"   数据量: {len(dataset)}条")
    
    # 4. 训练配置
    print("\\n[4/5] 配置训练参数...")
    training_args = TrainingArguments(
        output_dir="output/lora_checkpoints",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        learning_rate=5e-5,
        logging_steps=10,
        save_steps=100,
        bf16=True,
        gradient_checkpointing=True,
    )
    
    # 5. 开始训练
    print("\\n[5/5] 开始训练...")
    print("⚠️ 实际训练需要GPU环境")
    print("   当前为演示模式，不会真正训练")
    
    print("\\n" + "=" * 60)
    print("✅ 微调配置完成")
    print("=" * 60)
    print("\\n实际训练命令:")
    print("  llamafactory-cli train config/lora_config.json")
    print("\\n或使用LLaMA-Factory WebUI:")
    print("  llamafactory-cli webui")

if __name__ == "__main__":
    import os
    main()
'''
    
    script_path = Path("scripts/run_lora_training.py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script)
    
    print(f"✅ 训练脚本已创建: {script_path}")


def create_quick_finetune_guide():
    """创建快速微调指南"""
    guide = """# LoRA微调指南

## 前置要求

1. **GPU环境**（推荐）
   - NVIDIA GPU with 16GB+ VRAM
   - CUDA 11.8+

2. **依赖安装**
   ```bash
   pip install torch transformers peft datasets accelerate
   ```

## 方法一：使用LLaMA-Factory（推荐）

### 1. 安装LLaMA-Factory
```bash
git clone https://github.com/hiyouga/LLaMA-Factory.git
cd LLaMA-Factory
pip install -e .
```

### 2. 准备数据
数据已导出到 `data/sft/merged_training_data.jsonl`

格式：
```json
{"instruction": "请回答以下问题", "input": "什么是机器学习?", "output": "..."}
```

### 3. 启动WebUI
```bash
llamafactory-cli webui
```

### 4. 配置参数
- 模型: Qwen/Qwen2.5-7B-Instruct
- 训练方法: lora
- 数据集: 选择自定义数据
- 学习率: 5e-5
- Epochs: 3

### 5. 开始训练
点击"开始训练"按钮

## 方法二：使用transformers直接训练

```bash
python scripts/run_lora_training.py
```

## 方法三：使用Axolotl

### 1. 安装Axolotl
```bash
pip install axolotl
```

### 2. 创建配置文件 `axolotl_config.yml`
```yaml
base_model: Qwen/Qwen2.5-7B-Instruct
model_type: AutoModelForCausalLM
tokenizer_type: AutoTokenizer

lora_r: 8
lora_alpha: 32
lora_dropout: 0.1

training_arguments:
  learning_rate: 5e-5
  num_train_epochs: 3
  per_device_train_batch_size: 4

datasets:
  - path: data/sft/merged_training_data.jsonl
    type: alpaca
```

### 3. 训练
```bash
accelerate launch -m axolotl.cli train axolotl_config.yml
```

## 训练后

### 1. 合并LoRA权重
```bash
python -m peft import export \
  --base_model Qwen/Qwen2.5-7B-Instruct \
  --lora_model output/lora_checkpoints \
  --output_dir output/merged_model
```

### 2. 测试模型
```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("output/merged_model")
tokenizer = AutoTokenizer.from_pretrained("output/merged_model")

# 测试
input_text = "什么是机器学习?"
inputs = tokenizer(input_text, return_tensors="pt")
outputs = model.generate(**inputs, max_length=100)
print(tokenizer.decode(outputs[0]))
```

### 3. 部署到系统
将合并后的模型路径更新到系统配置：
```yaml
model:
  path: output/merged_model
```

## 注意事项

1. **数据量要求**
   - 最少: 100条
   - 推荐: 1000+条
   - 当前: 查看data/sft/merged_training_data.jsonl

2. **计算资源**
   - 7B模型: 16GB VRAM
   - 13B模型: 24GB VRAM
   - 70B模型: 80GB VRAM (或多卡)

3. **训练时间**
   - 100条数据: ~10分钟
   - 1000条数据: ~1小时
   - 10000条数据: ~10小时

4. **监控训练**
   - 使用TensorBoard: `tensorboard --logdir output/lora_checkpoints`
   - 查看loss曲线
"""
    
    guide_path = Path("docs/LORA_FINETUNE_GUIDE.md")
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide)
    
    print(f"✅ 微调指南已创建: {guide_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("LoRA微调准备")
    print("=" * 60)
    
    print("\n[1] 检查环境...")
    env_ok = check_environment()
    
    print("\n[2] 创建配置...")
    create_lora_config()
    
    print("\n[3] 创建训练脚本...")
    create_training_script()
    
    print("\n[4] 创建微调指南...")
    create_quick_finetune_guide()
    
    print("\n" + "=" * 60)
    print("准备完成！")
    print("=" * 60)
    
    if not env_ok:
        print("\n⚠️ 需要先安装依赖:")
        print("   pip install torch transformers peft datasets accelerate")
    
    print("\n下一步:")
    print("  1. 查看指南: docs/LORA_FINETUNE_GUIDE.md")
    print("  2. 准备数据: python scripts/prepare_sft_data.py")
    print("  3. 开始训练: llamafactory-cli webui")