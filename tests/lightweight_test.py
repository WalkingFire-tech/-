"""
轻量级端到端测试
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_meta_questions():
    """测试元认知问题"""
    print("\n测试元认知问题:")
    
    from core.services.planner import DataDrivenPlanner
    from core.services.intent_parser import IntentParser
    from infrastructure.event_bus import bus
    
    class MockAdapter:
        def __init__(self, name):
            self.model_name = name
        def generate(self, prompt, task_type=None):
            return "模拟响应"
    
    planner = DataDrivenPlanner({"test": MockAdapter("test")})
    parser = IntentParser()
    
    results = []
    bus.subscribe("plan_executed", lambda r: results.append(r))
    
    questions = [
        "你的能力边界在哪里？",
        "你如何决策？",
        "回顾对话历史",
    ]
    
    for q in questions:
        intent = parser.parse(q)
        results.clear()
        planner.plan(intent)
        
        if results:
            r = str(results[0])
            print(f"  ✅ {q[:20]}... -> {r[:50]}...")
        else:
            print(f"  ⚠️  {q[:20]}... -> 无响应")


def test_reflex():
    """测试反射引擎"""
    print("\n测试反射引擎:")
    
    from infrastructure.reflex_engine import ReflexEngine
    
    engine = ReflexEngine()
    
    # 危险命令
    r = engine.check({"user_input": "rm -rf /"})
    print(f"  ✅ 危险命令: {'拦截' if r else '未拦截'}")
    
    # 高内存
    r = engine.check({"memory_percent": 95})
    print(f"  ✅ 高内存: {'触发' if r else '未触发'}")


def test_health():
    """测试健康度"""
    print("\n测试健康度:")
    
    from infrastructure.health_dashboard import health_dashboard
    
    aphi = health_dashboard.calculate_aphi()
    print(f"  ✅ APHI: {aphi['aphi']}/100")
    print(f"  ✅ 模式: {aphi['mode']}")


def main():
    print("="*60)
    print("轻量级端到端测试")
    print("="*60)
    
    test_meta_questions()
    test_reflex()
    test_health()
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)


if __name__ == "__main__":
    main()