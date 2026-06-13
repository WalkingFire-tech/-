"""
联盟拓荒者健康度仪表盘 (Alliance Pioneer Health Index, APHI)
聚合所有底层指标为可行动的决策信号
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
import sqlite3
from pathlib import Path


class HealthDashboard:
    """健康度仪表盘 - 系统自我感知的核心"""
    
    def __init__(self):
        self.db_path = Path("health_history.db")
        self._init_db()
        
        self.weights = {
            "capability_coverage": 0.20,
            "task_success_rate": 0.30,
            "resource_availability": 0.10,
            "evolution_vitality": 0.20,
            "user_satisfaction": 0.20
        }
        
        self.thresholds = {
            "critical": 40,
            "warning": 60,
            "healthy": 80
        }
        
        self.mode = "normal"
        self.last_check_time = 0
        
        logger.info("健康度仪表盘已初始化")
    
    def _init_db(self):
        """初始化健康历史数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS health_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    aphi_score REAL,
                    capability_coverage REAL,
                    task_success_rate REAL,
                    resource_availability REAL,
                    evolution_vitality REAL,
                    user_satisfaction REAL,
                    mode TEXT,
                    details TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON health_history(timestamp)')
    
    def calculate_aphi(self) -> Dict:
        """计算联盟拓荒者健康度指数"""
        metrics = {}
        
        metrics["capability_coverage"] = self._measure_capability_coverage()
        metrics["task_success_rate"] = self._measure_task_success_rate()
        metrics["resource_availability"] = self._measure_resource_availability()
        metrics["evolution_vitality"] = self._measure_evolution_vitality()
        metrics["user_satisfaction"] = self._measure_user_satisfaction()
        
        aphi = sum(
            metrics[key] * self.weights[key] 
            for key in self.weights
        )
        
        metrics["aphi"] = round(aphi, 2)
        metrics["mode"] = self._determine_mode(aphi)
        metrics["timestamp"] = datetime.now().isoformat()
        
        self._save_health_record(metrics)
        
        self._check_action_triggers(metrics)
        
        return metrics
    
    def _measure_capability_coverage(self) -> float:
        """测量能力覆盖率"""
        try:
            from infrastructure.model_capability import model_capability
            
            stats = model_capability.export_stats()
            total_models = stats.get("total_models", 0)
            total_dimensions = stats.get("total_dimensions", 0)
            
            if total_models == 0 or total_dimensions == 0:
                return 50.0
            
            avg_confidence = stats.get("avg_confidence", 0.5)
            
            coverage = min(100, (total_models * total_dimensions * avg_confidence) / 10)
            
            return round(coverage, 2)
            
        except Exception as e:
            logger.warning(f"能力覆盖率测量失败: {e}")
            return 50.0
    
    def _measure_task_success_rate(self) -> float:
        """测量任务成功率（最近100次）"""
        try:
            from infrastructure.model_stats import ModelStats
            stats = ModelStats()
            
            all_stats = stats.get_all_model_stats()
            
            if not all_stats:
                return 70.0
            
            total_calls = sum(s.get("total_calls", 0) for s in all_stats.values())
            total_success = sum(s.get("success_count", 0) for s in all_stats.values())
            
            if total_calls == 0:
                return 70.0
            
            success_rate = (total_success / total_calls) * 100
            
            return round(success_rate, 2)
            
        except Exception as e:
            logger.warning(f"任务成功率测量失败: {e}")
            return 70.0
    
    def _measure_resource_availability(self) -> float:
        """测量资源可用性"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            cpu_score = max(0, 100 - cpu_percent)
            memory_score = memory.percent
            disk_score = disk.percent
            
            resource_score = (cpu_score * 0.4 + memory_score * 0.4 + disk_score * 0.2)
            
            return round(resource_score, 2)
            
        except ImportError:
            return 80.0
        except Exception as e:
            logger.warning(f"资源可用性测量失败: {e}")
            return 80.0
    
    def _measure_evolution_vitality(self) -> float:
        """测量进化活力"""
        try:
            from pathlib import Path
            import os
            
            rules_dir = Path("meta/generated_rules")
            rules_count = len(list(rules_dir.glob("*.yaml"))) if rules_dir.exists() else 0
            
            experience_db = Path("experience_pool.db")
            if experience_db.exists():
                with sqlite3.connect(experience_db) as conn:
                    cur = conn.execute("SELECT COUNT(*) FROM experiences WHERE timestamp > datetime('now', '-7 days')")
                    recent_experiences = cur.fetchone()[0]
            else:
                recent_experiences = 0
            
            vitality = min(100, 50 + rules_count * 5 + recent_experiences * 0.5)
            
            return round(vitality, 2)
            
        except Exception as e:
            logger.warning(f"进化活力测量失败: {e}")
            return 60.0
    
    def _measure_user_satisfaction(self) -> float:
        """测量用户满意度"""
        try:
            from infrastructure.model_stats import ModelStats
            stats = ModelStats()
            
            all_stats = stats.get_all_model_stats()
            
            if not all_stats:
                return 75.0
            
            total_feedback = 0
            positive = 0
            negative = 0
            
            for model_stats in all_stats.values():
                feedback = model_stats.get("avg_feedback", 0)
                if feedback != 0:
                    total_feedback += 1
                    if feedback > 0:
                        positive += 1
                    elif feedback < 0:
                        negative += 1
            
            if total_feedback == 0:
                return 75.0
            
            satisfaction = 75 + (positive - negative) * 2
            satisfaction = max(0, min(100, satisfaction))
            
            return round(satisfaction, 2)
            
        except Exception as e:
            logger.warning(f"用户满意度测量失败: {e}")
            return 75.0
    
    def _determine_mode(self, aphi: float) -> str:
        """根据APHI确定运行模式"""
        if aphi < self.thresholds["critical"]:
            return "emergency"
        elif aphi < self.thresholds["warning"]:
            return "energy_saving"
        elif aphi < self.thresholds["healthy"]:
            return "normal"
        else:
            return "optimal"
    
    def _check_action_triggers(self, metrics: Dict):
        """检查是否需要触发行动"""
        aphi = metrics["aphi"]
        mode = metrics["mode"]
        
        if mode == "emergency":
            logger.critical(f"APHI紧急状态 ({aphi})，系统进入应急模式")
            self._trigger_emergency_actions(metrics)
        
        elif mode == "energy_saving":
            logger.warning(f"APHI警告状态 ({aphi})，系统进入节能模式")
            self._trigger_energy_saving_actions(metrics)
        
        elif mode == "optimal":
            logger.success(f"APHI最优状态 ({aphi})，系统运行良好")
        
        self.mode = mode
    
    def _trigger_emergency_actions(self, metrics: Dict):
        """触发紧急行动"""
        try:
            from infrastructure.event_bus import bus
            bus.publish("system_emergency", {
                "aphi": metrics["aphi"],
                "metrics": metrics,
                "actions": [
                    "reduce_parallel_tasks",
                    "disable_non_essential_services",
                    "request_user_help"
                ]
            })
        except Exception as e:
            logger.error(f"紧急行动触发失败: {e}")
    
    def _trigger_energy_saving_actions(self, metrics: Dict):
        """触发节能行动"""
        try:
            from infrastructure.event_bus import bus
            bus.publish("system_energy_saving", {
                "aphi": metrics["aphi"],
                "metrics": metrics,
                "actions": [
                    "reduce_parallel_tasks",
                    "increase_cache_usage"
                ]
            })
        except Exception as e:
            logger.error(f"节能行动触发失败: {e}")
    
    def _save_health_record(self, metrics: Dict):
        """保存健康记录"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO health_history 
                    (timestamp, aphi_score, capability_coverage, task_success_rate,
                     resource_availability, evolution_vitality, user_satisfaction, mode, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    metrics["timestamp"],
                    metrics["aphi"],
                    metrics["capability_coverage"],
                    metrics["task_success_rate"],
                    metrics["resource_availability"],
                    metrics["evolution_vitality"],
                    metrics["user_satisfaction"],
                    metrics["mode"],
                    ""
                ))
        except Exception as e:
            logger.warning(f"健康记录保存失败: {e}")
    
    def get_health_trend(self, hours: int = 24) -> List[Dict]:
        """获取健康趋势"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute('''
                    SELECT timestamp, aphi_score, mode
                    FROM health_history
                    WHERE timestamp > datetime('now', ?)
                    ORDER BY timestamp DESC
                    LIMIT 100
                ''', (f'-{hours} hours',))
                
                return [
                    {"timestamp": row[0], "aphi": row[1], "mode": row[2]}
                    for row in cur.fetchall()
                ]
        except Exception as e:
            logger.warning(f"健康趋势获取失败: {e}")
            return []
    
    def get_status_report(self) -> str:
        """获取状态报告"""
        metrics = self.calculate_aphi()
        
        report = f"""
╔══════════════════════════════════════════════════════════╗
║          联盟拓荒者健康度报告                              ║
╠══════════════════════════════════════════════════════════╣
║  APHI指数: {metrics['aphi']:>6.2f} / 100  ({metrics['mode']})              ║
╠══════════════════════════════════════════════════════════╣
║  能力覆盖率:     {metrics['capability_coverage']:>6.2f}%                    ║
║  任务成功率:     {metrics['task_success_rate']:>6.2f}%                    ║
║  资源可用性:     {metrics['resource_availability']:>6.2f}%                    ║
║  进化活力:       {metrics['evolution_vitality']:>6.2f}%                    ║
║  用户满意度:     {metrics['user_satisfaction']:>6.2f}%                    ║
╚══════════════════════════════════════════════════════════╝
"""
        return report
    
    def should_reduce_load(self) -> bool:
        """判断是否应该降低负载"""
        return self.mode in ["emergency", "energy_saving"]
    
    def should_request_help(self) -> bool:
        """判断是否应该请求用户帮助"""
        return self.mode == "emergency"


health_dashboard = HealthDashboard()