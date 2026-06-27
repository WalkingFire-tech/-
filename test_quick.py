"""快速端到端测试"""
import requests
import json

BASE = "http://localhost:8000"

print("="*60)
print("端到端功能测试")
print("="*60)

# 1. 健康检查
print("\n[1] 健康检查...")
try:
    r = requests.get(f"{BASE}/api/health", timeout=3)
    print(f"✅ 服务运行: {r.json()}")
except Exception as e:
    print(f"❌ 服务未运行: {e}")
    exit(1)

# 2. 统计
print("\n[2] 统计数据...")
r = requests.get(f"{BASE}/api/stats", timeout=3)
print(f"✅ {r.json()}")

# 3. 模型列表
print("\n[3] 模型列表...")
r = requests.get(f"{BASE}/api/models", timeout=3)
data = r.json()
print(f"✅ 发现 {data['count']} 个模型")
if data['models']:
    for m in data['models'][:3]:
        print(f"   - {m['name']}")

# 4. 聊天测试
print("\n[4] 聊天功能测试...")
payload = {"message": "你好，请介绍一下你自己"}
r = requests.post(f"{BASE}/api/chat", json=payload, timeout=30)
data = r.json()

print(f"成功: {data.get('success')}")
print(f"响应: {data.get('response', '')[:100]}...")
print(f"意图: {data.get('intent', 'unknown')}")
print(f"置信度: {data.get('confidence', 0):.0%}")
print(f"路由: {data.get('route', 'unknown')}")

if "收到:" in data.get('response', ''):
    print("❌ 仍返回占位文本")
else:
    print("✅ 调用了核心模块")

# 5. 复杂问题
print("\n[5] 复杂问题测试...")
payload = {"message": "什么是认知科学？"}
r = requests.post(f"{BASE}/api/chat", json=payload, timeout=60)
data = r.json()
print(f"✅ 响应长度: {len(data.get('response', ''))} 字符")

print("\n" + "="*60)
print("测试完成")
print("="*60)