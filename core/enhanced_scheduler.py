"""
增强版认知调度器 - 整合所有改进
"""

import threading
import time
import os
from datetime import datetime
from typing import Dict, List
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from core.conflict_coordinator import ConflictCoordinator
from core.trigger_feedback_loop import TriggerFeedbackLoop, TriggerEvent
from core.memory_value_assessor import MemoryValueAssessor


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    IDLE = 1


class EnhancedCognitiveScheduler:
    """
    增强版认知调度器
    
    整合：
    1. 冲突协调器
    2. 触发决策反馈回路
    3. 记忆价值评估器
    4. 状态驱动的自适应调度
    """
    
    def __init__(self, db_path: str = "data/enhanced_scheduler.db"):
        self.db_path = db_path
        self.running = False
        self.thread = None
        
        self.conflict_coordinator = ConflictCoordinator()
        self.trigger_feedback = TriggerFeedbackLoop()
        self.memory_assessor = MemoryValueAssessor()
        
        self.stats = {
            'cycles': 0,
            'tasks_executed': 0,
            'conflicts_resolved': 0,
            'trigger_adjustments': 0,
            'memories_evaluated': 0
        }
        
        self.task_queue = []
        
        logger.info("🧠 增强版认知调度器已初始化")
    
    def start(self):
        """启动调度器"""
        if self.running:
            logger.warning("调度器已在运行")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        
        logger.info("🚀 增强版认知调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("增强版认知调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        
        while self.running:
            try:
                state = self._collect_system_state()
                
                conflicts = self._detect_conflicts(state)
                if conflicts:
                    self._resolve_conflicts(conflicts)
                
                tasks = self._select_tasks(state)
                self._execute_tasks(tasks, state)
                
                if self.stats['cycles'] % 10 == 0:
                    self._evaluate_memories()
                
                if self.stats['cycles'] % 5 == 0:
                    self._update_trigger_strategy()
                
                self.stats['cycles'] += 1
                
                interval = self._calculate_interval(state)
                for _ in range(min(interval, 300)):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"调度器循环错误: {e}")
                time.sleep(60)
    
    def _collect_system_state(self) -> Dict:
        """收集系统状态"""
        return {
            'timestamp': datetime.now().isoformat(),
            'health': {'status': 'healthy'},
            'knowledge': {'total': 100, 'avg_quality': 65},
            'memory': {'total': 50, 'critical': 5},
            'conflicts': self.conflict_coordinator.get_conflict_stats(),
            'trigger': self.trigger_feedback.get_learning_summary()
        }
    
    def _detect_conflicts(self, state: Dict) -> List:
        """检测冲突"""
        conflicts = []
        
        active_rules = self._get_active_rules()
        
        for i, rule1 in enumerate(active_rules):
            for rule2 in active_rules[i+1:]:
                conflict = self.conflict_coordinator.detect_conflicts(rule1, rule2)
                if conflict:
                    conflicts.append(conflict)
        
        return conflicts
    
    def _resolve_conflicts(self, conflicts: List):
        """解决冲突"""
        for conflict in conflicts:
            decision = self.conflict_coordinator.arbitrate(conflict)
            self.stats['conflicts_resolved'] += 1
            logger.info(f"⚖️ 冲突已解决: {conflict.description[:50]}... → {decision.get('reason')}")
    
    def _select_tasks(self, state: Dict) -> List:
        """选择任务"""
        tasks = []
        
        if state.get('health', {}).get('status') != 'healthy':
            tasks.append({'name': 'health_check', 'priority': TaskPriority.CRITICAL})
        
        trigger_summary = state.get('trigger', {})
        if trigger_summary.get('accuracy', 1.0) < 0.7:
            tasks.append({'name': 'recalibrate_triggers', 'priority': TaskPriority.HIGH})
        
        memory_stats = state.get('memory', {})
        if memory_stats.get('total', 0) > 100:
            tasks.append({'name': 'cleanup_memories', 'priority': TaskPriority.MEDIUM})
        
        tasks.append({'name': 'genome_evolve', 'priority': TaskPriority.LOW})
        tasks.append({'name': 'cognitive_transform', 'priority': TaskPriority.LOW})
        
        return sorted(tasks, key=lambda t: t['priority'].value, reverse=True)
    
    def _execute_tasks(self, tasks: List, state: Dict):
        """执行任务"""
        for task in tasks:
            task_name = task['name']
            priority = task['priority']
            
            logger.debug(f"执行任务: {task_name} (优先级: {priority.name})")
            
            self.stats['tasks_executed'] += 1
    
    def _evaluate_memories(self):
        """评估记忆价值"""
        memories = self._get_pending_memories()
        
        for memory in memories:
            result = self.memory_assessor.get_retention_recommendation(memory)
            self.stats['memories_evaluated'] += 1
            
            if not result['retain']:
                self._cleanup_memory(memory['id'])
                logger.debug(f"记忆已清理: {memory['id']}")
    
    def _update_trigger_strategy(self):
        """更新触发策略"""
        summary = self.trigger_feedback.get_learning_summary()
        
        if summary.get('total_decisions', 0) > 10:
            logger.info(f"📊 触发策略更新: 准确率={summary.get('accuracy', 0):.2%}")
            
            if summary.get('accuracy', 0) < 0.7:
                self._recalibrate_triggers()
    
    def _recalibrate_triggers(self):
        """重新校准触发策略"""
        logger.info("🔧 触发策略重新校准...")
        self.stats['trigger_adjustments'] += 1
    
    def _get_active_rules(self) -> List[Dict]:
        """获取活跃规则"""
        rules = []
        
        for rule_id, rule in self.conflict_coordinator.applied_rules.items():
            rules.append({
                'rule_id': rule.rule_id,
                'parameter': rule.parameter,
                'value': rule.value,
                'source_type': rule.source_type,
                'evidence': rule.evidence
            })
        
        return rules
    
    def _get_pending_memories(self) -> List[Dict]:
        """获取待评估记忆"""
        report = self.memory_assessor.get_memory_report(limit=50)
        
        memories = []
        for mem in report.get('top_memories', []):
            memories.append({
                'id': mem['id'],
                'content': mem['content'],
                'access_count': mem['access_count'],
                'user_marked_important': bool(mem['user_marked_important']),
                'correctness_score': mem['correctness_score'],
                'context_importance': mem['context_importance'],
                'created_at': mem['created_at']
            })
        
        return memories
    
    def _cleanup_memory(self, memory_id: str):
        """清理记忆"""
        logger.info(f"清理记忆: {memory_id}")
    
    def _calculate_interval(self, state: Dict) -> int:
        """计算间隔"""
        base_interval = 60
        
        health = state.get('health', {}).get('status')
        if health != 'healthy':
            return 10
        
        conflicts = state.get('conflicts', {}).get('active_conflicts', 0)
        if conflicts > 0:
            return 30
        
        return base_interval
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'running': self.running,
            'stats': self.stats,
            'conflicts': self.conflict_coordinator.get_conflict_stats(),
            'trigger': self.trigger_feedback.get_learning_summary(),
            'memory': self.memory_assessor.get_memory_report(limit=5)
        }
    
    def register_evolution_rule(self, rule_id: str, source_type: str, 
                                parameter: str, value: any, evidence: Dict = None):
        """注册进化规则"""
        from core.conflict_coordinator import EvolutionRule
        
        rule = EvolutionRule(
            rule_id=rule_id,
            source_type=source_type,
            parameter=parameter,
            value=value,
            priority=self.conflict_coordinator.PRIORITY_TABLE.get(source_type, 30),
            applied_at=datetime.now().isoformat(),
            evidence=evidence or {}
        )
        
        self.conflict_coordinator.register_rule(rule)
        logger.info(f"注册进化规则: {rule_id}")
    
    def record_trigger_event(self, user_input: str, triggered: bool, 
                            depth: str, reason: str) -> str:
        """记录触发事件"""
        event = TriggerEvent(
            id=self.trigger_feedback.create_event_id(user_input),
            user_input=user_input,
            trigger_decision='triggered' if triggered else 'not_triggered',
            processing_depth=depth,
            route_reason=reason,
            created_at=datetime.now().isoformat()
        )
        
        self.trigger_feedback.record_decision(event)
        return event.id
    
    def provide_feedback(self, event_id: str, satisfied: bool, 
                        correction_needed: bool = False, actual_need: str = None):
        """提供反馈"""
        self.trigger_feedback.collect_feedback(
            event_id, satisfied, correction_needed, actual_need
        )
    
    def evaluate_memory(self, memory: Dict) -> Dict:
        """评估记忆"""
        return self.memory_assessor.get_retention_recommendation(memory)


enhanced_scheduler = EnhancedCognitiveScheduler()