"""
端到端全功能测试脚本
验证联盟拓荒者系统的所有核心功能
"""
import sys
import time
import json
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "http://localhost:8000"

class TestResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def add_pass(self, test_name, detail=""):
        self.passed.append((test_name, detail))
        print(f"✅ {test_name} {detail}")
    
    def add_fail(self, test_name, error):
        self.failed.append((test_name, error))
        print(f"❌ {test_name}: {error}")
    
    def add_warning(self, test_name, warning):
        self.warnings.append((test_name, warning))
        print(f"⚠️  {test_name}: {warning}")
    
    def summary(self):
        print("\n" + "="*60)
        print("测试总结")
        print("="*60)
        print(f"✅ 通过: {len(self.passed)}")
        print(f"❌ 失败: {len(self.failed)}")
        print(f"⚠️  警告: {len(self.warnings)}")
        
        if self.failed:
            print("\n失败详情:")
            for name, error in self.failed:
                print(f"  - {name}: {error}")
        
        return len(self.failed) == 0

def test_server_running(result: TestResult):
    """测试服务器是否运行"""
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            result.add_pass("服务器运行", f"版本: {data.get('version', 'unknown')}")
        else:
            result.add_fail("服务器运行", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("服务器运行", str(e))

def test_frontend_access(result: TestResult):
    """测试前端访问"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            if "html" in response.text.lower():
                result.add_pass("前端页面", "HTML内容正常")
            else:
                result.add_warning("前端页面", "响应不是HTML")
        else:
            result.add_fail("前端页面", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("前端页面", str(e))

def test_stats_api(result: TestResult):
    """测试统计API"""
    try:
        response = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            experiences = data.get("experiences", 0)
            rules = data.get("rules", 0)
            result.add_pass("统计API", f"经验: {experiences}, 规则: {rules}")
        else:
            result.add_fail("统计API", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("统计API", str(e))

def test_models_api(result: TestResult):
    """测试模型API"""
    try:
        response = requests.get(f"{BASE_URL}/api/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            count = data.get("count", 0)
            if count > 0:
                model_names = [m["name"] for m in models[:3]]
                result.add_pass("模型API", f"发现{count}个模型: {', '.join(model_names)}")
            else:
                result.add_warning("模型API", "未发现Ollama模型，请确保Ollama已启动")
        else:
            result.add_fail("模型API", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("模型API", str(e))

def test_chat_simple(result: TestResult):
    """测试简单聊天"""
    try:
        payload = {"message": "你好"}
        response = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                response_text = data.get("response", "")
                intent = data.get("intent", "unknown")
                confidence = data.get("confidence", 0)
                route = data.get("route", "unknown")
                
                if "收到:" in response_text:
                    result.add_fail("聊天功能", "仍返回占位文本，未调用核心模块")
                else:
                    result.add_pass("聊天功能", f"意图:{intent}, 置信度:{confidence:.0%}, 路由:{route}")
                    result.add_pass("聊天响应", f"内容: {response_text[:50]}...")
            else:
                result.add_fail("聊天功能", data.get("response", "未知错误"))
        else:
            result.add_fail("聊天功能", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("聊天功能", str(e))

def test_chat_complex(result: TestResult):
    """测试复杂问题"""
    try:
        payload = {"message": "什么是认知科学？请详细解释"}
        response = requests.post(f"{BASE_URL}/api/chat", json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                response_text = data.get("response", "")
                thinking = data.get("thinking_process", {})
                
                if len(response_text) > 20:
                    result.add_pass("复杂问题处理", f"响应长度: {len(response_text)}字符")
                    
                    if thinking:
                        deep_intent = thinking.get("deep_intent", "")
                        strategy = thinking.get("response_strategy", "")
                        result.add_pass("思考过程", f"意图:{deep_intent}, 策略:{strategy}")
                else:
                    result.add_warning("复杂问题处理", "响应过短")
            else:
                result.add_warning("复杂问题处理", "处理失败但不影响基本功能")
        else:
            result.add_warning("复杂问题处理", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_warning("复杂问题处理", str(e))

def test_models_reload(result: TestResult):
    """测试模型重载"""
    try:
        response = requests.post(f"{BASE_URL}/api/models/reload", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                result.add_pass("模型重载", f"共{data.get('total', 0)}个模型")
            else:
                result.add_warning("模型重载", "重载失败")
        else:
            result.add_warning("模型重载", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_warning("模型重载", str(e))

def test_knowledge_health(result: TestResult):
    """测试知识库健康检查"""
    try:
        response = requests.get(f"{BASE_URL}/api/knowledge/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            status = data.get("status", "unknown")
            result.add_pass("知识库健康", f"状态: {status}")
        else:
            result.add_fail("知识库健康", f"状态码: {response.status_code}")
    except Exception as e:
        result.add_fail("知识库健康", str(e))

def test_core_modules(result: TestResult):
    """测试核心模块导入"""
    modules_to_test = [
        ("core.orchestrator", "SystemOrchestrator"),
        ("core.cognitive_dispatcher", "CognitiveDispatcher"),
        ("core.metacognitive_executor", "MetacognitiveExecutor"),
        ("infrastructure.reflection_pipeline", "ReflectionPipeline"),
        ("infrastructure.experience_pool", "ExperiencePool"),
        ("tools.registry", "registry"),
    ]
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            result.add_pass(f"模块导入", f"{module_name}.{class_name}")
        except Exception as e:
            result.add_fail(f"模块导入", f"{module_name}.{class_name}: {str(e)[:50]}")

def test_database_files(result: TestResult):
    """测试数据库文件"""
    db_files = [
        "data/experience_pool.db",
        "data/learning_rules.db",
        "logs/campfire_log.db"
    ]
    
    for db_file in db_files:
        path = Path(db_file)
        if path.exists():
            size = path.stat().st_size
            result.add_pass("数据库文件", f"{db_file} ({size} bytes)")
        else:
            result.add_warning("数据库文件", f"{db_file} 不存在")

def test_layers_initialization(result: TestResult):
    """测试层初始化"""
    try:
        from core.orchestrator import SystemOrchestrator
        orchestrator = SystemOrchestrator({"persistence_dir": "data/test_orchestrator"})
        
        layers = ["L2", "L3", "L4", "L5", "L6", "existence"]
        for layer_name in layers:
            if layer_name in orchestrator.layers:
                result.add_pass("层初始化", layer_name)
            else:
                result.add_warning("层初始化", f"{layer_name} 未加载")
    except Exception as e:
        result.add_fail("层初始化", str(e))

def main():
    print("="*60)
    print("联盟拓荒者 - 端到端全功能测试")
    print("="*60)
    print()
    
    result = TestResult()
    
    print("\n[1/11] 测试服务器运行状态...")
    test_server_running(result)
    
    print("\n[2/11] 测试前端页面访问...")
    test_frontend_access(result)
    
    print("\n[3/11] 测试统计API...")
    test_stats_api(result)
    
    print("\n[4/11] 测试模型API...")
    test_models_api(result)
    
    print("\n[5/11] 测试简单聊天功能...")
    test_chat_simple(result)
    
    print("\n[6/11] 测试复杂问题处理...")
    test_chat_complex(result)
    
    print("\n[7/11] 测试模型重载...")
    test_models_reload(result)
    
    print("\n[8/11] 测试知识库健康检查...")
    test_knowledge_health(result)
    
    print("\n[9/11] 测试核心模块导入...")
    test_core_modules(result)
    
    print("\n[10/11] 测试数据库文件...")
    test_database_files(result)
    
    print("\n[11/11] 测试层初始化...")
    test_layers_initialization(result)
    
    success = result.summary()
    
    if success:
        print("\n🎉 所有测试通过！系统运行正常。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查上述错误。")
        return 1

if __name__ == "__main__":
    sys.exit(main())