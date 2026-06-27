"""
修复scripts/verification目录下脚本的sys.path设置
"""
import os
import glob

scripts = glob.glob("scripts/verification/*.py")
fixed = 0

for script in scripts:
    with open(script, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已有sys.path设置
    if 'sys.path.insert' in content or 'sys.path.append' in content:
        continue
    
    # 在文件开头添加sys.path设置
    lines = content.split('\n')
    new_lines = []
    
    # 找到第一个import sys的位置
    sys_import_found = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        
        if not sys_import_found and line.strip() == 'import sys' and i < 10:
            sys_import_found = True
            # 添加路径设置
            new_lines.append('import os')
            new_lines.append('os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))')
            new_lines.append('sys.path.insert(0, ".")')
    
    if sys_import_found:
        # 写回文件
        with open(script, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        fixed += 1
        print(f"✓ {os.path.basename(script)}")

print(f"\n修复了 {fixed} 个脚本")