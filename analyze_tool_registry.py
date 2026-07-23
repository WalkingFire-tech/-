#!/usr/bin/env python
"""分析core/tool_registry.py的结构"""
import ast

with open('core/tool_registry.py', 'r', encoding='utf-8') as f:
    tree = ast.parse(f.read())

# 获取所有类
classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
print(f'类数量: {len(classes)}')
print('\n类列表 (按行号排序):')
for i, cls in enumerate(sorted(classes, key=lambda c: c.lineno), 1):
    methods = [node for node in cls.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    print(f'  {i}. {cls.name} (行{cls.lineno}, {len(methods)}个方法)')

# 获取所有函数
functions = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
print(f'\n函数总数: {len(functions)}')
async_funcs = [f for f in functions if isinstance(f, ast.AsyncFunctionDef)]
sync_funcs = [f for f in functions if isinstance(f, ast.FunctionDef)]
print(f'  - async函数: {len(async_funcs)}')
print(f'  - sync函数: {len(sync_funcs)}')

# 分析最长函数
print('\n最长的10个函数:')
for i, func in enumerate(sorted(functions, key=lambda f: len(f.body), reverse=True)[:10], 1):
    func_type = 'async' if isinstance(func, ast.AsyncFunctionDef) else 'sync'
    print(f'  {i}. {func.name} ({func_type}, 行{func.lineno}, {len(func.body)}行)')