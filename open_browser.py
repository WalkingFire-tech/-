"""
等待服务启动并打开浏览器
"""
import time
import webbrowser
import urllib.request

print("等待服务启动...")

for i in range(15):
    time.sleep(1)
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=2) as response:
            if response.status == 200:
                print(f"\n✅ 服务已启动！")
                print("\n正在打开测试界面...")
                
                # 打开浏览器
                webbrowser.open("http://localhost:8000/docs")
                
                print("\n" + "="*60)
                print("测试界面已打开")
                print("="*60)
                print("\n如果浏览器未自动打开，请手动访问:")
                print("  http://localhost:8000/docs")
                print("\n其他接口:")
                print("  主页: http://localhost:8000")
                print("  健康检查: http://localhost:8000/health")
                print("="*60)
                break
    except:
        if i < 14:
            print(f"  启动中... {i+1}/15秒", end="\r")
        else:
            print(f"\n\n⚠️  服务启动超时")
            print("\n请手动启动:")
            print("  1. 打开新命令行窗口")
            print("  2. 运行: python backend_lite.py")
            print("  3. 浏览器访问: http://localhost:8000/docs")