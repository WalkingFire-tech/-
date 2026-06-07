"""
远程模型适配器 - 优化版本
支持OpenAI、DeepSeek等多种API
"""
import os
import time
from typing import Optional
from openai import OpenAI
from core.ports.llm_port import LLMPort
from infrastructure.model_stats import ModelStats
from infrastructure.quality_evaluator import QualityEvaluator
from infrastructure.config_manager import config
from loguru import logger


class RemoteAdapter(LLMPort):
    _stats = ModelStats()

    def __init__(self, model_name: str = "gpt-4o-mini", api_key: str = None, base_url: str = None):
        self._model_name = model_name
        
        # 获取模型配置
        model_config = self._get_model_config()
        
        # 设置API Key
        self.api_key = api_key or self._get_api_key(model_name)
        if not self.api_key:
            raise ValueError(f"未设置 {model_name} 的API Key环境变量")
        
        # 设置Base URL
        self.base_url = base_url or model_config.get("base_url")
        
        # 初始化OpenAI客户端
        client_kwargs = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        
        self.client = OpenAI(**client_kwargs)
        self.timeout = config.get("models.remote.timeout", 60)
        
        logger.info(f"远程适配器初始化,模型: {model_name}, Base URL: {self.base_url or 'OpenAI默认'}")

    @property
    def model_name(self) -> str:
        return f"remote/{self._model_name}"

    def _get_model_config(self) -> dict:
        """获取模型配置"""
        remote_models = config.get("models.remote.models", {})
        if self._model_name in remote_models:
            return remote_models[self._model_name]
        return {}

    def _get_api_key(self, model_name: str) -> Optional[str]:
        """根据模型名称获取对应的API Key"""
        # DeepSeek模型
        if "deepseek" in model_name.lower():
            return os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        # OpenAI模型
        return os.getenv("OPENAI_API_KEY")

    def _retry_request(self, messages: list, model: str, temperature: float, max_tokens: int) -> Optional[str]:
        """带重试的请求"""
        retry_config = config.get_retry_config(is_remote=True)
        retry_times = retry_config["times"]
        retry_delay = retry_config["delay"]

        for attempt in range(retry_times + 1):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.timeout
                )
                return response.choices[0].message.content.strip()
            
            except Exception as e:
                error_str = str(e).lower()
                
                # 超时错误
                if "timeout" in error_str or "timed out" in error_str:
                    if attempt < retry_times:
                        logger.warning(f"远程API超时,第{attempt + 1}次重试,等待{retry_delay}秒...")
                        time.sleep(retry_delay)
                        self.timeout = min(self.timeout + 10, 120)
                    else:
                        raise Exception(f"远程API超时,已重试{retry_times}次") from e
                
                # 连接错误
                elif "connection" in error_str or "network" in error_str:
                    if attempt < retry_times:
                        logger.warning(f"连接失败,第{attempt + 1}次重试,等待{retry_delay}秒...")
                        time.sleep(retry_delay)
                    else:
                        raise Exception(f"无法连接到远程API,已重试{retry_times}次") from e
                
                # API Key错误
                elif "api_key" in error_str or "unauthorized" in error_str or "401" in error_str:
                    raise Exception(f"API Key无效或未授权,请检查环境变量设置") from e
                
                # 其他错误
                else:
                    if attempt < retry_times:
                        logger.warning(f"请求失败: {e},第{attempt + 1}次重试...")
                        time.sleep(retry_delay)
                    else:
                        raise
        
        return None

    def generate(self, prompt: str, task_type: str = "chat", **kwargs) -> str:
        model_config = self._get_model_config()
        
        temperature = kwargs.get("temperature", model_config.get("temperature", 0.7))
        max_tokens = kwargs.get("max_tokens", model_config.get("max_tokens", 2048))

        start_time = time.time()
        success = False
        response_text = ""
        quality_score = 0

        try:
            messages = [{"role": "user", "content": prompt}]
            
            response_text = self._retry_request(messages, self._model_name, temperature, max_tokens)
            
            if response_text is None:
                raise Exception("请求失败,无返回数据")
            
            if not response_text:
                raise Exception("模型返回空响应")
            
            success = True
            quality_score = QualityEvaluator.evaluate(response_text, task_type)
            logger.info(f"质量评估: {quality_score}/100 for {task_type}")
            
            return response_text
        
        except Exception as e:
            logger.error(f"远程API调用失败: {e}")
            raise
        
        finally:
            duration = time.time() - start_time
            self._stats.record_call(
                model_name=self.model_name,
                task_type=task_type,
                duration=duration,
                success=success,
                user_feedback=None,
                input_tokens=len(prompt),
                output_tokens=len(response_text),
                quality_score=quality_score
            )
            logger.debug(f"记录统计: {self.model_name}, {task_type}, 耗时{duration:.2f}s, 质量{quality_score}")
