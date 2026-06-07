"""
核心模块单元测试 - 计算处理器
"""
import pytest
from infrastructure.calculation_handler import CalculationHandler


class TestCalculationHandler:
    """计算处理器测试类"""
    
    def test_is_pi_calculation(self):
        """测试π计算识别"""
        assert CalculationHandler.is_pi_calculation("输出π的前100位") is True
        assert CalculationHandler.is_pi_calculation("计算圆周率") is True
        assert CalculationHandler.is_pi_calculation("what is pi") is True
        assert CalculationHandler.is_pi_calculation("计算2+3") is False
    
    def test_extract_pi_digits(self):
        """测试提取π位数"""
        assert CalculationHandler.extract_pi_digits("输出π的前100位") == 100
        assert CalculationHandler.extract_pi_digits("计算π的50位") == 50
        assert CalculationHandler.extract_pi_digits("输出π") is None
    
    def test_is_expression(self):
        """测试表达式识别"""
        assert CalculationHandler.is_expression("2+3") is True
        assert CalculationHandler.is_expression("sin(pi/2)") is True
        assert CalculationHandler.is_expression("sqrt(16)") is True
        assert CalculationHandler.is_expression("输出π的前100位") is False
    
    def test_evaluate_expression_basic(self):
        """测试基础表达式计算"""
        assert CalculationHandler.evaluate_expression("2+3") == "5"
        assert CalculationHandler.evaluate_expression("2*3") == "6"
        assert CalculationHandler.evaluate_expression("10/2") == "5"
        assert CalculationHandler.evaluate_expression("2+3*4") == "14"
    
    def test_evaluate_expression_functions(self):
        """测试函数表达式计算"""
        result = CalculationHandler.evaluate_expression("sin(0)")
        assert float(result) == 0.0
        
        result = CalculationHandler.evaluate_expression("cos(0)")
        assert float(result) == 1.0
        
        result = CalculationHandler.evaluate_expression("sqrt(16)")
        assert result == "4"
    
    def test_evaluate_expression_error(self):
        """测试表达式错误处理"""
        with pytest.raises(ValueError):
            CalculationHandler.evaluate_expression("2/0")
        
        with pytest.raises(ValueError):
            CalculationHandler.evaluate_expression("unknown_func()")
    
    def test_handle_calculation_pi(self):
        """测试π值计算处理"""
        result = CalculationHandler.handle_calculation("输出π的前10位")
        
        assert result["success"] is True
        assert result["task_type"] == "pi_calculation"
        assert result["result"].startswith("3.14")
    
    def test_handle_calculation_expression(self):
        """测试表达式计算处理"""
        result = CalculationHandler.handle_calculation("计算 2+3*4")
        
        assert result["success"] is True
        assert result["task_type"] == "expression"
        assert result["result"] == "14"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])