"""
工具仲裁器 (Tool Arbiter) - T1直觉层增强
多臂老虎机算法，并行调用候选工具，选择最优结果

跨学科理论依据：
- 博弈论：多臂老虎机（MAB）问题
- 控制论：自适应控制（探索与利用平衡）
- 信息论：信噪比（SNR）评估

设计原则：
1. 并行调用候选工具
2. 基于历史成功率动态调整权重
3. 自动发现最优工具
4. 线程安全（并发锁）
"""
import asyncio
import logging
import math
import time
import threading
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class ToolArbiter:
    """
    工具仲裁器 - 在多个候选工具中选择最优
    
    算法：UCB1（Upper Confidence Bound）
    - 自动平衡探索（尝试新工具）和利用（使用已知好工具）
    - 基于历史成功率动态调整
    """
    
    def __init__(self, tool_registry=None, config: Dict = None):
        self.tools = tool_registry
        self.config = config or {}
        
        # 统计数据
        self.total_calls = 0
        self.tool_stats = defaultdict(lambda: {
            "success": 0,
            "attempts": 0,
            "total_time": 0.0,
            "total_quality": 0.0
        })
        
        # 超时统计（使用增量更新，不存储原始样本）
        self.timeout_stats = defaultdict(lambda: {
            "mean": 3.0,
            "std": 1.0,
            "count": 0,  # 样本数
            "m2": 0.0    # Welford算法的M2
        })
        
        # 并发锁（线程安全）
        self._lock = threading.Lock()
        
        # 配置参数
        self.default_timeout = self.config.get("default_timeout", 5.0)
        self.top_k_candidates = self.config.get("top_k_candidates", 2)
        self.quality_threshold = self.config.get("quality_threshold", 0.6)
        self.time_penalty_weight = self.config.get("time_penalty_weight", 0.1)
        
        logger.info("🔧 工具仲裁器已初始化（线程安全）")
    
    def get_candidates(self, task_type: str, query: str, top_k: int = 2) -> List[str]:
        """
        根据任务类型和查询内容，选出候选工具
        
        Args:
            task_type: 任务类型
            query: 用户查询
            top_k: 返回候选数量
            
        Returns:
            候选工具名称列表
        """
        candidates = []
        
        # 数学类任务
        math_keywords = ["计算", "+", "-", "*", "/", "平方", "根号", "π", "sin", "cos", "tan", "log", "sqrt", "开方", "乘", "除", "加", "减"]
        if any(k in query for k in math_keywords):
            candidates.extend(["math_calculator", "calculator"])
        
        # 搜索类任务
        search_keywords = ["搜索", "查找", "最新", "新闻", "百度", "google", "找", "查询"]
        if any(k in query for k in search_keywords):
            candidates.extend(["web_search", "quick_search", "search"])
        
        # 文件类任务
        file_keywords = ["文件", "读取", "保存", "打开", ".txt", ".pdf", ".docx", "写入"]
        if any(k in query for k in file_keywords):
            candidates.extend(["file_reader", "file_search"])
        
        # 知识类任务
        knowledge_keywords = ["什么是", "介绍", "解释", "说明", "定义"]
        if any(k in query for k in knowledge_keywords):
            candidates.extend(["knowledge_search", "vector_search"])
        
        # 去重
        candidates = list(dict.fromkeys(candidates))
        
        # 按 UCB1 分数排序
        scored = []
        for name in candidates:
            score = self._ucb_score(name)
            scored.append((name, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [name for name, _ in scored[:top_k]]
    
    def _ucb_score(self, tool_name: str) -> float:
        """
        计算 UCB1 分数
        
        UCB1 = 成功率 + sqrt(2 * ln(N) / n)
        其中：
        - N = 总调用次数
        - n = 该工具调用次数
        
        这会自动平衡：
        - 成功率高的工具（利用）
        - 尝试次数少的工具（探索）
        """
        stats = self.tool_stats[tool_name]
        attempts = stats["attempts"]
        
        if attempts == 0:
            return float('inf')  # 未探索的工具优先尝试
        
        success_rate = stats["success"] / attempts
        
        if self.total_calls > 0:
            exploration = math.sqrt(2 * math.log(self.total_calls + 1) / attempts)
        else:
            exploration = 0.0
        
        return success_rate + exploration
    
    def get_dynamic_timeout(self, tool_name: str) -> float:
        """
        计算动态超时（统计过程控制）
        
        timeout = mean + 2 * std
        
        这确保95%的调用在超时内完成
        """
        stats = self.timeout_stats[tool_name]
        mean = stats["mean"]
        std = stats["std"]
        return max(1.0, mean + 2 * std)
    
    async def arbitrate(
        self, 
        task_type: str, 
        query: str, 
        timeout: float = None
    ) -> Tuple[Optional[str], Any, Dict]:
        """
        仲裁主入口：并行调用候选工具，返回最优结果
        
        Args:
            task_type: 任务类型
            query: 用户查询
            timeout: 默认超时（None则使用配置值）
            
        Returns:
            (tool_name, result, metadata)
        """
        # 使用配置的超时值
        if timeout is None:
            timeout = self.default_timeout
        
        candidates = self.get_candidates(task_type, query, top_k=self.top_k_candidates)
        
        if not candidates:
            logger.info("🔧 工具仲裁: 无候选工具，使用LLM推理")
            return None, None, {"error": "no_tool", "candidates": []}
        
        logger.info(f"🔧 工具仲裁: 候选 {candidates}")
        
        # 并行调用候选工具
        tasks = []
        for name in candidates:
            tasks.append(self._call_with_timeout(name, query, timeout))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 评估结果
        best_name = None
        best_result = None
        best_score = -1
        best_metadata = {}
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"工具 {candidates[i]} 执行异常: {result}")
                continue
            if result is None:
                continue
            
            name = candidates[i]
            output, quality, time_used = result
            
            # 评分：质量 + 时间惩罚（使用配置权重）
            time_penalty = (time_used / timeout) * self.time_penalty_weight
            score = quality - time_penalty
            
            if score > best_score:
                best_score = score
                best_name = name
                best_result = output
                best_metadata = {
                    "quality": quality,
                    "time_ms": int(time_used * 1000),
                    "score": score
                }
        
        # 更新统计（线程安全）
        if best_name:
            success = best_score > self.quality_threshold
            self._update_tool_stats(best_name, success, best_score)
        
        if best_name:
            logger.info(f"✅ 仲裁胜出: {best_name} (score={best_score:.2f})")
        else:
            logger.warning("⚠️ 所有工具均失败")
        
        return best_name, best_result, best_metadata
    
    async def _call_with_timeout(
        self, 
        tool_name: str, 
        query: str, 
        timeout: float
    ) -> Optional[Tuple[str, float, float]]:
        """
        带超时的工具调用
        
        Returns:
            (output, quality, time_used)
        """
        start = time.time()
        
        try:
            # 尝试导入工具
            if tool_name == "math_calculator" or tool_name == "calculator":
                from tools.math_calculator import MathCalculator
                tool = MathCalculator()
                result = tool.execute(query=query)
            elif tool_name == "web_search" or tool_name == "search":
                from tools.web_search import WebSearchTool
                tool = WebSearchTool()
                result = tool.execute(query=query)
            else:
                # 未知工具
                return None
            
            time_used = time.time() - start
            quality = self._evaluate_quality(str(result), query)
            
            # 更新超时统计
            self._update_timeout_stats(tool_name, time_used)
            
            return str(result), quality, time_used
            
        except asyncio.TimeoutError:
            logger.warning(f"工具 {tool_name} 超时 ({timeout}s)")
            return None
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行错误: {e}")
            return None
    
    def _evaluate_quality(self, result: str, query: str) -> float:
        """
        评估工具返回结果的质量
        
        评分维度：
        1. 长度合理性（太长可能冗余，太短可能不完整）
        2. 相关度（关键词重叠）
        """
        if not result:
            return 0.0
        
        # 长度评分
        length_score = min(1.0, len(result) / 50)
        if len(result) > 500:
            length_score = max(0.3, 1.0 - (len(result) - 500) / 2000)
        
        # 相关度评分
        query_words = set(query.lower().split())
        result_words = set(result.lower().split())
        if query_words:
            overlap = len(query_words & result_words) / len(query_words)
            relevance = min(1.0, overlap * 2)
        else:
            relevance = 0.5
        
        # 综合评分
        return 0.6 * length_score + 0.4 * relevance
    
    def _update_timeout_stats(self, tool_name: str, time_used: float):
        """
        更新超时统计（Welford算法 - 增量更新）
        
        优势：
        1. 无需存储原始样本，节省内存
        2. 单次遍历，计算稳定
        3. 数值稳定性好
        """
        with self._lock:
            stats = self.timeout_stats[tool_name]
            
            # Welford算法
            count = stats["count"]
            mean = stats["mean"]
            m2 = stats["m2"]
            
            count += 1
            delta = time_used - mean
            mean += delta / count
            delta2 = time_used - mean
            m2 += delta * delta2
            
            # 更新统计
            stats["count"] = count
            stats["mean"] = mean
            stats["m2"] = m2
            
            # 计算标准差
            if count > 1:
                stats["std"] = math.sqrt(m2 / (count - 1))
            else:
                stats["std"] = 1.0  # 默认值
    
    def _update_tool_stats(self, tool_name: str, success: bool, quality: float = 0.0):
        """
        更新工具统计（线程安全）
        """
        with self._lock:
            self.total_calls += 1
            stats = self.tool_stats[tool_name]
            stats["attempts"] += 1
            
            if success:
                stats["success"] += 1
                stats["total_quality"] += quality
            
            if stats["attempts"] > 0:
                stats["success_rate"] = stats["success"] / stats["attempts"]
            else:
                stats["success_rate"] = 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_calls": self.total_calls,
            "tool_stats": dict(self.tool_stats),
            "timeout_stats": {k: {"mean": v["mean"], "std": v["std"]} 
                             for k, v in self.timeout_stats.items()}
        }


# 全局实例
_arbiter = None

def get_tool_arbiter(tool_registry=None) -> ToolArbiter:
    """获取工具仲裁器实例（单例）"""
    global _arbiter
    if _arbiter is None:
        _arbiter = ToolArbiter(tool_registry)
    return _arbiter