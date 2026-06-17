"""
Ollama模型适配器 - 优化版本
添加重试机制、超时处理、智能降级
"""
import requests
import time
import threading
from typing import Optional
from core.ports.llm_port import LLMPort
from infrastructure.model_stats import ModelStats
from infrastructure.quality_evaluator import QualityEvaluator
from infrastructure.config_manager import config
from loguru import logger


class OllamaAdapter(LLMPort):
    _stats = ModelStats()
    
    # 类级别的失败计数（所有实例共享）
    _failure_counts = {}  # {model_name: count}
    _circuit_breaker = {}  # {model_name: until_timestamp}
    _lock = threading.Lock()  # 保护类变量的线程锁

    def __init__(self, model_name: str = "mindchat", base_url: str = None):
        self._model_name = model_name
        self.base_url = base_url or config.get("models.local.ollama_base_url", "http://localhost:11434")
        self.default_timeout = None  # 不限制超时，让模型充分思考
        
        # 熔断配置 - 已禁用
        self.failure_threshold = 999999  # 实际上禁用熔断
        self.circuit_breaker_duration = 0  # 不禁用模型
        
        logger.info(f"Ollama适配器初始化,模型: {model_name}, URL: {self.base_url}, 超时: 无限制")

    @property
    def model_name(self) -> str:
        return self._model_name
    
    def _is_circuit_broken(self) -> bool:
        """检查是否处于熔断状态 - 已禁用"""
        return False  # 永不禁用模型
    
    def _record_success(self):
        """记录成功调用，重置失败计数"""
        with self._lock:
            self._failure_counts[self._model_name] = 0
    
    def _record_failure(self, error: str):
        """记录失败调用 - 已禁用熔断"""
        logger.warning(f"模型 {self._model_name} 调用失败: {error}")
        # 不触发熔断，模型始终可用

    def _get_model_config(self) -> dict:
        """获取模型配置"""
        model_key = self._model_name.replace(":", ".")
        return config.get_model_config(model_key)

    def _retry_request(self, url: str, payload: dict, timeout: int) -> Optional[dict]:
        """带重试的请求"""
        retry_config = config.get_retry_config(is_remote=False)
        retry_times = retry_config["times"]
        retry_delay = retry_config["delay"]

        for attempt in range(retry_times + 1):
            try:
                response = requests.post(url, json=payload, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout as e:
                if attempt < retry_times:
                    logger.warning(f"请求超时,第{attempt + 1}次重试,等待{retry_delay}秒...")
                    time.sleep(retry_delay)
                    # 不再增加超时时间，保持原始超时设置
                else:
                    raise Exception(f"请求超时,已重试{retry_times}次") from e
            except requests.exceptions.ConnectionError as e:
                if attempt < retry_times:
                    logger.warning(f"连接失败,第{attempt + 1}次重试,等待{retry_delay}秒...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"无法连接到Ollama服务({self.base_url}),已重试{retry_times}次") from e
            except requests.exceptions.HTTPError as e:
                if response.status_code == 404:
                    raise Exception(f"模型{self._model_name}未找到,请先使用'ollama pull {self._model_name}'下载") from e
                else:
                    raise Exception(f"HTTP错误: {response.status_code}") from e
            except Exception as e:
                if attempt < retry_times:
                    logger.warning(f"请求失败: {e},第{attempt + 1}次重试...")
                    time.sleep(retry_delay)
                else:
                    raise
        
        return None

    def generate(self, prompt: str, task_type: str = "chat", **kwargs) -> str:
        # 检查熔断状态
        if self._is_circuit_broken():
            raise Exception(f"模型 {self._model_name} 处于熔断状态，请稍后重试或使用其他模型")
        
        url = f"{self.base_url}/api/generate"
        
        model_config = self._get_model_config()
        temperature = kwargs.get("temperature", model_config.get("temperature", 0.9))
        max_tokens = kwargs.get("max_tokens", model_config.get("max_tokens", 512))
        timeout = kwargs.get("timeout", self.default_timeout)

        payload = {
            "model": self._model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "top_p": 0.95,
            }
        }

        start_time = time.time()
        success = False
        response_text = ""
        quality_score = 0

        try:
            data = self._retry_request(url, payload, timeout)
            if data is None:
                raise Exception("请求失败,无返回数据")
            
            response_text = data.get("response", "").strip()
            if not response_text:
                raise Exception("模型返回空响应")
            
            success = True
            quality_score = QualityEvaluator.evaluate(response_text, task_type)
            logger.info(f"质量评估: {quality_score}/100 for {task_type}")
            
            # 记录成功，重置失败计数
            self._record_success()
            
            return response_text
        
        except Exception as e:
            logger.error(f"Ollama请求失败: {e}")
            
            # 记录失败，可能触发熔断
            self._record_failure(str(e))
            
            raise
        
        finally:
            duration = time.time() - start_time
            self._stats.record_call(
                model_name=self._model_name,
                task_type=task_type,
                duration=duration,
                success=success,
                user_feedback=None,
                input_tokens=len(prompt),
                output_tokens=len(response_text),
                quality_score=quality_score
            )
            logger.debug(f"记录统计: {self._model_name}, {task_type}, 耗时{duration:.2f}s, 质量{quality_score}")
