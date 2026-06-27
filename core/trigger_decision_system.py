"""
四层触发决策系统
将触发机制从"静态关键词匹配"升级为"认知决策系统"

架构：
  第1层：前置过滤器 → 极轻量，快速排除无效输入
  第2层：上下文感知 → 结合对话历史，判断真实意图
  第3层：深度评估 → 多维度评估处理需求
  第4层：路由决策 → 决定执行路径
"""

import re
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger


# ==================== 第1层：前置过滤器 ====================

class PreFilter:
    """
    前置过滤器 - 极轻量规则
    通过率控制在60-70%，确保大部分明显无效输入被排除
    """
    
    # 黑名单：这些模式一定不需要处理
    PATTERN_BLACKLIST = [
        r'^(你好|hi|hello|hey|在吗|在不在)$',
        r'^(好的|谢谢|ok|嗯|哦|明白|知道了|收到)$',
        r'^[0-9]+$',  # 纯数字
        r'^(天气|时间|日期|新闻)',
        r'^(再见|拜拜|bye)$',
    ]
    
    # 白名单：这些模式一定需要处理（高优先级）
    PATTERN_WHITELIST = [
        r'(推荐|选型|选择).*(芯片|IC|方案|工具)',
        r'(选型|选择).*(芯片|IC)',  # 新增：选型芯片
        r'(反思|回顾).*(历史|对话|错误)',
        r'(分析|诊断).*(问题|代码|错误|性能)',
        r'(为什么|如何).*(推荐|选择|设计)',
        r'(比较|对比).*(方案|芯片|工具)',
    ]
    
    def should_process(self, text: str, context: dict = None) -> str:
        """
        返回: 'block' | 'pass' | 'evaluate'
        """
        text_lower = text.lower().strip()
        
        # 黑名单检查
        for pattern in self.PATTERN_BLACKLIST:
            if re.match(pattern, text_lower):
                return 'block'
        
        # 白名单检查（直接通过）
        for pattern in self.PATTERN_WHITELIST:
            if re.search(pattern, text_lower):
                return 'pass'
        
        # 需要进一步评估
        return 'evaluate'


# ==================== 第2层：上下文感知器 ====================

class ContextAwareTrigger:
    """
    上下文感知触发
    结合对话历史判断是否需要六层处理
    """
    
    def __init__(self, conversation_history: List[Dict] = None):
        self.history = conversation_history or []
    
    def analyze(self, current_text: str) -> Dict:
        """
        返回上下文分析结果
        """
        result = {
            'should_trigger': False,
            'confidence': 0.0,
            'context_type': None,  # 'new_query' | 'follow_up' | 'clarification' | 'challenge'
            'reasoning': []
        }
        
        # 1. 判断对话类型
        if self._is_new_query():
            # 新问题：评估是否复杂
            complexity = self._assess_complexity(current_text)
            result['confidence'] = complexity
            result['context_type'] = 'new_query'
            result['should_trigger'] = complexity > 0.5
            result['reasoning'].append(f"新问题，复杂度: {complexity:.2f}")
        
        elif self._is_follow_up(current_text):
            # 后续追问：通常会触发
            result['confidence'] = 0.7
            result['context_type'] = 'follow_up'
            result['should_trigger'] = True
            result['reasoning'].append("后续追问")
        
        elif self._is_challenge(current_text):
            # 质疑/纠错：必须触发
            result['confidence'] = 0.9
            result['context_type'] = 'challenge'
            result['should_trigger'] = True
            result['reasoning'].append("质疑/纠错")
        
        elif self._is_clarification(current_text):
            # 澄清请求
            result['confidence'] = 0.6
            result['context_type'] = 'clarification'
            result['should_trigger'] = True
            result['reasoning'].append("澄清请求")
        
        else:
            result['context_type'] = 'new_query'
            complexity = self._assess_complexity(current_text)
            result['confidence'] = complexity
            result['should_trigger'] = complexity > 0.5
        
        return result
    
    def _is_new_query(self) -> bool:
        """是否是新问题"""
        if not self.history:
            return True
        
        # 检查最近一条是否是系统回复
        last = self.history[-1] if self.history else {}
        return last.get('role') == 'assistant'
    
    def _is_follow_up(self, text: str) -> bool:
        """是否是后续追问"""
        follow_up_patterns = [
            r'那|那么|如果|假如|比如|例如',
            r'还有|另外|此外',
            r'具体|详细|更多',
        ]
        
        for pattern in follow_up_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _is_challenge(self, text: str) -> bool:
        """是否是质疑/纠错"""
        challenge_patterns = [
            r'不对|错了|不是|不正确',
            r'为什么.*推荐|为什么.*选择',
            r'这个.*有问题|这个.*不对',
            r'我觉.*不对|我认为.*错误',
        ]
        
        for pattern in challenge_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _is_clarification(self, text: str) -> bool:
        """是否是澄清请求"""
        clarification_patterns = [
            r'什么意思|什么含义',
            r'能详细|能具体',
            r'解释.*一下|说明.*一下',
        ]
        
        for pattern in clarification_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _assess_complexity(self, text: str) -> float:
        """评估问题复杂度"""
        complexity = 0.0
        
        # 关键词复杂度
        complexity_keywords = ['为什么', '如何', '分析', '比较', '推荐', '优化', '最佳', '方案', '选择', '选型']
        for kw in complexity_keywords:
            if kw in text:
                complexity += 0.15
        
        # 长度复杂度
        if len(text) > 30:
            complexity += 0.1
        if len(text) > 80:
            complexity += 0.1
        
        # 技术术语复杂度
        technical_terms = ['参数', '配置', '接口', '性能', '架构', '协议', '算法', '芯片', '电池', '电路']
        for term in technical_terms:
            if term in text:
                complexity += 0.08
        
        return min(complexity, 1.0)


# ==================== 第3层：深度评估器 ====================

class DepthEvaluator:
    """
    深度评估器
    评估六层处理的必要性和深度
    """
    
    def evaluate(self, text: str, context: Dict) -> Dict:
        """
        返回评估结果
        """
        scores = {
            'need_reflection': self._need_reflection(text, context),
            'need_learning': self._need_learning(text, context),
            'need_verification': self._need_verification(text, context),
            'need_evolution': self._need_evolution(text, context),
        }
        
        total_score = sum(scores.values())
        
        # 决策
        if total_score > 2.0:
            return {
                'should_trigger': True,
                'processing_depth': 'full',  # 完整六层
                'confidence': min(total_score / 3.0, 1.0),
                'scores': scores
            }
        elif total_score > 1.0:
            return {
                'should_trigger': True,
                'processing_depth': 'partial',  # 部分层
                'confidence': min(total_score / 2.0, 1.0),
                'scores': scores
            }
        else:
            return {
                'should_trigger': False,
                'processing_depth': 'none',
                'confidence': 0.0,
                'scores': scores
            }
    
    def _need_reflection(self, text: str, context: Dict) -> float:
        """是否需要反思处理"""
        reflection_keywords = ['反思', '回顾', '历史', '之前', '以前', '上次', '错误', '修正', '不对', '错了']
        score = sum(0.4 for kw in reflection_keywords if kw in text)  # 提高权重
        
        # 如果历史中有错误，提高分数
        if context.get('has_recent_error', False):
            score += 0.3
        
        return min(score, 1.0)
    
    def _need_learning(self, text: str, context: Dict) -> float:
        """是否需要学习新知识"""
        learning_keywords = ['推荐', '选型', '选择', '最佳', '方案', '对比', '哪个', '比较']
        score = sum(0.3 for kw in learning_keywords if kw in text)  # 提高权重
        
        # 如果是技术领域问题，提高分数
        technical_domains = ['芯片', '电池', '算法', '架构', '设计', '优化', '电路', '电源', 'IC']
        if any(domain in text for domain in technical_domains):
            score += 0.4  # 提高权重
        
        return min(score, 1.0)
    
    def _need_verification(self, text: str, context: Dict) -> float:
        """是否需要验证"""
        verification_keywords = ['确定', '确认', '正确', '准确', '验证', '检查', '对不对', '是否']
        score = sum(0.25 for kw in verification_keywords if kw in text)
        
        # 如果涉及数字/具体参数，提高分数
        if re.search(r'[0-9]+', text):
            score += 0.2
        
        return min(score, 1.0)
    
    def _need_evolution(self, text: str, context: Dict) -> float:
        """是否需要进化"""
        evolution_keywords = ['改进', '优化', '提升', '进化', '学习', '成长', '更好']
        score = sum(0.25 for kw in evolution_keywords if kw in text)
        
        # 如果有错误反馈，提高分数
        if context.get('has_user_correction', False):
            score += 0.4
        
        return min(score, 1.0)


# ==================== 第4层：路由决策器 ====================

class RouteDecider:
    """
    路由决策器
    决定执行路径：none | light | partial | full | interactive
    """
    
    def decide(self, trigger_input: Dict) -> Dict:
        """
        决策路由
        """
        # 前置过滤器结果
        if trigger_input['pre_filter'] == 'block':
            return {'route': 'none', 'reason': 'pre_filter_blocked'}
        
        # 白名单直接通过 → 完整处理
        if trigger_input['pre_filter'] == 'pass':
            return {
                'route': 'full',
                'reason': 'whitelist_match',
                'depth': 'full',
                'layers': ['existence', 'perception', 'learning', 'integration', 'verification', 'evolution']
            }
        
        # 上下文感知结果
        context_result = trigger_input.get('context', {})
        if context_result.get('should_trigger') is False:
            # 需要深度评估
            depth_result = trigger_input.get('depth_evaluation', {})
            
            if not depth_result.get('should_trigger', False):
                return {
                    'route': 'none',
                    'reason': f"深度评估不足: {depth_result.get('confidence', 0):.2f}"
                }
            else:
                # 根据深度评估决定
                return self._route_by_depth(depth_result)
        else:
            # 上下文认为需要触发
            depth_result = trigger_input.get('depth_evaluation', {})
            if depth_result:
                return self._route_by_depth(depth_result)
            else:
                # 默认完整处理
                return {
                    'route': 'full',
                    'reason': f"context_trigger: {context_result.get('context_type')}",
                    'depth': 'full',
                    'layers': ['existence', 'perception', 'learning', 'integration', 'verification', 'evolution']
                }
    
    def _route_by_depth(self, depth_result: Dict) -> Dict:
        """根据深度评估结果路由"""
        
        processing_depth = depth_result.get('processing_depth', 'none')
        confidence = depth_result.get('confidence', 0)
        
        if processing_depth == 'full':
            return {
                'route': 'full',
                'reason': f"需要完整六层处理 (置信度: {confidence:.2f})",
                'depth': 'full',
                'layers': ['existence', 'perception', 'learning', 'integration', 'verification', 'evolution']
            }
        elif processing_depth == 'partial':
            return {
                'route': 'partial',
                'reason': f"需要部分层处理 (置信度: {confidence:.2f})",
                'depth': 'partial',
                'layers': ['perception', 'verification']  # 轻量：仅感知和校验
            }
        else:
            return {
                'route': 'light',
                'reason': f"需要轻量处理 (置信度: {confidence:.2f})",
                'depth': 'light',
                'layers': ['perception']  # 仅感知
            }


# ==================== 整合：完整的触发决策系统 ====================

class TriggerDecisionSystem:
    """
    触发决策系统 - 完整实现
    
    集成四层：前置过滤器 → 上下文感知 → 深度评估 → 路由决策
    """
    
    def __init__(self, conversation_history: List[Dict] = None):
        self.conversation_history = conversation_history or []
        self.pre_filter = PreFilter()
        self.context_aware = ContextAwareTrigger(self.conversation_history)
        self.depth_evaluator = DepthEvaluator()
        self.route_decider = RouteDecider()
        
        # 自我学习：记录触发决策的效果
        self.decision_history = []
        self.trigger_stats = {
            'total_decisions': 0,
            'full_route': 0,
            'partial_route': 0,
            'light_route': 0,
            'none_route': 0,
            'user_corrections_after_trigger': 0  # 触发后用户纠错
        }
        self.optimization_interval = 100  # 每100次决策后自动优化
        
        logger.info("🎯 四层触发决策系统已初始化")
    
    def decide(self, user_input: str) -> Dict:
        """
        完整触发决策流程
        """
        start_time = time.time()
        
        # 第1层：前置过滤
        pre_result = self.pre_filter.should_process(user_input, {})
        
        # 第2层：上下文感知
        context_result = self.context_aware.analyze(user_input)
        
        # 第3层：深度评估（仅在需要时）
        if pre_result == 'evaluate':
            depth_result = self.depth_evaluator.evaluate(user_input, context_result)
        else:
            depth_result = {'should_trigger': False, 'processing_depth': 'none', 'confidence': 0.0}
        
        # 第4层：路由决策
        decision_input = {
            'pre_filter': pre_result,
            'context': context_result,
            'depth_evaluation': depth_result
        }
        route_decision = self.route_decider.decide(decision_input)
        
        # 记录决策
        self._record_decision(user_input, route_decision)
        
        # 记录触发统计
        self.trigger_stats['total_decisions'] += 1
        route = route_decision.get('route', 'none')
        if route == 'full':
            self.trigger_stats['full_route'] += 1
        elif route == 'partial':
            self.trigger_stats['partial_route'] += 1
        elif route == 'light':
            self.trigger_stats['light_route'] += 1
        else:
            self.trigger_stats['none_route'] += 1
        
        # 自适应优化
        if self.trigger_stats['total_decisions'] % self.optimization_interval == 0:
            self._auto_optimize()
        
        duration = (time.time() - start_time) * 1000  # ms
        
        return {
            'should_trigger': route_decision.get('route') != 'none',
            'route': route_decision.get('route'),
            'reason': route_decision.get('reason'),
            'depth': route_decision.get('depth'),
            'layers': route_decision.get('layers', []),
            'confidence': context_result.get('confidence', 0),
            'context_type': context_result.get('context_type'),
            'pre_filter_result': pre_result,
            'processing_time_ms': duration
        }
    
    def _record_decision(self, user_input: str, decision: Dict):
        """记录决策"""
        self.decision_history.append({
            'timestamp': datetime.now().isoformat(),
            'input': user_input[:100],
            'route': decision.get('route'),
            'reason': decision.get('reason')
        })
        
        # 保留最近1000条
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]
    
    def _auto_optimize(self):
        """自适应优化触发策略"""
        stats = self.trigger_stats
        
        # 分析：如果大量触发后用户纠错 → 触发过于激进
        total_triggered = stats['full_route'] + stats['partial_route']
        if total_triggered > 0:
            correction_rate = stats['user_corrections_after_trigger'] / total_triggered
            
            if correction_rate > 0.3:
                logger.warning(f"⚠️ 触发过于激进，纠错率: {correction_rate:.1%}")
    
    def report_feedback(self, triggered: bool, user_satisfied: bool):
        """接收用户反馈，用于优化触发策略"""
        if triggered and not user_satisfied:
            self.trigger_stats['user_corrections_after_trigger'] += 1
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return self.trigger_stats.copy()


# ==================== 全局实例 ====================

trigger_decision_system = TriggerDecisionSystem()