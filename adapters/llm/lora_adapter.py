"""
LoRA模型适配器
将训练好的LoRA模型集成到联盟拓荒者系统
"""
import os
import torch
from pathlib import Path
from typing import Optional, Dict, Any, List
from loguru import logger

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel
    LORA_AVAILABLE = True
except ImportError:
    LORA_AVAILABLE = False
    logger.warning("transformers或peft未安装，LoRA模型不可用")


class LoRAAdapter:
    """LoRA微调模型适配器"""
    
    def __init__(
        self,
        base_model: str = "Qwen/Qwen2.5-7B-Instruct",
        lora_path: Optional[str] = None,
        device_map: str = "auto",
        **kwargs
    ):
        """
        初始化LoRA模型
        
        Args:
            base_model: 基础模型路径
            lora_path: LoRA权重路径
            device_map: 设备映射策略
        """
        if not LORA_AVAILABLE:
            raise ImportError("请安装transformers和peft: pip install transformers peft")
        
        self.base_model_path = base_model
        self.lora_path = lora_path or self._find_lora_path()
        self.device_map = device_map
        self.model = None
        self.tokenizer = None
        self.model_name = "closed_loop_lora"
        
        self._load_model()
    
    def _find_lora_path(self) -> str:
        """自动查找LoRA权重路径"""
        possible_paths = [
            Path(r"C:\Users\Administrator\alliance_pioneer\models\closed_loop_lora"),
            Path(r"C:\Users\Administrator\alliance_pioneer\autodl_backup\output\closed_loop_lora"),
            Path(__file__).parent.parent.parent / "models" / "closed_loop_lora",
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "adapter_model.safetensors").exists():
                logger.info(f"找到LoRA权重: {path}")
                return str(path)
        
        raise FileNotFoundError("未找到LoRA权重文件")
    
    def _load_model(self):
        """加载模型"""
        logger.info(f"加载基础模型: {self.base_model_path}")
        
        # 检查CUDA是否可用
        use_cuda = torch.cuda.is_available()
        if not use_cuda:
            logger.warning("CUDA不可用，使用CPU推理（速度较慢）")
            self.device_map = "cpu"
            torch_dtype = torch.float32
        else:
            torch_dtype = torch.bfloat16
        
        # 加载tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.base_model_path,
            trust_remote_code=True
        )
        
        # 加载基础模型
        self.model = AutoModelForCausalLM.from_pretrained(
            self.base_model_path,
            torch_dtype=torch_dtype,
            device_map=self.device_map,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        
        # 加载LoRA权重
        logger.info(f"加载LoRA权重: {self.lora_path}")
        self.model = PeftModel.from_pretrained(self.model, self.lora_path)
        self.model.eval()
        
        logger.success("LoRA模型加载完成")
    
    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.8,
        top_k: int = 20,
        do_sample: bool = True,
        **kwargs
    ) -> str:
        """
        生成回复
        
        Args:
            prompt: 输入提示
            max_new_tokens: 最大生成长度
            temperature: 温度参数
            top_p: top_p采样
            top_k: top_k采样
            do_sample: 是否采样
        
        Returns:
            生成的文本
        """
        # 构建消息
        messages = [
            {"role": "system", "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
        
        # 应用chat模板
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # 编码
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        # 生成
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        # 解码
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )
        
        return response.strip()
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 512,
        **kwargs
    ) -> str:
        """
        多轮对话
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            max_new_tokens: 最大生成长度
        
        Returns:
            回复内容
        """
        # 添加系统消息
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {
                "role": "system",
                "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
            })
        
        # 应用chat模板
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # 编码
        inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        # 生成
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=kwargs.get("temperature", 0.7),
                top_p=kwargs.get("top_p", 0.8),
                do_sample=kwargs.get("do_sample", True),
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        
        # 解码
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )
        
        return response.strip()
    
    def __call__(self, prompt: str, **kwargs) -> str:
        """支持直接调用"""
        return self.generate(prompt, **kwargs)
    
    def get_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "base_model": self.base_model_path,
            "lora_path": self.lora_path,
            "device": str(self.model.device) if self.model else "N/A",
            "dtype": "bfloat16",
        }


class MockLoRAAdapter:
    """Mock LoRA适配器（用于测试）"""
    
    def __init__(self):
        self.model_name = "mock_lora"
        logger.warning("使用Mock LoRA适配器")
    
    def generate(self, prompt: str, **kwargs) -> str:
        return f"[Mock LoRA] 收到问题: {prompt[:50]}..."
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        return "[Mock LoRA] 多轮对话回复"
    
    def __call__(self, prompt: str, **kwargs) -> str:
        return self.generate(prompt, **kwargs)
    
    def get_info(self) -> Dict[str, Any]:
        return {"model_name": self.model_name, "status": "mock"}


def create_lora_adapter(
    use_mock: bool = False,
    **kwargs
) -> LoRAAdapter:
    """
    创建LoRA适配器
    
    Args:
        use_mock: 是否使用Mock适配器
        **kwargs: 传递给LoRAAdapter的参数
    
    Returns:
        LoRA适配器实例
    """
    if use_mock:
        return MockLoRAAdapter()
    
    try:
        return LoRAAdapter(**kwargs)
    except Exception as e:
        logger.error(f"LoRA模型加载失败: {e}")
        logger.warning("回退到Mock适配器")
        return MockLoRAAdapter()


if __name__ == "__main__":
    # 测试LoRA适配器
    print("=" * 60)
    print("LoRA适配器测试")
    print("=" * 60)
    
    try:
        adapter = create_lora_adapter()
        
        print(f"\n模型信息: {adapter.get_info()}")
        
        # 测试生成
        test_prompts = [
            "当你从外部模型获取了一段代码后，你会如何验证它的正确性？",
            "什么是深度学习的特点？",
            "如何系统地识别出自己所在岗位需要掌握的关键技术领域？"
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n[测试 {i}]")
            print(f"问题: {prompt}")
            response = adapter.generate(prompt, max_new_tokens=256)
            print(f"回答: {response}")
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()