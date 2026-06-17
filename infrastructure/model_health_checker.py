"""
模型健康检查器 - 自动管理模型黑名单
避免对已失败模型的重复调用
"""
import time
from collections import defaultdict
from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger


class ModelHealthChecker:
    """模型健康检查器"""
    
    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_seconds: int = 300,
        max_blacklist_size: int = 10
    ):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.max_blacklist_size = max_blacklist_size
        
        self.failure_counts = defaultdict(int)
        self.success_counts = defaultdict(int)
        self.blacklist = {}  # {model_name: ban_timestamp}
        self.last_check_time = defaultdict(float)
        
        logger.info(f"模型健康检查器已初始化 (失败阈值: {failure_threshold}, 冷却: {cooldown_seconds}s)")
    
    def is_blacklisted(self, model_name: str) -> bool:
        """检查模型是否在黑名单中 - 已禁用"""
        return False  # 永不将模型加入黑名单
    
    def is_available(self, model_name: str) -> bool:
        """检查模型是否可用
        
        Args:
            model_name: 模型名称
        
        Returns:
            是否可用
        """
        return not self.is_blacklisted(model_name)
    
    def record_success(self, model_name: str, response_time: float = None):
        """记录成功调用
        
        Args:
            model_name: 模型名称
            response_time: 响应时间
        """
        self.success_counts[model_name] += 1
        self.failure_counts[model_name] = 0  # 重置失败计数
        
        # 如果在黑名单中，移除
        if model_name in self.blacklist:
            del self.blacklist[model_name]
            logger.info(f"模型 {model_name} 恢复正常，已从黑名单移除")
        
        logger.debug(f"模型 {model_name} 调用成功 (总成功: {self.success_counts[model_name]})")
    
    def record_failure(
        self,
        model_name: str,
        error_type: str = "unknown",
        error_message: str = None
    ):
        """记录失败调用 - 不加入黑名单"""
        self.failure_counts[model_name] += 1
        failures = self.failure_counts[model_name]
        
        logger.warning(f"模型 {model_name} 调用失败 (连续失败: {failures}) - {error_type}")
        # 不将模型加入黑名单，始终可用
    
    def _add_to_blacklist(
        self,
        model_name: str,
        error_type: str,
        error_message: str
    ):
        """加入黑名单"""
        # 检查黑名单大小限制
        if len(self.blacklist) >= self.max_blacklist_size:
            # 移除最旧的条目
            oldest = min(self.blacklist.items(), key=lambda x: x[1])
            del self.blacklist[oldest[0]]
            logger.info(f"黑名单已满，移除最旧条目: {oldest[0]}")
        
        self.blacklist[model_name] = time.time()
        logger.warning(
            f"⚠️ 模型 {model_name} 已加入黑名单 "
            f"(原因: {error_type}, 冷却: {self.cooldown_seconds}s)"
        )
    
    def get_available_models(self, all_models: List[str]) -> List[str]:
        """获取可用模型列表
        
        Args:
            all_models: 所有模型列表
        
        Returns:
            可用模型列表
        """
        available = []
        for model in all_models:
            if self.is_available(model):
                available.append(model)
        
        return available
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        all_models = set(self.success_counts.keys()) | set(self.failure_counts.keys())
        
        stats = {
            "total_models": len(all_models),
            "blacklisted": len(self.blacklist),
            "models": {}
        }
        
        for model in all_models:
            stats["models"][model] = {
                "success_count": self.success_counts[model],
                "failure_count": self.failure_counts[model],
                "is_blacklisted": model in self.blacklist,
                "success_rate": (
                    self.success_counts[model] / 
                    max(1, self.success_counts[model] + self.failure_counts[model])
                )
            }
        
        return stats
    
    def get_blacklist_report(self) -> str:
        """获取黑名单报告"""
        if not self.blacklist:
            return "✅ 无模型在黑名单中"
        
        report = f"""
╔══════════════════════════════════════════════════════════╗
║              模型黑名单报告                                ║
╚══════════════════════════════════════════════════════════╝

⚠️ 当前有 {len(self.blacklist)} 个模型在黑名单中:
"""
        
        for model, ban_time in self.blacklist.items():
            elapsed = time.time() - ban_time
            remaining = max(0, self.cooldown_seconds - elapsed)
            failures = self.failure_counts[model]
            
            report += f"""
  • {model}
    - 连续失败: {failures}次
    - 剩余冷却: {remaining:.0f}秒
"""
        
        return report
    
    def clear_blacklist(self):
        """清空黑名单"""
        self.blacklist.clear()
        self.failure_counts.clear()
        logger.info("黑名单已清空")
    
    def force_enable(self, model_name: str):
        """强制启用模型"""
        if model_name in self.blacklist:
            del self.blacklist[model_name]
        self.failure_counts[model_name] = 0
        logger.info(f"模型 {model_name} 已强制启用")


model_health_checker = ModelHealthChecker()