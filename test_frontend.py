"""
测试minimal_app是否能正确返回前端
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
FRONTEND_DIR = ROOT_DIR / "frontend"

print("=" * 70)
print("前端文件测试")
print("=" * 70)
print()

print(f"ROOT_DIR: {ROOT_DIR.absolute()}")
print(f"FRONTEND_DIR: {FRONTEND_DIR.absolute()}")
print()

frontend_index = FRONTEND_DIR / "index.html"
print(f"index.html路径: {frontend_index.absolute()}")
print(f"index.html存在: {frontend_index.exists()}")
print()

if frontend_index.exists():
    with open(frontend_index, 'r', encoding='utf-8') as f:
        content = f.read()
    print(f"文件大小: {len(content)} 字节")
    print(f"前100字符: {content[:100]}")
    print()
    print("✅ 前端文件正常")
else:
    print("❌ 前端文件不存在")
    print()
    print("可能原因:")
    print("  1. 路径错误")
    print("  2. 文件被删除")
    print("  3. 工作目录错误")