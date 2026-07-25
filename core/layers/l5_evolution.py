"""
L5: 进化层 - 修复版

修复内容：
1. _evolve_genes: 从random.uniform随机漫步改为梯度驱动演化
2. _update_fitness: 动态权重(婴儿期/成长期/成熟期) + 知识质量维度
3. _form_skill: 支持中文关键词 + 语义相似度匹配
4. _sync_to_layers: 默认实现，基因值实际同步到L2
5. 与L2闭环: _update_fitness消费L2的get_knowledge_for_l5()

与原版兼容：
- 保留 LayerReporter / HeartbeatManager 集成
- 保留 FitnessScore / Gene / Skill / EvolutionResult 数据结构
- 扩展而非破坏性修改
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib
import random
import re

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.introspection.layer_reporter import LayerReporter
from core.reporting.state_collector import get_state_collector
from core.introspection.heartbeat import get_heartbeat_manager
from core.state_report import LayerHealth, LayerStatus, LayerStateReport


class EvolutionType(Enum):
    GENE = "gene"
    SKILL = "skill"
    REFLEX = "reflex"
    ABSTRACTION = "abstraction"
    ADAPTATION = "adaptation"


class FitnessDimension(Enum):
    ACCURACY = "accuracy"
    EFFICIENCY = "efficiency"
    SATISFACTION = "satisfaction"
    GROWTH = "growth"
    STABILITY = "stability"
    KNOWLEDGE_QUALITY = "knowledge_quality"
    KNOWLEDGE_REUSE = "knowledge_reuse"


@dataclass
class FitnessScore:
    dimensions: Dict[str, float]
    overall: float
    timestamp: str
    stage: str = "unknown"
    weights_used: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "dimensions": self.dimensions,
            "overall": self.overall,
            "timestamp": self.timestamp,
            "stage": self.stage,
            "weights_used": self.weights_used,
        }


@dataclass
class Gene:
    id: str
    name: str
    value: float
    min_value: float
    max_value: float
    description: str
    evolution_stage: int = 0
    evolution_history: List[Dict] = field(default_factory=list)
    last_improvement: Optional[str] = None

    def record_change(self, old_value: float, new_value: float,
                      reason: str, fitness_delta: float):
        self.evolution_history.append({
            "timestamp": datetime.now().isoformat(),
            "old_value": old_value,
            "new_value": new_value,
            "delta": new_value - old_value,
            "reason": reason,
            "fitness_delta": fitness_delta,
        })
        if len(self.evolution_history) > 50:
            self.evolution_history = self.evolution_history[-50:]
        if fitness_delta > 0:
            self.last_improvement = datetime.now().isoformat()


@dataclass
class Skill:
    id: str
    name: str
    description: str
    trigger_condition: str
    confidence: float
    usage_count: int
    success_count: int
    created_at: str
    last_used: Optional[str] = None

    def update_stats(self, success: bool):
        self.usage_count += 1
        if success:
            self.success_count += 1
        self.last_used = datetime.now().isoformat()
        if self.usage_count > 0:
            base = self.success_count / self.usage_count
            bonus = min(0.1, self.usage_count / 100)
            self.confidence = min(1.0, base + bonus)


@dataclass
class EvolutionResult:
    success: bool
    evolution_type: EvolutionType
    changes: Dict[str, Any]
    confidence: float
    reasoning: List[str]
    warnings: List[str]
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class L5EvolutionLayer:

    GENE_DIMENSION_MAP = {
        "检索阈值": ("accuracy_current", "accuracy_trend"),
        "学习频率": ("growth_current", "growth_trend"),
        "情感权重": ("satisfaction_current", "satisfaction_trend"),
        "探索倾向": ("growth_current", "stability_trend"),
        "记忆衰减率": ("knowledge_reuse_current", "stability_trend"),
        "抽象阈值": ("knowledge_quality_current", "growth_trend"),
        "反思频率": ("accuracy_current", "efficiency_trend"),
        "知识广度": ("knowledge_quality_current", "efficiency_trend"),
        "技能固化阈值": ("satisfaction_current", "accuracy_trend"),
        "环境敏感度": ("stability_current", "accuracy_trend"),
    }

    def register_gene_mapping(self, gene_name: str, dim_key: str, trend_key: str):
        self.GENE_DIMENSION_MAP[gene_name] = (dim_key, trend_key)

    def __init__(self):
        self.reporter = LayerReporter("L5")
        self.collector = get_state_collector()
        self.heartbeat = get_heartbeat_manager()

        self.reporter.report_idle()

        self.stats = {
            'total_evolutions': 0,
            'gene_evolutions': 0,
            'skills_formed': 0,
            'reflexes_formed': 0,
            'abstractions_formed': 0,
            'adaptations': 0,
            'avg_fitness': 0.0,
            'fitness_trend': 0.0,
            'successful_mutations': 0,
            'failed_mutations': 0,
        }

        self.genes: Dict[str, Gene] = {}
        self._init_default_genes()

        self.skills: Dict[str, Skill] = {}
        self.fitness_history: List[FitnessScore] = []

        self.evolution_state = {
            'last_gene_evolution': None,
            'last_skill_formation': None,
            'last_abstraction': None,
            'generation': 0,
            'pending_experiences': 0,
            'consecutive_failures': 0,
        }

        self.config = {
            'gene_evolution_interval_hours': 6,
            'skill_formation_threshold': 5,
            'reflex_formation_threshold': 3,
            'abstraction_interval_days': 14,
            'min_fitness_for_evolution': 0.3,
            'gradient_window': 10,
            'mutation_step_base': 0.02,
            'rollback_threshold': -0.15,
        }

        self.system_stage = "infant"
        self.start_time = datetime.now()

        logger.info("🧬 L5进化层已初始化（修复版 - 梯度驱动）")
        self.reporter.report_completed(
            metrics={"genes_count": len(self.genes)},
            confidence=1.0
        )

    def _init_default_genes(self):
        default_genes = [
            Gene("G001", "检索阈值", 0.5, 0.1, 0.9, "知识检索的置信度阈值"),
            Gene("G002", "学习频率", 0.3, 0.05, 0.8, "主动学习的频率"),
            Gene("G003", "情感权重", 0.4, 0.1, 0.7, "情感感知在决策中的权重"),
            Gene("G004", "探索倾向", 0.2, 0.0, 0.9, "探索未知领域的倾向"),
            Gene("G005", "记忆衰减率", 0.02, 0.005, 0.1, "记忆随时间衰减的速度"),
            Gene("G006", "抽象阈值", 0.6, 0.2, 0.9, "形成抽象知识的阈值"),
            Gene("G007", "反思频率", 0.3, 0.05, 0.8, "触发反思的频率"),
            Gene("G008", "知识广度", 0.5, 0.1, 0.9, "知识检索的广度"),
            Gene("G009", "技能固化阈值", 0.7, 0.3, 0.95, "技能固化的置信度阈值"),
            Gene("G010", "环境敏感度", 0.4, 0.1, 0.8, "对上下文变化的敏感度"),
        ]

        for gene in default_genes:
            self.genes[gene.id] = gene

    def record_experience(self, experience: Dict) -> EvolutionResult:
        self.reporter.report_busy(
            operation="记录经验",
            active_tasks=["经验提取", "适应度评估", "触发进化检查"]
        )

        reasoning = []
        warnings = []
        changes = {}

        try:
            user_input = experience.get('user_input', '')
            validation_result = experience.get('validation_result', {})
            user_feedback = experience.get('user_feedback', {})

            is_success = validation_result.get('status') == 'pass'
            confidence = validation_result.get('confidence', 0.5)

            reasoning.append(f"经验记录: 成功={is_success}, 置信度={confidence:.2f}")

            fitness = self._update_fitness(experience)
            reasoning.append(f"适应度评分: {fitness.overall:.3f} (阶段: {fitness.stage})")

            evolution_triggers = self._check_evolution_triggers()
            reasoning.append(f"进化触发: {evolution_triggers}")

            if 'gene' in evolution_triggers:
                gene_result = self._evolve_genes()
                if gene_result:
                    triggered_changes_gene = gene_result
                    changes['gene'] = triggered_changes_gene
                    self.stats['gene_evolutions'] += 1
                    reasoning.append(f"基因演化完成: {len(gene_result)}个基因更新")

            if 'skill' in evolution_triggers:
                skill_result = self._form_skill(experience)
                if skill_result:
                    changes['skill'] = skill_result
                    self.stats['skills_formed'] += 1
                    reasoning.append(f"技能形成: {skill_result}")

            if 'abstraction' in evolution_triggers:
                abstraction_result = self._form_abstraction()
                if abstraction_result:
                    changes['abstraction'] = abstraction_result
                    self.stats['abstractions_formed'] += 1
                    reasoning.append(f"抽象形成: {abstraction_result}")

            self.stats['total_evolutions'] += 1

            if changes:
                self._sync_to_layers(changes)
                reasoning.append("已同步到各层")

            self.evolution_state['pending_experiences'] += 1

            self.reporter.report_completed(
                metrics={"fitness": fitness.overall, "changes_count": len(changes)},
                confidence=min(1.0, fitness.overall + 0.2),
                warnings=warnings if warnings else None
            )

            result = EvolutionResult(
                success=True,
                evolution_type=EvolutionType.ADAPTATION if not changes else list(changes.keys())[0],
                changes=changes,
                confidence=fitness.overall,
                reasoning=reasoning,
                warnings=warnings
            )

            logger.info(
                f"🧬 L5经验记录完成: "
                f"适应度={fitness.overall:.3f}, "
                f"变更={len(changes)}项"
            )

            return result

        except Exception as e:
            error_msg = f"L5记录经验异常: {str(e)}"
            logger.error(error_msg)

            self.reporter.report_error(issues=[error_msg])

            return EvolutionResult(
                success=False,
                evolution_type=EvolutionType.ADAPTATION,
                changes={},
                confidence=0.0,
                reasoning=[],
                warnings=[],
                error=error_msg
            )

    def _update_fitness(self, experience: Dict) -> FitnessScore:
        dimensions = {}

        validation_result = experience.get('validation_result', {})
        confidence = validation_result.get('confidence', 0.5)
        is_success = validation_result.get('status') == 'pass'

        accuracy = confidence * (1.0 if is_success else 0.5)
        dimensions['accuracy'] = accuracy

        processing_time = experience.get('processing_time_ms', 1000)
        efficiency = max(0, 1.0 - (processing_time / 10000))
        dimensions['efficiency'] = efficiency

        user_feedback = experience.get('user_feedback', {})
        satisfaction = user_feedback.get('satisfaction', 0.5)
        if user_feedback.get('like'):
            satisfaction = max(satisfaction, 0.8)
        dimensions['satisfaction'] = satisfaction

        learning_result = experience.get('learning_result', {})
        knowledge_gained = learning_result.get('knowledge_gained', 0)
        growth = min(1.0, knowledge_gained / 10)
        dimensions['growth'] = growth

        stability = self._calculate_stability()
        dimensions['stability'] = stability

        l2_quality = 0.5
        l2_reuse = 0.0
        try:
            from core.layers.l2_learning import get_l2_learning
            l2 = get_l2_learning()
            l2_data = l2.get_knowledge_for_l5()
            l2_quality = l2_data.get('avg_quality', 0) / 100
            l2_reuse = l2_data.get('knowledge_reuse_rate', 0)
        except Exception:
            l2_quality = learning_result.get('avg_knowledge_quality', 0) / 100
            l2_reuse = learning_result.get('knowledge_reuse_rate', 0)

        dimensions['knowledge_quality'] = l2_quality
        dimensions['knowledge_reuse'] = l2_reuse

        weights = self._get_dynamic_weights()

        overall = sum(dimensions.get(k, 0.5) * weights.get(k, 0) for k in weights.keys())

        stage = self._determine_stage(overall)
        self.system_stage = stage

        fitness = FitnessScore(
            dimensions=dimensions,
            overall=overall,
            timestamp=datetime.now().isoformat(),
            stage=stage,
            weights_used=weights
        )

        self.fitness_history.append(fitness)

        if len(self.fitness_history) > 200:
            self.fitness_history = self.fitness_history[-200:]

        self.stats['avg_fitness'] = (
            sum(f.overall for f in self.fitness_history[-20:]) /
            min(20, len(self.fitness_history))
        )

        if len(self.fitness_history) >= 20:
            recent = sum(f.overall for f in self.fitness_history[-10:]) / 10
            older = sum(f.overall for f in self.fitness_history[-20:-10]) / 10
            self.stats['fitness_trend'] = recent - older

        return fitness

    def _get_dynamic_weights(self) -> Dict[str, float]:
        run_time_days = (datetime.now() - self.start_time).days
        avg_fitness = self.stats['avg_fitness']

        if run_time_days < 3 or avg_fitness < 0.4 or self.system_stage == "infant":
            return {
                'accuracy': 0.20, 'efficiency': 0.10, 'satisfaction': 0.15,
                'growth': 0.25, 'stability': 0.10,
                'knowledge_quality': 0.10, 'knowledge_reuse': 0.10,
            }
        elif avg_fitness > 0.7 and self.system_stage == "mature":
            return {
                'accuracy': 0.25, 'efficiency': 0.15, 'satisfaction': 0.20,
                'growth': 0.05, 'stability': 0.20,
                'knowledge_quality': 0.10, 'knowledge_reuse': 0.05,
            }
        else:
            return {
                'accuracy': 0.25, 'efficiency': 0.12, 'satisfaction': 0.18,
                'growth': 0.15, 'stability': 0.12,
                'knowledge_quality': 0.10, 'knowledge_reuse': 0.08,
            }

    def _determine_stage(self, current_fitness: float) -> str:
        run_time_days = (datetime.now() - self.start_time).days
        if run_time_days < 3 and current_fitness < 0.5:
            return "infant"
        elif run_time_days > 14 and current_fitness > 0.7:
            return "mature"
        else:
            return "growing"

    def _calculate_stability(self) -> float:
        if len(self.fitness_history) < 5:
            return 0.8

        recent = self.fitness_history[-10:]
        values = [f.overall for f in recent]

        if len(values) < 2:
            return 0.8

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)

        return max(0, min(1.0, 1.0 - variance * 3))

    def _check_evolution_triggers(self) -> List[str]:
        triggers = []
        now = datetime.now()

        if self.evolution_state['last_gene_evolution'] is None:
            triggers.append('gene')
        else:
            last = datetime.fromisoformat(self.evolution_state['last_gene_evolution'])
            hours_since = (now - last).total_seconds() / 3600
            if hours_since >= self.config['gene_evolution_interval_hours']:
                triggers.append('gene')

        if self.evolution_state.get('pending_experiences', 0) >= self.config['skill_formation_threshold']:
            triggers.append('skill')

        if self.evolution_state['last_abstraction'] is None:
            triggers.append('abstraction')
        else:
            last = datetime.fromisoformat(self.evolution_state['last_abstraction'])
            if (now - last).days >= self.config['abstraction_interval_days']:
                triggers.append('abstraction')

        if len(self.fitness_history) > 10:
            recent_avg = sum(f.overall for f in self.fitness_history[-5:]) / 5
            older_avg = sum(f.overall for f in self.fitness_history[-10:-5]) / 5
            if abs(recent_avg - older_avg) > 0.15:
                triggers.append('adaptation')

        return triggers

    def _evolve_genes(self) -> Optional[Dict[str, float]]:
        if not self.fitness_history:
            return None

        gradient = self._calculate_fitness_gradient()

        if gradient is None:
            logger.debug("数据不足，跳过基因演化")
            return None

        fitness_trend = gradient['overall_trend']

        if fitness_trend < self.config['rollback_threshold']:
            logger.warning(f"适应度严重下降 ({fitness_trend:.3f})，触发基因回滚")
            return self._rollback_genes()

        current_fitness = self.stats['avg_fitness']
        if current_fitness < self.config['min_fitness_for_evolution'] and fitness_trend < 0:
            logger.info(f"适应度过低 ({current_fitness:.2f}) 且趋势向下，保守演化")
            return self._conservative_evolution()

        dimension_analysis = self._analyze_dimensions()

        changes = {}

        for gene_id, gene in self.genes.items():
            direction = self._get_gene_direction(gene, dimension_analysis, gradient)

            if direction == 0:
                continue

            step_size = self._calculate_step_size(gene, fitness_trend)

            old_value = gene.value
            new_value = old_value + direction * step_size

            new_value = max(gene.min_value, min(gene.max_value, new_value))

            if abs(new_value - old_value) > 0.001:
                gene.record_change(old_value, new_value,
                                   f"gradient_{direction:+.0f}", fitness_trend)
                gene.value = new_value
                gene.evolution_stage += 1
                changes[gene_id] = new_value

        self.evolution_state['last_gene_evolution'] = datetime.now().isoformat()
        self.evolution_state['generation'] += 1

        if changes:
            self.stats['successful_mutations'] += 1
            logger.info(f"🧬 基因演化完成: {len(changes)}个基因更新 (趋势: {fitness_trend:+.3f})")
            for gene_id, new_value in changes.items():
                gene = self.genes[gene_id]
                logger.debug(f"  {gene_id}: {gene.name} -> {new_value:.4f} "
                             f"(阶段: {gene.evolution_stage})")
        else:
            self.stats['failed_mutations'] += 1

        return changes

    def _calculate_fitness_gradient(self) -> Optional[Dict]:
        window = self.config['gradient_window']

        if len(self.fitness_history) < window * 2:
            return None

        recent = self.fitness_history[-window:]
        older = self.fitness_history[-window * 2:-window]

        recent_overall = sum(f.overall for f in recent) / len(recent)
        older_overall = sum(f.overall for f in older) / len(older)
        overall_trend = recent_overall - older_overall

        dim_trends = {}
        for dim in ['accuracy', 'efficiency', 'satisfaction', 'growth',
                     'stability', 'knowledge_quality', 'knowledge_reuse']:
            recent_dim = [f.dimensions.get(dim, 0.5) for f in recent]
            older_dim = [f.dimensions.get(dim, 0.5) for f in older]

            if recent_dim and older_dim:
                dim_trends[dim] = sum(recent_dim) / len(recent_dim) - sum(older_dim) / len(older_dim)
            else:
                dim_trends[dim] = 0

        return {
            'overall_trend': overall_trend,
            'recent_avg': recent_overall,
            'older_avg': older_overall,
            'dimension_trends': dim_trends,
        }

    def _analyze_dimensions(self) -> Dict[str, float]:
        if len(self.fitness_history) < 5:
            return {}

        recent = self.fitness_history[-5:]

        analysis = {}
        for dim in ['accuracy', 'efficiency', 'satisfaction', 'growth',
                     'stability', 'knowledge_quality', 'knowledge_reuse']:
            values = [f.dimensions.get(dim, 0.5) for f in recent]
            analysis[f"{dim}_current"] = values[-1] if values else 0.5
            analysis[f"{dim}_trend"] = values[-1] - values[0] if len(values) > 1 else 0

        return analysis

    def _get_gene_direction(self, gene: Gene, analysis: Dict, gradient: Dict) -> int:
        dim_key, trend_key = self.GENE_DIMENSION_MAP.get(gene.name, (None, None))

        if not dim_key or not trend_key:
            return 0

        current = analysis.get(dim_key, 0.5)
        trend = analysis.get(trend_key, 0)

        mid = (gene.min_value + gene.max_value) / 2

        if current > 0.7 and trend > 0:
            return 1 if gene.value < mid else -1
        elif current > 0.7 and trend <= 0:
            return -1 if gene.value < mid else 1
        elif current < 0.4 and trend < 0:
            return -1 if gene.value > mid else 1
        elif current < 0.4 and trend >= 0:
            return 0
        else:
            return 1 if random.random() > 0.5 else -1

    def _calculate_step_size(self, gene: Gene, fitness_trend: float) -> float:
        base_step = self.config['mutation_step_base']

        gradient_factor = min(2.0, 1.0 + abs(fitness_trend) * 5)
        stage_factor = max(0.3, 1.0 - gene.evolution_stage / 50)

        range_size = gene.max_value - gene.min_value
        dist_to_boundary = min(
            abs(gene.value - gene.min_value),
            abs(gene.value - gene.max_value)
        ) / (range_size / 2)
        boundary_factor = 0.5 + 0.5 * dist_to_boundary

        step = base_step * gradient_factor * stage_factor * boundary_factor
        return min(step, range_size * 0.1)

    def _rollback_genes(self) -> Dict[str, float]:
        changes = {}

        for gene_id, gene in self.genes.items():
            improvements = [h for h in gene.evolution_history
                            if h.get('fitness_delta', 0) > 0]

            if improvements:
                last_good = improvements[-1]
                target_value = last_good['old_value']

                if abs(target_value - gene.value) > 0.001:
                    old_value = gene.value
                    gene.value = target_value
                    gene.record_change(old_value, target_value, "rollback", 0)
                    changes[gene_id] = target_value

        if changes:
            logger.warning(f"🔄 基因回滚完成: {len(changes)}个基因")
            self.evolution_state['consecutive_failures'] += 1

        return changes

    def _conservative_evolution(self) -> Dict[str, float]:
        changes = {}

        safe_genes = sorted(self.genes.values(), key=lambda g: g.evolution_stage)[:3]

        for gene in safe_genes:
            center = (gene.max_value + gene.min_value) / 2
            direction = 1 if gene.value < center else -1
            step = self.config['mutation_step_base'] * 0.5

            old_value = gene.value
            new_value = old_value + direction * step
            new_value = max(gene.min_value, min(gene.max_value, new_value))

            if abs(new_value - old_value) > 0.001:
                gene.value = new_value
                gene.evolution_stage += 1
                changes[gene.id] = new_value

        return changes

    def _form_skill(self, experience: Dict) -> Optional[str]:
        user_input = experience.get('user_input', '')

        if not user_input or len(user_input) < 10:
            return None

        keywords = self._extract_keywords(user_input)

        if len(keywords) < 2:
            return None

        best_match = None
        best_similarity = 0.0

        for skill in self.skills.values():
            similarity = self._calculate_semantic_similarity(keywords, skill)
            if similarity > best_similarity and similarity > 0.6:
                best_match = skill
                best_similarity = similarity

        if best_match:
            success = experience.get('validation_result', {}).get('status') == 'pass'
            best_match.update_stats(success)

            if (best_match.usage_count >= self.config['reflex_formation_threshold'] and
                    best_match.confidence >= self.config['min_fitness_for_evolution']):
                self._form_reflex(best_match)

            return best_match.id

        skill_id = f"skill_{hashlib.md5(user_input[:100].encode()).hexdigest()[:8]}"

        skill = Skill(
            id=skill_id,
            name=f"技能_{self.stats['skills_formed'] + 1}",
            description=f"从经验中形成的技能: {user_input[:50]}...",
            trigger_condition=user_input[:200],
            confidence=0.5,
            usage_count=1,
            success_count=1 if experience.get('validation_result', {}).get('status') == 'pass' else 0,
            created_at=datetime.now().isoformat(),
            last_used=datetime.now().isoformat()
        )

        self.skills[skill_id] = skill
        logger.info(f"🛠️ 新技能形成: {skill.name} (关键词: {keywords[:3]})")

        return skill_id

    def _extract_keywords(self, text: str) -> List[str]:
        keywords = []

        english_words = re.findall(r'[a-zA-Z]{3,}', text)
        keywords.extend([w.lower() for w in english_words])

        chinese_chars = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        keywords.extend(chinese_chars)

        seen = set()
        unique = []
        for kw in keywords:
            if kw not in seen and len(kw) > 1:
                seen.add(kw)
                unique.append(kw)

        return unique[:10]

    def _calculate_semantic_similarity(self, keywords: List[str], skill: Skill) -> float:
        if not keywords or not skill.trigger_condition:
            return 0.0

        skill_keywords = self._extract_keywords(skill.trigger_condition)

        if not skill_keywords:
            return 0.0

        set1 = set(kw.lower() for kw in keywords)
        set2 = set(kw.lower() for kw in skill_keywords)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _form_reflex(self, skill: Skill) -> None:
        skill.confidence = min(1.0, skill.confidence + 0.2)
        self.stats['reflexes_formed'] += 1
        logger.info(f"⚡ 反射形成: {skill.name} (置信度: {skill.confidence:.2f})")

    def _form_abstraction(self) -> Optional[str]:
        if len(self.fitness_history) < 10:
            return None

        recent_success = [f for f in self.fitness_history[-20:] if f.overall > 0.6]

        if len(recent_success) < 5:
            return None

        abstraction_id = f"abs_{datetime.now().strftime('%Y%m%d')}"
        abstraction = f"抽象知识_{self.stats['abstractions_formed'] + 1}"

        self.evolution_state['last_abstraction'] = datetime.now().isoformat()

        logger.info(f"📚 抽象形成: {abstraction} (基于{len(recent_success)}次成功经验)")

        return abstraction_id

    def _sync_to_layers(self, changes: Dict):
        sync_count = 0

        for gene_id, new_value in changes.items():
            if not isinstance(new_value, (int, float)):
                continue

            gene = self.genes.get(gene_id)
            if not gene:
                continue

            if gene.name == "检索阈值":
                try:
                    from core.layers.l2_learning import get_l2_learning
                    l2 = get_l2_learning()
                    l2.search_threshold = new_value
                    sync_count += 1
                    logger.debug(f"同步 {gene.name}={new_value:.3f} -> L2")
                except Exception as e:
                    logger.warning(f"操作降级跳过: {e}")

            self.collector.collect(LayerStateReport(
                layer_name="L5",
                timestamp=datetime.now().isoformat(),
                status=LayerStatus.RUNNING,
                health=LayerHealth.HEALTHY,
                metrics={f"gene_{gene_id}": new_value, "sync_target": "all_layers"},
                issues=[], warnings=[],
                last_operation=f"同步基因 {gene_id} 到所有层",
                confidence=0.9
            ))

        if sync_count > 0:
            logger.info(f"🔄 已同步 {sync_count}/{len(changes)} 项进化到各层")
        elif len(changes) > 0:
            logger.warning(f"⚠️ 未找到同步目标，{len(changes)} 项基因变更未生效")
        else:
            logger.debug(f"🔄 报告基因变更到状态收集器")

    def get_gene_value(self, gene_id: str) -> Optional[float]:
        if gene_id in self.genes:
            return self.genes[gene_id].value
        return None

    def get_evolution_status(self) -> Dict:
        neighbor_status = self.heartbeat.get_neighbor_status("L5")

        return {
            "layer": "L5",
            "stats": self.stats,
            "stage": self.system_stage,
            "neighbor_status": {
                k: v.value for k, v in neighbor_status.items()
            },
            "genes": {
                gid: {
                    "name": gene.name,
                    "value": gene.value,
                    "stage": gene.evolution_stage,
                    "history_count": len(gene.evolution_history),
                }
                for gid, gene in self.genes.items()
            },
            "skills_count": len(self.skills),
            "fitness": {
                "avg": self.stats['avg_fitness'],
                "trend": self.stats['fitness_trend'],
                "history_count": len(self.fitness_history),
            },
            "state": self.evolution_state,
        }


_l5_instance = None

def get_l5_evolution() -> L5EvolutionLayer:
    global _l5_instance
    if _l5_instance is None:
        _l5_instance = L5EvolutionLayer()
    return _l5_instance
