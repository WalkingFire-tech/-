"""测试数学计算器"""
from tools.math_calculator import math_calculator

# 测试1: 函数参数（逗号）
print("测试1: 函数参数支持")
result = math_calculator.calculate('max(1,2)')
print(f"  max(1,2) = {result.get('result')} (成功: {result.get('success')})")

result = math_calculator.calculate('min(5,3)')
print(f"  min(5,3) = {result.get('result')} (成功: {result.get('success')})")

# 测试2: 常量
print("\n测试2: 常量支持")
result = math_calculator.calculate('π')
print(f"  π = {result.get('result')[:20]}... (成功: {result.get('success')})")

result = math_calculator.calculate('e')
print(f"  e = {result.get('result')[:20]}... (成功: {result.get('success')})")

# 测试3: 基本计算
print("\n测试3: 基本计算")
result = math_calculator.calculate('25*4+18/3')
print(f"  25*4+18/3 = {result.get('result')} (成功: {result.get('success')})")

result = math_calculator.calculate('sqrt(16)')
print(f"  sqrt(16) = {result.get('result')} (成功: {result.get('success')})")

# 测试4: 三角函数
print("\n测试4: 三角函数")
result = math_calculator.calculate('sin(pi/2)')
print(f"  sin(pi/2) = {result.get('result')} (成功: {result.get('success')})")

result = math_calculator.calculate('cos(0)')
print(f"  cos(0) = {result.get('result')} (成功: {result.get('success')})")

# 测试5: datetime导入验证
print("\n测试5: datetime导入验证")
try:
    from tools.math_calculator import datetime
    print(f"  ✅ datetime已导入: {datetime.now()}")
except ImportError:
    print("  ❌ datetime未导入")

# 测试6: 工具接口
print("\n测试6: 工具接口")
from tools.math_calculator import math_calculator_tool
print(f"  工具名称: {math_calculator_tool.name}")
print(f"  工具描述: {math_calculator_tool.description}")
tool_dict = math_calculator_tool.to_dict()
print(f"  to_dict: {tool_dict}")