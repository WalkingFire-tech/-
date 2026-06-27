"""
LoRA模型集成脚本
将训练好的LoRA权重集成到联盟拓荒者主系统
"""
import os
import json
from pathlib import Path

class LoRAIntegrator:
    def __init__(self):
        self.project_root = Path(r"C:\Users\Administrator\alliance_pioneer")
        self.lora_path = self.project_root / "models" / "closed_loop_lora"
        self.config_path = self.project_root / "config"
        
    def verify_lora_files(self):
        """验证LoRA文件完整性"""
        required_files = [
            "adapter_config.json",
            "adapter_model.safetensors"
        ]
        
        print("=== 验证LoRA文件 ===")
        for file in required_files:
            path = self.lora_path / file
            if path.exists():
                size = path.stat().st_size / 1024 / 1024
                print(f"✓ {file}: {size:.2f} MB")
            else:
                print(f"✗ {file}: 不存在")
                return False
        
        # 读取adapter_config
        with open(self.lora_path / "adapter_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"\nLoRA配置:")
        print(f"  - rank: {config['r']}")
        print(f"  - alpha: {config['lora_alpha']}")
        print(f"  - dropout: {config['lora_dropout']}")
        print(f"  - target_modules: {config['target_modules']}")
        
        return True
    
    def create_model_config(self):
        """创建模型配置文件"""
        config = {
            "base_model": "Qwen/Qwen2.5-7B-Instruct",
            "lora_path": str(self.lora_path),
            "adapter_config": str(self.lora_path / "adapter_config.json"),
            "adapter_weights": str(self.lora_path / "adapter_model.safetensors"),
            "training_info": {
                "training_data": "727 samples",
                "epochs": 3,
                "loss": 1.8123,
                "eval_loss": 1.6767
            }
        }
        
        config_file = self.config_path / "lora_model_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ 模型配置已创建: {config_file}")
        return config_file
    
    def create_inference_script(self):
        """创建推理脚本"""
        script = '''"""
使用LoRA微调模型进行推理
"""
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

class LoRAInference:
    def __init__(self):
        # 加载基础模型
        self.base_model_path = "Qwen/Qwen2.5-7B-Instruct"
        self.lora_path = r"C:\\Users\\Administrator\\alliance_pioneer\\models\\closed_loop_lora"
        
        print("加载基础模型...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.base_model_path,
            torch_dtype=torch.bfloat16,
            device_map="auto"
        )
        
        print("加载LoRA权重...")
        self.model = PeftModel.from_pretrained(self.model, self.lora_path)
        self.model.eval()
        print("模型加载完成!")
    
    def generate(self, prompt, max_length=512):
        """生成回复"""
        messages = [
            {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
        
        text = self.tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_length,
                temperature=0.7,
                top_p=0.8,
                do_sample=True
            )
        
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], 
            skip_special_tokens=True
        )
        
        return response

if __name__ == "__main__":
    # 测试推理
    inference = LoRAInference()
    
    test_prompts = [
        "当你从外部模型获取了一段代码后，你会如何验证它的正确性？",
        "如何系统地识别出自己所在岗位需要掌握的关键技术领域？",
        "什么是深度学习的特点？"
    ]
    
    for prompt in test_prompts:
        print(f"\\n问题: {prompt}")
        print(f"回答: {inference.generate(prompt)}")
'''
        
        script_path = self.project_root / "scripts" / "lora_inference.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script)
        
        print(f"✓ 推理脚本已创建: {script_path}")
        return script_path
    
    def integrate(self):
        """执行集成"""
        print("=" * 60)
        print("LoRA模型集成")
        print("=" * 60)
        
        # 1. 验证文件
        if not self.verify_lora_files():
            print("\n✗ LoRA文件验证失败")
            return False
        
        # 2. 创建配置
        self.create_model_config()
        
        # 3. 创建推理脚本
        self.create_inference_script()
        
        print("\n" + "=" * 60)
        print("✓ 集成完成!")
        print("=" * 60)
        print("\n使用方法:")
        print("1. 运行推理脚本测试模型:")
        print("   python scripts/lora_inference.py")
        print("\n2. 在代码中使用:")
        print("   from scripts.lora_inference import LoRAInference")
        print("   inference = LoRAInference()")
        print("   response = inference.generate('你的问题')")
        
        return True

if __name__ == "__main__":
    integrator = LoRAIntegrator()
    integrator.integrate()