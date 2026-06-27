"""
LoRA推理引擎 - 加载并使用训练好的闭环能力
"""
import torch
from pathlib import Path
from loguru import logger
from typing import Optional, Dict, Any

class LoRAInferenceEngine:
    """LoRA推理引擎 - 激活训练好的闭环能力"""
    
    def __init__(self, base_model: str = "Qwen/Qwen2.5-7B-Instruct"):
        self.base_model = base_model
        self.model = None
        self.tokenizer = None
        self.lora_path = Path("models/closed_loop_lora")
        self.is_loaded = False
        
    def load(self):
        """加载带LoRA的模型"""
        if self.is_loaded:
            return True
            
        try:
            logger.info("🔄 加载LoRA增强模型...")
            
            # 检查LoRA权重是否存在
            if not self.lora_path.exists():
                logger.warning(f"LoRA权重不存在: {self.lora_path}")
                return False
            
            adapter_file = self.lora_path / "adapter_model.safetensors"
            if not adapter_file.exists():
                logger.warning(f"LoRA适配器文件不存在: {adapter_file}")
                return False
            
            logger.info(f"✓ 找到LoRA权重: {adapter_file} ({adapter_file.stat().st_size / 1024 / 1024:.1f}MB)")
            
            # 尝试加载模型（需要transformers和peft）
            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer
                from peft import PeftModel
                
                logger.info(f"加载基础模型: {self.base_model}")
                
                # 加载tokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(
                    self.base_model,
                    trust_remote_code=True
                )
                
                # 加载基础模型
                base_model_obj = AutoModelForCausalLM.from_pretrained(
                    self.base_model,
                    torch_dtype=torch.float16,
                    device_map="auto",
                    trust_remote_code=True
                )
                
                # 加载LoRA适配器
                logger.info(f"加载LoRA适配器: {self.lora_path}")
                self.model = PeftModel.from_pretrained(
                    base_model_obj,
                    str(self.lora_path)
                )
                
                self.is_loaded = True
                logger.info("✅ LoRA增强模型加载成功！闭环能力已激活")
                return True
                
            except ImportError as e:
                logger.warning(f"缺少依赖库: {e}")
                logger.info("提示: pip install transformers peft accelerate")
                return False
                
        except Exception as e:
            logger.error(f"LoRA模型加载失败: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        max_length: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """使用LoRA增强模型生成回答"""
        
        if not self.is_loaded:
            # 尝试加载
            if not self.load():
                # 加载失败，返回None（降级到其他模型）
                return None
        
        try:
            # 构建prompt（Qwen格式）
            messages = [
                {"role": "system", "content": "你是一个具备完整元认知循环的自主进化AI系统。你会自我提问、分解问题、调用工具、评估结果、反思学习，形成闭环式的自我提升。"},
                {"role": "user", "content": prompt}
            ]
            
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # 编码
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=max_length
            ).to(self.model.device)
            
            # 生成
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=512,
                    temperature=temperature,
                    top_p=top_p,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id
                )
            
            # 解码
            response = self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[1]:],
                skip_special_tokens=True
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"LoRA推理失败: {e}")
            return None
    
    def is_available(self) -> bool:
        """检查LoRA是否可用"""
        return self.lora_path.exists() and (self.lora_path / "adapter_model.safetensors").exists()
    
    def get_info(self) -> Dict[str, Any]:
        """获取LoRA信息"""
        if not self.is_available():
            return {"available": False}
        
        adapter_config = self.lora_path / "adapter_config.json"
        trainer_state = self.lora_path / "trainer_state.json"
        
        info = {
            "available": True,
            "path": str(self.lora_path),
            "loaded": self.is_loaded
        }
        
        # 读取配置
        if adapter_config.exists():
            import json
            with open(adapter_config) as f:
                config = json.load(f)
                info["lora_r"] = config.get("r", "unknown")
                info["lora_alpha"] = config.get("lora_alpha", "unknown")
        
        # 读取训练状态
        if trainer_state.exists():
            import json
            with open(trainer_state) as f:
                state = json.load(f)
                info["training_steps"] = state.get("global_step", "unknown")
                info["best_loss"] = state.get("best_metric", "unknown")
        
        return info


# 全局实例
_lora_engine = None

def get_lora_engine() -> LoRAInferenceEngine:
    """获取全局LoRA引擎"""
    global _lora_engine
    if _lora_engine is None:
        _lora_engine = LoRAInferenceEngine()
    return _lora_engine