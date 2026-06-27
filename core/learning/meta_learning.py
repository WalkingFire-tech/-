"""
元学习策略优化 - 学习如何更好地学习

核心理念：最高层次的学习是学习"如何学习"
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum


class StrategyType(Enum):
    MEMORIZATION = "memorization"
    UNDERSTANDING = "understanding"
    APPLICATION = "application"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    EVALUATION = "evaluation"


class EvaluationMetric(Enum):
    SPEED = "speed"
    ACCURACY = "accuracy"
    RETENTION = "retention"
    TRANSFER = "transfer"
    EFFICIENCY = "efficiency"


@dataclass
class LearningStrategy:
    strategy_id: str
    name: str
    type: StrategyType
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    applicable_contexts: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class StrategyEvaluation:
    strategy_id: str
    metric: EvaluationMetric
    score: float
    sample_size: int
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class StrategyRecommendation:
    strategy: LearningStrategy
    confidence: float
    reason: str
    expected_improvement: float


class MetaLearner:
    """
    元学习器
    
    优化学习策略本身，实现"学习如何学习"
    """
    
    def __init__(self):
        self.strategies: Dict[str, LearningStrategy] = {}
        self.evaluations: Dict[str, List[StrategyEvaluation]] = {}
        self.strategy_performance: Dict[str, Dict[EvaluationMetric, List[float]]] = {}
        self.context_history: List[Dict[str, Any]] = []
        self.active_strategies: List[str] = []
        
        self.strategy_rules: List[Callable] = []
        self.optimization_history: List[Dict[str, Any]] = []
        
        self._setup_default_strategies()
        self._setup_default_rules()
    
    def _setup_default_strategies(self):
        default_strategies = [
            LearningStrategy(
                strategy_id="spaced_repetition",
                name="间隔重复",
                type=StrategyType.MEMORIZATION,
                description="按间隔递增的方式复习，强化长期记忆",
                parameters={"initial_interval": 1, "multiplier": 2.0},
                applicable_contexts=["记忆", "背诵", "词汇"],
            ),
            LearningStrategy(
                strategy_id="elaboration",
                name="精细加工",
                type=StrategyType.UNDERSTANDING,
                description="将新知识与已有知识建立深层联系",
                parameters={"depth": 3, "connections": 5},
                applicable_contexts=["理解", "概念", "原理"],
            ),
            LearningStrategy(
                strategy_id="practice_by_doing",
                name="实践练习",
                type=StrategyType.APPLICATION,
                description="通过实际应用来巩固知识",
                parameters={"iterations": 10, "variety": True},
                applicable_contexts=["技能", "操作", "应用"],
            ),
            LearningStrategy(
                strategy_id="comparative_analysis",
                name="比较分析",
                type=StrategyType.ANALYSIS,
                description="通过比较异同来深入理解",
                parameters={"dimensions": 5},
                applicable_contexts=["分析", "对比", "分类"],
            ),
            LearningStrategy(
                strategy_id="synthesis",
                name="综合整合",
                type=StrategyType.SYNTHESIS,
                description="将多个知识点整合成新见解",
                parameters={"min_sources": 3},
                applicable_contexts=["整合", "创新", "综合"],
            ),
            LearningStrategy(
                strategy_id="self_testing",
                name="自我测试",
                type=StrategyType.EVALUATION,
                description="通过自我测试检验学习效果",
                parameters={"frequency": 0.3, "immediate_feedback": True},
                applicable_contexts=["检验", "评估", "复习"],
            ),
        ]
        
        for strategy in default_strategies:
            self.strategies[strategy.strategy_id] = strategy
            self.evaluations[strategy.strategy_id] = []
            self.strategy_performance[strategy.strategy_id] = {
                metric: [] for metric in EvaluationMetric
            }
    
    def _setup_default_rules(self):
        def rule_memorization_context(context: Dict) -> Optional[str]:
            if context.get("task_type") in ["记忆", "背诵", "词汇"]:
                return "spaced_repetition"
            return None
        
        def rule_understanding_context(context: Dict) -> Optional[str]:
            if context.get("task_type") in ["理解", "概念", "原理"]:
                return "elaboration"
            return None
        
        def rule_application_context(context: Dict) -> Optional[str]:
            if context.get("task_type") in ["技能", "操作", "应用"]:
                return "practice_by_doing"
            return None
        
        def rule_low_accuracy(context: Dict) -> Optional[str]:
            if context.get("recent_accuracy", 1.0) < 0.5:
                return "self_testing"
            return None
        
        self.strategy_rules = [
            rule_memorization_context,
            rule_understanding_context,
            rule_application_context,
            rule_low_accuracy,
        ]
    
    def register_strategy(self, strategy: LearningStrategy) -> None:
        self.strategies[strategy.strategy_id] = strategy
        self.evaluations[strategy.strategy_id] = []
        self.strategy_performance[strategy.strategy_id] = {
            metric: [] for metric in EvaluationMetric
        }
    
    def evaluate_strategy(
        self,
        strategy_id: str,
        metric: EvaluationMetric,
        score: float,
        context: Dict[str, Any] = None,
    ) -> None:
        if strategy_id not in self.strategies:
            return
        
        evaluation = StrategyEvaluation(
            strategy_id=strategy_id,
            metric=metric,
            score=score,
            sample_size=1,
            context=context or {},
        )
        
        self.evaluations[strategy_id].append(evaluation)
        self.strategy_performance[strategy_id][metric].append(score)
        
        if len(self.strategy_performance[strategy_id][metric]) > 100:
            self.strategy_performance[strategy_id][metric] = \
                self.strategy_performance[strategy_id][metric][-50:]
    
    def recommend_strategy(
        self,
        context: Dict[str, Any],
    ) -> List[StrategyRecommendation]:
        recommendations = []
        
        for rule in self.strategy_rules:
            strategy_id = rule(context)
            if strategy_id and strategy_id in self.strategies:
                strategy = self.strategies[strategy_id]
                confidence = self._calculate_strategy_confidence(strategy_id)
                expected_improvement = self._estimate_improvement(strategy_id, context)
                
                recommendations.append(StrategyRecommendation(
                    strategy=strategy,
                    confidence=confidence,
                    reason=f"规则匹配: {context.get('task_type', '未知')}",
                    expected_improvement=expected_improvement,
                ))
        
        top_performers = self._get_top_performing_strategies(context)
        for strategy_id, performance in top_performers:
            if strategy_id not in [r.strategy.strategy_id for r in recommendations]:
                strategy = self.strategies[strategy_id]
                recommendations.append(StrategyRecommendation(
                    strategy=strategy,
                    confidence=performance,
                    reason="历史表现优秀",
                    expected_improvement=performance * 0.2,
                ))
        
        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        
        return recommendations[:5]
    
    def _calculate_strategy_confidence(self, strategy_id: str) -> float:
        if strategy_id not in self.strategy_performance:
            return 0.5
        
        performances = self.strategy_performance[strategy_id]
        
        if not performances or not any(performances.values()):
            return 0.5
        
        scores = []
        for metric, values in performances.items():
            if values:
                avg = sum(values) / len(values)
                weight = self._get_metric_weight(metric)
                scores.append(avg * weight)
        
        if not scores:
            return 0.5
        
        return sum(scores) / sum(self._get_metric_weight(m) for m in EvaluationMetric)
    
    def _get_metric_weight(self, metric: EvaluationMetric) -> float:
        weights = {
            EvaluationMetric.ACCURACY: 1.0,
            EvaluationMetric.EFFICIENCY: 0.8,
            EvaluationMetric.RETENTION: 0.9,
            EvaluationMetric.TRANSFER: 0.7,
            EvaluationMetric.SPEED: 0.6,
        }
        return weights.get(metric, 0.5)
    
    def _estimate_improvement(
        self,
        strategy_id: str,
        context: Dict[str, Any],
    ) -> float:
        base_confidence = self._calculate_strategy_confidence(strategy_id)
        
        recent_accuracy = context.get("recent_accuracy", 0.5)
        improvement_potential = 1.0 - recent_accuracy
        
        return base_confidence * improvement_potential
    
    def _get_top_performing_strategies(
        self,
        context: Dict[str, Any],
    ) -> List[tuple]:
        performances = []
        
        for strategy_id in self.strategies:
            confidence = self._calculate_strategy_confidence(strategy_id)
            if confidence > 0.5:
                performances.append((strategy_id, confidence))
        
        performances.sort(key=lambda x: x[1], reverse=True)
        return performances[:3]
    
    def optimize_parameters(
        self,
        strategy_id: str,
    ) -> Dict[str, Any]:
        if strategy_id not in self.strategies:
            return {}
        
        strategy = self.strategies[strategy_id]
        current_params = strategy.parameters.copy()
        
        evaluations = self.evaluations[strategy_id]
        if len(evaluations) < 5:
            return current_params
        
        recent_evals = evaluations[-20:]
        
        avg_scores = {}
        for metric in EvaluationMetric:
            scores = [
                e.score for e in recent_evals
                if e.metric == metric
            ]
            if scores:
                avg_scores[metric] = sum(scores) / len(scores)
        
        optimized_params = current_params.copy()
        
        if avg_scores.get(EvaluationMetric.SPEED, 1.0) < 0.5:
            if "iterations" in optimized_params:
                optimized_params["iterations"] = max(1, int(optimized_params["iterations"] * 0.8))
        
        if avg_scores.get(EvaluationMetric.ACCURACY, 1.0) < 0.5:
            if "depth" in optimized_params:
                optimized_params["depth"] = min(10, optimized_params["depth"] + 1)
        
        self.optimization_history.append({
            "strategy_id": strategy_id,
            "old_params": current_params,
            "new_params": optimized_params,
            "timestamp": datetime.now().isoformat(),
        })
        
        return optimized_params
    
    def apply_optimized_parameters(self, strategy_id: str) -> bool:
        if strategy_id not in self.strategies:
            return False
        
        optimized = self.optimize_parameters(strategy_id)
        if optimized:
            self.strategies[strategy_id].parameters = optimized
            return True
        
        return False
    
    def learn_from_experience(
        self,
        strategy_id: str,
        outcome: Dict[str, Any],
    ) -> None:
        context = outcome.get("context", {})
        self.context_history.append(context)
        
        if "accuracy" in outcome:
            self.evaluate_strategy(
                strategy_id,
                EvaluationMetric.ACCURACY,
                outcome["accuracy"],
                context,
            )
        
        if "speed" in outcome:
            self.evaluate_strategy(
                strategy_id,
                EvaluationMetric.SPEED,
                outcome["speed"],
                context,
            )
        
        if "retention" in outcome:
            self.evaluate_strategy(
                strategy_id,
                EvaluationMetric.RETENTION,
                outcome["retention"],
                context,
            )
        
        if len(self.context_history) % 10 == 0:
            self.apply_optimized_parameters(strategy_id)
    
    def add_strategy_rule(self, rule: Callable[[Dict], Optional[str]]) -> None:
        self.strategy_rules.append(rule)
    
    def get_strategy_stats(self, strategy_id: str) -> Dict[str, Any]:
        if strategy_id not in self.strategies:
            return {}
        
        strategy = self.strategies[strategy_id]
        performances = self.strategy_performance[strategy_id]
        
        stats = {
            "name": strategy.name,
            "type": strategy.type.value,
            "total_evaluations": len(self.evaluations[strategy_id]),
            "metrics": {},
        }
        
        for metric, values in performances.items():
            if values:
                stats["metrics"][metric.value] = {
                    "average": sum(values) / len(values),
                    "recent": sum(values[-10:]) / min(10, len(values)),
                    "trend": "improving" if len(values) > 5 and
                             sum(values[-5:]) > sum(values[-10:-5]) else "stable",
                }
        
        return stats
    
    def get_overall_stats(self) -> Dict[str, Any]:
        all_confidences = []
        
        for strategy_id in self.strategies:
            confidence = self._calculate_strategy_confidence(strategy_id)
            all_confidences.append(confidence)
        
        return {
            "total_strategies": len(self.strategies),
            "total_evaluations": sum(len(e) for e in self.evaluations.values()),
            "total_optimizations": len(self.optimization_history),
            "average_confidence": (
                sum(all_confidences) / len(all_confidences)
                if all_confidences else 0
            ),
            "best_strategy": max(
                self.strategies.keys(),
                key=lambda s: self._calculate_strategy_confidence(s),
            ) if self.strategies else None,
        }
    
    def compare_strategies(
        self,
        strategy_ids: List[str],
        metric: EvaluationMetric = EvaluationMetric.ACCURACY,
    ) -> Dict[str, float]:
        comparison = {}
        
        for strategy_id in strategy_ids:
            if strategy_id in self.strategy_performance:
                values = self.strategy_performance[strategy_id][metric]
                if values:
                    comparison[strategy_id] = sum(values) / len(values)
                else:
                    comparison[strategy_id] = 0.0
        
        return comparison
    
    def export_state(self) -> Dict[str, Any]:
        return {
            "strategies": {
                k: {
                    "name": v.name,
                    "type": v.type.value,
                    "parameters": v.parameters,
                }
                for k, v in self.strategies.items()
            },
            "performance_summary": {
                k: {
                    metric.value: sum(values) / len(values) if values else 0
                    for metric, values in v.items()
                }
                for k, v in self.strategy_performance.items()
            },
            "overall_stats": self.get_overall_stats(),
        }