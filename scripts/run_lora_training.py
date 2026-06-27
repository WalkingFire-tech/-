#!/usr/bin/env python
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
    print(f"\n[1/5] 加载模型: {model_name}")
    
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
    print("\n[2/5] 配置LoRA...")
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
    print("\n[3/5] 加载训练数据...")
    data_file = "data/sft/merged_training_data.jsonl"
    
    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在: {data_file}")
        return
    
    dataset = load_custom_dataset(data_file)
    print(f"   数据量: {len(dataset)}条")
    
    # 4. 训练配置
    print("\n[4/5] 配置训练参数...")
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
    print("\n[5/5] 开始训练...")
    print("⚠️ 实际训练需要GPU环境")
    print("   当前为演示模式，不会真正训练")
    
    print("\n" + "=" * 60)
    print("✅ 微调配置完成")
    print("=" * 60)
    print("\n实际训练命令:")
    print("  llamafactory-cli train config/lora_config.json")
    print("\n或使用LLaMA-Factory WebUI:")
    print("  llamafactory-cli webui")

if __name__ == "__main__":
    import os
    main()
