#!/usr/bin/env python
"""测试socket连接"""
import socket

print("=== 测试socket连接 ===")
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    result = sock.connect_ex(('127.0.0.1', 11434))
    sock.close()
    if result == 0:
        print("连接成功")
    else:
        print(f"连接失败: {result}")
except Exception as e:
    print(f"异常: {e}")