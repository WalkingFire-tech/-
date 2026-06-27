"""
检查所有文件中的路径引用
"""
import os
import re

print("=" * 70)
print("路径引用检查")
print("=" * 70)
print()

# 关键文件列表
key_files = [
    'infrastructure/reflection_pipeline.py',
    'infrastructure/experience_pool.py',
    'infrastructure/quick_reflex.py',
    'infrastructure/config_manager.py',
    'core/orchestrator.py',
    'core/cognitive_dispatcher.py',
    'core/metacognitive_executor.py',
    'core/sleep_consolidator.py',
    'core/canary_evaluator.py',
    'meta/induction.py',
    'tools/registry.py',
    'tools/arbiter.py',
    'backend/main.py',
    'minimal_app.py',
]

# 路径引用
path_refs = []

for file_path in key_files:
    if not os.path.exists(file_path):
        print(f"✗ 文件不存在: {file_path}")
        continue
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        # 检查各种路径引用
        if any(p in line for p in ['data/', 'logs/', 'config/']):
            # 过滤掉注释
            if not line.strip().startswith('#'):
                path_refs.append({
                    'file': file_path,
                    'line': i,
                    'content': line.strip()[:100]
                })

print(f"检查了 {len(key_files)} 个文件")
print(f"发现 {len(path_refs)} 个路径引用")
print()

# 按文件分组显示
from collections import defaultdict
by_file = defaultdict(list)
for ref in path_refs:
    by_file[ref['file']].append(ref)

for file_path in sorted(by_file.keys()):
    refs = by_file[file_path]
    print(f"\n{file_path} ({len(refs)}个引用):")
    for ref in refs[:5]:  # 每个文件最多显示5个
        print(f"  L{ref['line']}: {ref['content']}")

print("\n" + "=" * 70)
print("检查完成")
print("=" * 70)