#!/usr/bin/env python
"""分析chat_orchestrator.py的函数结构"""
import ast

with open('backend/services/chat_orchestrator.py', 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())

functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

print(f'函数数量: {len(functions)}')
print('\n函数列表 (按行号排序):')
for i, func in enumerate(sorted(functions, key=lambda f: f.lineno)[:30], 1):
    print(f'  {i}. {func.name} (行{func.lineno}, {len(func.body)}行)')

if len(functions) > 30:
    print(f'  ... 还有 {len(functions)-30} 个函数')

# 分析最长函数
print('\n最长的10个函数:')
for i, func in enumerate(sorted(functions, key=lambda f: len(f.body), reverse=True)[:10], 1):
    print(f'  {i}. {func.name} (行{func.lineno}, {len(func.body)}行)')