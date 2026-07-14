#!/usr/bin/env python
"""用socket发送HTTP POST请求"""
import socket
import json

print("=== 用socket发送HTTP POST请求 ===")
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(60)
    s.connect(('127.0.0.1', 11434))

    payload = json.dumps({"model": "gemma-4-12B", "prompt": "1+1", "stream": False})
    request = f"POST /api/generate HTTP/1.1\r\nHost: 127.0.0.1:11434\r\nContent-Type: application/json\r\nContent-Length: {len(payload)}\r\n\r\n{payload}"

    s.sendall(request.encode())
    response = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        response += chunk
        # 简单的HTTP响应结束检测
        if b"\r\n\r\n" in response:
            # 检查是否有Content-Length
            headers, _, body = response.partition(b"\r\n\r\n")
            if b"Content-Length:" in headers:
                # 提取Content-Length
                for line in headers.split(b"\r\n"):
                    if line.startswith(b"Content-Length:"):
                        length = int(line.split(b":")[1].strip())
                        if len(body) >= length:
                            break
            else:
                # 没有Content-Length，等待一段时间
                import time
                time.sleep(0.1)
                if len(response) > 1000:  # 假设响应不会太长
                    break

    print(f"响应长度: {len(response)}")
    print(f"响应前500字符: {response[:500]}")
    s.close()
except Exception as e:
    print(f"失败: {e}")
    import traceback
    traceback.print_exc()