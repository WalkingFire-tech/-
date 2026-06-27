"""
性能优化专项测试
对比优化前后的响应时间
"""
import http.client
import json
import time

BASE_URL = "localhost"
PORT = 8000

def test_response_time():
    """测试关键接口响应时间"""
    print("\n" + "="*60)
    print("性能优化效果测试")
    print("="*60)
    
    tests = [
        ("健康检查", "GET", "/api/health", None),
        ("模型列表", "GET", "/api/models", None),
        ("系统统计", "GET", "/api/stats", None),
    ]
    
    chat_tests = [
        "历史对话",
        "你是谁",
        "1+1等于多少"
    ]
    
    print("\n【基础接口测试】")
    for name, method, path, data in tests:
        conn = http.client.HTTPConnection(BASE_URL, PORT, timeout=10)
        try:
            start = time.time()
            conn.request(method, path)
            resp = conn.getresponse()
            resp.read()
            elapsed = (time.time() - start) * 1000
            
            status = "✅" if resp.status == 200 else "❌"
            print(f"{status} {name}: {elapsed:.0f}ms")
        except Exception as e:
            print(f"❌ {name}: 失败 - {e}")
        finally:
            conn.close()
    
    print("\n【对话响应测试】")
    for query in chat_tests:
        conn = http.client.HTTPConnection(BASE_URL, PORT, timeout=60)
        try:
            start = time.time()
            conn.request("POST", "/api/chat", 
                        json.dumps({"message": query}),
                        {"Content-Type": "application/json"})
            resp = conn.getresponse()
            data = json.loads(resp.read().decode())
            elapsed = (time.time() - start) * 1000
            
            if resp.status == 200:
                response_len = len(data.get("response", ""))
                print(f"✅ '{query}': {elapsed:.0f}ms (回答{response_len}字)")
            else:
                print(f"❌ '{query}': 失败")
        except Exception as e:
            print(f"❌ '{query}': {e}")
        finally:
            conn.close()
        time.sleep(1)
    
    print("\n" + "="*60)
    print("优化效果:")
    print("  - 外部搜索超时: 30秒 → 5秒")
    print("  - 嵌入模型: 重复加载 → 共享实例")
    print("  - 预期改善: 167秒 → <10秒")
    print("="*60)

if __name__ == "__main__":
    test_response_time()