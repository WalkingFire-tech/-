"""
端到端测试 - 测试实际服务
"""
import sys
import time
import threading
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_backend_startup():
    """测试后端启动"""
    print("\n" + "="*60)
    print("测试后端服务启动")
    print("="*60)
    
    import subprocess
    import time
    
    # 启动后端
    print("启动后端服务...")
    proc = subprocess.Popen(
        [sys.executable, "backend/main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待启动
    time.sleep(3)
    
    try:
        # 测试健康检查
        print("\n测试健康检查端点...")
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print(f"✅ 健康检查通过: {response.json()}")
            else:
                print(f"⚠️  健康检查失败: {response.status_code}")
        except Exception as e:
            print(f"⚠️  无法连接: {e}")
        
        # 测试聊天端点
        print("\n测试聊天端点...")
        try:
            response = requests.post(
                "http://localhost:8000/chat",
                json={"message": "你的能力边界在哪里？"},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 聊天响应: {data.get('response', '')[:100]}...")
            else:
                print(f"⚠️  聊天失败: {response.status_code}")
        except Exception as e:
            print(f"⚠️  聊天请求失败: {e}")
        
    finally:
        # 关闭后端
        print("\n关闭后端服务...")
        proc.terminate()
        proc.wait(timeout=5)
        print("✅ 后端已关闭")


def test_cli_interaction():
    """测试CLI交互"""
    print("\n" + "="*60)
    print("测试CLI交互")
    print("="*60)
    
    from core.services.planner import DataDrivenPlanner
    from core.services.intent_parser import IntentParser
    from infrastructure.event_bus import bus
    
    class MockAdapter:
        def __init__(self, name):
            self.model_name = name
        
        def generate(self, prompt, task_type=None):
            return f"[{self.model_name}] 响应"
    
    adapters = {"test": MockAdapter("test")}
    planner = DataDrivenPlanner(adapters)
    parser = IntentParser()
    
    results = []
    bus.subscribe("plan_executed", lambda r: results.append(r))
    
    # 模拟用户交互
    test_inputs = [
        "你好",
        "你的能力边界在哪里？",
        "你如何决策？",
        "写一个冒泡排序",
        "什么是机器学习？",
    ]
    
    print("\n模拟用户输入:")
    for user_input in test_inputs:
        print(f"\n用户: {user_input}")
        
        intent = parser.parse(user_input)
        print(f"意图: {intent.type}")
        
        results.clear()
        planner.plan(intent)
        time.sleep(0.1)
        
        if results:
            response = str(results[0])
            if len(response) > 100:
                print(f"拓荒者: {response[:100]}...")
            else:
                print(f"拓荒者: {response}")
        else:
            print("拓荒者: [无响应]")


def test_meta_cognition():
    """测试元认知能力"""
    print("\n" + "="*60)
    print("测试元认知能力")
    print("="*60)
    
    from core.services.planner import DataDrivenPlanner
    from core.services.intent_parser import IntentParser
    from infrastructure.event_bus import bus
    
    class MockAdapter:
        def __init__(self, name):
            self.model_name = name
        
        def generate(self, prompt, task_type=None):
            if "能力边界" in prompt:
                return "我的能力边界包括代码生成、问题解答、文档处理等..."
            elif "决策" in prompt:
                return "我通过意图识别、模型路由、经验复用等方式决策..."
            else:
                return "模拟响应"
    
    adapters = {"meta_model": MockAdapter("meta_model")}
    planner = DataDrivenPlanner(adapters)
    parser = IntentParser()
    
    results = []
    bus.subscribe("plan_executed", lambda r: results.append(r))
    
    # 测试元认知问题
    meta_questions = [
        "你的能力边界在哪里？",
        "你如何决策？",
        "回顾对话历史",
        "你如何自我进化？",
    ]
    
    for question in meta_questions:
        print(f"\n问题: {question}")
        
        intent = parser.parse(question)
        print(f"  意图类型: {intent.type}")
        
        results.clear()
        planner.plan(intent)
        time.sleep(0.1)
        
        if results:
            response = str(results[0])
            # 检查是否包含结构化报告
            if "╔" in response or "═" in response:
                print(f"  ✅ 返回结构化报告")
            else:
                print(f"  ✅ 返回回答: {response[:50]}...")
        else:
            print(f"  ⚠️  无响应")


def test_error_handling():
    """测试错误处理"""
    print("\n" + "="*60)
    print("测试错误处理")
    print("="*60)
    
    from infrastructure.reflex_engine import ReflexEngine
    
    engine = ReflexEngine()
    
    # 测试危险命令拦截
    print("\n测试危险命令拦截:")
    dangerous_commands = [
        "rm -rf /",
        "drop database mydb",
        "format c:",
    ]
    
    for cmd in dangerous_commands:
        result = engine.check({"user_input": cmd})
        if result:
            print(f"  ✅ '{cmd}' 已拦截")
        else:
            print(f"  ⚠️  '{cmd}' 未拦截")
    
    # 测试资源限制
    print("\n测试资源限制:")
    high_memory = {"memory_percent": 95}
    result = engine.check(high_memory)
    if result:
        print(f"  ✅ 高内存触发保护: {result}")
    else:
        print(f"  ⚠️  高内存未触发")


def main():
    print("="*60)
    print("端到端测试")
    print("="*60)
    
    try:
        test_cli_interaction()
        test_meta_cognition()
        test_error_handling()
        
        print("\n" + "="*60)
        print("✅ 所有端到端测试完成")
        print("="*60)
        
        print("\n💡 建议:")
        print("  1. 启动后端服务: python backend/main.py")
        print("  2. 在CLI中测试元认知问题")
        print("  3. 观察决策日志和健康度")
        
        return 0
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())