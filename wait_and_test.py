"""
等待并测试服务
"""
import time
import urllib.request
import json

print("等待服务启动...")
for i in range(10):
    time.sleep(1)
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read())
                print("\n✅ 服务已启动成功！\n")
                print("="*60)
                print("测试界面访问地址")
                print("="*60)
                print("\n🌐 Web界面:")
                print("  主页: http://localhost:8000")
                print("  健康检查: http://localhost:8000/health")
                print("  API文档: http://localhost:8000/docs")
                print("  测试接口: http://localhost:8000/test")
                print("\n📊 系统状态:")
                print(f"  APHI: {data.get('aphi', 'N/A')}")
                print(f"  模式: {data.get('mode', 'N/A')}")
                print("\n💡 测试示例:")
                print("  浏览器访问: http://localhost:8000/test")
                print("="*60)
                break
    except Exception as e:
        if i < 9:
            print(f"  尝试 {i+1}/10...", end="\r")
        else:
            print(f"\n❌ 服务启动失败: {e}")
            print("\n请手动启动:")
            print("  python simple_backend.py")