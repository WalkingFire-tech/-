"""
元控制层核心控制器 - 统一调度优化、归纳、冲突检测
实现每周自动任务、配置热加载、评估函数
"""
try:
    import schedule
except ImportError:
    schedule = None
import time
import threading
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger
from infrastructure.model_stats import ModelStats
from infrastructure.event_bus import bus
from infrastructure.database_manager import DatabaseManager
from meta.bayesian_optimizer import bayesian_optimizer
from meta.conflict_detector import conflict_detector
from meta.induction import induction_scheduler


class MetaController:
    """元控制层控制器"""
    
    def __init__(self, llm_adapter=None):
        self.llm = llm_adapter
        self.stats = ModelStats()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        bus.subscribe("config_updated", self._on_config_updated)
        
        logger.info("元控制层控制器初始化完成")
    
    def _on_config_updated(self, data):
        """配置更新回调(用于热加载)"""
        new_params = data.get("new_params", {})
        logger.info(f"收到配置更新事件: {new_params}")
        
        bus.publish("reload_config", new_params)
    
    def evaluate_params(self, params: Dict) -> float:
        """评估一组超参数的得分(供优化器调用)"""
        recent = self._get_recent_performance(days=7)
        
        if not recent:
            return 0.5
        
        quality_weight = params.get("quality_weight", 0.5)
        speed_weight = params.get("speed_weight", 0.3)
        cost_weight = params.get("cost_weight", 0.2)
        
        task_type_weights = {
            "code": 1.5,
            "question": 1.0,
            "calculation": 1.2,
            "document": 0.8,
            "chat": 0.6
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for task_type, weight in task_type_weights.items():
            task_perf = self._get_task_performance(task_type, days=7)
            
            if task_perf:
                norm_quality = task_perf.get("avg_quality", 50) / 100.0
                norm_speed = 1 - min(1.0, task_perf.get("avg_duration", 10) / 60.0)
                norm_cost = 1 - min(1.0, task_perf.get("avg_cost", 0.01) / 0.1)
                
                task_score = (quality_weight * norm_quality +
                             speed_weight * norm_speed +
                             cost_weight * norm_cost)
                
                total_score += task_score * weight
                total_weight += weight
        
        if total_weight > 0:
            score = total_score / total_weight
        else:
            norm_quality = recent.get("avg_quality", 50) / 100.0
            norm_speed = 1 - min(1.0, recent.get("avg_duration", 10) / 60.0)
            norm_cost = 1 - min(1.0, recent.get("avg_cost", 0.01) / 0.1)
            
            score = (quality_weight * norm_quality +
                    speed_weight * norm_speed +
                    cost_weight * norm_cost)
        
        logger.warning(f"参数评估: {params} -> 得分 {score:.4f}")
        return score
    
    def _get_recent_performance(self, days: int = 7) -> Dict:
        """从统计库获取最近几天的汇总性能"""
        try:
            db_path = "data/model_stats.db"
            
            db = DatabaseManager.get(db_path)
            row = db.query_one('''
                SELECT
                    AVG(quality_score) as avg_quality,
                    AVG(duration) as avg_duration,
                    AVG(input_tokens + output_tokens) as avg_tokens
                FROM model_performance
                WHERE datetime(timestamp) > datetime('now', ?)
            ''', (f'-{days} days',))
            
            if row and row[0] is not None:
                return {
                    "avg_quality": row[0],
                    "avg_duration": row[1],
                    "avg_tokens": row[2],
                    "avg_cost": row[2] * 0.000002
                }
        
        except Exception as e:
            logger.warning(f"获取性能数据失败: {e}")
        
        return {}
    
    def _get_task_performance(self, task_type: str, days: int = 7) -> Dict:
        """获取特定任务类型的性能数据"""
        try:
            db_path = "data/experience_pool.db"
            
            db = DatabaseManager.get(db_path)
            row = db.query_one('''
                SELECT
                    AVG(quality_score) as avg_quality,
                    AVG(duration) as avg_duration
                FROM experiences
                WHERE intent_type = ? 
                AND datetime(timestamp) > datetime('now', ?)
            ''', (task_type, f'-{days} days'))
            
            if row and row[0] is not None:
                return {
                    "avg_quality": row[0],
                    "avg_duration": row[1],
                    "avg_cost": 0.01
                }
        
        except Exception as e:
            logger.error(f"获取任务{task_type}性能失败: {e}")
        
        return {}
    
    def run_weekly_tasks(self):
        """每周执行一次:归纳、冲突检测、超参数优化"""
        logger.info("========== 开始每周元学习任务 ==========")
        
        try:
            logger.info("[1/3] 执行离线归纳...")
            result = induction_scheduler.run_induction(days=7)
            logger.info(f"归纳完成: 发现{result.get('patterns', 0)}个模式, 生成{result.get('rules', 0)}条规则")
        except Exception as e:
            logger.error(f"归纳失败: {e}")
        
        try:
            logger.info("[2/3] 检测规则冲突...")
            conflicts = conflict_detector.detect_conflicts()
            
            if conflicts:
                logger.warning(f"发现{len(conflicts)}个规则冲突")
                for c in conflicts[:5]:
                    resolution = conflict_detector.resolve_conflict(c, resolution="auto")
                    logger.info(f"冲突解决: {resolution}")
            else:
                logger.info("未发现规则冲突")
        except Exception as e:
            logger.error(f"冲突检测失败: {e}")
        
        try:
            logger.info("[3/3] 执行超参数优化...")
            bayesian_optimizer.define_objective_function(self.evaluate_params)
            
            result = bayesian_optimizer.optimize(
                params_to_optimize=["quality_weight", "speed_weight", "cost_weight"],
                n_iterations=15,
                method="bayesian"
            )
            
            bayesian_optimizer.apply_best_params(result.best_params)
            bayesian_optimizer.save_optimization_result(result)
            logger.info(f"超参数优化完成: 最佳得分 {result.best_score:.4f}")
        except Exception as e:
            logger.error(f"超参数优化失败: {e}")
        
        logger.info("========== 每周元学习任务完成 ==========")
    
    def start_scheduler(self):
        """启动后台调度器(每周运行)"""
        if schedule is None:
            logger.warning("schedule库未安装，调度器不可用")
            return
        schedule.every().week.do(self.run_weekly_tasks)
        
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        
        logger.info("元控制层调度器已启动(每周自动运行)")
    
    def _scheduler_loop(self):
        """调度循环"""
        while self.running:
            if schedule is not None:
                schedule.run_pending()
            time.sleep(60)
    
    def stop_scheduler(self):
        """停止调度器(线程安全)"""
        if not self.running:
            logger.debug("调度器已停止,跳过")
            return
        
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3)
        
        logger.info("元控制层调度器已停止")
    
    def run_manual_optimization(self, method: str = "bayesian", 
                                n_iterations: int = 15) -> Dict:
        """手动触发优化"""
        try:
            bayesian_optimizer.define_objective_function(self.evaluate_params)
            
            result = bayesian_optimizer.optimize(
                params_to_optimize=["quality_weight", "speed_weight", "cost_weight"],
                n_iterations=n_iterations,
                method=method
            )
            
            bayesian_optimizer.apply_best_params(result.best_params)
            
            return {
                "success": True,
                "best_score": result.best_score,
                "best_params": result.best_params,
                "iterations": result.iterations
            }
        
        except Exception as e:
            logger.error(f"手动优化失败: {e}")
            return {"success": False, "error": str(e)}
    
    def get_status(self) -> Dict:
        """获取元控制层状态"""
        return {
            "running": self.running,
            "scheduler_active": self.thread.is_alive() if self.thread else False,
            "current_params": bayesian_optimizer.current_params,
            "last_optimization": bayesian_optimizer.optimization_history[-1] if bayesian_optimizer.optimization_history else None
        }


_meta_controller: Optional[MetaController] = None


def get_meta_controller(llm_adapter=None) -> MetaController:
    """获取元控制层单例"""
    global _meta_controller
    
    if _meta_controller is None:
        _meta_controller = MetaController(llm_adapter)
    
    return _meta_controller
