# LoRA微调指南

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
python -m peft import export   --base_model Qwen/Qwen2.5-7B-Instruct   --lora_model output/lora_checkpoints   --output_dir output/merged_model
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
