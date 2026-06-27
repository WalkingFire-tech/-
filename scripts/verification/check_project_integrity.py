import os
import sys

init_files = [
    'meta/__init__.py',
    'adapters/__init__.py',
    'adapters/llm/__init__.py',
    'adapters/input/__init__.py',
    'adapters/ui/__init__.py',
    'core/__init__.py',
    'tools/__init__.py',
    'infrastructure/__init__.py',
]

print('=== 项目完整性检查 ===\n')
print('1. __init__.py文件检查:')
all_ok = True
for f in init_files:
    exists = os.path.exists(f)
    status = '✓' if exists else '✗'
    print(f'   {status} {f}')
    if not exists:
        all_ok = False

print('\n2. 核心模块检查:')
core_modules = [
    'infrastructure/reflection_pipeline.py',
    'infrastructure/quick_reflex.py',
    'core/orchestrator.py',
    'core/cognitive_dispatcher.py',
    'core/metacognitive_executor.py',
    'core/sleep_consolidator.py',
    'core/canary_evaluator.py',
    'tools/arbiter.py',
    'tools/registry.py',
    'meta/induction.py',
]

for m in core_modules:
    exists = os.path.exists(m)
    status = '✓' if exists else '✗'
    print(f'   {status} {m}')
    if not exists:
        all_ok = False

print('\n3. 数据库检查:')
dbs = [
    'data/experience_pool.db',
    'data/learning_rules.db',
    'logs/campfire_log.db',
]

for d in dbs:
    exists = os.path.exists(d)
    status = '✓' if exists else '✗'
    print(f'   {status} {d}')
    if not exists:
        all_ok = False

print('\n4. 配置文件检查:')
configs = [
    'config/reflex_rules.yaml',
]

for c in configs:
    exists = os.path.exists(c)
    status = '✓' if exists else '✗'
    print(f'   {status} {c}')
    if not exists:
        all_ok = False

print(f'\n=== 结果: {"全部通过 ✓" if all_ok else "存在问题 ✗"} ===')