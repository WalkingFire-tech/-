"""
循环推理引擎 - 借鉴OpenMythos的RDT架构思想
实现单模型内部的"深度思考"能力

核心思想：
- 不增加参数，通过循环迭代提升推理深度
- LTI稳定性约束保证思考过程收敛
- ACT机制动态决定思考深度
"""
import time
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from loguru import logger
from infrastructure.config_manager import config


@dataclass
class ThoughtIteration:
    """单次思考迭代"""
    iteration: int
    response: str
    quality_score: float
    hidden_state: Optional[str] = None
    convergence_metric: float = 0.0
    duration: float = 0.0


class RecurrentReasoner:
    """循环推理器 - RDT核心实现"""
    
    def __init__(self):
        self.max_iterations = config.get("recurrent.max_iterations", 4)
        self.convergence_threshold = config.get("recurrent.convergence_threshold", 0.95)
        self.quality_threshold = config.get("recurrent.quality_threshold", 0.85)
        self.stability_factor = config.get("recurrent.stability_factor", 0.9)  # LTI衰减因子
        
        logger.info(f"循环推理器初始化: max_iter={self.max_iterations}, "
                   f"convergence={self.convergence_threshold}, "
                   f"stability={self.stability_factor}")
    
    def reason_with_loops(
        self,
        model,
        prompt: str,
        intent_type: str = "chat",
        context: str = "",
        max_iterations: Optional[int] = None
    ) -> Tuple[str, List[ThoughtIteration]]:
        """
        循环推理主入口
        
        Args:
            model: 模型适配器
            prompt: 用户输入
            intent_type: 意图类型
            context: 上下文
            max_iterations: 最大迭代次数（None则使用配置）
        
        Returns:
            (最终回答, 思考轨迹)
        """
        max_iter = max_iterations or self._estimate_iterations(prompt, intent_type)
        
        logger.info(f"开始循环推理: intent={intent_type}, max_iter={max_iter}")
        
        trajectory = []
        hidden_state = ""
        best_response = ""
        best_quality = 0.0
        
        # Prelude: 初始编码
        prelude_prompt = self._build_prelude_prompt(prompt, context, intent_type)
        
        for iteration in range(max_iter):
            start_time = time.time()
            
            # Recurrent Block: 循环更新
            recurrent_prompt = self._build_recurrent_prompt(
                prelude_prompt,
                hidden_state,
                iteration,
                intent_type
            )
            
            try:
                response = model.generate(recurrent_prompt)
                quality = self._evaluate_quality(response, intent_type)
                
                # LTI稳定性约束: 衰减hidden_state
                hidden_state = self._apply_lti_constraint(
                    hidden_state,
                    response,
                    iteration
                )
                
                # 收敛检测
                convergence = self._check_convergence(
                    trajectory,
                    response,
                    quality
                )
                
                duration = time.time() - start_time
                
                thought = ThoughtIteration(
                    iteration=iteration,
                    response=response,
                    quality_score=quality,
                    hidden_state=hidden_state[:200] if hidden_state else None,
                    convergence_metric=convergence,
                    duration=duration
                )
                trajectory.append(thought)
                
                logger.info(f"迭代{iteration}: quality={quality:.2f}, "
                           f"convergence={convergence:.2f}, "
                           f"duration={duration:.2f}s")
                
                # 更新最佳答案
                if quality > best_quality:
                    best_quality = quality
                    best_response = response
                
                # ACT: 自适应计算时间，检查是否提前退出
                if self._should_halt(quality, convergence, iteration, max_iter):
                    logger.info(f"ACT触发提前退出: iteration={iteration}, "
                               f"quality={quality:.2f}, convergence={convergence:.2f}")
                    break
                
            except Exception as e:
                logger.error(f"迭代{iteration}失败: {e}")
                break
        
        # Coda: 最终输出
        final_response = self._apply_coda(best_response, trajectory, intent_type)
        
        logger.info(f"循环推理完成: iterations={len(trajectory)}, "
                   f"best_quality={best_quality:.2f}")
        
        return final_response, trajectory
    
    def _estimate_iterations(self, prompt: str, intent_type: str) -> int:
        """估算任务复杂度，决定迭代次数"""
        factors = {
            "length": min(len(prompt) / 200, 2),  # 文本长度
            "code": 1.5 if intent_type == "code" else 0,
            "question": 1.0 if intent_type == "question" else 0,
            "why": 1.5 if "为什么" in prompt else 0,
            "analyze": 1.5 if "分析" in prompt else 0,
            "compare": 1.0 if "比较" in prompt or "对比" in prompt else 0,
        }
        
        complexity = sum(factors.values())
        
        if complexity < 1.5:
            iterations = 1  # 简单任务：快速响应
        elif complexity < 3:
            iterations = 2  # 中等任务：适度思考
        else:
            iterations = min(int(complexity), self.max_iterations)  # 复杂任务：深度思考
        
        logger.debug(f"复杂度评估: complexity={complexity:.2f}, iterations={iterations}")
        return iterations
    
    def _build_prelude_prompt(self, prompt: str, context: str, intent_type: str) -> str:
        """Prelude: 初始编码"""
        if intent_type == "code":
            system = "你是一个专业的代码助手。请仔细思考后给出高质量的代码实现。"
        elif intent_type == "question":
            system = "你是一个知识渊博的助手。请深入思考后给出准确、全面的回答。"
        else:
            system = "你是一个智能助手。请思考后给出贴切的回答。"
        
        prelude = f"{system}\n\n"
        if context:
            prelude += f"【上下文】\n{context}\n\n"
        prelude += f"【用户问题】\n{prompt}\n\n请给出你的回答："
        
        return prelude
    
    def _build_recurrent_prompt(
        self,
        prelude: str,
        hidden_state: str,
        iteration: int,
        intent_type: str
    ) -> str:
        """Recurrent Block: 循环更新提示"""
        if iteration == 0:
            return prelude
        
        # 注入历史思考（类似OpenMythos的input injection）
        recurrent = f"{prelude}\n\n"
        recurrent += f"【上一轮思考（迭代{iteration}）】\n{hidden_state}\n\n"
        
        # 不同迭代阶段的指导语
        if iteration == 1:
            recurrent += "请基于上一轮思考，进一步完善你的回答："
        elif iteration == 2:
            recurrent += "请检查上一轮回答的逻辑完整性和准确性，如有不足请修正："
        else:
            recurrent += "请最终确认你的回答是否完整、准确、贴切："
        
        return recurrent
    
    def _apply_lti_constraint(
        self,
        hidden_state: str,
        new_response: str,
        iteration: int
    ) -> str:
        """
        LTI稳定性约束
        
        确保hidden_state不会无限膨胀
        类似OpenMythos的谱半径约束: ρ(A) < 1
        """
        if not hidden_state:
            return new_response
        
        # 衰减因子: 随迭代次数增加，历史信息权重降低
        decay = self.stability_factor ** iteration
        
        # 限制hidden_state长度
        max_len = 500
        if len(hidden_state) > max_len:
            hidden_state = hidden_state[:max_len]
        
        # 融合新旧信息
        combined = f"[历史思考(权重{decay:.2f})]\n{hidden_state}\n\n[本轮思考]\n{new_response}"
        
        return combined
    
    def _evaluate_quality(self, response: str, intent_type: str) -> float:
        """评估回答质量"""
        if not response:
            return 0.0
        
        score = 0.5  # 基础分
        
        # 长度合理性
        if 50 < len(response) < 2000:
            score += 0.1
        elif len(response) >= 2000:
            score += 0.05
        
        # 结构完整性
        if any(marker in response for marker in ["首先", "其次", "最后", "因此", "所以"]):
            score += 0.1
        
        # 代码任务特殊检查
        if intent_type == "code":
            if "```" in response or "def " in response or "class " in response:
                score += 0.15
        
        # 避免重复
        words = response.split()
        if len(words) > 10:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio > 0.7:
                score += 0.1
        
        return min(score, 1.0)
    
    def _check_convergence(
        self,
        trajectory: List[ThoughtIteration],
        new_response: str,
        new_quality: float
    ) -> float:
        """检查收敛性"""
        if len(trajectory) < 1:
            return 0.0
        
        prev = trajectory[-1]
        
        # 质量提升幅度
        quality_delta = new_quality - prev.quality_score
        
        # 响应相似度
        similarity = self._calculate_similarity(prev.response, new_response)
        
        # 综合收敛指标
        convergence = similarity * 0.7 + max(0, 1 - abs(quality_delta)) * 0.3
        
        return convergence
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度（简化版）"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _should_halt(
        self,
        quality: float,
        convergence: float,
        iteration: int,
        max_iter: int
    ) -> bool:
        """
        ACT: 自适应计算时间
        
        决定是否提前退出循环
        """
        # 达到最大迭代
        if iteration >= max_iter - 1:
            return True
        
        # 质量足够高
        if quality >= self.quality_threshold:
            return True
        
        # 收敛（连续两轮高度相似）
        if convergence >= self.convergence_threshold:
            return True
        
        return False
    
    def _apply_coda(
        self,
        response: str,
        trajectory: List[ThoughtIteration],
        intent_type: str
    ) -> str:
        """Coda: 最终输出处理"""
        # 添加思考轨迹摘要（可选，用于调试）
        if len(trajectory) > 1:
            summary = f"\n\n_思考深度: {len(trajectory)}轮迭代_"
            return response + summary
        
        return response


# 全局实例
recurrent_reasoner = RecurrentReasoner()