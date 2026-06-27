"""
直接测试root函数
"""
import sys
import os
from pathlib import Path

# 切换到项目根目录
os.chdir(Path(__file__).parent)
ROOT_DIR = Path.cwd()
FRONTEND_DIR = ROOT_DIR / "frontend"

print("=" * 70)
print("Root函数模拟测试")
print("=" * 70)
print()

print(f"工作目录: {os.getcwd()}")
print(f"ROOT_DIR: {ROOT_DIR}")
print(f"FRONTEND_DIR: {FRONTEND_DIR}")
print()

frontend_index = FRONTEND_DIR / "index.html"
print(f"index.html: {frontend_index}")
print(f"存在: {frontend_index.exists()}")
print()

if frontend_index.exists():
    with open(frontend_index, 'r', encoding='utf-8') as f:
        html_content = f.read()
    print(f"✅ 成功读取前端文件: {len(html_content)} 字节")
    print()
    print("前200字符:")
    print(html_content[:200])
else:
    print("❌ 文件不存在")
    print()
    print("返回JSON: {\"message\":\"联盟拓荒者 API\",\"docs\":\"/docs\"}")