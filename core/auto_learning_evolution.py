"""
自动学习进化流程 - 当检测到知识缺失时自动学习
"""
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

import sys
sys.path.insert(0, '.')

from loguru import logger
from core.knowledge_gap_detector import gap_detector
from core.external_learner import external_learner

class AutoLearningEvolution:
    """自动学习进化系统"""
    
    def __init__(self):
        self.learning_history = []
        logger.info("自动学习进化系统已初始化")
    
    def process_query_with_evolution(self, user_query: str, initial_response: str,
                                     confidence: float = 1.0) -> dict:
        """
        带进化的查询处理
        
        流程:
        1. 检测知识缺失
        2. 触发外部学习
        3. 内部校准审核
        4. 返回正确结果
        """
        
        result = {
            'original_response': initial_response,
            'final_response': initial_response,
            'learned': False,
            'learning_reason': '',
            'corrected': False,
            'validation': None
        }
        
        # 步骤1: 检测知识缺失
        has_gap, reason, issues = gap_detector.detect_knowledge_gap(
            user_query, initial_response, confidence
        )
        
        if not has_gap:
            logger.info("未检测到知识缺失，直接返回")
            return result
        
        logger.warning(f"检测到知识缺失: {reason}")
        logger.info(f"问题列表: {issues}")
        result['learning_reason'] = reason
        
        # 步骤2: 触发外部学习
        logger.info("触发外部学习...")
        
        try:
            # 从外部学习
            learned_items = external_learner.learn_from_external(
                user_input=user_query,
                context=f"初始回答有误: {initial_response}\n问题: {', '.join(issues)}",
                trigger_reason=reason
            )
            
            if learned_items:
                logger.info(f"外部学习成功，获得 {len(learned_items)} 条知识")
                result['learned'] = True
                
                # 步骤3: 内部校准和审核
                corrected_response = self._validate_and_correct(
                    user_query, initial_response, learned_items
                )
                
                if corrected_response != initial_response:
                    result['final_response'] = corrected_response
                    result['corrected'] = True
                    logger.info("✓ 响应已校准修正")
                else:
                    logger.info("响应无需修正")
                    
                result['validation'] = {
                    'issues_found': issues,
                    'knowledge_learned': len(learned_items),
                    'correction_applied': result['corrected']
                }
                
            else:
                logger.warning("外部学习未获得有效知识")
                
        except Exception as e:
            logger.error(f"外部学习失败: {e}")
        
        return result
    
    def _validate_and_correct(self, user_query: str, original_response: str,
                             learned_items: list) -> str:
        """内部校准和审核"""
        
        # 简单的校准逻辑：如果学习到新知识，使用新知识
        if learned_items:
            # 提取最相关的知识点
            best_match = learned_items[0] if learned_items else None
            
            if best_match:
                # 构建修正后的响应
                corrected = f"""
【已校准修正】

原始回答存在问题，经过外部学习，正确答案如下：

{best_match.get('answer', best_match.get('content', ''))}

---
_本次回答经过外部学习校准_
"""
                return corrected
        
        return original_response

# 全局实例
auto_evolution = AutoLearningEvolution()

# 测试案例
if __name__ == "__main__":
    print("=" * 70)
    print("自动学习进化测试")
    print("=" * 70)
    
    # 测试错误推荐案例
    user_query = "推荐一款26650的锂电保护板控制芯片，需要带平衡功能"
    wrong_response = "推荐使用TPS61182，这款芯片具有内置的平衡电路..."
    
    print(f"\n用户问题: {user_query}")
    print(f"初始回答: {wrong_response}")
    
    result = auto_evolution.process_query_with_evolution(
        user_query, wrong_response, confidence=0.6
    )
    
    print(f"\n是否学习: {result['learned']}")
    print(f"学习原因: {result['learning_reason']}")
    print(f"是否修正: {result['corrected']}")
    print(f"\n最终回答:\n{result['final_response']}")