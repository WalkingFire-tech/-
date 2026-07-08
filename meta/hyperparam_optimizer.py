"""
超参数自动调优器 - 元控制层核心组件
使用贝叶斯优化自动调整路由权重等超参数
"""
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from infrastructure.config_manager import config
from infrastructure.database_manager import DatabaseManager


class HyperparamOptimizer:
    """超参数自动调优器"""
    
    BASE_DATA_DIR = Path("data")
    BASE_CONFIG_DIR = Path("config")
    
    def __init__(self):
        self.optimization_history_file = self.BASE_DATA_DIR / "hyperparam_optimization_history.json"
        self.history = self._load_history()
        self.optimization_interval = config.get("hyperparam.optimization_interval_days", 7)
        self.min_samples = config.get("hyperparam.min_samples", 50)
        self._lock = threading.Lock()
        
        self.param_space = {
            "quality_weight": (0.0, 1.0),
            "speed_weight": (0.0, 1.0),
            "cost_weight": (0.0, 0.5),
            "success_weight": (0.0, 0.3),
            "quality_threshold": (30, 70),
            "decay_rate": (0.001, 0.1),
            "importance_threshold": (0.1, 0.5)
        }
    
    def _load_history(self) -> List[Dict]:
        """加载优化历史"""
        self.BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        if self.optimization_history_file.exists():
            try:
                with open(self.optimization_history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载优化历史失败: {e}")
        return []
    
    def _save_history(self):
        """保存优化历史"""
        with self._lock:
            try:
                self.BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
                with open(self.optimization_history_file, 'w', encoding='utf-8') as f:
                    json.dump(self.history, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"保存优化历史失败: {e}")
    
    def should_optimize(self) -> bool:
        """判断是否应该进行优化"""
        # 检查上次优化时间
        if not self.history:
            return True
        
        last_optimization = self.history[-1]
        last_time = datetime.fromisoformat(last_optimization["timestamp"])
        
        if datetime.now() - last_time < timedelta(days=self.optimization_interval):
            return False
        
        # 检查样本数量
        sample_count = self._get_sample_count()
        if sample_count < self.min_samples:
            logger.info(f"样本数量不足({sample_count}<{self.min_samples}),暂不优化")
            return False
        
        return True
    
    def _get_sample_count(self) -> int:
        """获取样本数量"""
        stats_db = self.BASE_DATA_DIR / "model_stats.db"
        if not stats_db.exists():
            return 0
        
        try:
            conn = DatabaseManager.get(str(stats_db))._get_conn()
            cur = conn.execute('SELECT COUNT(*) FROM model_performance')
            return cur.fetchone()[0]
        except:
            return 0
    
    def optimize(self, dry_run: bool = False) -> Optional[Dict]:
        """执行超参数优化"""
        if not self.should_optimize():
            logger.info("不满足优化条件,跳过")
            return None
        
        logger.info("开始超参数优化...")
        
        # 1. 评估当前参数
        current_params = self._get_current_params()
        current_score = self._evaluate_params(current_params)
        
        logger.info(f"当前参数得分: {current_score:.3f}")
        
        # 2. 生成候选参数(简化版贝叶斯优化)
        candidates = self._generate_candidates(current_params)
        
        # 3. 评估候选参数
        best_params = current_params
        best_score = current_score
        
        for candidate in candidates:
            score = self._evaluate_params(candidate)
            logger.debug(f"候选参数得分: {score:.3f}")
            
            if score > best_score:
                best_params = candidate
                best_score = score
        
        # 4. 应用最优参数
        improvement = best_score - current_score
        
        optimization_result = {
            "timestamp": datetime.now().isoformat(),
            "previous_params": current_params,
            "previous_score": current_score,
            "optimized_params": best_params,
            "optimized_score": best_score,
            "improvement": improvement,
            "sample_count": self._get_sample_count()
        }
        
        self.history.append(optimization_result)
        self._save_history()
        
        if not dry_run and improvement > 0.01:
            self._apply_params(best_params)
            logger.info(f"应用优化参数,提升: {improvement:.3f}")
        else:
            logger.info(f"优化完成,提升: {improvement:.3f} (未应用)")
        
        return optimization_result
    
    def _get_current_params(self) -> Dict:
        """获取当前参数"""
        return {
            "quality_weight": config.get("routing.quality_weight", 0.4),
            "speed_weight": config.get("routing.speed_weight", 0.3),
            "cost_weight": config.get("routing.cost_weight", 0.2),
            "success_weight": config.get("routing.success_weight", 0.1),
            "quality_threshold": config.get("planner.quality_threshold", 50),
            "decay_rate": config.get("experience.decay_rate", 0.01),
            "importance_threshold": config.get("experience.importance_threshold", 0.3)
        }
    
    def _evaluate_params(self, params: Dict) -> float:
        """评估参数组合"""
        stats_db = self.BASE_DATA_DIR / "model_stats.db"
        if not stats_db.exists():
            return 0.0
        
        try:
            conn = DatabaseManager.get(str(stats_db))._get_conn()
            cur = conn.execute('''
                SELECT 
                    quality_score,
                    duration,
                    cost,
                    CASE WHEN success THEN 1.0 ELSE 0 END as success,
                    user_feedback
                FROM model_performance
                ORDER BY timestamp DESC
                LIMIT 1000
            ''')
            
            scores = []
            for row in cur.fetchall():
                quality, duration, cost, success, feedback = row
                
                norm_quality = (quality or 50) / 100.0
                norm_speed = max(0, 1 - (duration or 10) / 60.0)
                norm_cost = max(0, 1 - (cost or 0) * 100)
                norm_success = success
                
                score = (
                    params["quality_weight"] * norm_quality +
                    params["speed_weight"] * norm_speed +
                    params["cost_weight"] * norm_cost +
                    params["success_weight"] * norm_success
                )
                
                if feedback is not None:
                    score *= (1 + feedback * 0.2)
                
                scores.append(score)
            
            return sum(scores) / len(scores) if scores else 0.0
        
        except Exception as e:
            logger.error(f"评估参数失败: {e}")
            return 0.0
    
    def _generate_candidates(self, current: Dict) -> List[Dict]:
        """生成候选参数(简化版)"""
        import random
        
        candidates = []
        num_candidates = 10
        
        for _ in range(num_candidates):
            candidate = {}
            
            for param, (min_val, max_val) in self.param_space.items():
                current_val = current.get(param, (min_val + max_val) / 2)
                
                # 在当前值附近采样
                delta = (max_val - min_val) * 0.2
                new_val = current_val + random.uniform(-delta, delta)
                new_val = max(min_val, min(max_val, new_val))
                
                candidate[param] = new_val
            
            # 确保权重和为1(近似)
            weight_sum = (
                candidate["quality_weight"] +
                candidate["speed_weight"] +
                candidate["cost_weight"] +
                candidate["success_weight"]
            )
            
            if weight_sum > 0:
                candidate["quality_weight"] /= weight_sum
                candidate["speed_weight"] /= weight_sum
                candidate["cost_weight"] /= weight_sum
                candidate["success_weight"] /= weight_sum
            
            candidates.append(candidate)
        
        return candidates
    
    def _apply_params(self, params: Dict):
        """应用参数到配置"""
        config_file = self.BASE_CONFIG_DIR / "settings.yaml"
        
        if config_file.exists():
            import yaml
            
            try:
                with self._lock:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = yaml.safe_load(f)
                    
                    config_data.setdefault("routing", {})["quality_weight"] = params["quality_weight"]
                    config_data["routing"]["speed_weight"] = params["speed_weight"]
                    config_data["routing"]["cost_weight"] = params["cost_weight"]
                    config_data["routing"]["success_weight"] = params["success_weight"]
                    
                    config_data.setdefault("planner", {})["quality_threshold"] = int(params["quality_threshold"])
                    
                    config_data.setdefault("experience", {})["decay_rate"] = params["decay_rate"]
                    config_data["experience"]["importance_threshold"] = params["importance_threshold"]
                    
                    self.BASE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
                    with open(config_file, 'w', encoding='utf-8') as f:
                        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
                
                logger.info("参数已更新到配置文件")
                
                from infrastructure.config_manager import config as config_manager
                config_manager.reload()
            
            except Exception as e:
                logger.error(f"应用参数失败: {e}")
    
    def get_optimization_history(self, limit: int = 10) -> List[Dict]:
        """获取优化历史"""
        return self.history[-limit:]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        if not self.history:
            return {
                "total_optimizations": 0,
                "last_optimization": None,
                "avg_improvement": 0.0,
                "best_improvement": 0.0
            }
        
        improvements = [h["improvement"] for h in self.history]
        
        return {
            "total_optimizations": len(self.history),
            "last_optimization": self.history[-1]["timestamp"],
            "avg_improvement": sum(improvements) / len(improvements),
            "best_improvement": max(improvements),
            "current_params": self._get_current_params()
        }
