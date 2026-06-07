"""
统一错误处理模块
提供友好的错误消息和异常处理
"""
from typing import Optional, Dict, Any
from loguru import logger
from infrastructure.config_manager import config


class CampfireError(Exception):
    """营火基础异常"""
    def __init__(self, message: str, error_code: str = "UNKNOWN", details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_user_message(self) -> str:
        """转换为用户友好的消息"""
        return self.message


class ModelNotFoundError(CampfireError):
    """模型未找到异常"""
    def __init__(self, model_name: str):
        super().__init__(
            message=f"模型 '{model_name}' 未找到",
            error_code="MODEL_NOT_FOUND",
            details={"model_name": model_name}
        )
    
    def to_user_message(self) -> str:
        model_name = self.details.get("model_name", "")
        return f"抱歉,找不到模型 '{model_name}'。请先使用 'ollama pull {model_name}' 下载该模型。"


class ModelTimeoutError(CampfireError):
    """模型超时异常"""
    def __init__(self, model_name: str, timeout: int):
        super().__init__(
            message=f"模型 '{model_name}' 响应超时({timeout}秒)",
            error_code="MODEL_TIMEOUT",
            details={"model_name": model_name, "timeout": timeout}
        )
    
    def to_user_message(self) -> str:
        return "抱歉,模型响应超时。建议:\n1. 稍后重试\n2. 简化问题\n3. 检查系统资源"


class ConnectionError(CampfireError):
    """连接异常"""
    def __init__(self, service: str, url: str):
        super().__init__(
            message=f"无法连接到 {service} ({url})",
            error_code="CONNECTION_ERROR",
            details={"service": service, "url": url}
        )
    
    def to_user_message(self) -> str:
        service = self.details.get("service", "服务")
        return f"抱歉,无法连接到{service}。请检查:\n1. 服务是否启动\n2. 网络连接是否正常"


class IntentParseError(CampfireError):
    """意图解析异常"""
    def __init__(self, text: str, reason: str):
        super().__init__(
            message=f"意图解析失败: {reason}",
            error_code="INTENT_PARSE_ERROR",
            details={"text": text[:100], "reason": reason}
        )
    
    def to_user_message(self) -> str:
        return "抱歉,无法理解您的意图。请尝试更清晰地表达您的需求。"


class CalculationError(CampfireError):
    """计算异常"""
    def __init__(self, task: str, reason: str):
        super().__init__(
            message=f"计算任务失败: {reason}",
            error_code="CALCULATION_ERROR",
            details={"task": task, "reason": reason}
        )
    
    def to_user_message(self) -> str:
        return f"抱歉,计算失败。原因: {self.details.get('reason', '未知错误')}"


class AuditBlockedError(CampfireError):
    """安全审核拦截异常"""
    def __init__(self, reason: str):
        super().__init__(
            message=f"操作被安全审核拦截: {reason}",
            error_code="AUDIT_BLOCKED",
            details={"reason": reason}
        )
    
    def to_user_message(self) -> str:
        return f"⚠️ 系统检测到危险操作,已拦截。原因: {self.details.get('reason', '安全风险')}"


class ErrorHandler:
    """错误处理器"""
    
    ERROR_MESSAGES = {
        "timeout": {
            "pattern": ["timeout", "timed out", "超时"],
            "message": "抱歉,请求超时。请稍后重试或简化您的问题。"
        },
        "connection": {
            "pattern": ["connection", "connect", "连接", "network"],
            "message": "抱歉,网络连接失败。请检查网络设置和服务状态。"
        },
        "not_found": {
            "pattern": ["not found", "404", "未找到", "不存在"],
            "message": "抱歉,找不到请求的资源。请检查配置是否正确。"
        },
        "permission": {
            "pattern": ["permission", "权限", "forbidden", "403"],
            "message": "抱歉,权限不足。请检查访问权限设置。"
        },
        "memory": {
            "pattern": ["memory", "内存", "oom", "out of memory"],
            "message": "抱歉,内存不足。请尝试关闭其他程序或简化任务。"
        },
        "model": {
            "pattern": ["model", "模型"],
            "message": "抱歉,模型处理失败。请检查模型是否正确加载。"
        }
    }
    
    @classmethod
    def handle(cls, error: Exception, context: str = "") -> str:
        """处理异常并返回用户友好的消息"""
        if isinstance(error, CampfireError):
            logger.error(f"{context} - {error.error_code}: {error.message}")
            return error.to_user_message()
        
        error_str = str(error).lower()
        
        for error_type, config in cls.ERROR_MESSAGES.items():
            for pattern in config["pattern"]:
                if pattern in error_str:
                    logger.error(f"{context} - {error_type}: {error}")
                    return config["message"]
        
        logger.error(f"{context} - UNKNOWN: {error}")
        return f"抱歉,处理请求时出错: {str(error)}"
    
    @classmethod
    def is_retriable(cls, error: Exception) -> bool:
        """判断错误是否可重试"""
        if isinstance(error, (ModelTimeoutError, ConnectionError)):
            return True
        
        error_str = str(error).lower()
        retriable_patterns = ["timeout", "connection", "network", "临时"]
        
        return any(pattern in error_str for pattern in retriable_patterns)
    
    @classmethod
    def get_error_suggestion(cls, error: Exception) -> Optional[str]:
        """获取错误建议"""
        if isinstance(error, ModelNotFoundError):
            model_name = error.details.get("model_name", "")
            return f"运行命令: ollama pull {model_name}"
        
        if isinstance(error, ModelTimeoutError):
            return "尝试简化问题或等待系统负载降低"
        
        if isinstance(error, ConnectionError):
            service = error.details.get("service", "")
            if "ollama" in service.lower():
                return "运行命令: ollama serve"
            return "检查服务状态和网络连接"
        
        return None