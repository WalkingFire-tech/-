"""
通用数学计算器工具 - 支持动态计算、自动学习
不再硬编码固定值，而是通过工具调用实现
"""
import math
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

try:
    import mpmath
    MPMATH_AVAILABLE = True
except ImportError:
    MPMATH_AVAILABLE = False
    logger.warning("mpmath未安装，使用标准math库")

try:
    import numexpr as ne
    NUMEXPR_AVAILABLE = True
except ImportError:
    NUMEXPR_AVAILABLE = False
    logger.warning("numexpr未安装，使用eval")


class MathCalculator:
    """通用数学计算器 - 动态计算、可学习"""
    
    ALLOWED_FUNCTIONS = {
        # 三角函数
        'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
        'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
        # 对数指数
        'log', 'log10', 'log2', 'exp', 'sqrt',
        # 其他
        'abs', 'round', 'floor', 'ceil',
        'factorial', 'gamma',
        # 统计函数
        'max', 'min', 'sum',
    }
    
    CONSTANTS = {
        'π': 'pi',
        'pi': 'pi',
        'e': 'e',
        'φ': 'phi',
        'phi': 'phi',
        '黄金分割比': 'phi',
    }
    
    def __init__(self, precision: int = 100):
        self.precision = precision
        self.learning_history = []
        
        if MPMATH_AVAILABLE:
            mpmath.mp.dps = precision
        
        logger.info(f"数学计算器已初始化 (精度: {precision}位)")
    
    def calculate(self, expression: str) -> Dict[str, Any]:
        """计算数学表达式
        
        Args:
            expression: 数学表达式（如 "π的前100位", "25*4+18/3"）
        
        Returns:
            计算结果字典
        """
        logger.info(f"计算表达式: {expression}")
        
        # 1. 预处理表达式
        processed = self._preprocess(expression)
        
        # 2. 尝试计算
        try:
            result = self._evaluate(processed)
            
            return {
                'success': True,
                'result': result,
                'expression': expression,
                'processed': processed,
                'method': 'calculator'
            }
            
        except Exception as e:
            logger.warning(f"计算失败: {e}")
            
            # 3. 尝试学习新表达式
            learned = self._try_learn(expression, str(e))
            
            if learned:
                return {
                    'success': True,
                    'result': learned,
                    'expression': expression,
                    'method': 'learned'
                }
            
            return {
                'success': False,
                'error': str(e),
                'expression': expression,
                'suggestion': '请提供更明确的数学表达式'
            }
    
    def _preprocess(self, expression: str) -> str:
        """预处理表达式"""
        import re
        
        chinese_num_map = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '百': 100, '千': 1000, '万': 10000
        }
        
        def convert_chinese_num(text: str) -> str:
            if not any(cn in text for cn in chinese_num_map):
                return text
            
            result = text
            for cn, num in chinese_num_map.items():
                result = result.replace(cn, str(num))
            
            return result
        
        expression = convert_chinese_num(expression)
        
        pi_pattern = re.search(r'π.*?前.*?(\d+).*?位', expression)
        if pi_pattern:
            digits = int(pi_pattern.group(1))
            if MPMATH_AVAILABLE:
                mpmath.mp.dps = digits + 2
                return f"str(mpmath.pi)[:{digits+1}]"
            else:
                return f"math.pi"
        
        for const, name in self.CONSTANTS.items():
            if const in expression:
                expression = expression.replace(const, name)
        
        math_expr = re.findall(r'[\d\+\-\*\/\(\)\.\s\w,]+', expression)
        if math_expr:
            expression = ''.join(math_expr)
        
        return expression.strip()
    
    def _evaluate(self, expression: str) -> str:
        """求值表达式"""
        import re
        
        safe_chars = re.match(r'^[\d\+\-\*\/\(\)\.\s\w,\%\^]+$', expression)
        if not safe_chars:
            raise ValueError(f"表达式包含非法字符: {expression}")
        
        dangerous_patterns = ['__', 'import', 'exec', 'eval', 'compile', 'open']
        for pattern in dangerous_patterns:
            if pattern in expression.lower():
                raise ValueError(f"表达式包含危险模式: {pattern}")
        
        safe_dict = {
            'pi': mpmath.pi if MPMATH_AVAILABLE else math.pi,
            'e': mpmath.e if MPMATH_AVAILABLE else math.e,
            'phi': (1 + mpmath.sqrt(5)) / 2 if MPMATH_AVAILABLE else (1 + math.sqrt(5)) / 2,
        }
        
        if MPMATH_AVAILABLE:
            for func in self.ALLOWED_FUNCTIONS:
                if hasattr(mpmath, func):
                    safe_dict[func] = getattr(mpmath, func)
                elif hasattr(math, func):
                    safe_dict[func] = getattr(math, func)
        else:
            for func in self.ALLOWED_FUNCTIONS:
                if hasattr(math, func):
                    safe_dict[func] = getattr(math, func)
        
        safe_dict['max'] = max
        safe_dict['min'] = min
        safe_dict['sum'] = sum
        safe_dict['abs'] = abs
        safe_dict['round'] = round
        
        if NUMEXPR_AVAILABLE:
            try:
                result = ne.evaluate(expression, local_dict=safe_dict)
                return self._format_result(result)
            except Exception:
                logger.warning("操作降级跳过")
        
        try:
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return self._format_result(result)
        except Exception:
            logger.warning("操作降级跳过")
        
        if MPMATH_AVAILABLE:
            try:
                result = mpmath.mpf(expression)
                return self._format_result(result)
            except Exception:
                logger.warning("操作降级跳过")
        
        raise ValueError(f"无法计算表达式: {expression}")
    
    def _format_result(self, result) -> str:
        """格式化结果"""
        if MPMATH_AVAILABLE and isinstance(result, mpmath.mpf):
            return mpmath.nstr(result, min(self.precision, 50))
        elif isinstance(result, float):
            if abs(result) < 1e-10 or abs(result) > 1e10:
                return f"{result:.15e}"
            else:
                return f"{result:.15g}"
        else:
            return str(result)
    
    def _try_learn(self, expression: str, error: str) -> Optional[str]:
        """尝试学习新表达式"""
        # 记录失败
        self.learning_history.append({
            'expression': expression,
            'error': error,
            'timestamp': str(datetime.now())
        })
        
        # 简单的学习策略：尝试分解表达式
        import re
        
        # 检测是否是序列求和
        if '求和' in expression or 'sum' in expression.lower():
            # 提取求和范围
            nums = re.findall(r'\d+', expression)
            if len(nums) >= 2:
                start, end = int(nums[0]), int(nums[1])
                # 尝试简单求和
                result = sum(range(start, end + 1))
                logger.info(f"学习成功: 求和 {start}到{end} = {result}")
                return str(result)
        
        # 检测是否是阶乘
        if '阶乘' in expression or '!' in expression:
            nums = re.findall(r'\d+', expression)
            if nums:
                n = int(nums[0])
                if n < 100:  # 安全限制
                    result = math.factorial(n)
                    logger.info(f"学习成功: {n}! = {result}")
                    return str(result)
        
        return None
    
    def get_constant(self, name: str, digits: int = 50) -> str:
        """获取数学常量
        
        Args:
            name: 常量名（pi, e, phi等）
            digits: 精度位数
        
        Returns:
            常量值字符串
        """
        if MPMATH_AVAILABLE:
            mpmath.mp.dps = digits + 2
            
            if name in ['pi', 'π']:
                return str(mpmath.pi)
            elif name == 'e':
                return str(mpmath.e)
            elif name in ['phi', 'φ']:
                return str((1 + mpmath.sqrt(5)) / 2)
        
        # 降级到标准库
        if name in ['pi', 'π']:
            return str(math.pi)
        elif name == 'e':
            return str(math.e)
        elif name in ['phi', 'φ']:
            return str((1 + math.sqrt(5)) / 2)
        
        raise ValueError(f"未知常量: {name}")
    
    def export_stats(self) -> Dict:
        """导出统计信息"""
        return {
            'precision': self.precision,
            'mpmath_available': MPMATH_AVAILABLE,
            'numexpr_available': NUMEXPR_AVAILABLE,
            'learning_attempts': len(self.learning_history),
            'allowed_functions': len(self.ALLOWED_FUNCTIONS),
            'constants': len(self.CONSTANTS)
        }


math_calculator = MathCalculator()


# 工具接口（供tool_registry调用）
try:
    from tools.base import Tool, ToolCategory, Parameter, ToolResult
    
    class MathCalculatorTool(Tool):
        """数学计算器工具（工具系统接口）"""
        
        @property
        def name(self) -> str:
            return "math_calculator"
        
        @property
        def description(self) -> str:
            return "计算数学表达式、常量、函数值（支持高精度计算）"
        
        @property
        def category(self) -> ToolCategory:
            return ToolCategory.CALCULATION
        
        @property
        def parameters(self):
            return [
                Parameter(
                    name="expression",
                    type="str",
                    description="数学表达式（如 'π的前100位', '25*4+18/3', 'sin(pi/2)'）",
                    required=True
                )
            ]
        
        def execute(self, **kwargs) -> ToolResult:
            """执行计算"""
            expression = kwargs.get("expression", "")
            if not expression:
                return ToolResult(
                    success=False,
                    output=None,
                    error="缺少表达式参数"
                )
            
            result = math_calculator.calculate(expression)
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    output=result.get('result'),
                    metadata={
                        'expression': expression,
                        'processed': result.get('processed'),
                        'method': result.get('method')
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=result.get('error', '计算失败')
                )
    
    math_calculator_tool = MathCalculatorTool()

except ImportError:
    logger.warning("Tool基类未找到，使用简化版")
    
    class MathCalculatorTool:
        """数学计算器工具（简化版）"""
        
        name = "math_calculator"
        description = "计算数学表达式、常量、函数值"
        
        def execute(self, expression: str):
            """执行计算"""
            return math_calculator.calculate(expression)
        
        def to_dict(self):
            return {
                "name": self.name,
                "description": self.description,
                "category": "calculation"
            }
    
    math_calculator_tool = MathCalculatorTool()