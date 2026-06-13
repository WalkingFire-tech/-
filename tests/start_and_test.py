"""启动后端并捕获日志"""
import subprocess
import sys
import time
from pathlib import Path

print("=" * 60)
print("启动后端服务")
print("=" * 60)

# 启动uvicorn
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd=Path(__file__).parent
)

print(f"进程ID: {proc.pid}")
print("等待启动...\n")

# 读取输出10秒
start_time = time.time()
output_lines = []

try:
    while time.time() - start_time < 10:
        line = proc.stdout.readline()
        if line:
            output_lines.append(line.strip())
            print(line.strip())
            
            # 检查是否启动成功
            if "Application startup complete" in line:
                print("\n✅ 后端启动成功！")
                print("访问地址: http://localhost:8000/")
                
                # 测试API
                import requests
                try:
                    response = requests.get("http://localhost:8000/api/health", timeout=5)
                    print(f"\n健康检查: {response.json()}")
                except Exception as e:
                    print(f"\n健康检查失败: {e}")
                
                break
except KeyboardInterrupt:
    print("\n用户中断")

# 如果没有启动成功
if not any("Application startup complete" in line for line in output_lines):
    print("\n❌ 启动失败")
    print("\n最后20行输出:")
    for line in output_lines[-20:]:
        print(line)
    
    # 检查错误
    if any("Error" in line or "error" in line for line in output_lines):
        print("\n发现错误，请检查上述日志")

# 保持进程运行
print(f"\n进程仍在运行 (PID: {proc.pid})")
print("按Ctrl+C停止")