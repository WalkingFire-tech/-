import time
import http.client
import json

print('等待后端重载...')
time.sleep(12)

print('测试: 天为什么是蓝的？')
conn = http.client.HTTPConnection('localhost', 8000, timeout=30)
start = time.time()

try:
    conn.request('POST', '/api/chat', json.dumps({'message': '天为什么是蓝的？'}), {'Content-Type': 'application/json'})
    r = conn.getresponse()
    elapsed = time.time() - start
    data = json.loads(r.read().decode())
    
    print(f'状态: {r.status}')
    print(f'耗时: {elapsed:.2f}秒')
    print(f'响应: {data.get("response", "")[:300]}...')
except Exception as e:
    print(f'错误: {e}')
finally:
    conn.close()