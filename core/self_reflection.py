"""
系统自我复盘模块
让系统主动分析自己的思考过程，找出可改进之处
这是元认知循环的第一步
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
try:
    from core.spirit_core import spirit_core
    SPIRIT_CORE_AVAILABLE = True
except ImportError:
    SPIRIT_CORE_AVAILABLE = False
    spirit_core = None

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


@dataclass
class SelfReflectionResult:
    """自我复盘结果"""
    what_i_did_well: List[str]
    what_i_could_improve: List[str]
    alternative_approaches: List[str]
    uncertainties: List[str]
    next_time_strategy: str
    confidence_level: float
    reflection_depth: str  # 'shallow', 'medium', 'deep'
    spirit_resonances: List[Dict[str, Any]] = None  # 精神共振结果


class SelfReflection:
    """
    系统自我复盘
    
    核心理念：让系统主动审视自己的思考过程
    不是等外部反馈，而是先自己诊断
    """
    
    def __init__(self):
        self.reflection_history = []
    
    def reflect_on_interaction(
        self,
        question: str,
        response: str,
        decision_chain: List[Dict] = None,
        knowledge_used: List[str] = None,
        objective_score: float = 0.0,
        context: Dict = None
    ) -> SelfReflectionResult:
        """
        系统自我复盘
        
        Args:
            question: 用户问题
            response: 系统回答
            decision_chain: 决策链
            knowledge_used: 使用的知识来源
            objective_score: 客观分
            context: 上下文
        
        Returns:
            自我复盘结果
        """
        logger.info(f"🔍 开始自我复盘: {question[:50]}...")
        
        # 精神共振检测：分析问题与精神内核的共鸣
        spirit_resonances = []
        if SPIRIT_CORE_AVAILABLE and question:
            try:
                resonances = spirit_core.resonate(question, context_type="reasoning")
                for r in resonances[:3]:  # 只记录前3个共振原则
                    spirit_resonances.append({
                        "principle": r.get("principle"),
                        "strength": r.get("strength"),
                        "drive_direction": r.get("drive_direction")
                    })
                if spirit_resonances:
                    logger.debug(f"自我复盘精神共振: {spirit_resonances}")
            except Exception as e:
                logger.debug(f"自我复盘精神共振检测失败: {e}")
        
        # 分析做得好的地方
        what_i_did_well = self._analyze_strengths(
            question, response, decision_chain, knowledge_used, objective_score
        )
        
        # 分析可改进的地方
        what_i_could_improve = self._analyze_weaknesses(
            question, response, decision_chain, knowledge_used, objective_score
        )
        
        # 思考替代方案
        alternative_approaches = self._think_alternatives(
            question, response, decision_chain
        )
        
        # 识别不确定性
        uncertainties = self._identify_uncertainties(
            question, response, knowledge_used
        )
        
        # 制定下次策略
        next_time_strategy = self._formulate_next_strategy(
            what_i_did_well, what_i_could_improve, alternative_approaches,
            context=context,
        )
        
        # 评估置信度
        confidence_level = self._assess_confidence(
            objective_score, len(knowledge_used or []), len(uncertainties)
        )
        
        # 确定反思深度
        reflection_depth = self._determine_reflection_depth(
            objective_score, len(what_i_could_improve)
        )
        
        result = SelfReflectionResult(
            what_i_did_well=what_i_did_well,
            what_i_could_improve=what_i_could_improve,
            alternative_approaches=alternative_approaches,
            uncertainties=uncertainties,
            next_time_strategy=next_time_strategy,
            confidence_level=confidence_level,
            reflection_depth=reflection_depth,
            spirit_resonances=spirit_resonances
        )
        
        # 记录历史
        self.reflection_history.append({
            'question': question,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        try:
            from core.learning.meta_learning import MetaLearner
            _ml = MetaLearner()
            _ml.learn_from_experience("self_testing", {
                "accuracy": confidence_level,
                "speed": 1.0 if len(response) > 50 else 0.5,
                "retention": min(1.0, len(knowledge_used or []) * 0.2 + 0.3),
                "context": {"intent_type": (context or {}).get("intent_type", "unknown")},
            })
        except Exception as e:
            logger.warning(f"操作降级跳过: {e}")
        
        logger.info(f"✅ 自我复盘完成: 置信度={confidence_level:.2f}, 深度={reflection_depth}")
        
        return result
    
    def _analyze_strengths(
        self,
        question: str,
        response: str,
        decision_chain: List[Dict],
        knowledge_used: List[str],
        objective_score: float
    ) -> List[str]:
        """分析做得好的地方"""
        strengths = []
        
        # 评分高
        if objective_score >= 70:
            strengths.append("回答质量较高，客观分达标")
        
        # 使用了知识
        if knowledge_used and len(knowledge_used) > 0:
            strengths.append(f"成功运用了{len(knowledge_used)}个知识来源")
        
        # 回答结构化
        if len(response) > 100 and ('。' in response or '\n' in response):
            strengths.append("回答结构清晰，有层次")
        
        # 决策链完整
        if decision_chain and len(decision_chain) >= 3:
            strengths.append("思考过程完整，经过多层推理")
        
        # 识别了问题类型
        if decision_chain:
            for step in decision_chain:
                if '意图' in str(step.get('reasoning', '')):
                    strengths.append("准确识别了问题意图")
                    break
        
        if not strengths:
            strengths.append("完成了基本的问答任务")
        
        return strengths
    
    def _analyze_weaknesses(
        self,
        question: str,
        response: str,
        decision_chain: List[Dict],
        knowledge_used: List[str],
        objective_score: float
    ) -> List[str]:
        """分析可改进的地方"""
        weaknesses = []
        
        # 评分低
        if objective_score < 50:
            weaknesses.append("回答质量偏低，需要提升")
        
        # 没有使用知识
        if not knowledge_used or len(knowledge_used) == 0:
            weaknesses.append("未运用已有知识，回答可能不够准确")
        
        # 回答太短
        if len(response) < 50:
            weaknesses.append("回答过于简短，缺乏详细说明")
        
        # 决策链不完整
        if not decision_chain or len(decision_chain) < 2:
            weaknesses.append("思考过程不够深入")
        
        # 可能遗漏了关键点
        if '什么' in question and len(response) < 100:
            weaknesses.append("可能遗漏了问题的关键方面")
        
        # 没有追问
        if '?' not in response and '吗' not in response:
            # 回答中没有反问，可能错失了澄清机会
            pass  # 这个不一定是问题
        
        return weaknesses
    
    def _think_alternatives(
        self,
        question: str,
        response: str,
        decision_chain: List[Dict]
    ) -> List[str]:
        """思考替代方案"""
        alternatives = []
        
        # 基于问题类型的替代方案
        if '为什么' in question:
            alternatives.append("可以从因果链的角度逐步分析")
            alternatives.append("可以提供具体例子来说明原因")
        
        if '怎么' in question or '如何' in question:
            alternatives.append("可以分步骤详细说明")
            alternatives.append("可以提供实际案例演示")
        
        if '什么' in question:
            alternatives.append("可以从定义、特征、例子多角度解释")
            alternatives.append("可以对比相关概念帮助理解")
        
        # 基于回答长度的替代方案
        if len(response) < 100:
            alternatives.append("可以扩展回答，提供更多细节")
        
        # 基于决策链的替代方案
        if decision_chain:
            # 检查是否跳过了某些层
            layers = [step.get('layer', '') for step in decision_chain]
            if 'L3' not in layers:
                alternatives.append("可以增加推理层的深度思考")
        
        return alternatives[:5]  # 最多5个
    
    def _identify_uncertainties(
        self,
        question: str,
        response: str,
        knowledge_used: List[str]
    ) -> List[str]:
        """识别不确定性"""
        uncertainties = []
        
        # 没有使用知识
        if not knowledge_used:
            uncertainties.append("对问题相关领域的知识储备不足")
        
        # 回答中有模糊表述
        vague_terms = ['可能', '大概', '应该', '似乎', '好像']
        for term in vague_terms:
            if term in response:
                uncertainties.append(f"回答中使用了模糊表述'{term}'，需要更确定的知识")
        
        # 问题中有专业术语
        if any(char.isupper() for char in question):
            uncertainties.append("问题包含专业术语，需要确认理解是否准确")
        
        return uncertainties
    
    def _formulate_next_strategy(
        self,
        what_i_did_well: List[str],
        what_i_could_improve: List[str],
        alternative_approaches: List[str],
        context: Dict = None,
    ) -> str:
        """制定下次策略 — 优先使用MetaLearner推荐，回退硬编码"""
        try:
            from core.learning.meta_learning import MetaLearner
            _ml = MetaLearner()
            ml_context = {
                "task_type": context.get("intent_type", "unknown") if context else "unknown",
                "recent_accuracy": context.get("objective_score", 50) / 100.0 if context else 0.5,
                "weakness_count": len(what_i_could_improve),
                "alternative_count": len(alternative_approaches),
            }
            recommendations = _ml.recommend_strategy(ml_context)
            if recommendations and recommendations[0].confidence > 0.5:
                top = recommendations[0]
                strategy_parts = []
                if what_i_could_improve:
                    strategy_parts.append(f"重点改进: {what_i_could_improve[0]}")
                strategy_parts.append(f"元学习推荐: {top.strategy.name}({top.reason}, 置信度={top.confidence:.2f})")
                if what_i_did_well:
                    strategy_parts.append(f"继续保持: {what_i_did_well[0]}")
                return "；".join(strategy_parts)
        except Exception as e:
            logger.debug(f"MetaLearner推荐跳过: {e}")

        strategies = []

        if what_i_could_improve:
            strategies.append(f"重点改进: {what_i_could_improve[0]}")

        if alternative_approaches:
            strategies.append(f"尝试方法: {alternative_approaches[0]}")

        if what_i_did_well:
            strategies.append(f"继续保持: {what_i_did_well[0]}")

        if not strategies:
            strategies.append("保持当前策略，持续优化")

        return "；".join(strategies)
    
    def _assess_confidence(
        self,
        objective_score: float,
        knowledge_count: int,
        uncertainty_count: int
    ) -> float:
        """评估置信度"""
        # 基础分
        confidence = 0.5
        
        # 客观分影响
        confidence += (objective_score / 100) * 0.3
        
        # 知识使用影响
        confidence += min(knowledge_count * 0.05, 0.15)
        
        # 不确定性影响
        confidence -= uncertainty_count * 0.05
        
        return max(0.0, min(1.0, confidence))
    
    def _determine_reflection_depth(
        self,
        objective_score: float,
        weakness_count: int
    ) -> str:
        """确定反思深度"""
        if objective_score < 40 or weakness_count >= 3:
            return 'deep'
        elif objective_score < 60 or weakness_count >= 1:
            return 'medium'
        else:
            return 'shallow'
    
    def to_dict(self, result: SelfReflectionResult) -> Dict:
        """转换为字典"""
        return {
            'what_i_did_well': result.what_i_did_well,
            'what_i_could_improve': result.what_i_could_improve,
            'alternative_approaches': result.alternative_approaches,
            'uncertainties': result.uncertainties,
            'next_time_strategy': result.next_time_strategy,
            'confidence_level': result.confidence_level,
            'reflection_depth': result.reflection_depth,
            'spirit_resonances': result.spirit_resonances or []
        }


self_reflection = SelfReflection()