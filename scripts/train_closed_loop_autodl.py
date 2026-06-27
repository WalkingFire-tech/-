"""
### 闭环进化系统训练配置
### AutoDL训练脚本

训练目标：
- 基础框架数据：300条（人格、方法论、情感、知识、伦理）
- 闭环进化数据：255条（元认知、拆解、工具、评估、进化）
- 总计：555条高质量训练数据

训练配置：
- 模型：Qwen2.5-7B-Instruct
- 方法：LoRA微调
- GPU：RTX 5090 / 32GB
- 价格：¥2.78/小时
- 预计时间：20-30分钟
- 预计成本：¥1-1.5
"""

# ============================================================
# 1. AutoDL环境准备
# ============================================================

"""
在AutoDL JupyterLab中执行以下命令：

# 安装依赖
pip install llamafactory peft datasets accelerate transformers torch

# 验证GPU
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0)}'); print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB')"

# 预期输出：
# GPU: NVIDIA GeForce RTX 5090
# VRAM: 32.0GB
"""

# ============================================================
# 2. 数据准备
# ============================================================

"""
上传文件到AutoDL：

1. 上传训练数据：
   - data/sft/final_training_data.jsonl (221条)
   - data/sft/base_framework_300.jsonl (300条) - 需要你提供
   - data/sft/closed_loop_system_complete.jsonl (255条) - 需要你提供

2. 上传配置文件：
   - data/dataset_info.json
   - config/train_closed_loop_lora.yaml

3. 合并数据：
   cat data/sft/final_training_data.jsonl data/sft/base_framework_300.jsonl data/sft/closed_loop_system_complete.jsonl > data/sft/combined_all_training_data.jsonl
   
4. 验证数据：
   wc -l data/sft/combined_all_training_data.jsonl
   # 预期输出：776 (221 + 300 + 255)
"""

# ============================================================
# 3. LoRA训练配置
# ============================================================

TRAINING_CONFIG = """
### model
model_name_or_path: Qwen/Qwen2.5-7B-Instruct

### method
stage: sft
do_train: true
finetuning_type: lora
lora_target: all

### dataset
dataset: combined_all
template: qwen
cutoff_len: 2048
overwrite_cache: true
preprocessing_num_workers: 16

### output
output_dir: output/closed_loop_lora
logging_steps: 10
save_steps: 100
plot_loss: true
overwrite_output_dir: true

### train
per_device_train_batch_size: 4
gradient_accumulation_steps: 4
learning_rate: 3.0e-5
num_train_epochs: 3.0
lr_scheduler_type: cosine
warmup_ratio: 0.1
bf16: true

### eval
val_size: 0.1
per_device_eval_batch_size: 4
eval_strategy: steps
eval_steps: 100
"""

# ============================================================
# 4. 训练命令
# ============================================================

"""
开始训练：

# 方法1：使用LLaMA Factory CLI
llamafactory-cli train config/train_closed_loop_lora.yaml

# 方法2：使用Python API
from llamafactory.train.tuner import run_exp

args = {
    "stage": "sft",
    "do_train": True,
    "model_name_or_path": "Qwen/Qwen2.5-7B-Instruct",
    "dataset": "combined_all",
    "template": "qwen",
    "finetuning_type": "lora",
    "lora_target": "all",
    "output_dir": "output/closed_loop_lora",
    "per_device_train_batch_size": 4,
    "gradient_accumulation_steps": 4,
    "learning_rate": 3e-5,
    "num_train_epochs": 3.0,
    "bf16": True,
}
run_exp(args)

# 预计训练时间：20-30分钟
# 预计成本：¥1-1.5
"""

# ============================================================
# 5. 训练后验证
# ============================================================

"""
验证训练效果：

# 测试命令
python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# 加载基础模型
base_model = AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-7B-Instruct', device_map='auto')
tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen2.5-7B-Instruct')

# 加载LoRA权重
model = PeftModel.from_pretrained(base_model, 'output/closed_loop_lora')

# 测试问题
test_questions = [
    '收到问题后，你应该先做什么？',
    '如何拆解一个复杂问题？',
    '当用户表达沮丧时，你该如何回应？',
]

for q in test_questions:
    inputs = tokenizer(q, return_tensors='pt').to('cuda')
    outputs = model.generate(**inputs, max_length=512)
    print(f'Q: {q}')
    print(f'A: {tokenizer.decode(outputs[0], skip_special_tokens=True)}')
    print('-' * 60)
]
"

# 预期效果：
# 1. 能够正确启动元认知循环
# 2. 能够合理拆解复杂问题
# 3. 能够提供情感支持
# 4. 能够调用工具执行任务
# 5. 能够进行自我反思
"""

# ============================================================
# 6. 模型导出与下载
# ============================================================

"""
导出完整模型：

# 合并LoRA权重到基础模型
python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

base_model = AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-7B-Instruct')
tokenizer = AutoTokenizer.from_pretrained('Qwen/Qwen2.5-7B-Instruct')

model = PeftModel.from_pretrained(base_model, 'output/closed_loop_lora')
merged_model = model.merge_and_unload()

merged_model.save_pretrained('output/closed_loop_merged')
tokenizer.save_pretrained('output/closed_loop_merged')
"

# 打包下载
tar -czf closed_loop_model.tar.gz output/closed_loop_merged/

# 下载到本地（使用AutoDL的文件管理器或scp）
"""

# ============================================================
# 7. 集成到联盟拓荒者系统
# ============================================================

"""
将训练好的模型集成到主系统：

1. 下载模型到本地：
   C:\\Users\\Administrator\\alliance_pioneer\\models\\closed_loop_lora\\

2. 更新主系统配置：
   config/model_config.yaml:
   ```yaml
   model:
     name: "closed_loop_evolution"
     path: "models/closed_loop_lora"
     base_model: "Qwen/Qwen2.5-7B-Instruct"
     type: "lora"
   ```

3. 在主系统中加载：
   ```python
   from core.closed_loop_module import ClosedLoopIntegrator
   
   class AlliancePioneer:
       def __init__(self):
           self.closed_loop = ClosedLoopIntegrator(self)
       
       def process(self, question):
           return self.closed_loop.process_with_loop(question)
   ```

4. 启动系统测试：
   python main_integrated.py
"""

# ============================================================
# 8. 持续进化机制
# ============================================================

"""
闭环进化系统的持续改进：

1. 数据积累：
   - 每次对话后，自动收集高质量的问答对
   - 存储到 data/evolution/new_training_data.jsonl

2. 定期微调：
   - 当新数据积累到100条以上
   - 自动触发LoRA微调
   - 合并新权重到主模型

3. 知识固化：
   - 从成功案例中提取知识条目
   - 存入知识库 data/closed_loop/knowledge.json

4. 工具生成：
   - 从可复用的解决方案生成工具脚本
   - 存入工具库 data/closed_loop/tools.json

5. 自我评估：
   - 定期评估模型性能
   - 识别能力缺口
   - 触发针对性学习
"""

if __name__ == "__main__":
    print("=" * 60)
    print("闭环进化系统训练指南")
    print("=" * 60)
    print("\n1. 数据准备：776条高质量训练数据")
    print("   - 基础框架：300条")
    print("   - 闭环进化：255条")
    print("   - 原始数据：221条")
    print("\n2. 训练配置：")
    print("   - 模型：Qwen2.5-7B-Instruct")
    print("   - 方法：LoRA微调")
    print("   - GPU：RTX 5090 / 32GB")
    print("   - 预计时间：20-30分钟")
    print("   - 预计成本：¥1-1.5")
    print("\n3. 训练步骤：")
    print("   a. 上传数据和配置文件到AutoDL")
    print("   b. 运行训练命令")
    print("   c. 验证训练效果")
    print("   d. 导出并下载模型")
    print("   e. 集成到主系统")
    print("\n4. 持续进化：")
    print("   - 数据积累 → 定期微调 → 知识固化 → 工具生成")
    print("=" * 60)