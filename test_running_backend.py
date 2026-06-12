"""测试已运行的后端"""
import json
import sys
from pathlib import Path

print("=" * 70)
print("测试后端API（假设后端已运行）")
print("=" * 70)

tests = [
    ("健康检查", "/api/health"),
    ("统计信息", "/api/stats"),
    ("模型列表", "/api/models"),
    ("前端页面", "/"),
]

results = []

for name, endpoint in tests:
    print(f"\n测试: {name} ({endpoint})")
    try:
        import urllib.request
        url = f"http://localhost:8000{endpoint}"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = response.read()
            
            if endpoint == "/":
                print(f"  ✓ 状态码: {response.status}")
                print(f"  ✓ 内容长度: {len(data)} bytes")
            else:
                json_data = json.loads(data)
                print(f"  ✓ 响应: {json.dumps(json_data, ensure_ascii=False, indent=2)[:200]}")
            
            results.append((name, True))
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        results.append((name, False))

print("\n" + "=" * 70)
print("测试总结")
print("=" * 70)

passed = sum(1 for _, r in results if r)
total = len(results)

for name, result in results:
    status = "✓" if result else "✗"
    print(f"{status} {name}")

print(f"\n通过: {passed}/{total}")

if passed == total:
    print("\n🎉 所有测试通过！")
    print("\n浏览器访问: http://localhost:8000/")
else:
    print("\n⚠️ 部分测试失败")
    print("\n请确保后端已启动:")
    print("  python -m uvicorn api:app --host 0.0.0.0 --port 8000")