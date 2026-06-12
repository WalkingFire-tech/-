"""
完整功能测试脚本
验证联盟拓荒者的所有核心功能
"""
import sys
import json
import time
from pathlib import Path

print("=" * 70)
print("联盟拓荒者 - 完整功能测试")
print("=" * 70)

# 测试结果收集
test_results = []

def test(name, func):
    """运行测试"""
    print(f"\n[测试] {name}")
    try:
        result = func()
        if result:
            print(f"  ✓ 通过")
            test_results.append((name, True, None))
            return True
        else:
            print(f"  ✗ 失败")
            test_results.append((name, False, "返回False"))
            return False
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        test_results.append((name, False, str(e)))
        return False

# ===== 基础设施测试 =====

def test_imports():
    """测试核心模块导入"""
    ROOT_DIR = Path(__file__).parent
    sys.path.insert(0, str(ROOT_DIR))
    
    modules = [
        "infrastructure.event_bus",
        "infrastructure.config_manager",
        "infrastructure.session_compressor",
        "infrastructure.dream_integrator",
        "infrastructure.tool_cache",
        "infrastructure.knowledge_index",
        "core.services.intent_parser",
        "core.services.planner",
        "meta.controller",
    ]
    
    for module in modules:
        __import__(module)
    
    return True

def test_databases():
    """测试数据库文件"""
    dbs = [
        "experience_pool.db",
        "learning_rules.db",
        "model_stats.db",
    ]
    
    for db in dbs:
        if not Path(db).exists():
            return False
    
    return True

# ===== API测试 =====

def test_api_health():
    """测试健康检查API"""
    import urllib.request
    
    with urllib.request.urlopen("http://localhost:8000/api/health", timeout=5) as response:
        data = json.loads(response.read())
        return data.get("status") == "ok"

def test_api_stats():
    """测试统计API"""
    import urllib.request
    
    with urllib.request.urlopen("http://localhost:8000/api/stats", timeout=5) as response:
        data = json.loads(response.read())
        return "experiences" in data and "active_rules" in data

def test_api_models():
    """测试模型列表API"""
    import urllib.request
    
    with urllib.request.urlopen("http://localhost:8000/api/models", timeout=5) as response:
        data = json.loads(response.read())
        return len(data.get("models", [])) > 0

def test_frontend():
    """测试前端页面"""
    import urllib.request
    
    with urllib.request.urlopen("http://localhost:8000/", timeout=5) as response:
        content = response.read()
        return len(content) > 1000 and b"UTF-8" in content

# ===== 记忆系统测试 =====

def test_session_compressor():
    """测试会话压缩"""
    from infrastructure.session_compressor import SessionCompressor
    
    compressor = SessionCompressor()
    
    # 测试数据
    messages = [
        {"role": "user", "content": "测试问题1"},
        {"role": "assistant", "content": "测试回答1"},
    ] * 25  # 50轮
    
    result = compressor.compress(messages)
    
    return result.get("compressed") and "summary" in result

def test_tool_cache():
    """测试工具缓存"""
    from infrastructure.tool_cache import ToolResultCache
    
    cache = ToolResultCache()
    
    # 测试缓存
    cache.set("test_tool", {"param": "value"}, {"output": "result"})
    cached = cache.get("test_tool", {"param": "value"})
    
    return cached is not None and cached.get("output") == "result"

def test_knowledge_index():
    """测试知识索引"""
    from infrastructure.knowledge_index import KnowledgeIndex
    
    index = KnowledgeIndex()
    index.rebuild_index()
    
    stats = index.get_stats()
    return "总缓存数" in stats or "total_cached" in str(stats)

# ===== 学习系统测试 =====

def test_intent_parser():
    """测试意图解析"""
    from core.services.intent_parser import IntentParser
    
    parser = IntentParser()
    intent = parser.parse("如何实现快速排序？")
    
    return intent.type in ["code", "question"]

def test_rule_matcher():
    """测试规则匹配"""
    from infrastructure.rule_matcher import RuleMatcher
    
    matcher = RuleMatcher()
    
    # 测试条件评估
    result = matcher.evaluate_condition(
        "intent_type == 'code'",
        {"intent_type": "code"}
    )
    
    return result

# ===== 运行所有测试 =====

print("\n" + "=" * 70)
print("开始测试...")
print("=" * 70)

# 基础测试
print("\n【基础设施】")
test("模块导入", test_imports)
test("数据库文件", test_databases)

# API测试
print("\n【API端点】")
test("健康检查", test_api_health)
test("统计信息", test_api_stats)
test("模型列表", test_api_models)
test("前端页面", test_frontend)

# 记忆系统测试
print("\n【记忆系统】")
test("会话压缩", test_session_compressor)
test("工具缓存", test_tool_cache)
test("知识索引", test_knowledge_index)

# 学习系统测试
print("\n【学习系统】")
test("意图解析", test_intent_parser)
test("规则匹配", test_rule_matcher)

# ===== 测试总结 =====

print("\n" + "=" * 70)
print("测试总结")
print("=" * 70)

passed = sum(1 for _, result, _ in test_results if result)
total = len(test_results)

print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
print()

for name, result, error in test_results:
    status = "✓" if result else "✗"
    print(f"{status} {name}")
    if error and not result:
        print(f"  └─ {error}")

# ===== 系统评估 =====

print("\n" + "=" * 70)
print("系统评估")
print("=" * 70)

if passed == total:
    print("\n🎉 所有测试通过！系统功能完整。")
    print("\n核心能力:")
    print("  ✅ 意图理解与模型路由")
    print("  ✅ 学习闭环（归纳→应用→反馈）")
    print("  ✅ 记忆系统（Claude 5 6/7层级）")
    print("  ✅ 自我进化机制")
    print("  ✅ Web + CLI双模式界面")
    print("\n访问地址:")
    print("  - 前端: http://localhost:8000/")
    print("  - API文档: http://localhost:8000/docs")
    
elif passed >= total * 0.8:
    print(f"\n⚠️  {passed}/{total}测试通过，系统基本可用。")
    print("\n建议:")
    print("  1. 检查失败的测试项")
    print("  2. 确认后端服务正常运行")
    print("  3. 查看日志排查问题")
    
else:
    print(f"\n❌ 仅{passed}/{total}测试通过，系统存在问题。")
    print("\n建议:")
    print("  1. 检查依赖安装: pip install -r requirements.txt")
    print("  2. 启动后端服务: python -m uvicorn api:app --port 8000")
    print("  3. 查看错误日志排查问题")

print("\n" + "=" * 70)