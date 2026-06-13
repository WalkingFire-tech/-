"""
P0优化集成测试 - 测试完整流程
"""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_planner_flow():
    """测试planner完整流程"""
    print("\n" + "="*60)
    print("测试Planner完整流程")
    print("="*60)
    
    from core.services.planner import DataDrivenPlanner
    from core.services.intent_parser import IntentParser, Intent
    from infrastructure.event_bus import bus
    
    # 创建模拟适配器
    class MockAdapter:
        def __init__(self, name):
            self.model_name = name
        
        def generate(self, prompt, task_type=None):
            return f"[{self.model_name}] 模拟响应"
    
    adapters = {
        "test_model": MockAdapter("test_model"),
        "fallback_model": MockAdapter("fallback_model")
    }
    
    planner = DataDrivenPlanner(adapters)
    parser = IntentParser()
    
    # 收集结果
    results = []
    
    def on_plan_executed(result):
        results.append(result)
    
    bus.subscribe("plan_executed", on_plan_executed)
    
    # 测试场景
    test_cases = [
        ("你好", "chat", "正常对话"),
        ("你的能力边界在哪里？", "meta", "元认知问题"),
        ("写一个冒泡排序", "code", "代码生成"),
        ("什么是机器学习？", "question", "知识问答"),
    ]
    
    for text, expected_type, desc in test_cases:
        print(f"\n测试: {desc}")
        print(f"  输入: {text}")
        
        results.clear()
        intent = parser.parse(text)
        
        print(f"  意图: {intent.type} (期望: {expected_type})")
        
        # 执行plan
        try:
            planner.plan(intent)
            time.sleep(0.1)  # 等待异步事件
            
            if results:
                print(f"  ✅ 响应: {str(results[0])[:100]}...")
            else:
                print(f"  ⚠️  无响应")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
    
    bus.unsubscribe("plan_executed", on_plan_executed)


def test_reflex_interception():
    """测试反射拦截"""
    print("\n" + "="*60)
    print("测试反射拦截")
    print("="*60)
    
    from infrastructure.reflex_engine import ReflexEngine
    
    engine = ReflexEngine()
    
    # 测试危险命令
    context = {
        "user_input": "rm -rf /",
        "memory_percent": 50,
        "recent_failures": 0
    }
    
    result = engine.check(context)
    if result:
        print(f"✅ 危险命令已拦截: {result}")
    else:
        print("⚠️  危险命令未拦截")
    
    # 测试高内存
    context = {
        "user_input": "正常命令",
        "memory_percent": 95,
        "recent_failures": 0
    }
    
    result = engine.check(context)
    if result:
        print(f"✅ 高内存已触发: {result}")
    else:
        print("⚠️  高内存未触发")


def test_capability_matrix():
    """测试能力矩阵"""
    print("\n" + "="*60)
    print("测试能力矩阵")
    print("="*60)
    
    import tempfile
    import os
    from infrastructure.model_capability import ModelCapability
    
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = temp_db.name
    temp_db.close()
    
    capability = None
    try:
        capability = ModelCapability(db_path=db_path)
        
        # 注册模型
        capability.register_model("fast_model", {'speed': 0.9, 'coding': 0.7})
        capability.register_model("quality_model", {'speed': 0.5, 'coding': 0.95})
        
        print("✅ 模型已注册")
        
        # 测试选择
        top_models = capability.get_top_models("code", top_k=1)
        if top_models:
            print(f"✅ 最佳模型: {top_models[0][0]}")
        else:
            print("⚠️  未找到最佳模型")
        
        # 测试反馈更新
        capability.update_from_feedback(
            model_name="fast_model",
            task_type="code",
            success=True,
            quality_score=0.9
        )
        print("✅ 反馈更新成功")
        
        # 关闭数据库连接
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.close()
        
    finally:
        import time
        time.sleep(0.1)
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except:
                pass


def test_health_dashboard():
    """测试健康度仪表盘"""
    print("\n" + "="*60)
    print("测试健康度仪表盘")
    print("="*60)
    
    from infrastructure.health_dashboard import health_dashboard
    
    aphi = health_dashboard.calculate_aphi()
    
    print(f"APHI指数: {aphi['aphi']}/100")
    print(f"运行模式: {aphi['mode']}")
    print(f"能力覆盖率: {aphi['capability_coverage']}%")
    print(f"任务成功率: {aphi['task_success_rate']}%")
    print(f"用户满意度: {aphi['user_satisfaction']}%")
    
    if aphi['aphi'] >= 60:
        print("✅ 系统健康")
    else:
        print("⚠️  系统需要优化")


def test_emotion_inferencer():
    """测试情绪推断器"""
    print("\n" + "="*60)
    print("测试情绪推断器")
    print("="*60)
    
    from infrastructure.emotion_inferencer import emotion_inferencer
    
    test_cases = [
        "你好，请帮我写代码",
        "快点！我要结果！",
        "这个不对，再试一次",
        "谢谢你的帮助",
    ]
    
    for text in test_cases:
        result = emotion_inferencer.infer(text)
        print(f"  '{text[:20]}...' -> {result['emotion']} (耐心: {result['patience']:.2f})")


def main():
    print("="*60)
    print("P0优化集成测试")
    print("="*60)
    
    try:
        test_reflex_interception()
        test_capability_matrix()
        test_health_dashboard()
        test_emotion_inferencer()
        test_planner_flow()
        
        print("\n" + "="*60)
        print("✅ 所有集成测试完成")
        print("="*60)
        
        return 0
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())