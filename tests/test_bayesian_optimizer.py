"""
核心模块单元测试 - 贝叶斯优化器
"""
import pytest
import numpy as np
from meta.bayesian_optimizer import BayesianOptimizer, OptimizationResult


class TestBayesianOptimizer:
    """贝叶斯优化器测试类"""
    
    @pytest.fixture
    def optimizer(self):
        """创建优化器实例"""
        return BayesianOptimizer()
    
    def test_initialization(self, optimizer):
        """测试初始化"""
        assert optimizer.current_params is not None
        assert "quality_weight" in optimizer.current_params
        assert "speed_weight" in optimizer.current_params
        assert "cost_weight" in optimizer.current_params
    
    def test_define_objective_function(self, optimizer):
        """测试目标函数定义"""
        def dummy_eval(params):
            return 0.5
        
        optimizer.define_objective_function(dummy_eval)
        
        assert optimizer.eval_function is not None
        assert optimizer.eval_function({"quality_weight": 0.5}) == 0.5
    
    def test_random_search(self, optimizer):
        """测试随机搜索"""
        def eval_func(params):
            q = params.get("quality_weight", 0.5)
            return q * 0.6 + 0.3
        
        optimizer.define_objective_function(eval_func)
        
        result = optimizer.optimize(
            params_to_optimize=["quality_weight"],
            n_iterations=10,
            method="random"
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.best_score > 0
        assert len(result.optimization_history) == 10
        assert "quality_weight" in result.best_params
    
    def test_grid_search(self, optimizer):
        """测试网格搜索"""
        def eval_func(params):
            return params.get("quality_weight", 0.5)
        
        optimizer.define_objective_function(eval_func)
        
        result = optimizer.optimize(
            params_to_optimize=["quality_weight"],
            n_iterations=5,
            method="grid"
        )
        
        assert isinstance(result, OptimizationResult)
        assert result.best_score >= 0
        assert result.iterations > 0
    
    def test_apply_best_params(self, optimizer):
        """测试应用最佳参数"""
        best_params = {
            "quality_weight": 0.7,
            "speed_weight": 0.2,
            "cost_weight": 0.1
        }
        
        optimizer.apply_best_params(best_params)
        
        assert optimizer.current_params["quality_weight"] == 0.7
        assert optimizer.current_params["speed_weight"] == 0.2
        assert optimizer.current_params["cost_weight"] == 0.1
    
    def test_param_suggestions(self, optimizer):
        """测试参数建议生成"""
        def eval_func(params):
            return 0.8
        
        optimizer.define_objective_function(eval_func)
        optimizer.optimize(
            params_to_optimize=["quality_weight"],
            n_iterations=5,
            method="random"
        )
        
        suggestions = optimizer.get_param_suggestions()
        
        assert isinstance(suggestions, dict)
        assert len(suggestions) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])