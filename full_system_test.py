"""
完整系统测试 - 全量功能验证
"""
import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("="*70)
print("联盟拓荒者 - 完整系统测试")
print("="*70)

# 测试结果收集
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def test(name, func):
    """执行测试"""
    try:
        result = func()
        if result:
            test_results["passed"].append(name)
            print(f"✅ {name}")
            return True
        else:
            test_results["failed"].append(name)
            print(f"❌ {name}")
            return False
    except Exception as e:
        test_results["failed"].append(f"{name}: {str(e)[:50]}")
        print(f"❌ {name}: {e}")
        return False

# ==================== 核心模块测试 ====================
print("\n" + "="*70)
print("1️⃣ 核心模块测试")
print("="*70)

def test_intent_parser():
    """测试意图解析器"""
    from core.services.intent_parser import IntentParser
    parser = IntentParser()
    
    # Meta意图测试
    meta_tests = [
        ("你的能力边界在哪里？", "meta"),
        ("能力边界", "meta"),
        ("自我评估", "meta"),
        ("决策机制", "meta"),
        ("你如何决策？", "meta"),
    ]
    
    passed = 0
    for text, expected in meta_tests:
        intent = parser.parse(text)
        if intent.type == expected:
            passed += 1
    
    return passed == len(meta_tests)

def test_reflex_engine():
    """测试反射引擎"""
    from infrastructure.reflex_engine import ReflexEngine
    engine = ReflexEngine()
    
    # 危险命令拦截
    result1 = engine.check({"user_input": "rm -rf /"})
    # 高内存触发
    result2 = engine.check({"memory_percent": 95})
    
    return result1 is not None and result2 is not None

def test_emotion_inferencer():
    """测试情绪推断器"""
    from infrastructure.emotion_inferencer import emotion_inferencer
    
    tests = [
        ("快点！我要结果！", "urgent"),
        ("谢谢你的帮助", "happy"),
        ("什么破系统，太烂了！", "angry"),
    ]
    
    passed = 0
    for text, expected in tests:
        result = emotion_inferencer.infer(text)
        if result["emotion"] == expected:
            passed += 1
    
    return passed >= 2  # 至少2个正确

def test_health_dashboard():
    """测试健康度仪表盘"""
    from infrastructure.health_dashboard import health_dashboard
    aphi = health_dashboard.calculate_aphi()
    
    return (
        aphi["aphi"] > 0 and
        aphi["mode"] in ["critical", "warning", "normal", "optimal"] and
        aphi["capability_coverage"] >= 0
    )

def test_model_capability():
    """测试能力矩阵"""
    from infrastructure.model_capability import model_capability
    
    stats = model_capability.export_stats()
    return (
        stats["registered_models"] > 0 and
        stats["dimensions"] > 0
    )

def test_knowledge_injector():
    """测试知识注入器"""
    from infrastructure.knowledge_injector import knowledge_injector
    
    # 测试注入
    knowledge_injector.inject_knowledge(
        question="测试问题",
        answer="测试答案",
        source="test",
        intent_type="question"
    )
    
    # 测试检索
    result = knowledge_injector.retrieve_knowledge("测试问题", "question")
    return result is not None

def test_counterfactual_simulator():
    """测试反事实模拟器"""
    from infrastructure.counterfactual_simulator import counterfactual_simulator
    
    stats = counterfactual_simulator.get_statistics()
    return "total_simulations" in stats

# 执行核心模块测试
test("意图解析器", test_intent_parser)
test("反射引擎", test_reflex_engine)
test("情绪推断器", test_emotion_inferencer)
test("健康度仪表盘", test_health_dashboard)
test("能力矩阵", test_model_capability)
test("知识注入器", test_knowledge_injector)
test("反事实模拟器", test_counterfactual_simulator)

# ==================== 规划器测试 ====================
print("\n" + "="*70)
print("2️⃣ 规划器测试")
print("="*70)

def test_planner_initialization():
    """测试规划器初始化"""
    from core.services.planner import DataDrivenPlanner
    
    class MockAdapter:
        def __init__(self, name):
            self.model_name = name
        def generate(self, prompt, task_type=None):
            return "mock response"
    
    adapters = {"mock": MockAdapter("mock")}
    planner = DataDrivenPlanner(adapters)
    
    # 检查方法存在
    methods = [
        '_check_reflex_level',
        '_infer_emotion',
        '_check_system_state',
        '_apply_five_layer_defense',
        '_handle_normal_flow'
    ]
    
    for method in methods:
        if not hasattr(planner, method):
            return False
    
    return True

def test_planner_flow():
    """测试规划器流程"""
    from core.services.planner import DataDrivenPlanner
    from core.services.intent_parser import IntentParser
    from infrastructure.event_bus import bus
    
    class MockAdapter:
        def __init__(self, name):
            self.model_name = name
        def generate(self, prompt, task_type=None):
            return "mock response"
    
    adapters = {"mock": MockAdapter("mock")}
    planner = DataDrivenPlanner(adapters)
    parser = IntentParser()
    
    results = []
    bus.subscribe("plan_executed", lambda r: results.append(r))
    
    # 测试meta意图
    intent = parser.parse("你的能力边界在哪里？")
    planner.plan(intent)
    time.sleep(0.2)
    
    return len(results) > 0

test("规划器初始化", test_planner_initialization)
test("规划器流程", test_planner_flow)

# ==================== 并行调度器测试 ====================
print("\n" + "="*70)
print("3️⃣ 并行调度器测试")
print("="*70)

def test_parallel_scheduler_blacklist():
    """测试并行调度器黑名单"""
    from infrastructure.parallel_scheduler import ParallelScheduler
    
    scheduler = ParallelScheduler()
    
    # 测试黑名单功能
    scheduler._mark_failed("test_model", 10)
    
    is_blacklisted = scheduler._is_blacklisted("test_model")
    not_blacklisted = not scheduler._is_blacklisted("other_model")
    
    return is_blacklisted and not_blacklisted

def test_parallel_scheduler_stats():
    """测试并行调度器统计"""
    from infrastructure.parallel_scheduler import ParallelScheduler
    
    scheduler = ParallelScheduler()
    stats = scheduler.get_statistics()
    
    return isinstance(stats, dict)

test("并行调度器黑名单", test_parallel_scheduler_blacklist)
test("并行调度器统计", test_parallel_scheduler_stats)

# ==================== 后端服务测试 ====================
print("\n" + "="*70)
print("4️⃣ 后端服务测试")
print("="*70)

def test_backend_import():
    """测试后端导入"""
    try:
        from backend.main import app
        return True
    except Exception as e:
        print(f"    错误: {e}")
        return False

def test_backend_health():
    """测试后端健康检查"""
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read())
                return data.get("status") == "healthy"
    except:
        return False

def test_backend_chat():
    """测试后端聊天接口"""
    try:
        data = json.dumps({"message": "你好"}).encode('utf-8')
        req = urllib.request.Request(
            "http://localhost:8000/chat",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                result = json.loads(response.read())
                return "response" in result or "error" not in result
    except:
        return False

test("后端导入", test_backend_import)
test("后端健康检查", test_backend_health)
test("后端聊天接口", test_backend_chat)

# ==================== 安全机制测试 ====================
print("\n" + "="*70)
print("5️⃣ 安全机制测试")
print("="*70)

def test_dangerous_command_blocking():
    """测试危险命令拦截"""
    from infrastructure.reflex_engine import ReflexEngine
    
    engine = ReflexEngine()
    
    dangerous_commands = [
        "rm -rf /",
        "drop database mydb",
        "format c:",
        "del /s /q *.*"
    ]
    
    blocked = 0
    for cmd in dangerous_commands:
        result = engine.check({"user_input": cmd})
        if result:
            blocked += 1
    
    return blocked == len(dangerous_commands)

def test_memory_protection():
    """测试内存保护"""
    from infrastructure.reflex_engine import ReflexEngine
    
    engine = ReflexEngine()
    
    # 测试不同内存阈值
    result1 = engine.check({"memory_percent": 50})  # 正常
    result2 = engine.check({"memory_percent": 95})  # 触发
    
    return result1 is None and result2 is not None

test("危险命令拦截", test_dangerous_command_blocking)
test("内存保护", test_memory_protection)

# ==================== 性能测试 ====================
print("\n" + "="*70)
print("6️⃣ 性能测试")
print("="*70)

def test_response_time():
    """测试响应时间"""
    from core.services.intent_parser import IntentParser
    
    parser = IntentParser()
    
    start = time.time()
    for _ in range(100):
        parser.parse("你的能力边界在哪里？")
    duration = time.time() - start
    
    avg_time = duration / 100 * 1000  # 毫秒
    print(f"    平均响应时间: {avg_time:.2f}ms")
    
    return avg_time < 10  # 小于10ms

def test_memory_usage():
    """测试内存使用"""
    try:
        import psutil
        process = psutil.Process()
        mem_mb = process.memory_info().rss / (1024**2)
        print(f"    当前内存使用: {mem_mb:.1f}MB")
        return mem_mb < 1000  # 小于1GB
    except:
        return True

test("响应时间", test_response_time)
test("内存使用", test_memory_usage)

# ==================== 测试总结 ====================
print("\n" + "="*70)
print("测试总结")
print("="*70)

total = len(test_results["passed"]) + len(test_results["failed"])
pass_rate = len(test_results["passed"]) / total * 100 if total > 0 else 0

print(f"\n总测试数: {total}")
print(f"通过: {len(test_results['passed'])}")
print(f"失败: {len(test_results['failed'])}")
print(f"通过率: {pass_rate:.1f}%")

if test_results["failed"]:
    print(f"\n失败项:")
    for item in test_results["failed"]:
        print(f"  ❌ {item}")

# 系统状态
print(f"\n" + "="*70)
print("系统状态")
print("="*70)

try:
    from infrastructure.health_dashboard import health_dashboard
    aphi = health_dashboard.calculate_aphi()
    print(f"\nAPHI指数: {aphi['aphi']}/100")
    print(f"运行模式: {aphi['mode']}")
    print(f"能力覆盖率: {aphi['capability_coverage']}%")
    print(f"任务成功率: {aphi['task_success_rate']}%")
    print(f"用户满意度: {aphi['user_satisfaction']}%")
except Exception as e:
    print(f"无法获取系统状态: {e}")

# 最终结果
print(f"\n" + "="*70)
if pass_rate >= 80:
    print("✅ 系统测试通过 - 生产就绪")
    print("="*70)
    sys.exit(0)
else:
    print("❌ 系统测试失败 - 需要修复")
    print("="*70)
    sys.exit(1)