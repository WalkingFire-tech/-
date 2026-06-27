# 闭环进化系统 - AutoDL训练完整指南

## ✅ 数据准备完成

### 数据统计
| 数据源 | 条数 | 状态 |
|--------|------|------|
| 原始训练数据 | 221条 | ✅ |
| 基础框架数据 | 253条 | ✅ |
| 闭环进化数据 | 253条 | ✅ |
| **总计** | **727条** | ✅ |

### 数据质量
- 有效数据：727条（100%）
- 平均问题长度：25.1字符
- 平均回答长度：220.6字符
- 数据格式：JSONL（ShareGPT格式）

---

## 🚀 AutoDL训练步骤

### 步骤1：租用GPU实例

访问 [AutoDL](https://www.autodl.com/)，选择：
- **镜像**：PyTorch 2.0 + Python 3.10
- **GPU**：RTX 5090 / 32GB
- **价格**：¥2.78/小时
- **数据盘**：勾选（用于保存模型）

### 步骤2：连接实例

使用JupyterLab或SSH连接到实例。

### 步骤3：安装依赖

```bash
# 安装LLaMA Factory
pip install llamafactory peft datasets accelerate transformers

# 验证GPU
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}'); print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')"
```

预期输出：
```
GPU: NVIDIA GeForce RTX 5090
VRAM: 32.0GB
```

### 步骤4：上传文件

在JupyterLab中，上传以下文件：

```
📁 项目结构
├── data/
│   ├── sft/
│   │   └── combined_all_training_data.jsonl  (727条)
│   └── dataset_info.json
└── config/
    └── train_closed_loop_lora.yaml
```

### 步骤5：开始训练

```bash
# 方法1：使用CLI
llamafactory-cli train config/train_closed_loop_lora.yaml

# 方法2：使用Python API
python << EOF
from llamafactory.train.tuner import run_exp

args = dict(
    stage="sft",
    do_train=True,
    model_name_or_path="Qwen/Qwen2.5-7B-Instruct",
    dataset="combined_all",
    template="qwen",
    finetuning_type="lora",
    lora_target="all",
    output_dir="output/closed_loop_lora",
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=3e-5,
    num_train_epochs=3.0,
    bf16=True,
)
run_exp(args)
EOF
```

### 步骤6：监控训练

训练过程中会显示：
```
Step  Training Loss  Validation Loss
10    2.345         2.456
20    1.987         2.123
30    1.654         1.876
...
```

预计训练时间：**20-30分钟**

### 步骤7：验证模型

训练完成后，测试模型：

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# 加载模型
base_model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen2.5-7B-Instruct",
    device_map="auto",
    torch_dtype="auto"
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")

# 加载LoRA权重
model = PeftModel.from_pretrained(base_model, "output/closed_loop_lora")

# 测试问题
test_questions = [
    "收到问题后，你应该先做什么？",
    "如何拆解一个复杂问题？",
    "当用户表达沮丧时，你该如何回应？",
]

for q in test_questions:
    inputs = tokenizer(q, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=512)
    print(f"Q: {q}")
    print(f"A: {tokenizer.decode(outputs[0], skip_special_tokens=True)}")
    print("-" * 60)
```

### 步骤8：导出模型

合并LoRA权重到基础模型：

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# 加载并合并
base_model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-7B-Instruct")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-7B-Instruct")

model = PeftModel.from_pretrained(base_model, "output/closed_loop_lora")
merged_model = model.merge_and_unload()

# 保存
merged_model.save_pretrained("output/closed_loop_merged")
tokenizer.save_pretrained("output/closed_loop_merged")
```

### 步骤9：下载模型

打包并下载：
```bash
# 打包
tar -czf closed_loop_model.tar.gz output/closed_loop_merged/

# 通过AutoDL文件管理器下载
```

---

## 📊 训练配置详情

| 参数 | 值 | 说明 |
|------|-----|------|
| 模型 | Qwen2.5-7B-Instruct | 基础模型 |
| 方法 | LoRA | 参数高效微调 |
| LoRA Rank | 8 | 低秩矩阵维度 |
| Learning Rate | 3e-5 | 学习率 |
| Batch Size | 4 | 每GPU批次大小 |
| Gradient Accumulation | 4 | 梯度累积步数 |
| Epochs | 3 | 训练轮数 |
| BF16 | True | 混合精度训练 |
| Max Length | 2048 | 最大序列长度 |

---

## 💰 成本估算

| 项目 | 数值 |
|------|------|
| GPU价格 | ¥2.78/小时 |
| 预计时间 | 20-30分钟 |
| **预计成本** | **¥1-1.5** |

---

## 🔗 集成到联盟拓荒者

训练完成后，将模型集成到主系统：

### 1. 下载模型到本地

```
C:\Users\Administrator\alliance_pioneer\models\closed_loop_lora\
```

### 2. 更新主系统配置

```yaml
# config/model_config.yaml
model:
  name: "closed_loop_evolution"
  path: "models/closed_loop_lora"
  base_model: "Qwen/Qwen2.5-7B-Instruct"
  type: "lora"
```

### 3. 在主系统中加载

```python
# main_integrated.py
from core.closed_loop_module import ClosedLoopIntegrator

class AlliancePioneer:
    def __init__(self):
        # ... 现有初始化 ...
        self.closed_loop = ClosedLoopIntegrator(self)
    
    def process_with_evolution(self, question: str):
        """使用闭环进化处理问题"""
        result = self.closed_loop.process_with_loop(question)
        return result['answer']
```

### 4. 启动测试

```bash
python main_integrated.py
```

---

## 🎯 训练后系统能力

训练完成后，系统将具备：

1. ✅ **元认知能力** - 自动自我提问、识别问题类型
2. ✅ **问题拆解能力** - MECE原则、依赖图、任务调度
3. ✅ **工具调用能力** - 自动生成并执行Python脚本
4. ✅ **反思优化能力** - 评估结果、调整策略、迭代改进
5. ✅ **知识固化能力** - 从成功案例中提取知识
6. ✅ **工具生成能力** - 将解决方案转化为可复用工具
7. ✅ **自我进化能力** - 积累数据、触发微调、持续改进

---

## 📞 问题排查

### 问题1：CUDA内存不足
**解决方案**：减小batch_size或使用梯度检查点
```yaml
per_device_train_batch_size: 2
gradient_checkpointing: true
```

### 问题2：训练速度慢
**解决方案**：增加数据加载线程数
```yaml
preprocessing_num_workers: 16
dataloader_num_workers: 4
```

### 问题3：模型效果不好
**解决方案**：
1. 检查数据质量
2. 增加训练轮数
3. 调整学习率
```yaml
num_train_epochs: 5.0
learning_rate: 5.0e-5
```

---

## 🎉 完成

恭喜！你现在拥有一个具备完整元认知闭环进化能力的AI系统！

**下一步**：开始训练，见证系统的自我进化！