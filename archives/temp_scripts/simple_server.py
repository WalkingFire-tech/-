"""
最简单的HTTP服务器 - 用于测试
"""
import http.server
import socketserver
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

PORT = 8000

print("=" * 70)
print("简单HTTP服务器")
print("=" * 70)
print()
print(f"服务地址: http://localhost:{PORT}/")
print(f"前端文件: {os.path.join(os.getcwd(), 'frontend')}")
print()
print("按 Ctrl+C 停止")
print("=" * 70)
print()

# 切换到frontend目录
os.chdir("frontend")

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"服务已启动在端口 {PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")