"""
认知驱动的自适应调度器
不再机械执行固定任务，而是基于系统状态动态决策
"""

import threading
import time
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger
import math


# ==================== 任务定义 ====================

class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 5   # 必须立即执行
    HIGH = 4       # 尽快执行
    MEDIUM = 3     # 正常执行
    LOW = 2        # 空闲时执行
    IDLE = 1       # 仅在系统空闲时执行


class TaskCategory(Enum):
    """任务类别"""
    LEARNING = "learning"       # 学习新知识
    CLEANUP = "cleanup"         # 清理和维护
    EVOLUTION = "evolution"     # 基因演化
    TRANSFORMATION = "transformation"  # 认知转化
    REVIEW = "review"          # 回顾和反思
    SANDBOX = "sandbox"        # 进化沙盒


@dataclass
class CognitiveTask:
    """认知任务"""
    id: str
    name: str
    category: TaskCategory
    priority: TaskPriority
    function: callable
    description: str
    
    # 执行状态
    last_run: Optional[datetime] = None
    last_duration: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    
    # 调度元数据
    cooldown_minutes: int = 60  # 冷却时间（分钟）
    max_interval_minutes: int = 1440  # 最大间隔（24小时）
    min_interval_minutes: int = 5  # 最小间隔
    adaptive: bool = True  # 是否自适应调整间隔
    
    def is_ready(self) -> bool:
        """判断任务是否准备就绪（冷却结束）"""
        if self.last_run is None:
            return True
        
        elapsed = (datetime.now() - self.last_run).total_seconds() / 60
        return elapsed >= self.cooldown_minutes


# ==================== 任务注册表 ====================

class TaskRegistry:
    """任务注册表 - 管理所有可执行任务"""
    
    def __init__(self):
        self.tasks: Dict[str, CognitiveTask] = {}
        self._register_default_tasks()
    
    def _register_default_tasks(self):
        """注册默认任务"""
        
        # 学习任务
        self.register(CognitiveTask(
            id="learn_new_knowledge",
            name="学习新知识",
            category=TaskCategory.LEARNING,
            priority=TaskPriority.HIGH,
            function=self._learn_new_knowledge,
            description="从外部搜索获取新知识",
            cooldown_minutes=30
        ))
        
        # 规则生成
        self.register(CognitiveTask(
            id="generate_rules",
            name="生成规则",
            category=TaskCategory.EVOLUTION,
            priority=TaskPriority.MEDIUM,
            function=self._generate_rules,
            description="从经验模式中提取规则",
            cooldown_minutes=60
        ))
        
        # 工具生成
        self.register(CognitiveTask(
            id="generate_tools",
            name="生成工具",
            category=TaskCategory.EVOLUTION,
            priority=TaskPriority.MEDIUM,
            function=self._generate_tools,
            description="自动生成实用工具",
            cooldown_minutes=120
        ))
        
        # 知识清理
        self.register(CognitiveTask(
            id="cleanup_knowledge",
            name="知识清理",
            category=TaskCategory.CLEANUP,
            priority=TaskPriority.MEDIUM,
            function=self._cleanup_knowledge,
            description="清理低质量和过时知识",
            cooldown_minutes=240
        ))
        
        # 质量衰减
        self.register(CognitiveTask(
            id="decay_quality",
            name="质量衰减",
            category=TaskCategory.CLEANUP,
            priority=TaskPriority.LOW,
            function=self._decay_quality,
            description="对长期未访问的知识进行质量衰减",
            cooldown_minutes=180
        ))
        
        # 记忆回顾
        self.register(CognitiveTask(
            id="memory_review",
            name="记忆回顾",
            category=TaskCategory.REVIEW,
            priority=TaskPriority.LOW,
            function=self._memory_review,
            description="生成记忆回顾报告",
            cooldown_minutes=360
        ))
        
        # 认知转化
        self.register(CognitiveTask(
            id="cognitive_transform",
            name="认知转化",
            category=TaskCategory.TRANSFORMATION,
            priority=TaskPriority.LOW,
            function=self._cognitive_transform,
            description="将经验转化为技能和反射",
            cooldown_minutes=720,  # 12小时
            min_interval_minutes=360
        ))
        
        # 基因演化
        self.register(CognitiveTask(
            id="genome_evolve",
            name="基因演化",
            category=TaskCategory.EVOLUTION,
            priority=TaskPriority.LOW,
            function=self._genome_evolve,
            description="基于适应度评估进行基因演化",
            cooldown_minutes=1440,  # 24小时
            min_interval_minutes=720
        ))
        
        # 进化沙盒
        self.register(CognitiveTask(
            id="evolution_sandbox",
            name="进化沙盒",
            category=TaskCategory.SANDBOX,
            priority=TaskPriority.IDLE,
            function=self._evolution_sandbox,
            description="运行多智能体进化模拟",
            cooldown_minutes=2880,  # 48小时
            min_interval_minutes=1440
        ))
        
        # 错误感知
        self.register(CognitiveTask(
            id="error_perception",
            name="错误感知",
            category=TaskCategory.REVIEW,
            priority=TaskPriority.HIGH,
            function=self._error_perception,
            description="检测知识库中的潜在错误",
            cooldown_minutes=60
        ))
    
    def register(self, task: CognitiveTask):
        """注册任务"""
        self.tasks[task.id] = task
    
    def get_task(self, task_id: str) -> Optional[CognitiveTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_ready_tasks(self) -> List[CognitiveTask]:
        """获取所有准备就绪的任务"""
        return [t for t in self.tasks.values() if t.is_ready()]
    
    def get_tasks_by_priority(self, limit: int = 5) -> List[CognitiveTask]:
        """获取按优先级排序的任务"""
        ready = self.get_ready_tasks()
        return sorted(ready, key=lambda t: t.priority.value, reverse=True)[:limit]
    
    # ===== 任务实现（简化） =====
    
    def _learn_new_knowledge(self) -> Dict:
        """学习新知识"""
        return {'success': True, 'learned': 0, 'pending': 0}
    
    def _generate_rules(self) -> Dict:
        """生成规则"""
        return {'success': True, 'rules_count': 0}
    
    def _generate_tools(self) -> Dict:
        """生成工具"""
        return {'success': True, 'tools_count': 0}
    
    def _cleanup_knowledge(self) -> Dict:
        """清理知识"""
        return {'success': True, 'deleted': 0}
    
    def _decay_quality(self) -> Dict:
        """质量衰减"""
        return {'success': True, 'affected': 0}
    
    def _memory_review(self) -> Dict:
        """记忆回顾"""
        return {'success': True, 'review': {}}
    
    def _cognitive_transform(self) -> Dict:
        """认知转化"""
        return {'success': True, 'results': {}}
    
    def _genome_evolve(self) -> Dict:
        """基因演化"""
        return {'success': True, 'fitness': 0.5, 'child_ids': []}
    
    def _evolution_sandbox(self) -> Dict:
        """进化沙盒"""
        return {'success': True, 'result': {}}
    
    def _error_perception(self) -> Dict:
        """错误感知"""
        return {'success': True, 'errors_found': 0}


# ==================== 状态感知器 ====================

class SystemStateSensor:
    """
    系统状态感知器
    收集系统当前状态，为调度决策提供依据
    """
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        
        # 状态缓存
        self._cached_state = None
        self._last_update = None
    
    def sense(self) -> Dict[str, Any]:
        """感知系统状态"""
        
        if self._cached_state and self._last_update:
            elapsed = (datetime.now() - self._last_update).total_seconds()
            if elapsed < 60:  # 1分钟内不刷新
                return self._cached_state
        
        state = {
            'timestamp': datetime.now().isoformat(),
            
            # 知识库状态
            'knowledge': self._get_knowledge_stats(),
            
            # 系统负载
            'load': self._get_load_stats(),
            
            # 健康状态
            'health': self._get_health_stats(),
            
            # 进化状态
            'evolution': self._get_evolution_stats(),
            
            # 学习需求
            'learning_needs': self._get_learning_needs()
        }
        
        self._cached_state = state
        self._last_update = datetime.now()
        
        return state
    
    def _get_knowledge_stats(self) -> Dict:
        """获取知识库统计"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                cur = conn.execute('''
                    SELECT 
                        COUNT(*) as total,
                        AVG(quality_score) as avg_quality,
                        MAX(quality_score) as max_quality,
                        MIN(quality_score) as min_quality,
                        COUNT(CASE WHEN quality_score < 20 THEN 1 END) as low_quality,
                        AVG(access_count) as avg_access
                    FROM knowledge_items
                    WHERE knowledge_type = 'qa'
                ''')
                row = cur.fetchone()
                
                return {
                    'total': row['total'] or 0,
                    'avg_quality': row['avg_quality'] or 50.0,
                    'max_quality': row['max_quality'] or 0.0,
                    'low_quality_count': row['low_quality'] or 0,
                    'avg_access': row['avg_access'] or 0,
                    'new_last_24h': 0
                }
        except Exception as e:
            return {'total': 0, 'avg_quality': 50, 'low_quality_count': 0}
    
    def _get_load_stats(self) -> Dict:
        """获取系统负载"""
        return {
            'cpu_usage': 0.3,
            'memory_usage': 0.2,
            'active_threads': 5,
            'pending_tasks': 0
        }
    
    def _get_health_stats(self) -> Dict:
        """获取健康状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute('''
                    SELECT COUNT(*) as error_count
                    FROM knowledge_items
                    WHERE quality_score < 15
                ''')
                error_count = cur.fetchone()[0]
                
                total = self._get_knowledge_stats().get('total', 1)
                error_rate = error_count / max(total, 1)
                
                return {
                    'error_rate': error_rate,
                    'error_count': error_count,
                    'health_score': max(0, 1 - error_rate * 5),
                    'status': 'healthy' if error_rate < 0.1 else 'degraded'
                }
        except Exception as e:
            return {'error_rate': 0.05, 'health_score': 0.95, 'status': 'healthy'}
    
    def _get_evolution_stats(self) -> Dict:
        """获取进化状态"""
        return {'genome_version': 0, 'generation': 0}
    
    def _get_learning_needs(self) -> Dict:
        """获取学习需求"""
        knowledge_stats = self._get_knowledge_stats()
        new_knowledge = knowledge_stats.get('new_last_24h', 0)
        
        if new_knowledge < 5:
            need_score = 0.8
        elif new_knowledge < 20:
            need_score = 0.4
        else:
            need_score = 0.1
        
        return {
            'need_score': need_score,
            'priority': 'high' if need_score > 0.6 else 'normal'
        }


# ==================== 认知调度器 ====================

class CognitiveScheduler:
    """
    认知驱动的自适应调度器
    
    核心机制：
    1. 状态感知：收集系统当前状态
    2. 需求评估：判断当前最需要什么
    3. 智能调度：根据状态和需求动态决定执行什么
    4. 自适应：根据执行效果调整调度策略
    """
    
    def __init__(self, db_path: str = "data/knowledge_store.db"):
        self.db_path = db_path
        self.running = False
        self.thread = None
        
        # 组件
        self.registry = TaskRegistry()
        self.sensor = SystemStateSensor(db_path)
        
        # 调度状态
        self.schedule_state = {
            'last_full_cycle': None,
            'cycle_count': 0,
            'tasks_executed': 0,
            'tasks_failed': 0,
            'average_duration': 0.0,
            'adaptive_history': []
        }
        
        # 自适应配置
        self.config = {
            'min_interval_seconds': 30,
            'max_interval_seconds': 600,
            'adaptive_interval': True,
            'max_tasks_per_cycle': 5,
            'critical_threshold': 0.3,
        }
        
        logger.info("🧠 认知调度器已初始化")
    
    def start(self):
        """启动调度器"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        
        logger.info("🚀 认知调度器已启动")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("认知调度器已停止")
    
    def _scheduler_loop(self):
        """调度器主循环"""
        
        while self.running:
            try:
                # 1. 感知系统状态
                state = self.sensor.sense()
                
                # 2. 评估调度需求
                schedule_decision = self._evaluate_schedule(state)
                
                # 3. 执行调度
                if schedule_decision['should_run']:
                    self._run_schedule_cycle(state, schedule_decision)
                
                # 4. 动态调整间隔
                interval = self._calculate_interval(state)
                
                # 等待下一个周期
                for _ in range(int(interval)):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"调度循环错误: {e}")
                time.sleep(60)
    
    def _evaluate_schedule(self, state: Dict) -> Dict:
        """评估是否应该执行调度"""
        
        health = state.get('health', {})
        knowledge = state.get('knowledge', {})
        learning_needs = state.get('learning_needs', {})
        
        should_run = False
        reasons = []
        
        # 条件1：错误率过高 → 立即执行
        if health.get('error_rate', 0) > self.config['critical_threshold']:
            should_run = True
            reasons.append("错误率过高，需要紧急处理")
        
        # 条件2：学习需求高
        if learning_needs.get('need_score', 0) > 0.6:
            should_run = True
            reasons.append("学习需求高，需要获取新知识")
        
        # 条件3：知识库质量低
        if knowledge.get('avg_quality', 100) < 30:
            should_run = True
            reasons.append("知识库质量低，需要维护")
        
        # 条件4：定期执行
        if self.schedule_state['last_full_cycle'] is None:
            should_run = True
            reasons.append("首次启动")
        else:
            elapsed = (datetime.now() - self.schedule_state['last_full_cycle']).total_seconds()
            if elapsed > 1800:
                should_run = True
                reasons.append("定期执行")
        
        return {
            'should_run': should_run,
            'reasons': reasons,
            'urgency': 'critical' if health.get('error_rate', 0) > 0.3 else 'normal'
        }
    
    def _run_schedule_cycle(self, state: Dict, decision: Dict):
        """执行调度周期"""
        
        start_time = datetime.now()
        self.schedule_state['cycle_count'] += 1
        self.schedule_state['last_full_cycle'] = start_time
        
        logger.info(f"🔄 调度周期 #{self.schedule_state['cycle_count']} 开始")
        logger.info(f"  触发原因: {', '.join(decision['reasons'])}")
        
        tasks = self._select_tasks(state)
        
        if not tasks:
            logger.info("  ⏭️ 无任务需要执行")
            return
        
        logger.info(f"  📋 选择 {len(tasks)} 个任务执行")
        
        results = []
        for task in tasks:
            result = self._execute_task(task, state)
            results.append(result)
            
            if not result['success']:
                self.schedule_state['tasks_failed'] += 1
        
        self.schedule_state['tasks_executed'] += len(tasks)
        
        self._update_adaptive_feedback(results, state)
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"  ✅ 周期完成: {len(results)}个任务, 耗时{duration:.1f}秒")
    
    def _select_tasks(self, state: Dict) -> List[CognitiveTask]:
        """智能选择任务"""
        
        health = state.get('health', {})
        knowledge = state.get('knowledge', {})
        learning_needs = state.get('learning_needs', {})
        
        selected = []
        
        # 1. 错误率过高 → 优先错误感知
        if health.get('error_rate', 0) > 0.2:
            error_task = self.registry.get_task('error_perception')
            if error_task and error_task.is_ready():
                selected.append(error_task)
        
        # 2. 学习需求高 → 优先学习
        if learning_needs.get('need_score', 0) > 0.5:
            learn_task = self.registry.get_task('learn_new_knowledge')
            if learn_task and learn_task.is_ready():
                selected.append(learn_task)
        
        # 3. 知识库质量低 → 优先清理
        if knowledge.get('avg_quality', 100) < 40:
            cleanup_task = self.registry.get_task('cleanup_knowledge')
            if cleanup_task and cleanup_task.is_ready():
                selected.append(cleanup_task)
        
        # 4. 补充其他就绪任务
        ready_tasks = self.registry.get_tasks_by_priority(self.config['max_tasks_per_cycle'])
        
        for task in ready_tasks:
            if len(selected) >= self.config['max_tasks_per_cycle']:
                break
            if task not in selected:
                selected.append(task)
        
        return selected
    
    def _execute_task(self, task: CognitiveTask, state: Dict) -> Dict:
        """执行单个任务"""
        
        start_time = time.time()
        logger.debug(f"  执行: {task.name} (优先级: {task.priority.value})")
        
        try:
            result = task.function()
            
            duration = time.time() - start_time
            success = result.get('success', False)
            
            task.last_run = datetime.now()
            task.last_duration = duration
            
            if success:
                task.success_count += 1
                logger.debug(f"    ✅ {task.name} 完成 ({duration:.2f}秒)")
            else:
                task.failure_count += 1
                error = result.get('error', '未知错误')
                logger.warning(f"    ❌ {task.name} 失败: {error}")
            
            if task.adaptive:
                self._adjust_task_cooldown(task, result, state)
            
            return {
                'task_id': task.id,
                'name': task.name,
                'success': success,
                'duration': duration,
                'result': result
            }
            
        except Exception as e:
            duration = time.time() - start_time
            task.failure_count += 1
            logger.error(f"    ❌ {task.name} 异常: {e}")
            
            return {
                'task_id': task.id,
                'name': task.name,
                'success': False,
                'duration': duration,
                'error': str(e)
            }
    
    def _adjust_task_cooldown(self, task: CognitiveTask, result: Dict, state: Dict):
        """根据执行结果调整任务冷却时间"""
        
        success = result.get('success', False)
        
        if success:
            task.cooldown_minutes = min(
                task.max_interval_minutes,
                task.cooldown_minutes * 1.1
            )
        else:
            task.cooldown_minutes = max(
                task.min_interval_minutes,
                task.cooldown_minutes * 0.8
            )
        
        health = state.get('health', {})
        if health.get('status') == 'degraded':
            task.cooldown_minutes = max(
                task.min_interval_minutes,
                task.cooldown_minutes * 0.7
            )
    
    def _update_adaptive_feedback(self, results: List[Dict], state: Dict):
        """更新自适应反馈"""
        
        success_count = sum(1 for r in results if r.get('success'))
        total_count = len(results)
        
        if total_count > 0:
            success_rate = success_count / total_count
            
            self.schedule_state['adaptive_history'].append({
                'timestamp': datetime.now().isoformat(),
                'success_rate': success_rate,
                'tasks_count': total_count,
                'error_rate': state.get('health', {}).get('error_rate', 0)
            })
            
            if len(self.schedule_state['adaptive_history']) > 100:
                self.schedule_state['adaptive_history'] = self.schedule_state['adaptive_history'][-100:]
    
    def _calculate_interval(self, state: Dict) -> int:
        """动态计算下次执行间隔"""
        
        if not self.config['adaptive_interval']:
            return 60
        
        base_interval = 60
        health = state.get('health', {})
        knowledge = state.get('knowledge', {})
        
        error_rate = health.get('error_rate', 0)
        
        if error_rate > 0.3:
            interval = max(self.config['min_interval_seconds'], base_interval * 0.5)
        elif error_rate > 0.1:
            interval = base_interval
        else:
            interval = min(self.config['max_interval_seconds'], base_interval * 1.5)
        
        new_knowledge = knowledge.get('new_last_24h', 0)
        if new_knowledge < 5:
            interval = min(interval, base_interval * 0.8)
        
        return int(interval)
    
    def get_status(self) -> Dict:
        """获取调度器状态"""
        return {
            'running': self.running,
            'cycle_count': self.schedule_state['cycle_count'],
            'tasks_executed': self.schedule_state['tasks_executed'],
            'tasks_failed': self.schedule_state['tasks_failed'],
            'last_full_cycle': self.schedule_state['last_full_cycle'],
            'config': self.config
        }
    
    def run_once(self):
        """手动执行一次完整调度"""
        logger.info("🔧 手动执行调度...")
        state = self.sensor.sense()
        decision = {'should_run': True, 'reasons': ['手动触发'], 'urgency': 'normal'}
        self._run_schedule_cycle(state, decision)
        logger.info("手动调度完成")


# ==================== 全局实例 ====================

cognitive_scheduler = CognitiveScheduler()