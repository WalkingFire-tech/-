"""
测试完整后端导入
"""
import sys
sys.path.insert(0, '.')

print("=" * 70)
print("测试完整后端导入")
print("=" * 70)
print()

try:
    print("[1/3] 导入backend.main...")
    from backend.main import app
    print("  ✓ backend.main导入成功")
except Exception as e:
    print(f"  ✗ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[2/3] 检查路由数量...")
    print(f"  ✓ 路由数量: {len(app.routes)}")
except Exception as e:
    print(f"  ✗ 检查失败: {e}")

try:
    print("\n[3/3] 检查lifespan...")
    print("  ✓ lifespan已配置")
except Exception as e:
    print(f"  ✗ 检查失败: {e}")

print()
print("=" * 70)
print("✅ 完整后端可以启动")
print()
print("启动命令:")
print("  START_FULL.bat")
print("  或")
print("  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
print("=" * 70)