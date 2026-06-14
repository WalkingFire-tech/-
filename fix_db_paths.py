#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""批量修复数据库路径"""
import os
import re
from pathlib import Path

# 需要修复的数据库文件
db_files = [
    'experience_pool.db',
    'learning_rules.db',
    'model_stats.db',
    'counterfactual_history.db'
]

# 需要排除的目录
exclude_dirs = ['.venv', 'venv', '.git', '__pycache__', 'node_modules', '.codeartsdoer']

def should_fix_file(file_path: Path) -> bool:
    """判断文件是否需要修复"""
    # 排除特定目录
    for exclude in exclude_dirs:
        if exclude in str(file_path):
            return False
    
    # 只处理Python文件
    if file_path.suffix != '.py':
        return False
    
    return True

def fix_db_paths(file_path: Path) -> int:
    """修复文件中的数据库路径"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # 修复模式：sqlite3.connect('xxx.db') -> sqlite3.connect('data/xxx.db')
        for db_file in db_files:
            # 匹配 sqlite3.connect('data/experience_pool.db') 但不匹配已经有data/的
            pattern = rf"sqlite3\.connect\('{db_file}'\)"
            replacement = f"sqlite3.connect('data/{db_file}')"
            content = re.sub(pattern, replacement, content)
        
        # 如果有修改，写回文件
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return 1
        
        return 0
    
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return 0

def main():
    print("=" * 60)
    print("批量修复数据库路径")
    print("=" * 60)
    
    # 遍历所有Python文件
    fixed_count = 0
    total_count = 0
    
    for py_file in Path('.').rglob('*.py'):
        if should_fix_file(py_file):
            total_count += 1
            fixed = fix_db_paths(py_file)
            if fixed:
                fixed_count += 1
                print(f"  ✓ {py_file}")
    
    print("\n" + "=" * 60)
    print(f"扫描文件: {total_count}")
    print(f"修复文件: {fixed_count}")
    print("=" * 60)

if __name__ == '__main__':
    main()