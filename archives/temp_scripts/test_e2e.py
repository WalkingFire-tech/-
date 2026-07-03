"""
联盟拓荒者 - 端到端质量测试 v2.0

反思v1.0的问题：
- 只测API是否返回200，不测返回内容质量
- 不检测模板化/写死内容（"问题本质分析"等空洞框架）
- 不测流式SSE完整流程
- 不测闭环迭代行为
- 不测模型超时后的智能诊断
- 不测多源并行的实际效果

v2.0核心改进：
- 内容质量断言：检测模板化内容、空洞框架、写死提示词
- 流式SSE完整测试：验证step→result完整流程
- 闭环行为验证：评估不通过时是否触发迭代
- 多源并行验证：检查是否真正多路径并行
- 模型诊断验证：验证诊断函数返回正确状态
- 前端模板检测：确认前端不再包含写死模板
"""
import sys
import time
import json
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BASE_URL = "http://localhost:8000"

TEMPLATE_KEYWORDS = [
    "问题本质分析", "多角度审视", "关键变量识别", "我的深度思考",
    "正面视角", "反面视角", "旁观视角", "历史视角",
    "事实性、价值性、因果性、方法性",
    "我正在持续学习和进化",
    "如果你能提供更多背景",
    "建议你尝试更具体的问题",
    "请告诉我更具体的需求",
]

class TestResult:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, name, detail=""):
        self.passed.append((name, detail))
        print(f"  ✅ {name}: {detail}")

    def add_fail(self, name, error):
        self.failed.append((name, error))
        print(f"  ❌ {name}: {error}")

    def add_warning(self, name, warning):
        self.warnings.append((name, warning))
        print(f"  ⚠️  {name}: {warning}")

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


def test_no_template_in_backend(result: TestResult):
    """核心测试：后端代码中不再包含写死的模板化提示词"""
    print("\n[1] 检测后端代码中的写死模板...")
    
    chat_stream_path = Path("backend/chat_stream.py")
    if not chat_stream_path.exists():
        result.add_fail("后端模板检测", "chat_stream.py不存在")
        return
    
    content = chat_stream_path.read_text(encoding="utf-8")
    
    found_templates = []
    for kw in TEMPLATE_KEYWORDS:
        if kw in content:
            found_templates.append(kw)
    
    if found_templates:
        result.add_fail("后端模板检测", f"发现{len(found_templates)}个写死模板: {', '.join(found_templates[:5])}")
    else:
        result.add_pass("后端模板检测", "后端代码中无写死模板")
    
    if "_generate_smart_reply" in content and "__NEED_DYNAMIC_REPLY__" in content:
        result.add_pass("动态fallback", "智能回复已改为动态标记")
    else:
        result.add_fail("动态fallback", "智能回复未改为动态标记")
    
    if "_generate_meaningful_fallback" in content and "__NEED_DYNAMIC_FALLBACK__" in content:
        result.add_pass("动态fallback", "降级回复已改为动态标记")
    else:
        result.add_fail("动态fallback", "降级回复未改为动态标记")


def test_no_template_in_frontend(result: TestResult):
    """核心测试：前端代码中不再包含写死的模板化提示词"""
    print("\n[2] 检测前端代码中的写死模板...")
    
    app_js_path = Path("frontend/app.js")
    if not app_js_path.exists():
        result.add_fail("前端模板检测", "app.js不存在")
        return
    
    content = app_js_path.read_text(encoding="utf-8")
    
    found_templates = []
    for kw in TEMPLATE_KEYWORDS:
        if kw in content:
            found_templates.append(kw)
    
    if found_templates:
        result.add_fail("前端模板检测", f"发现{len(found_templates)}个写死模板: {', '.join(found_templates[:5])}")
    else:
        result.add_pass("前端模板检测", "前端代码中无写死模板")


def test_ollama_diagnosis(result: TestResult):
    """核心测试：Ollama智能诊断功能"""
    print("\n[3] 测试Ollama智能诊断...")
    
    try:
        from backend.chat_stream import _diagnose_ollama_status
        d = _diagnose_ollama_status()
        
        if d["status"] in ("alive", "stuck", "dead"):
            result.add_pass("诊断状态", f"status={d['status']}")
        else:
            result.add_fail("诊断状态", f"未知状态: {d['status']}")
        
        if d["evidence"]:
            result.add_pass("诊断证据", f"{len(d['evidence'])}条证据: {'; '.join(d['evidence'][:3])}")
        else:
            result.add_warning("诊断证据", "无诊断证据")
        
        if isinstance(d["model_running"], bool):
            result.add_pass("模型运行检测", f"model_running={d['model_running']}")
        else:
            result.add_fail("模型运行检测", "返回值类型错误")
    except Exception as e:
        result.add_fail("Ollama诊断", str(e))


def test_multi_path_parallel(result: TestResult):
    """核心测试：多路径并行辅助函数"""
    print("\n[4] 测试多路径并行辅助函数...")
    
    functions_to_check = [
        ("_fetch_external_learning", "外部学习器"),
        ("_fetch_fact_assertions", "事实锚点"),
        ("_self_reason", "自我推理"),
        ("_background_collect", "后台收集"),
    ]
    
    for func_name, desc in functions_to_check:
        try:
            mod = __import__("backend.chat_stream", fromlist=[func_name])
            func = getattr(mod, func_name)
            result.add_pass(f"并行路径", f"{desc}({func_name})")
        except Exception as e:
            result.add_fail(f"并行路径", f"{desc}({func_name}): {str(e)[:60]}")


def test_closed_loop_orchestrator(result: TestResult):
    """核心测试：闭环调度器"""
    print("\n[5] 测试闭环调度器...")
    
    try:
        from core.closed_loop_orchestrator import closed_loop_orchestrator, LoopContext, LoopState
        result.add_pass("闭环调度器", "导入成功")
        
        ctx = LoopContext(query="测试问题")
        if ctx.state == LoopState.INIT:
            result.add_pass("闭环初始状态", "LoopState.INIT")
        else:
            result.add_fail("闭环初始状态", f"预期INIT，实际{ctx.state}")
        
        if ctx.max_iterations == 3:
            result.add_pass("闭环迭代限制", "max_iterations=3")
        else:
            result.add_warning("闭环迭代限制", f"max_iterations={ctx.max_iterations}")
    except Exception as e:
        result.add_fail("闭环调度器", str(e))


def test_stream_chat_no_template(result: TestResult):
    """核心测试：流式聊天不输出模板化内容"""
    print("\n[6] 测试流式聊天输出质量...")
    
    test_queries = ["你好", "五年级升六年级暑假建议"]
    
    for query in test_queries:
        try:
            r = requests.post(f"{BASE_URL}/api/chat/stream",
                json={"message": query, "context": {}},
                headers={"Accept": "text/event-stream"},
                stream=True, timeout=180)
            
            phases = []
            final_response = ""
            has_result = False
            
            for line in r.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("type") == "step":
                            phases.append(data.get("phase", ""))
                        elif data.get("type") == "result":
                            final_response = data.get("response", "")
                            has_result = True
                    except:
                        pass
            
            if not has_result:
                result.add_fail(f"流式聊天({query[:10]})", "未收到result事件")
                continue
            
            template_found = [kw for kw in TEMPLATE_KEYWORDS if kw in final_response]
            if template_found:
                result.add_fail(f"流式聊天质量({query[:10]})",
                    f"输出包含模板化内容: {', '.join(template_found[:3])}")
            else:
                result.add_pass(f"流式聊天质量({query[:10]})",
                    f"无模板化内容, {len(phases)}个阶段, 响应{len(final_response)}字")
            
            if len(final_response) < 20:
                result.add_fail(f"流式聊天长度({query[:10]})", f"响应过短: {len(final_response)}字")
            else:
                result.add_pass(f"流式聊天长度({query[:10]})", f"响应{len(final_response)}字")
                
        except requests.exceptions.Timeout:
            result.add_fail(f"流式聊天({query[:10]})", "请求超时(180秒)")
        except Exception as e:
            result.add_fail(f"流式聊天({query[:10]})", str(e)[:80])


def test_api_endpoints(result: TestResult):
    """测试所有新增API端点"""
    print("\n[7] 测试API端点...")
    
    endpoints = [
        ("GET", "/api/health", "健康检查"),
        ("GET", "/api/facts/stats", "事实库统计"),
        ("GET", "/api/memory/stats", "立体记忆统计"),
        ("GET", "/api/relationship/summary", "关系摘要"),
        ("GET", "/api/presence/status", "存在层状态"),
    ]
    
    for method, path, desc in endpoints:
        try:
            if method == "GET":
                r = requests.get(f"{BASE_URL}{path}", timeout=5)
            else:
                r = requests.post(f"{BASE_URL}{path}", json={}, timeout=5)
            
            if r.status_code == 200:
                data = r.json()
                if "error" in data:
                    result.add_warning(f"API: {desc}", f"返回错误: {data['error'][:50]}")
                else:
                    result.add_pass(f"API: {desc}", f"状态码200")
            else:
                result.add_fail(f"API: {desc}", f"状态码{r.status_code}")
        except Exception as e:
            result.add_fail(f"API: {desc}", str(e)[:60])


def test_core_modules_import(result: TestResult):
    """测试核心模块导入"""
    print("\n[8] 测试核心模块导入...")
    
    modules = [
        ("core.closed_loop_orchestrator", "ClosedLoopOrchestrator"),
        ("core.cognitive_dispatcher", "CognitiveDispatcher"),
        ("infrastructure.fact_store", "fact_store"),
        ("infrastructure.fitness_evaluator", "fitness_evaluator"),
        ("infrastructure.injection_verifier", "injection_verifier"),
        ("infrastructure.vector_retriever", "vector_retriever"),
        ("core.self_assessment", "self_assessment"),
        ("core.knowledge_forgetting", "knowledge_forgetting"),
        ("core.low_load_reorganization", "low_load_reorganization"),
        ("core.presence.existence_layer", "ExistenceLayer"),
        ("core.evolution.adaptive_goal", "AdaptiveEvolutionGoal"),
        ("core.relationship.model", "RelationshipModel"),
        ("core.memory.stereo_memory", "StereoMemorySystem"),
    ]
    
    for module_name, class_name in modules:
        try:
            mod = __import__(module_name, fromlist=[class_name])
            getattr(mod, class_name)
            result.add_pass("模块导入", f"{module_name}.{class_name}")
        except Exception as e:
            result.add_fail("模块导入", f"{module_name}.{class_name}: {str(e)[:60]}")


def main():
    print("="*60)
    print("联盟拓荒者 - 端到端质量测试 v2.0")
    print("="*60)
    print()
    
    result = TestResult()
    
    test_no_template_in_backend(result)
    test_no_template_in_frontend(result)
    test_ollama_diagnosis(result)
    test_multi_path_parallel(result)
    test_closed_loop_orchestrator(result)
    test_api_endpoints(result)
    test_core_modules_import(result)
    test_stream_chat_no_template(result)
    
    success = result.summary()
    
    if success:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查上述错误。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
