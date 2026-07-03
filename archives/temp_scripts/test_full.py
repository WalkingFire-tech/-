"""
端到端全功能测试 - 完整版
运行方式：python test_full.py
"""
import sys
import time
import json
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000"

class E2ETest:
    def __init__(self):
        self.results = []
    
    def test(self, name, func):
        """运行测试"""
        print(f"\n[测试] {name}")
        print("-" * 60)
        try:
            result = func()
            if result:
                print(f"✅ 通过")
                self.results.append((name, True, ""))
                return True
            else:
                print(f"❌ 失败")
                self.results.append((name, False, "返回False"))
                return False
        except Exception as e:
            print(f"❌ 异常: {e}")
            self.results.append((name, False, str(e)))
            return False
    
    def summary(self):
        """打印总结"""
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        failed = sum(1 for _, success, _ in self.results if not success)
        
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        
        if failed > 0:
            print("\n失败详情:")
            for name, success, error in self.results:
                if not success:
                    print(f"  ❌ {name}: {error}")
        
        return failed == 0

def test_health():
    """测试健康检查"""
    r = requests.get(f"{BASE_URL}/api/health", timeout=5)
    data = r.json()
    print(f"响应: {data}")
    return r.status_code == 200 and data.get("status") == "ok"

def test_stats():
    """测试统计数据"""
    r = requests.get(f"{BASE_URL}/api/stats", timeout=5)
    data = r.json()
    print(f"经验: {data.get('experiences', 0)}")
    print(f"规则: {data.get('rules', 0)}")
    return r.status_code == 200

def test_models():
    """测试模型列表"""
    r = requests.get(f"{BASE_URL}/api/models", timeout=5)
    data = r.json()
    count = data.get("count", 0)
    print(f"模型数量: {count}")
    if count > 0:
        for m in data["models"][:3]:
            print(f"  - {m['name']}")
    return r.status_code == 200

def test_config_get():
    """测试获取配置"""
    r = requests.get(f"{BASE_URL}/api/config/external", timeout=5)
    print(f"响应: {r.json()}")
    return r.status_code == 200

def test_config_save():
    """测试保存配置"""
    config = {"apis": [{"name": "test", "url": "http://test.com"}]}
    r = requests.post(f"{BASE_URL}/api/config/external", json=config, timeout=5)
    print(f"响应: {r.json()}")
    return r.status_code == 200

def test_chat_greeting():
    """测试问候语"""
    payload = {"message": "你好"}
    r = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=10)
    data = r.json()
    
    print(f"成功: {data.get('success')}")
    print(f"响应: {data.get('response', '')[:100]}")
    print(f"意图: {data.get('intent')}")
    print(f"置信度: {data.get('confidence', 0):.0%}")
    
    # 不应该返回占位文本
    if "收到:" in data.get("response", ""):
        print("❌ 仍返回占位文本")
        return False
    
    return r.status_code == 200 and data.get("success")

def test_chat_question():
    """测试问题回答"""
    payload = {"message": "什么是认知科学？"}
    start = time.time()
    r = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=30)
    elapsed = time.time() - start
    
    data = r.json()
    print(f"耗时: {elapsed:.1f}秒")
    print(f"成功: {data.get('success')}")
    print(f"响应长度: {len(data.get('response', ''))}字符")
    print(f"路由: {data.get('route')}")
    
    return r.status_code == 200 and data.get("success")

def test_models_reload():
    """测试模型重载"""
    r = requests.post(f"{BASE_URL}/api/models/reload", timeout=10)
    data = r.json()
    print(f"成功: {data.get('success')}")
    print(f"模型数: {data.get('total', 0)}")
    return r.status_code == 200

def test_knowledge_health():
    """测试知识库健康"""
    r = requests.get(f"{BASE_URL}/api/knowledge/health", timeout=5)
    data = r.json()
    print(f"状态: {data.get('status')}")
    return r.status_code == 200

def test_frontend():
    """测试前端页面"""
    r = requests.get(f"{BASE_URL}/", timeout=5)
    print(f"状态码: {r.status_code}")
    print(f"内容长度: {len(r.text)}字符")
    return r.status_code == 200 and "html" in r.text.lower()

def main():
    print("=" * 60)
    print("端到端全功能测试")
    print("=" * 60)
    
    tester = E2ETest()
    
    # 基础功能测试
    print("\n【基础功能】")
    tester.test("健康检查", test_health)
    tester.test("统计数据", test_stats)
    tester.test("模型列表", test_models)
    tester.test("前端页面", test_frontend)
    
    # API端点测试
    print("\n【API端点】")
    tester.test("知识库健康", test_knowledge_health)
    tester.test("获取配置", test_config_get)
    tester.test("保存配置", test_config_save)
    tester.test("模型重载", test_models_reload)
    
    # 聊天功能测试
    print("\n【聊天功能】")
    tester.test("问候语", test_chat_greeting)
    tester.test("问题回答", test_chat_question)
    
    # 总结
    success = tester.summary()
    
    if success:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️ 部分测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())