"""
检查完整服务状态
"""
import time
import urllib.request
import json

print("等待完整服务启动...")
print("这可能需要10-30秒，因为需要加载模型和初始化系统\n")

for i in range(30):
    time.sleep(1)
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=2) as response:
            if response.status == 200:
                data = json.loads(response.read())
                print("\n" + "="*60)
                print("✅ 完整服务启动成功！")
                print("="*60)
                print("\n🌐 测试界面访问地址:")
                print("\n  ⭐ API文档 (Swagger UI):")
                print("     http://localhost:8000/docs")
                print("\n  📊 其他接口:")
                print("     主页: http://localhost:8000")
                print("     健康检查: http://localhost:8000/health")
                print("     能力矩阵: http://localhost:8000/api/capability_matrix")
                print("     APHI仪表盘: http://localhost:8000/api/aphi")
                print("\n📈 系统状态:")
                print(f"  APHI: {data.get('aphi', 'N/A')}")
                print(f"  模式: {data.get('mode', 'N/A')}")
                print("\n🧪 测试建议:")
                print("  1. 浏览器访问: http://localhost:8000/docs")
                print("  2. 点击 /chat 接口")
                print("  3. 点击 'Try it out'")
                print("  4. 输入测试消息: '你的能力边界在哪里？'")
                print("  5. 点击 'Execute' 查看结果")
                print("="*60)
                break
    except Exception as e:
        if i < 29:
            print(f"  启动中... {i+1}/30秒", end="\r")
        else:
            print(f"\n\n⚠️  服务启动超时")
            print("\n请检查日志:")
            print("  - server_output.log")
            print("  - server_error.log")
            print("\n或手动启动:")
            print("  python backend/main.py")
            print("\n常见问题:")
            print("  1. Ollama未运行 - 启动Ollama")
            print("  2. 模型未下载 - 运行 ollama pull mindchat")
            print("  3. 端口被占用 - 结束占用进程")