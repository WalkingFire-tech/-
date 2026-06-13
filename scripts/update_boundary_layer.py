"""更新README架构 - 将哲学层改为边界层"""
with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换哲学层为边界层
content = content.replace(
    'L0: 哲学层 (Philosophy Layer)',
    'L0: 边界层 (Boundary Layer)'
)

# 替换哲学层描述
old_desc = """│  ┌──────────────────────────────────────────────────────┐  │
│  │  不渡他人  │  知止  │  守底线  │  可被质疑           │  │
│  └──────────────────────────────────────────────────────┘  │
│  ↳ 所有回应必须通过哲学承诺检查                              │"""

new_desc = """│  ┌────────────────────────────────────────────────────┐  │
│  │  懂善恶  │  明事理  │  守底线  │  助文明  │  不渡他人  │  │
│  └────────────────────────────────────────────────────┘  │
│  ↳ 价值判断 → 逻辑验证 → 安全检查 → 社会责任 → 行为边界    │"""

content = content.replace(old_desc, new_desc)

# 替换防御机制表格
old_table = """| L0 | 哲学承诺 | 所有回应通过价值观检查 |"""

new_table = """| L0 | 边界守护 | 懂善恶、明事理、守底线、助文明、不渡他人 |"""

content = content.replace(old_table, new_table)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)

print('README.md已更新：哲学层 → 边界层')