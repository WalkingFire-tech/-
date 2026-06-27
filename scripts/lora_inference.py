"""
使用LoRA微调模型进行推理
"""
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

class LoRAInference:
    def __init__(self):
        # 加载基础模型
        self.base_model_path = "Qwen/Qwen2.5-7B-Instruct"
        self.lora_path = r"C:\Users\Administrator\alliance_pioneer\models\closed_loop_lora"
        
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
        print(f"\n问题: {prompt}")
        print(f"回答: {inference.generate(prompt)}")
