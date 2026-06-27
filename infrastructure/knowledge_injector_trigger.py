"""
知识注入触发器
当适应度评估发现客观分过低时，触发知识注入
实现"感知→学习→验证→修正"闭环
"""
from typing import Dict, Optional, List
from datetime import datetime
import uuid

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class KnowledgeInjector:
    """
    知识注入触发器
    
    当客观分过低时，触发外部学习或知识注入
    集成外部学习器和注入验证器
    """
    
    def __init__(self, enable_verification: bool = True):
        self.injection_history = []
        self.enable_verification = enable_verification
        self._verifier = None
        self._composite_learner = None
    
    def inject_for_question(
        self,
        question: str,
        response: str,
        objective_score: float,
        source: str = "low_score_trigger"
    ) -> Dict:
        """
        对低分问题执行知识注入
        
        Args:
            question: 问题
            response: 回答
            objective_score: 客观分
            source: 触发来源
        
        Returns:
            注入结果
        """
        logger.info(f"💉 触发知识注入: 问题={question[:50]}..., 客观分={objective_score:.1f}")
        
        result = {
            'question': question[:100],
            'triggered_at': datetime.now().isoformat(),
            'objective_score': objective_score,
            'source': source,
            'actions_taken': []
        }
        
        # 动作1: 记录到注入历史
        self.injection_history.append(result)
        result['actions_taken'].append('recorded_to_history')
        
        # 动作2: 触发外部学习（使用新的组合学习器）
        injected_knowledge = []
        try:
            if self._composite_learner is None:
                from infrastructure.external_learners import composite_learner
                self._composite_learner = composite_learner
            
            if self._composite_learner.is_available():
                knowledge_items = self._composite_learner.learn(
                    query=question,
                    context=response[:500],
                    max_results=5
                )
                
                injected_knowledge = [
                    {
                        'content': item.content,
                        'source': item.source,
                        'confidence': item.confidence,
                        'metadata': item.metadata
                    }
                    for item in knowledge_items
                ]
                
                if injected_knowledge:
                    result['injected_knowledge'] = injected_knowledge
                    result['knowledge_count'] = len(injected_knowledge)
                    result['actions_taken'].append('external_learning_triggered')
                    logger.info(f"  ✅ 外部学习已触发: {len(injected_knowledge)}条知识")
        except Exception as e:
            logger.debug(f"  外部学习不可用: {e}")
        
        # 动作3: 发布学习事件
        try:
            from infrastructure.event_bus import bus
            
            bus.publish("knowledge_injection_needed", {
                'question': question,
                'response': response[:500],
                'objective_score': objective_score,
                'source': source,
                'timestamp': datetime.now().isoformat()
            })
            
            result['actions_taken'].append('event_published')
            logger.info(f"  ✅ 学习事件已发布")
        except Exception as e:
            logger.debug(f"  事件总线不可用: {e}")
        
        # 动作4: 验证注入效果
        if self.enable_verification and injected_knowledge:
            try:
                if self._verifier is None:
                    from infrastructure.injection_verifier import injection_verifier
                    self._verifier = injection_verifier
                
                injection_id = str(uuid.uuid4())[:8]
                verification = self._verifier.verify_injection(
                    injection_id=injection_id,
                    question=question,
                    before_score=objective_score,
                    injected_knowledge=injected_knowledge,
                    improvement_threshold=5.0
                )
                
                result['verification'] = {
                    'injection_id': injection_id,
                    'passed': verification.passed,
                    'improvement': verification.improvement,
                    'after_score': verification.after_score
                }
                result['actions_taken'].append('effect_verified')
                
                if verification.passed:
                    logger.info(f"  ✅ 注入验证通过: 改进 {verification.improvement:.1f} 分")
                else:
                    logger.warning(f"  ⚠️ 注入验证未通过，需要修正")
                    result['needs_correction'] = True
            except Exception as e:
                logger.debug(f"  验证器不可用: {e}")
        
        # 动作5: 更新统计
        result['total_actions'] = len(result['actions_taken'])
        
        return result
    
    def get_injection_stats(self) -> Dict:
        """获取注入统计"""
        if not self.injection_history:
            return {
                'total_injections': 0,
                'avg_objective_score': 0,
                'sources': {}
            }
        
        scores = [r['objective_score'] for r in self.injection_history]
        sources = {}
        for r in self.injection_history:
            src = r['source']
            sources[src] = sources.get(src, 0) + 1
        
        return {
            'total_injections': len(self.injection_history),
            'avg_objective_score': sum(scores) / len(scores),
            'min_objective_score': min(scores),
            'max_objective_score': max(scores),
            'sources': sources
        }
    
    def should_inject(
        self,
        objective_score: float,
        total_score: float,
        objective_threshold: float = 30.0,
        total_threshold: float = 50.0
    ) -> tuple:
        """
        判断是否应该触发知识注入
        
        Returns:
            (should_inject, reason)
        """
        if objective_score < objective_threshold:
            return True, f"客观分过低({objective_score:.1f} < {objective_threshold})"
        
        if total_score < total_threshold:
            return True, f"总分过低({total_score:.1f} < {total_threshold})"
        
        return False, "评分合格"


knowledge_injector = KnowledgeInjector()