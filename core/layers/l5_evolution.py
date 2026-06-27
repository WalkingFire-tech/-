"""
L5: 进化层 - 从每次对话中提取经验，沉淀为长期能力

职责：
1. 基因演化：从适应度评估中优化系统参数
2. 认知转化：将经验固化为技能和反射
3. 适应度评估：衡量系统的整体表现
4. 跨层同步：将演化结果应用到所有层

核心机制：
- 适应度评分（每次对话后更新）
- 基因参数优化（定期执行）
- 经验归档（永久存储有价值的经验）
- 技能形成（从重复经验中抽象出技能）

与下游L6的关系：
L6是"观察者"，L5是"行动者"。
L6观察系统状态，L5根据观察结果采取行动。
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
    """进化类型"""
    GENE = "gene"
    SKILL = "skill"
    REFLEX = "reflex"
    ABSTRACTION = "abstraction"
    ADAPTATION = "adaptation"


class FitnessDimension(Enum):
    """适应度维度"""
    ACCURACY = "accuracy"
    EFFICIENCY = "efficiency"
    SATISFACTION = "satisfaction"
    GROWTH = "growth"
    STABILITY = "stability"


@dataclass
class FitnessScore:
    """适应度评分"""
    dimensions: Dict[str, float]
    overall: float
    timestamp: str
    
    def to_dict(self) -> Dict:
        return {
            "dimensions": self.dimensions,
            "overall": self.overall,
            "timestamp": self.timestamp
        }


@dataclass
class Gene:
    """基因参数"""
    id: str
    name: str
    value: float
    min_value: float
    max_value: float
    description: str
    evolution_stage: int = 0


@dataclass
class Skill:
    """技能"""
    id: str
    name: str
    description: str
    trigger_condition: str
    confidence: float
    usage_count: int
    success_count: int
    created_at: str
    last_used: Optional[str] = None


@dataclass
class EvolutionResult:
    """进化结果"""
    success: bool
    evolution_type: EvolutionType
    changes: Dict[str, Any]
    confidence: float
    reasoning: List[str]
    warnings: List[str]
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class L5EvolutionLayer:
    """L5: 进化层"""
    
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
        }
        
        self.config = {
            'gene_evolution_interval_days': 7,
            'skill_formation_threshold': 5,
            'reflex_formation_threshold': 3,
            'abstraction_interval_days': 14,
            'min_fitness_for_evolution': 0.3,
        }
        
        logger.info("🧬 L5进化层已初始化（含状态报告 + 多维度适应度）")
        self.reporter.report_completed(
            metrics={
                "genes_count": len(self.genes),
                "gene_evolution_interval": self.config['gene_evolution_interval_days']
            },
            confidence=1.0
        )
    
    def _init_default_genes(self):
        """初始化默认基因"""
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
        """
        记录一次经验（每次对话后调用）
        
        经验包含：
        - 用户输入
        - 系统响应
        - 校验结果（来自L4）
        - 用户反馈（如果有）
        - 处理时间
        - 使用的层
        """
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
            reasoning.append(f"适应度评分: {fitness.overall:.3f}")
            
            evolution_triggers = self._check_evolution_triggers()
            reasoning.append(f"进化触发: {evolution_triggers}")
            
            triggered_changes = {}
            
            if 'gene' in evolution_triggers:
                gene_result = self._evolve_genes()
                if gene_result:
                    triggered_changes['gene'] = gene_result
                    self.stats['gene_evolutions'] += 1
                    reasoning.append(f"基因演化完成: {len(gene_result)}个基因更新")
            
            if 'skill' in evolution_triggers:
                skill_result = self._form_skill(experience)
                if skill_result:
                    triggered_changes['skill'] = skill_result
                    self.stats['skills_formed'] += 1
                    reasoning.append(f"技能形成: {skill_result}")
            
            if 'abstraction' in evolution_triggers:
                abstraction_result = self._form_abstraction()
                if abstraction_result:
                    triggered_changes['abstraction'] = abstraction_result
                    self.stats['abstractions_formed'] += 1
                    reasoning.append(f"抽象形成: {abstraction_result}")
            
            changes = triggered_changes
            self.stats['total_evolutions'] += 1
            
            if changes:
                self._sync_to_layers(changes)
                reasoning.append("已同步到各层")
            
            self.evolution_state['pending_experiences'] += 1
            
            self.reporter.report_completed(
                metrics={
                    "fitness": fitness.overall,
                    "changes_count": len(changes)
                },
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
            
            self.reporter.report_error(
                issues=[error_msg]
            )
            
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
        """更新适应度评分"""
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
        
        weights = {
            'accuracy': 0.30,
            'efficiency': 0.15,
            'satisfaction': 0.25,
            'growth': 0.15,
            'stability': 0.15
        }
        
        overall = sum(dimensions.get(k, 0.5) * weights[k] for k in weights.keys())
        
        fitness = FitnessScore(
            dimensions=dimensions,
            overall=overall,
            timestamp=datetime.now().isoformat()
        )
        
        self.fitness_history.append(fitness)
        
        if len(self.fitness_history) > 100:
            self.fitness_history = self.fitness_history[-100:]
        
        self.stats['avg_fitness'] = (
            sum(f.overall for f in self.fitness_history) / len(self.fitness_history)
        )
        
        return fitness
    
    def _calculate_stability(self) -> float:
        """计算稳定性"""
        if len(self.fitness_history) < 3:
            return 0.8
        
        recent = self.fitness_history[-10:]
        confidences = [f.dimensions.get('accuracy', 0.5) for f in recent]
        
        if len(confidences) < 2:
            return 0.8
        
        mean = sum(confidences) / len(confidences)
        variance = sum((c - mean) ** 2 for c in confidences) / len(confidences)
        
        stability = max(0, 1.0 - variance * 2)
        return min(1.0, stability)
    
    def _check_evolution_triggers(self) -> List[str]:
        """检查进化触发条件"""
        triggers = []
        
        now = datetime.now()
        
        if self.evolution_state['last_gene_evolution'] is None:
            triggers.append('gene')
        else:
            last = datetime.fromisoformat(self.evolution_state['last_gene_evolution'])
            if (now - last).days >= self.config['gene_evolution_interval_days']:
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
            older_avg = sum(f.overall for f in self.fitness_history[-10:-5]) / 5 if len(self.fitness_history) >= 10 else recent_avg
            
            if abs(recent_avg - older_avg) > 0.15:
                triggers.append('adaptation')
        
        return triggers
    
    def _evolve_genes(self) -> Optional[Dict[str, float]]:
        """执行基因演化"""
        if not self.fitness_history:
            return None
        
        current_fitness = self.stats['avg_fitness']
        
        if current_fitness < self.config['min_fitness_for_evolution']:
            logger.info(f"适应度过低 ({current_fitness:.2f})，跳过基因演化")
            return None
        
        changes = {}
        
        for gene_id, gene in self.genes.items():
            if len(self.fitness_history) > 5:
                recent_fitness = [f.dimensions.get('accuracy', 0.5) for f in self.fitness_history[-5:]]
                trend = sum(recent_fitness) / len(recent_fitness)
                
                if gene.name == "检索阈值" and trend < 0.4:
                    delta = random.uniform(0.05, 0.15)
                else:
                    delta = random.uniform(-0.05, 0.05)
            else:
                delta = random.uniform(-0.03, 0.03)
            
            new_value = max(gene.min_value, min(gene.max_value, gene.value + delta))
            
            if abs(new_value - gene.value) > 0.01:
                changes[gene_id] = new_value
                gene.value = new_value
                gene.evolution_stage += 1
        
        self.evolution_state['last_gene_evolution'] = datetime.now().isoformat()
        self.evolution_state['generation'] += 1
        
        if changes:
            logger.info(f"🧬 基因演化完成: {len(changes)}个基因更新")
            for gene_id, new_value in changes.items():
                logger.debug(f"  {gene_id}: {self.genes[gene_id].name} → {new_value:.3f}")
        
        return changes
    
    def _form_skill(self, experience: Dict) -> Optional[str]:
        """从经验中形成技能"""
        user_input = experience.get('user_input', '')
        
        if not user_input:
            return None
        
        words = re.findall(r'[a-zA-Z]{3,}', user_input)
        
        if len(words) < 3:
            return None
        
        for skill in self.skills.values():
            if any(w in skill.trigger_condition for w in words[:3]):
                skill.usage_count += 1
                if experience.get('validation_result', {}).get('status') == 'pass':
                    skill.success_count += 1
                    skill.confidence = min(1.0, skill.confidence + 0.1)
                skill.last_used = datetime.now().isoformat()
                
                if skill.usage_count >= self.config['reflex_formation_threshold'] and \
                   skill.success_count / skill.usage_count >= 0.7:
                    self._form_reflex(skill)
                
                return skill.id
        
        skill_id = f"skill_{hashlib.md5(user_input[:100].encode()).hexdigest()[:8]}"
        skill = Skill(
            id=skill_id,
            name=f"技能_{self.stats['skills_formed'] + 1}",
            description=f"从经验中形成的技能: {user_input[:50]}...",
            trigger_condition=user_input[:100],
            confidence=0.5,
            usage_count=1,
            success_count=1 if experience.get('validation_result', {}).get('status') == 'pass' else 0,
            created_at=datetime.now().isoformat(),
            last_used=datetime.now().isoformat()
        )
        
        self.skills[skill_id] = skill
        logger.info(f"🛠️ 新技能形成: {skill.name} (触发: {skill.trigger_condition[:30]}...)")
        
        return skill_id
    
    def _form_reflex(self, skill: Skill) -> None:
        """将技能固化为反射"""
        skill.confidence = min(1.0, skill.confidence + 0.2)
        self.stats['reflexes_formed'] += 1
        
        logger.info(f"⚡ 反射形成: {skill.name} (置信度: {skill.confidence:.2f})")
    
    def _form_abstraction(self) -> Optional[str]:
        """从多个经验中形成抽象知识"""
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
        """将进化结果同步到各层"""
        for gene_id, new_value in changes.items():
            if isinstance(new_value, (int, float)):
                self.collector.collect(LayerStateReport(
                    layer_name="L5",
                    timestamp=datetime.now().isoformat(),
                    status=LayerStatus.RUNNING,
                    health=LayerHealth.HEALTHY,
                    metrics={
                        f"gene_{gene_id}": new_value,
                        "sync_target": "all_layers"
                    },
                    issues=[],
                    warnings=[],
                    last_operation=f"同步基因 {gene_id} 到所有层",
                    confidence=0.9
                ))
        
        logger.info(f"🔄 已同步 {len(changes)} 项进化到所有层")
    
    def get_gene_value(self, gene_id: str) -> Optional[float]:
        """获取基因当前值"""
        if gene_id in self.genes:
            return self.genes[gene_id].value
        return None
    
    def get_evolution_status(self) -> Dict:
        """获取进化状态"""
        neighbor_status = self.heartbeat.get_neighbor_status("L5")
        
        return {
            "layer": "L5",
            "stats": self.stats,
            "neighbor_status": {
                k: v.value for k, v in neighbor_status.items()
            },
            "genes": {
                gid: {
                    "name": gene.name,
                    "value": gene.value,
                    "stage": gene.evolution_stage
                }
                for gid, gene in self.genes.items()
            },
            "skills_count": len(self.skills),
            "fitness": {
                "avg": self.stats['avg_fitness'],
                "history_count": len(self.fitness_history)
            },
            "state": self.evolution_state
        }


_l5_instance = None

def get_l5_evolution() -> L5EvolutionLayer:
    global _l5_instance
    if _l5_instance is None:
        _l5_instance = L5EvolutionLayer()
    return _l5_instance
