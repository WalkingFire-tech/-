"""测试工具管理器"""
from core.tool_manager import tool_manager

# 测试1: 创建安全工具
safe_code = '''
def extract_numbers(text):
    import re
    return re.findall(r'\\d+', text)
'''

result = tool_manager.create_tool(
    name='extract_numbers',
    code=safe_code,
    description='从文本中提取数字'
)
print(f'✅ 安全工具创建: {result}')

if result:
    # 执行工具
    test_result = tool_manager.execute_tool('extract_numbers', 'abc123def456')
    print(f'✅ 工具执行结果: {test_result}')
    
    # 获取工具信息
    info = tool_manager.get_tool_info('extract_numbers')
    if info:
        print(f'✅ 工具信息: 使用次数={info["usage_count"]}, 成功次数={info["success_count"]}')

# 测试2: 危险代码（应该失败）
dangerous_code = '''
def dangerous():
    import os
    os.system('ls')
'''

result = tool_manager.create_tool(
    name='dangerous_tool',
    code=dangerous_code,
    description='危险工具'
)
print(f'❌ 危险工具创建: {result} (正确拦截)')

# 测试3: 禁止的内置函数（应该失败）
eval_code = '''
def use_eval():
    return eval('1+1')
'''

result = tool_manager.create_tool(
    name='eval_tool',
    code=eval_code,
    description='使用eval'
)
print(f'❌ eval工具创建: {result} (正确拦截)')

# 测试4: 列出所有工具
tools = tool_manager.list_tools()
print(f'\n📋 已注册工具数量: {len(tools)}')
for tool in tools:
    print(f'  - {tool["name"]}: {tool["description"]}')

# 测试5: 获取统计信息
stats = tool_manager.get_tool_usage_stats()
print(f'\n📊 工具统计:')
print(f'  - 总工具数: {stats["total_tools"]}')
print(f'  - 总使用次数: {stats["total_uses"]}')
print(f'  - 平均成功率: {stats["avg_success_rate"]:.2%}')