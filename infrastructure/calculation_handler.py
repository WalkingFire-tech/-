"""
计算任务处理模块 - 增强版
使用通用数学计算器工具，不再硬编码
"""
import re
import math
from typing import Dict, Any, Optional
from loguru import logger


SAFE_FUNCTIONS = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh,
    "log": math.log, "log10": math.log10, "exp": math.exp,
    "sqrt": math.sqrt, "pi": math.pi, "e": math.e,
    "degrees": math.degrees, "radians": math.radians,
    "factorial": math.factorial, "ceil": math.ceil, "floor": math.floor,
    "pow": pow
}


class CalculationHandler:
    """计算任务处理器 - 使用工具系统，支持自我进化"""
    
    @staticmethod
    def extract_pi_digits(text: str) -> Optional[int]:
        """从文本中提取π的小数位数"""
        patterns = [
            r'前\s*(\d+)\s*位',
            r'(\d+)\s*位',
            r'计算.*?(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return int(match.group(1))
        return None
    
    @staticmethod
    def is_pi_calculation(text: str) -> bool:
        """判断是否为π计算任务"""
        pi_keywords = ['π', 'Π', 'pi', '圆周率']
        return any(keyword in text.lower() for keyword in pi_keywords)
    
    @staticmethod
    def is_expression(text: str) -> bool:
        """判断是否为数学表达式"""
        expr_patterns = [
            r'[\d\+\-\*/\(\)%]',          
            r'\b(sin|cos|tan|log|sqrt|exp|pow|abs|round)\b',
        ]
        
        has_pattern = any(re.search(p, text.lower()) for p in expr_patterns)
        is_pi = CalculationHandler.is_pi_calculation(text)
        
        return has_pattern and not is_pi
    
    @staticmethod
    def calculate_pi(digits: int = 100) -> str:
        """计算π的前N位 - 使用工具系统"""
        try:
            from tools.math_calculator import math_calculator
            result = math_calculator.get_constant('pi', digits)
            logger.info(f"使用数学计算器计算π的前{digits}位")
            return result
        except Exception as e:
            logger.warning(f"数学计算器失败，降级到基础方法: {e}")
            try:
                from mpmath import mp
                mp.dps = digits + 10
                pi_str = str(mp.pi)
                return pi_str[:digits + 2]
            except ImportError:
                logger.warning("mpmath未安装,使用标准库")
                return str(math.pi)
    
    @staticmethod
    def evaluate_expression(expression: str) -> str:
        """安全计算数学表达式 - 使用工具系统"""
        try:
            from tools.math_calculator import math_calculator
            result = math_calculator.calculate(expression)
            if result.get('success'):
                logger.info(f"使用数学计算器计算表达式")
                return str(result['result'])
        except Exception as e:
            logger.warning(f"数学计算器失败，降级到基础方法: {e}")
        
        clean_expr = re.sub(r'[^a-zA-Z0-9+\-*/%().,\s]', '', expression)
        
        try:
            namespace = {"__builtins__": None, **SAFE_FUNCTIONS}
            result = eval(clean_expr, namespace)
            
            if isinstance(result, float):
                result = round(result, 15)
                if result.is_integer():
                    result = int(result)
            
            return str(result)
        
        except SyntaxError as e:
            raise ValueError(f"表达式语法错误: {e}")
        except ZeroDivisionError:
            raise ValueError("除数不能为零")
        except NameError as e:
            raise ValueError(f"未知函数或变量: {e}")
        except Exception as e:
            raise ValueError(f"计算错误: {e}")
    
    @staticmethod
    def handle_calculation(intent_text: str) -> Dict[str, Any]:
        """处理计算任务(π值或数学表达式) - 优先使用工具系统"""
        result = {
            "success": False,
            "result": None,
            "error": None,
            "task_type": None
        }
        
        try:
            if CalculationHandler.is_pi_calculation(intent_text):
                digits = CalculationHandler.extract_pi_digits(intent_text)
                if digits is None:
                    digits = 100
                
                pi_value = CalculationHandler.calculate_pi(digits)
                result["success"] = True
                result["result"] = pi_value
                result["task_type"] = "pi_calculation"
                logger.info(f"计算π的前{digits}位成功")
            
            elif CalculationHandler.is_expression(intent_text):
                expr = re.sub(r'^(计算|求值|等于|结果|算式)[:：]?', '', intent_text).strip()
                if not expr:
                    expr = intent_text
                
                value = CalculationHandler.evaluate_expression(expr)
                result["success"] = True
                result["result"] = value
                result["task_type"] = "expression"
                logger.info(f"计算表达式 '{expr}' = {value}")
            
            else:
                result["error"] = "不支持的计算类型"
        
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"计算失败: {e}")
        
        return result
