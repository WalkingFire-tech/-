"""
贝叶斯优化器 - 超参数自动调优(使用scikit-optimize)
真正的贝叶斯优化:高斯过程代理模型+采集函数(EI)
"""
import numpy as np
from typing import Dict, List, Tuple, Callable, Optional
from datetime import datetime
from dataclasses import dataclass
from loguru import logger
from infrastructure.event_bus import bus

try:
    from skopt import gp_minimize
    from skopt.space import Real, Integer
    from skopt.utils import use_named_args
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False
    logger.warning("scikit-optimize未安装,将使用随机搜索降级。安装命令: pip install scikit-optimize")


@dataclass
class OptimizationResult:
    """优化结果"""
    best_params: Dict[str, float]
    best_score: float
    optimization_history: List[Dict]
    iterations: int
    timestamp: str


class BayesianOptimizer:
    """贝叶斯优化器"""
    
    def __init__(self):
        if SKOPT_AVAILABLE:
            self.param_spaces = {
                "quality_weight": Real(0.0, 1.0, name="quality_weight"),
                "speed_weight": Real(0.0, 1.0, name="speed_weight"),
                "cost_weight": Real(0.0, 1.0, name="cost_weight"),
                "quality_threshold": Real(0.0, 100.0, name="quality_threshold"),
                "confidence_threshold": Real(0.0, 1.0, name="confidence_threshold"),
                "fallback_retry": Integer(1, 5, name="fallback_retry"),
            }
        else:
            self.param_spaces = {}
        
        self.default_params = {
            "quality_weight": 0.5,
            "speed_weight": 0.3,
            "cost_weight": 0.2,
            "quality_threshold": 50.0,
            "confidence_threshold": 0.6,
            "fallback_retry": 3,
        }
        
        self.current_params = self.default_params.copy()
        self.optimization_history: List[Dict] = []
        self.eval_function: Optional[Callable] = None
        
        logger.info("贝叶斯优化器初始化完成")
    
    def define_objective_function(self, eval_function: Callable[[Dict], float]) -> None:
        """定义评估函数:输入参数字典,返回得分(越高越好)"""
        self.eval_function = eval_function
        logger.info("优化目标函数已定义")
    
    def optimize(self,
                params_to_optimize: List[str] = None,
                n_iterations: int = 20,
                method: str = "bayesian") -> OptimizationResult:
        """执行优化
        
        Args:
            params_to_optimize: 要优化的参数列表
            n_iterations: 迭代次数
            method: 优化方法 (bayesian, grid, random)
        """
        if params_to_optimize is None:
            params_to_optimize = ["quality_weight", "speed_weight", "cost_weight"]
        
        if self.eval_function is None:
            raise RuntimeError("请先调用 define_objective_function 设置评估函数")
        
        logger.info(f"开始优化: 参数={params_to_optimize}, 方法={method}, 迭代={n_iterations}")
        
        if method == "bayesian" and SKOPT_AVAILABLE:
            result = self._bayesian_optimization(params_to_optimize, n_iterations)
        elif method == "grid":
            result = self._grid_search(params_to_optimize)
        else:
            if method == "bayesian" and not SKOPT_AVAILABLE:
                logger.warning("scikit-optimize不可用,降级为随机搜索")
            result = self._random_search(params_to_optimize, n_iterations)
        
        self.optimization_history = result.optimization_history
        logger.info(f"优化完成: 最佳得分={result.best_score:.4f}")
        return result
    
    def _bayesian_optimization(self, params_to_optimize: List[str], 
                               n_iterations: int) -> OptimizationResult:
        """使用scikit-optimize进行真正的贝叶斯优化"""
        dimensions = [self.param_spaces[p] for p in params_to_optimize]
        
        @use_named_args(dimensions)
        def objective(**params):
            full_params = self.current_params.copy()
            full_params.update(params)
            
            try:
                score = self.eval_function(full_params)
            except Exception as e:
                logger.warning(f"评估参数集失败: {e}")
                score = 0.0
            
            return -score
        
        res = gp_minimize(
            func=objective,
            dimensions=dimensions,
            n_calls=n_iterations,
            n_initial_points=5,
            acq_func="EI",
            random_state=42,
            verbose=False
        )
        
        best_params = self.current_params.copy()
        for i, name in enumerate(params_to_optimize):
            best_params[name] = res.x[i]
        
        history = []
        for x, y in zip(res.x_iters, res.func_vals):
            params = self.current_params.copy()
            for i, name in enumerate(params_to_optimize):
                params[name] = x[i]
            history.append({
                "params": params.copy(),
                "score": -float(y),
                "timestamp": datetime.now().isoformat()
            })
        
        return OptimizationResult(
            best_params=best_params,
            best_score=-float(res.fun),
            optimization_history=history,
            iterations=len(res.x_iters),
            timestamp=datetime.now().isoformat()
        )
    
    def _grid_search(self, params_to_optimize: List[str], 
                    grid_points: int = 5) -> OptimizationResult:
        """简化的网格搜索"""
        from itertools import product
        
        best_score = -float('inf')
        best_params = self.current_params.copy()
        history = []
        
        param_values = {}
        for p in params_to_optimize:
            space = self.param_spaces[p]
            if isinstance(space, Integer):
                param_values[p] = list(range(int(space.low), int(space.high) + 1))
            else:
                param_values[p] = np.linspace(space.low, space.high, grid_points)
        
        total = 1
        for p in params_to_optimize:
            total *= len(param_values[p])
        
        logger.info(f"网格搜索: {total}个组合")
        
        for values in product(*[param_values[p] for p in params_to_optimize]):
            params = self.current_params.copy()
            for i, p in enumerate(params_to_optimize):
                params[p] = values[i]
            
            try:
                score = self.eval_function(params)
            except Exception as e:
                logger.warning(f"评估失败: {e}")
                score = 0.0
            
            history.append({
                "params": params.copy(),
                "score": score,
                "timestamp": datetime.now().isoformat()
            })
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            optimization_history=history,
            iterations=len(history),
            timestamp=datetime.now().isoformat()
        )
    
    def _random_search(self, params_to_optimize: List[str], 
                      n_iterations: int) -> OptimizationResult:
        """随机搜索"""
        best_score = -float('inf')
        best_params = self.current_params.copy()
        history = []
        
        for _ in range(n_iterations):
            params = self.current_params.copy()
            
            for p in params_to_optimize:
                space = self.param_spaces[p]
                if isinstance(space, Integer):
                    params[p] = np.random.randint(int(space.low), int(space.high) + 1)
                else:
                    params[p] = np.random.uniform(space.low, space.high)
            
            try:
                score = self.eval_function(params)
            except Exception:
                score = 0.0
            
            history.append({
                "params": params.copy(),
                "score": score,
                "timestamp": datetime.now().isoformat()
            })
            
            if score > best_score:
                best_score = score
                best_params = params.copy()
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            optimization_history=history,
            iterations=n_iterations,
            timestamp=datetime.now().isoformat()
        )
    
    def apply_best_params(self, best_params: Dict[str, float]) -> None:
        """应用最佳参数 — 通过MetaControlGovernor审批"""
        try:
            from meta.governor import meta_governor
            meta_governor.snapshot_params("bayesian_optimizer", self.current_params)
            approval = meta_governor.approve_adjustment("bayesian_optimizer", best_params)
            if not approval["approved"]:
                logger.warning(f"贝叶斯优化参数调整被治理器拒绝: {approval['reason']}")
                return
            if approval["clamped"]:
                logger.info(f"贝叶斯优化参数被钳位: {approval['clamped']}")
        except Exception:
            pass

        self.current_params.update(best_params)
        logger.info(f"应用最佳参数: {best_params}")
        
        bus.publish("config_updated", {"new_params": best_params})
    
    def rollback_params(self) -> bool:
        """回滚到上次参数快照"""
        try:
            from meta.governor import meta_governor
            snapshot = meta_governor.rollback_params("bayesian_optimizer")
            if snapshot:
                self.current_params.update(snapshot)
                bus.publish("config_updated", {"new_params": snapshot})
                return True
        except Exception:
            pass
        return False
    
    def save_optimization_result(self, result: OptimizationResult,
                                filepath: str = "data/optimization_result.json") -> None:
        """保存优化结果"""
        import json
        from pathlib import Path
        
        safe_path = Path(filepath).resolve()
        base_dir = Path("data").resolve()
        
        if not safe_path.is_relative_to(base_dir):
            logger.warning(f"路径越权，强制使用data目录: {filepath}")
            safe_path = base_dir / Path(filepath).name
        
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "best_params": result.best_params,
            "best_score": result.best_score,
            "iterations": result.iterations,
            "timestamp": result.timestamp,
            "history": result.optimization_history[-20:]
        }
        
        with open(safe_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"优化结果已保存至 {safe_path}")


bayesian_optimizer = BayesianOptimizer()
