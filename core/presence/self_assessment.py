"""
持续自我评估 (Continuous Self Assessment)

核心理念：系统在每次对话后自动回顾自己的表现
- 不是被动等待评估
- 而是主动反思自己的行为

核心能力：
1. 对话后自动回顾
2. 表现评估（多信号综合）
3. 洞察生成
4. 改进建议
5. 持久化存储
6. 与主系统集成（立体记忆、L5进化）

修复记录：
- P4: 添加SQLite持久化
- P1: 多信号评估逻辑
- P6: 立体记忆和L5进化集成
- P2: 改进问题检测逻辑
- P3: 规范单例实现
- P5: 配置化阈值
"""
from core.ports.adapters import get_storage_port
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class PerformanceMetric(Enum):
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    HELPFULNESS = "helpfulness"
    CLARITY = "clarity"
    TIMELINESS = "timeliness"
    INTEGRATION = "integration"
    SELF_MODEL_MATURITY = "self_model_maturity"


@dataclass
class AssessmentResult:
    """评估结果"""
    timestamp: datetime
    conversation_id: str
    
    overall_score: float
    metrics: Dict[str, float]
    insights: List[str]
    improvements: List[str]
    self_criticism: List[str]
    learning_points: List[str]


@dataclass
class AssessmentHistory:
    """评估历史"""
    results: List[AssessmentResult] = field(default_factory=list)
    
    def add(self, result: AssessmentResult):
        self.results.append(result)
        if len(self.results) > 100:
            self.results = self.results[-50:]
    
    def get_recent(self, count: int = 10) -> List[AssessmentResult]:
        return self.results[-count:]
    
    def get_average_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.overall_score for r in self.results) / len(self.results)


class ContinuousSelfAssessment:
    """
    持续自我评估
    
    让系统在每次对话后自动回顾自己的表现
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {
            'score_thresholds': {
                'excellent': 0.8,
                'good': 0.6,
                'needs_improvement': 0.4
            },
            'metric_weights': {
                'accuracy': 0.25,
                'relevance': 0.20,
                'helpfulness': 0.20,
                'clarity': 0.08,
                'timeliness': 0.07,
                'integration': 0.10,
                'self_model_maturity': 0.10
            },
            'min_response_length': 30,
            'question_words': ["?", "吗", "呢", "怎样", "如何", "为什么", "what", "how", "why"]
        }
        
        self.history = AssessmentHistory()
        self.current_assessment: Optional[AssessmentResult] = None
        self._db_path = Path("data/self_assessment.db")
        
        self.assessment_criteria = {
            PerformanceMetric.ACCURACY: {
                "weight": self.config['metric_weights']['accuracy'],
                "description": "回答是否准确无误",
            },
            PerformanceMetric.RELEVANCE: {
                "weight": self.config['metric_weights']['relevance'],
                "description": "回答是否切题",
            },
            PerformanceMetric.HELPFULNESS: {
                "weight": self.config['metric_weights']['helpfulness'],
                "description": "回答是否有帮助",
            },
            PerformanceMetric.CLARITY: {
                "weight": self.config['metric_weights']['clarity'],
                "description": "回答是否清晰",
            },
            PerformanceMetric.TIMELINESS: {
                "weight": self.config['metric_weights']['timeliness'],
                "description": "回答是否及时",
            },
            PerformanceMetric.INTEGRATION: {
                "weight": self.config['metric_weights']['integration'],
                "description": "系统各模块集成度",
            },
            PerformanceMetric.SELF_MODEL_MATURITY: {
                "weight": self.config['metric_weights']['self_model_maturity'],
                "description": "自我模型成熟度",
            },
        }
        
        self.stats = {
            "total_assessments": 0,
            "average_score": 0.0,
            "improving_count": 0,
            "declining_count": 0,
        }
        
        self._init_database()
        self._load_history_from_db()
    
    def _init_database(self):
        """初始化评估数据库"""
        try:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            
            db = get_storage_port(str(self._db_path))
            db.executescript('''
                CREATE TABLE IF NOT EXISTS assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT,
                    timestamp TEXT,
                    overall_score REAL,
                    metrics TEXT,
                    insights TEXT,
                    improvements TEXT,
                    self_criticism TEXT,
                    learning_points TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_conversation 
                ON assessments(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON assessments(timestamp)
            ''')
            logger.debug("自我评估数据库初始化成功")
        except Exception as e:
            logger.warning(f"自我评估数据库初始化失败: {e}")
    
    def _load_history_from_db(self):
        """从数据库加载历史评估"""
        try:
            if not self._db_path.exists():
                return
            
            db = get_storage_port(str(self._db_path))
            rows = db.query('''
                SELECT conversation_id, timestamp, overall_score, 
                       metrics, insights, improvements, 
                       self_criticism, learning_points
                FROM assessments
                ORDER BY timestamp DESC
                LIMIT 50
            ''')
            
            for row in rows:
                result = AssessmentResult(
                    timestamp=datetime.fromisoformat(row[1]),
                    conversation_id=row[0],
                    overall_score=row[2],
                    metrics=json.loads(row[3]) if row[3] else {},
                    insights=json.loads(row[4]) if row[4] else [],
                    improvements=json.loads(row[5]) if row[5] else [],
                    self_criticism=json.loads(row[6]) if row[6] else [],
                    learning_points=json.loads(row[7]) if row[7] else [],
                )
                self.history.results.insert(0, result)
            
            logger.warning(f"从数据库加载了 {len(self.history.results)} 条历史评估")
        except Exception as e:
            logger.warning(f"加载历史评估失败: {e}")
    
    def _save_assessment_to_db(self, result: AssessmentResult):
        """保存评估结果到数据库"""
        try:
            db = get_storage_port(str(self._db_path))
            db.execute('''
                INSERT INTO assessments
                (conversation_id, timestamp, overall_score, metrics, insights,
                 improvements, self_criticism, learning_points)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.conversation_id,
                result.timestamp.isoformat(),
                result.overall_score,
                json.dumps(result.metrics),
                json.dumps(result.insights),
                json.dumps(result.improvements),
                json.dumps(result.self_criticism),
                json.dumps(result.learning_points)
            ), commit=True)
            logger.warning(f"评估结果已保存: {result.conversation_id}")
        except Exception as e:
            logger.warning(f"保存评估结果失败: {e}")
    
    def assess_conversation(
        self,
        conversation_id: str,
        user_input: str,
        system_response: str,
        context: Dict[str, Any] = None,
        user_feedback: float = None,
    ) -> AssessmentResult:
        """
        评估一次对话
        
        Args:
            conversation_id: 对话ID
            user_input: 用户输入
            system_response: 系统响应
            context: 上下文（包含校验结果、知识匹配等）
            user_feedback: 用户反馈 (0-1)
        
        Returns:
            评估结果
        """
        now = datetime.now()
        context = context or {}
        
        metrics = self._evaluate_metrics(
            user_input,
            system_response,
            context,
            user_feedback,
        )
        
        overall_score = self._calculate_overall_score(metrics)
        
        insights = self._generate_insights(metrics, user_input, system_response)
        
        improvements = self._identify_improvements(metrics)
        
        self_criticism = self._self_critique(metrics, user_input, system_response)
        
        learning_points = self._extract_learning_points(
            metrics,
            user_input,
            system_response,
            self_criticism,
        )
        
        result = AssessmentResult(
            timestamp=now,
            conversation_id=conversation_id,
            overall_score=overall_score,
            metrics=metrics,
            insights=insights,
            improvements=improvements,
            self_criticism=self_criticism,
            learning_points=learning_points,
        )
        
        self.current_assessment = result
        self.history.add(result)
        
        self._update_stats(result)
        
        self._save_assessment_to_db(result)
        
        self._save_to_stereo_memory(result, user_input, system_response)
        
        self._trigger_evolution(result)
        
        return result
    
    def _evaluate_metrics(
        self,
        user_input: str,
        system_response: str,
        context: Dict[str, Any],
        user_feedback: float,
    ) -> Dict[str, float]:
        """
        评估各维度 - 多信号综合评估
        
        修复P1: 使用多个信号来源，而非简单的长度判断
        """
        metrics = {}
        
        accuracy_signals = []
        accuracy_weights = []
        
        validation = context.get('validation', {})
        if validation.get('status') == 'pass':
            accuracy_signals.append(0.95)
            accuracy_weights.append(0.4)
        elif validation.get('status') == 'partial':
            accuracy_signals.append(0.65)
            accuracy_weights.append(0.3)
        elif validation.get('status') == 'fail':
            accuracy_signals.append(0.3)
            accuracy_weights.append(0.4)
        
        if user_feedback is not None:
            accuracy_signals.append(user_feedback)
            accuracy_weights.append(0.3)
        
        knowledge_match = context.get('knowledge_match')
        if knowledge_match is not None:
            accuracy_signals.append(knowledge_match)
            accuracy_weights.append(0.2)
        
        if context.get('has_factual_content'):
            accuracy_signals.append(0.8)
            accuracy_weights.append(0.1)
        
        if accuracy_signals:
            total_weight = sum(accuracy_weights)
            accuracy = sum(s * w for s, w in zip(accuracy_signals, accuracy_weights)) / total_weight
        else:
            accuracy = 0.5
            if len(system_response) > 50:
                accuracy += 0.15
            if "error" not in system_response.lower():
                accuracy += 0.15
            if "抱歉" not in system_response and "对不起" not in system_response:
                accuracy += 0.1
        
        metrics[PerformanceMetric.ACCURACY.value] = min(1.0, accuracy)
        
        relevance_signals = []
        
        if context.get('topic_match'):
            relevance_signals.append(0.9)
        
        if context.get('intent_match'):
            relevance_signals.append(0.85)
        
        if len(user_input) > 0:
            input_keywords = set(user_input.lower().split())
            response_words = set(system_response.lower().split())
            overlap = len(input_keywords & response_words) / max(len(input_keywords), 1)
            relevance_signals.append(0.5 + overlap * 0.4)
        
        if relevance_signals:
            relevance = sum(relevance_signals) / len(relevance_signals)
        else:
            if len(user_input) > 0:
                ratio = len(system_response) / len(user_input)
                relevance = min(1.0, 0.5 + ratio * 0.05)
            else:
                relevance = 0.5
        
        metrics[PerformanceMetric.RELEVANCE.value] = relevance
        
        helpfulness_signals = []
        
        if user_feedback is not None:
            helpfulness_signals.append(user_feedback)
        
        if context.get('user_satisfied'):
            helpfulness_signals.append(0.9)
        
        if len(system_response) > 100:
            helpfulness_signals.append(0.7)
        elif len(system_response) > 50:
            helpfulness_signals.append(0.6)
        
        if any(word in system_response for word in ["建议", "可以", "方法", "步骤"]):
            helpfulness_signals.append(0.75)
        
        if helpfulness_signals:
            helpfulness = sum(helpfulness_signals) / len(helpfulness_signals)
        else:
            helpfulness = 0.6
        
        metrics[PerformanceMetric.HELPFULNESS.value] = helpfulness
        
        clarity_signals = []
        
        if "\n\n" in system_response:
            clarity_signals.append(0.85)
        elif "\n" in system_response:
            clarity_signals.append(0.75)
        
        sentence_endings = system_response.count("。") + system_response.count(".")
        if sentence_endings >= 3:
            clarity_signals.append(0.8)
        elif sentence_endings >= 1:
            clarity_signals.append(0.7)
        
        if any(marker in system_response for marker in ["1.", "一、", "首先", "第一"]):
            clarity_signals.append(0.85)
        
        if clarity_signals:
            clarity = sum(clarity_signals) / len(clarity_signals)
        else:
            clarity = 0.6
        
        metrics[PerformanceMetric.CLARITY.value] = min(1.0, clarity)
        
        response_time = context.get('response_time_ms')
        if response_time is not None:
            if response_time < 1000:
                timeliness = 0.95
            elif response_time < 3000:
                timeliness = 0.85
            elif response_time < 5000:
                timeliness = 0.7
            else:
                timeliness = 0.5
        else:
            timeliness = 0.9
        
        metrics[PerformanceMetric.TIMELINESS.value] = timeliness
        
        integration_score = 0.5
        try:
            from core.monitoring.runtime_trigger_monitor import trigger_monitor
            stats = trigger_monitor.get_all_stats()
            if stats:
                triggered = sum(1 for s in stats.values() if s.get("trigger_count", 0) > 0)
                total = len(stats)
                integration_score = triggered / max(total, 1)
        except Exception:
            pass
        metrics[PerformanceMetric.INTEGRATION.value] = integration_score
        
        maturity_score = 0.5
        try:
            from core.self.model import get_self_model
            sm = get_self_model()
            scores = sm.get_maturity_score()
            maturity_score = scores.get("overall", 0.5)
        except Exception:
            pass
        metrics[PerformanceMetric.SELF_MODEL_MATURITY.value] = maturity_score
        
        return metrics
    
    def _calculate_overall_score(self, metrics: Dict[str, float]) -> float:
        """计算整体评分"""
        weighted_sum = 0.0
        total_weight = 0.0
        
        for metric, criteria in self.assessment_criteria.items():
            weight = criteria["weight"]
            value = metrics.get(metric.value, 0.5)
            weighted_sum += weight * value
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.5
    
    def _generate_insights(
        self,
        metrics: Dict[str, float],
        user_input: str,
        system_response: str,
    ) -> List[str]:
        """
        生成洞察
        
        修复P2: 改进问题检测逻辑
        """
        insights = []
        excellent_threshold = self.config['score_thresholds']['excellent']
        needs_improvement_threshold = self.config['score_thresholds']['needs_improvement']
        
        for metric, value in metrics.items():
            if value >= excellent_threshold:
                insights.append(f"{metric}表现优秀 ({value:.2f})")
        
        for metric, value in metrics.items():
            if value < needs_improvement_threshold:
                insights.append(f"{metric}需要改进 ({value:.2f})")
        
        if len(user_input) < 20 and len(system_response) > 200:
            insights.append("对简短输入给出了详细响应")
        
        question_words = self.config['question_words']
        has_question = any(qw in user_input for qw in question_words)
        
        if has_question and len(system_response) < 20:
            insights.append("用户提问但响应过于简短，可能未充分回答问题")
        
        if "?" in user_input and "?" not in system_response:
            if not any(word in system_response for word in ["是", "对", "可以", "能够"]):
                pass
        
        return insights
    
    def _identify_improvements(self, metrics: Dict[str, float]) -> List[str]:
        """识别改进建议"""
        improvements = []
        good_threshold = self.config['score_thresholds']['good']
        
        for metric, value in metrics.items():
            if value < good_threshold:
                try:
                    criteria = self.assessment_criteria.get(PerformanceMetric(metric))
                    if criteria:
                        improvements.append(f"提升{criteria['description']}")
                except ValueError:
                    pass
        
        return improvements
    
    def _self_critique(
        self,
        metrics: Dict[str, float],
        user_input: str,
        system_response: str,
    ) -> List[str]:
        """自我批评"""
        criticisms = []
        min_length = self.config['min_response_length']
        
        if len(system_response) < min_length:
            criticisms.append("响应过于简短，可能缺乏充分解释")
        
        if user_input in system_response and len(user_input) > 10:
            criticisms.append("响应包含用户输入原文，可能缺乏加工")
        
        needs_improvement_threshold = self.config['score_thresholds']['needs_improvement']
        for metric, value in metrics.items():
            if value < needs_improvement_threshold:
                criticisms.append(f"{metric}得分过低，需要重点关注")
        
        if "抱歉" in system_response or "对不起" in system_response:
            if metrics.get(PerformanceMetric.ACCURACY.value, 0) < 0.5:
                criticisms.append("使用了道歉语言但可能未能解决问题")
        
        return criticisms
    
    def _extract_learning_points(
        self,
        metrics: Dict[str, float],
        user_input: str,
        system_response: str,
        criticisms: List[str],
    ) -> List[str]:
        """提取学习点"""
        learning_points = []
        
        for criticism in criticisms:
            if "简短" in criticism:
                learning_points.append("学习：提供更详细的响应")
            elif "重复" in criticism:
                learning_points.append("学习：对用户输入进行更多加工")
            elif "得分过低" in criticism:
                learning_points.append("学习：改进低分维度")
            elif "道歉" in criticism:
                learning_points.append("学习：提供实质性解决方案而非道歉")
        
        excellent_threshold = self.config['score_thresholds']['excellent']
        for metric, value in metrics.items():
            if value >= excellent_threshold:
                learning_points.append(f"保持：{metric}的优秀表现")
        
        return learning_points
    
    def _update_stats(self, result: AssessmentResult):
        """更新统计"""
        self.stats["total_assessments"] += 1
        
        total = self.stats["total_assessments"]
        old_avg = self.stats["average_score"]
        self.stats["average_score"] = (old_avg * (total - 1) + result.overall_score) / total
        
        if len(self.history.results) >= 2:
            previous = self.history.results[-2]
            if result.overall_score > previous.overall_score:
                self.stats["improving_count"] += 1
            elif result.overall_score < previous.overall_score:
                self.stats["declining_count"] += 1
    
    def _save_to_stereo_memory(self, result: AssessmentResult,
                               user_input: str, system_response: str):
        """
        保存到立体记忆
        
        修复P6: 与主系统集成
        """
        try:
            from core.memory.stereo_memory import get_stereo_memory
            store = get_stereo_memory()
            
            assessment_summary = (
                f"自我评估 [{result.overall_score:.2f}]\n"
                f"洞察: {', '.join(result.insights[:3])}\n"
                f"改进: {', '.join(result.improvements[:2])}"
            )
            
            store.save({
                "user_content": f"对话评估: {user_input[:50]}...",
                "content": f"对话评估: {user_input[:50]}...",
                "system_content": assessment_summary,
                "intent": "self_assessment",
                "topic": "continuous_improvement",
                "memory_type": "conversation",
                "importance": 0.7,
            })
            logger.debug("评估结果已保存到立体记忆")
        except ImportError:
            logger.debug("立体记忆模块未安装，跳过保存")
        except Exception as e:
            logger.error(f"保存到立体记忆失败: {e}")
    
    def _trigger_evolution(self, result: AssessmentResult):
        """
        触发L5进化
        
        修复P6: 与主系统集成
        """
        try:
            from core.layers.l5_evolution import get_l5_evolution
            l5 = get_l5_evolution()
            
            l5.record_experience({
                "user_input": "自我评估结果",
                "response": f"评分: {result.overall_score:.2f}",
                "validation_result": {
                    "status": "pass" if result.overall_score > 0.6 else "fail",
                    "confidence": result.overall_score
                },
                "insights": result.insights,
                "learning_points": result.learning_points,
                "learning_result": {"knowledge_gained": 0, "avg_knowledge_quality": 0, "knowledge_reuse_rate": 0},
            })
            logger.debug("评估结果已触发L5进化")
        except ImportError:
            logger.debug("L5进化层未安装，跳过触发")
        except Exception as e:
            logger.error(f"触发L5进化失败: {e}")
    
    def get_current_assessment(self) -> Optional[Dict[str, Any]]:
        """获取当前评估"""
        if not self.current_assessment:
            return None
        
        return {
            "timestamp": self.current_assessment.timestamp.isoformat(),
            "conversation_id": self.current_assessment.conversation_id,
            "overall_score": self.current_assessment.overall_score,
            "metrics": self.current_assessment.metrics,
            "insights": self.current_assessment.insights,
            "improvements": self.current_assessment.improvements,
            "self_criticism": self.current_assessment.self_criticism,
            "learning_points": self.current_assessment.learning_points,
        }
    
    def get_performance_trend(self) -> Dict[str, Any]:
        """获取表现趋势"""
        recent = self.history.get_recent(10)
        
        if len(recent) < 2:
            return {"trend": "insufficient_data"}
        
        scores = [r.overall_score for r in recent]
        
        first_half = scores[:len(scores)//2]
        second_half = scores[len(scores)//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        if second_avg > first_avg + 0.05:
            trend = "improving"
        elif second_avg < first_avg - 0.05:
            trend = "declining"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "recent_average": sum(scores) / len(scores),
            "first_half_average": first_avg,
            "second_half_average": second_avg,
            "change": second_avg - first_avg,
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_assessments": self.stats["total_assessments"],
            "average_score": self.stats["average_score"],
            "improving_count": self.stats["improving_count"],
            "declining_count": self.stats["declining_count"],
            "trend": self.get_performance_trend(),
        }
    
    def get_historical_assessments(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取历史评估"""
        try:
            db = get_storage_port(str(self._db_path))
            rows = db.query('''
                SELECT conversation_id, timestamp, overall_score, metrics
                FROM assessments
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            results = []
            for row in rows:
                results.append({
                    "conversation_id": row[0],
                    "timestamp": row[1],
                    "overall_score": row[2],
                    "metrics": json.loads(row[3]) if row[3] else {}
                })
            return results
        except Exception as e:
            logger.warning(f"获取历史评估失败: {e}")
            return []


_self_assessment: Optional[ContinuousSelfAssessment] = None


def get_self_assessment(config: Optional[Dict] = None) -> ContinuousSelfAssessment:
    """
    获取自我评估单例
    
    修复P3: 规范单例实现
    """
    global _self_assessment
    if _self_assessment is None:
        _self_assessment = ContinuousSelfAssessment(config)
    return _self_assessment
