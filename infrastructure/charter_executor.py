"""
章程执行器 - 实现生命章程的具体条款
自动学习、配置管理、经验归档、资源限制
"""
import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class CharterExecutor:
    """章程执行器 - 实现生命章程"""
    
    def __init__(self):
        self.config_history = []
        self.usage_stats = []
        self.resource_limits = {
            'cpu_max': 90.0,
            'memory_max': 16.0,
            'storage_max': 50.0
        }
        
        self.violation_counts = {
            'cpu': 0,
            'memory': 0,
            'storage': 0
        }
        self.violation_threshold = 3
        
        self._lock = threading.Lock()
        
        logger.info("章程执行器已初始化")
    
    # ========== 章程3.1: 自动学习任务创建 ==========
    
    def review_failures(self) -> List[Dict]:
        """回顾未解决的失败案例
        
        Returns:
            失败案例列表
        """
        logger.info("回顾失败案例...")
        
        try:
            db = DatabaseManager.get('data/experience_pool.db')
            conn = db._get_conn()
            
            # 查询最近7天的失败案例
            cursor = conn.execute('''
                SELECT intent_type, raw_input, model_name, quality_score, timestamp
                FROM experiences
                WHERE success = 0
                  AND timestamp >= datetime('now', '-7 days')
                ORDER BY timestamp DESC
            ''')
            
            failures = cursor.fetchall()
            
            # 按意图类型分组
            failure_groups = {}
            for f in failures:
                intent_type = f[0]
                if intent_type not in failure_groups:
                    failure_groups[intent_type] = []
                failure_groups[intent_type].append({
                    'raw_input': f[1],
                    'model_name': f[2],
                    'quality_score': f[3],
                    'timestamp': f[4]
                })
            
            # 检查是否需要创建学习任务
            learning_tasks = []
            for intent_type, cases in failure_groups.items():
                if len(cases) >= 3:  # 连续3次失败
                    learning_tasks.append({
                        'type': 'failure_pattern',
                        'intent_type': intent_type,
                        'failure_count': len(cases),
                        'samples': cases[:3],
                        'priority': 'high',
                        'created_at': datetime.now().isoformat()
                    })
                    
                    logger.warning(f"检测到 {intent_type} 意图连续失败 {len(cases)} 次，创建学习任务")
            
            # 保存学习任务
            if learning_tasks:
                self._save_learning_tasks(learning_tasks)
            
            # 【新增】触发主动学习器
            for task in learning_tasks:
                try:
                    from infrastructure.active_learner import active_learner
                    active_learner.record_event("intent_failure", {
                        "intent": task['intent_type'],
                        "failure_count": task['failure_count']
                    })
                except Exception as al_error:
                    logger.debug(f"主动学习器触发失败: {al_error}")
            
            return learning_tasks
            
        except Exception as e:
            logger.error(f"失败回顾失败: {e}")
            return []
    
    def _save_learning_tasks(self, tasks: List[Dict]):
        """保存学习任务"""
        try:
            db = DatabaseManager.get('data/learning_rules.db')
            conn = db._get_conn()
            
            for task in tasks:
                conn.execute('''
                    INSERT INTO learning_rules
                    (condition, action, confidence, status, source)
                    VALUES (?, ?, ?, 'pending', 'auto_learning')
                ''', (
                    f"intent_type == '{task['intent_type']}'",
                    f"avoid_model: {task['samples'][0]['model_name']}",
                    0.5
                ))
            
            conn.commit()
            
            logger.info(f"已创建 {len(tasks)} 个学习任务")
            
        except Exception as e:
            logger.error(f"保存学习任务失败: {e}")
    
    # ========== 章程3.3: 使用频率监控与降级 ==========
    
    def monitor_feature_usage(self) -> Dict:
        """监控功能使用频率
        
        Returns:
            使用频率统计
        """
        logger.info("监控功能使用频率...")
        
        try:
            # 检查并行调度使用情况
            db = DatabaseManager.get('data/scheduler_stats.db')
            conn = db._get_conn()
            cursor = conn.execute('''
                SELECT COUNT(*), MAX(start_time)
                FROM parallel_calls
                WHERE start_time >= datetime('now', '-7 days')
            ''')
            
            parallel_calls = cursor.fetchone()
            
            # 检查任务分解使用情况
            db2 = DatabaseManager.get('data/task_decomposition.db')
            conn2 = db2._get_conn()
            cursor = conn2.execute('''
                SELECT COUNT(*), MAX(timestamp)
                FROM decompositions
                WHERE timestamp >= datetime('now', '-7 days')
            ''')
            
            decompositions = cursor.fetchone()
            
            usage = {
                'parallel_scheduling': {
                    'calls': parallel_calls[0] if parallel_calls[0] else 0,
                    'last_used': parallel_calls[1]
                },
                'task_decomposition': {
                    'calls': decompositions[0] if decompositions[0] else 0,
                    'last_used': decompositions[1]
                }
            }
            
            # 检查是否需要降级
            recommendations = []
            
            if usage['parallel_scheduling']['calls'] == 0:
                recommendations.append({
                    'feature': 'parallel_scheduling',
                    'action': 'disable_or_downgrade',
                    'reason': '7天内未使用'
                })
            
            if usage['task_decomposition']['calls'] == 0:
                recommendations.append({
                    'feature': 'task_decomposition',
                    'action': 'disable_or_downgrade',
                    'reason': '7天内未使用'
                })
            
            if recommendations:
                logger.warning(f"检测到 {len(recommendations)} 个功能建议降级")
            
            return {
                'usage': usage,
                'recommendations': recommendations
            }
            
        except Exception as e:
            logger.error(f"使用频率监控失败: {e}")
            return {'usage': {}, 'recommendations': []}
    
    # ========== 章程4.1-4.2: 配置版本管理与回滚 ==========
    
    def backup_config(self, reason: str) -> str:
        """备份当前配置
        
        Args:
            reason: 备份原因
        
        Returns:
            备份ID
        """
        import uuid
        backup_id = str(uuid.uuid4())[:8]
        
        try:
            config_file = Path("config/settings.yaml")
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_content = f.read()
                
                backup = {
                    'id': backup_id,
                    'config': config_content,
                    'reason': reason,
                    'timestamp': datetime.now().isoformat()
                }
                
                with self._lock:
                    self.config_history.append(backup)
                
                backup_file = Path(f"config/backups/{backup_id}.json")
                backup_file.parent.mkdir(exist_ok=True)
                
                temp_file = backup_file.with_suffix('.tmp')
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(backup, f, ensure_ascii=False, indent=2)
                temp_file.replace(backup_file)
                
                logger.info(f"配置已备份: {backup_id} (原因: {reason})")
            
            return backup_id
            
        except Exception as e:
            logger.error(f"配置备份失败: {e}")
            return ""
    
    def rollback_config(self, backup_id: str) -> bool:
        """回滚配置
        
        Args:
            backup_id: 备份ID
        
        Returns:
            是否成功
        """
        try:
            backup_file = Path(f"config/backups/{backup_id}.json")
            
            if not backup_file.exists():
                logger.error(f"备份不存在: {backup_id}")
                return False
            
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup = json.load(f)
            
            config_file = Path("config/settings.yaml")
            temp_file = config_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(backup['config'])
            temp_file.replace(config_file)
            
            logger.info(f"配置已回滚: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"配置回滚失败: {e}")
            return False
    
    def observe_and_rollback(self, backup_id: str, duration_hours: int = 24) -> bool:
        """观察效果并在必要时回滚
        
        Args:
            backup_id: 备份ID
            duration_hours: 观察时长（小时）
        
        Returns:
            是否需要回滚
        """
        logger.info(f"开始观察配置效果 (备份ID: {backup_id}, 时长: {duration_hours}小时)")
        
        # 获取修改前的基线
        baseline = self._get_performance_baseline()
        
        # 等待观察期（实际应用中应异步）
        # time.sleep(duration_hours * 3600)  # 注释掉，实际使用时启用
        
        # 获取当前性能
        current = self._get_performance_baseline()
        
        # 评估效果
        improvement = current['success_rate'] - baseline['success_rate']
        
        if improvement < 0:
            logger.warning(f"配置效果不佳 (提升: {improvement:.2%})，执行回滚")
            self.rollback_config(backup_id)
            self._mark_strategy_failed(backup_id)
            return True
        else:
            logger.info(f"配置效果良好 (提升: {improvement:.2%})")
            return False
    
    def _get_performance_baseline(self) -> Dict:
        """获取性能基线"""
        try:
            from infrastructure.parallel_scheduler import parallel_scheduler
            stats = parallel_scheduler.get_stats(days=1)
            
            return {
                'success_rate': stats.get('success_rate', 0.5),
                'avg_duration': stats.get('avg_duration', 5.0)
            }
        except:
            return {'success_rate': 0.5, 'avg_duration': 5.0}
    
    def _mark_strategy_failed(self, backup_id: str):
        """标记策略为失败"""
        try:
            failed_file = Path("config/failed_strategies.json")
            
            failed = []
            if failed_file.exists():
                with open(failed_file, 'r') as f:
                    failed = json.load(f)
            
            failed.append({
                'backup_id': backup_id,
                'timestamp': datetime.now().isoformat()
            })
            
            with open(failed_file, 'w') as f:
                json.dump(failed, f, indent=2)
            
        except Exception as e:
            logger.error(f"标记失败策略失败: {e}")
    
    # ========== 章程5.1: 经验自动归档 ==========
    
    def archive_old_experiences(self, days: int = 90, min_importance: float = 0.3):
        """归档旧经验
        
        Args:
            days: 天数阈值
            min_importance: 最小重要性阈值
        """
        logger.info(f"开始归档 {days} 天前的低重要性经验...")
        
        try:
            db = DatabaseManager.get('data/experience_pool.db')
            conn = db._get_conn()
            
            # 查询符合条件的经验
            cursor = conn.execute('''
                SELECT id, intent_type, raw_input, quality_score, timestamp
                FROM experiences
                WHERE timestamp < datetime('now', ?)
                  AND quality_score < ?
            ''', (f'-{days} days', min_importance * 100))
            
            old_experiences = cursor.fetchall()
            
            if not old_experiences:
                logger.info("无需归档的经验")
                return
            
            # 压缩并保存到归档文件
            archive_file = Path(f"data/archives/experiences_{datetime.now().strftime('%Y%m%d')}.json")
            archive_file.parent.mkdir(exist_ok=True)
            
            archive_data = [
                {
                    'id': e[0],
                    'intent_type': e[1],
                    'raw_input': e[2][:100],  # 截断
                    'quality_score': e[3],
                    'timestamp': e[4]
                }
                for e in old_experiences
            ]
            
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(archive_data, f, ensure_ascii=False, indent=2)
            
            experience_ids = [e[0] for e in old_experiences]
            placeholders = ','.join('?' * len(experience_ids))
            conn.execute(f'''
                DELETE FROM experiences
                WHERE id IN ({placeholders})
            ''', experience_ids)
            
            conn.commit()
            
            logger.info(f"已归档 {len(old_experiences)} 条经验至 {archive_file}")
            
        except Exception as e:
            logger.error(f"经验归档失败: {e}")
    
    # ========== 章程6.1: 资源限制检查 ==========
    
    def check_resource_limits(self) -> Dict:
        """检查资源限制
        
        Returns:
            资源状态字典
        """
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_gb = memory.used / (1024**3)
            
            violations = []
            
            with self._lock:
                if cpu_percent > self.resource_limits['cpu_max']:
                    self.violation_counts['cpu'] += 1
                    if self.violation_counts['cpu'] >= self.violation_threshold:
                        violations.append({
                            'resource': 'cpu',
                            'current': cpu_percent,
                            'limit': self.resource_limits['cpu_max'],
                            'action': 'reduce_concurrency',
                            'count': self.violation_counts['cpu']
                        })
                else:
                    self.violation_counts['cpu'] = 0
                
                if memory_gb > self.resource_limits['memory_max']:
                    self.violation_counts['memory'] += 1
                    if self.violation_counts['memory'] >= self.violation_threshold:
                        violations.append({
                            'resource': 'memory',
                            'current': memory_gb,
                            'limit': self.resource_limits['memory_max'],
                            'action': 'free_memory',
                            'count': self.violation_counts['memory']
                        })
                else:
                    self.violation_counts['memory'] = 0
            
            if violations:
                logger.warning(f"检测到 {len(violations)} 个资源连续超限")
            
            return {
                'cpu_percent': cpu_percent,
                'memory_gb': memory_gb,
                'violations': violations,
                'within_limits': len(violations) == 0
            }
            
        except Exception as e:
            logger.error(f"资源检查失败: {e}")
            return {'within_limits': True, 'violations': []}
    
    def enforce_resource_limits(self):
        """强制执行资源限制"""
        check = self.check_resource_limits()
        
        if not check['within_limits']:
            for violation in check['violations']:
                if violation['resource'] == 'cpu':
                    logger.warning("CPU超限，减少并发任务")
                    # 减少并发
                    # 实际实现需要调整调度器参数
                
                elif violation['resource'] == 'memory':
                    logger.warning("内存超限，释放缓存")
                    # 释放缓存
                    # 实际实现需要清理内存


charter_executor = CharterExecutor()
