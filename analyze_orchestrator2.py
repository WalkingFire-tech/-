#!/usr/bin/env python
"""分析chat_orchestrator.py的async函数结构"""
import ast

with open('backend/services/chat_orchestrator.py', 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())

functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]

print(f'函数总数: {len(functions)}')
async_funcs = [f for f in functions if isinstance(f, ast.AsyncFunctionDef)]
sync_funcs = [f for f in functions if isinstance(f, ast.FunctionDef)]
print(f'  - async函数: {len(async_funcs)}')
print(f'  - sync函数: {len(sync_funcs)}')

print('\nAsync函数列表 (按行号排序):')
for i, func in enumerate(sorted(async_funcs, key=lambda f: f.lineno), 1):
    print(f'  {i}. {func.name} (行{func.lineno}, {len(func.body)}行)')

print('\nSync函数列表 (按行号排序):')
for i, func in enumerate(sorted(sync_funcs, key=lambda f: f.lineno), 1):
    print(f'  {i}. {func.name} (行{func.lineno}, {len(func.body)}行)')

# 分析最长函数
print('\n最长的10个函数:')
for i, func in enumerate(sorted(functions, key=lambda f: len(f.body), reverse=True)[:10], 1):
    func_type = 'async' if isinstance(func, ast.AsyncFunctionDef) else 'sync'
    print(f'  {i}. {func.name} ({func_type}, 行{func.lineno}, {len(func.body)}行)')