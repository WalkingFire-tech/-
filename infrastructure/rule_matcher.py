"""
规则匹配引擎 - 支持复杂条件表达式
使用simpleeval实现安全的表达式求值
"""
import re
from typing import Dict, Any, Optional
from loguru import logger


class RuleMatcher:
    """规则匹配引擎"""
    
    def __init__(self):
        self.safe_names = {
            "True": True,
            "False": False,
            "None": None,
        }
        logger.info("规则匹配引擎初始化完成")
    
    def evaluate_condition(self, 
                          condition: str, 
                          context: Dict[str, Any]) -> bool:
        """评估条件表达式
        
        Args:
            condition: 条件字符串(如 "intent_type == 'code' and quality < 30")
            context: 上下文变量(如 {"intent_type": "code", "quality": 25})
        
        Returns:
            条件是否满足
        """
        try:
            return self._simple_eval(condition, context)
        except Exception as e:
            logger.debug(f"条件评估失败: {condition}, 错误: {e}")
            return self._fallback_match(condition, context)
    
    def _simple_eval(self, expression: str, context: Dict[str, Any]) -> bool:
        """简单表达式求值(安全)"""
        try:
            from simpleeval import simple_eval
            
            names = {**self.safe_names, **context}
            
            result = simple_eval(
                expression,
                names=names,
                functions={}
            )
            
            return bool(result)
        
        except ImportError:
            logger.warning("simpleeval未安装,使用降级匹配")
            return self._fallback_match(expression, context)
    
    def _fallback_match(self, condition: str, context: Dict[str, Any]) -> bool:
        """降级匹配(字符串精确匹配)"""
        for key, value in context.items():
            if isinstance(value, str):
                pattern = f"{key} == '{value}'"
                if pattern in condition:
                    continue
                elif f"{key} == \"{value}\"" in condition:
                    continue
                else:
                    return False
            elif isinstance(value, (int, float)):
                import re
                pattern = rf"{key}\s*[<>=!]+\s*{value}"
                if not re.search(pattern, condition):
                    return False
        
        return True
    
    def parse_complex_condition(self, condition: str) -> Dict[str, Any]:
        """解析复杂条件表达式
        
        Returns:
            {
                "type": "simple" | "and" | "or" | "complex",
                "parts": [...],  # 子条件列表
                "raw": condition
            }
        """
        if " and " in condition.lower():
            parts = re.split(r'\s+and\s+', condition, flags=re.IGNORECASE)
            return {
                "type": "and",
                "parts": [self.parse_complex_condition(p) for p in parts],
                "raw": condition
            }
        
        elif " or " in condition.lower():
            parts = re.split(r'\s+or\s+', condition, flags=re.IGNORECASE)
            return {
                "type": "or",
                "parts": [self.parse_complex_condition(p) for p in parts],
                "raw": condition
            }
        
        else:
            return {
                "type": "simple",
                "parts": [condition],
                "raw": condition
            }
    
    def condition_overlap(self, cond1: str, cond2: str) -> bool:
        """检测两个条件是否重叠(语义)
        
        Args:
            cond1: 条件1
            cond2: 条件2
        
        Returns:
            是否存在重叠
        """
        if cond1 == cond2:
            return True
        
        parsed1 = self.parse_complex_condition(cond1)
        parsed2 = self.parse_complex_condition(cond2)
        
        if parsed1["type"] == "simple" and parsed2["type"] == "simple":
            return self._simple_overlap(cond1, cond2)
        
        return False
    
    def _simple_overlap(self, cond1: str, cond2: str) -> bool:
        """简单条件重叠检测"""
        var1 = self._extract_variable(cond1)
        var2 = self._extract_variable(cond2)
        
        if var1 and var2 and var1 != var2:
            return False
        
        if var1 and var1 == var2:
            op1, val1 = self._extract_op_value(cond1)
            op2, val2 = self._extract_op_value(cond2)
            
            if op1 and op2 and val1 and val2:
                return self._range_overlap(op1, val1, op2, val2)
        
        return False
    
    def _extract_variable(self, condition: str) -> Optional[str]:
        """提取条件中的变量名"""
        match = re.search(r'(\w+)\s*[<>=!]', condition)
        return match.group(1) if match else None
    
    def _extract_op_value(self, condition: str) -> tuple:
        """提取操作符和值"""
        match = re.search(r'(\w+)\s*([<>=!]+)\s*(\d+\.?\d*)', condition)
        if match:
            return match.group(2), float(match.group(3))
        return None, None
    
    def _range_overlap(self, op1: str, val1: float, op2: str, val2: float) -> bool:
        """判断两个数值范围是否重叠"""
        range1 = self._op_to_range(op1, val1)
        range2 = self._op_to_range(op2, val2)
        
        if not range1 or not range2:
            return False
        
        min1, max1 = range1
        min2, max2 = range2
        
        return not (max1 < min2 or max2 < min1)
    
    def _op_to_range(self, op: str, val: float) -> Optional[tuple]:
        """操作符转换为范围"""
        if op == "<":
            return (float('-inf'), val)
        elif op == "<=":
            return (float('-inf'), val)
        elif op == ">":
            return (val, float('inf'))
        elif op == ">=":
            return (val, float('inf'))
        elif op == "==" or op == "=":
            return (val, val)
        else:
            return None


rule_matcher = RuleMatcher()