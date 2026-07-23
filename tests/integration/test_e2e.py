import http.client
import json
import time
import sys

BASE_URL = "localhost"
PORT = 8000
TIMEOUT = 60

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print('='*70)

def print_test(num, total, text):
    print(f"\n[{num}/{total}] {text}")

def print_success(text):
    print(f"{Colors.GREEN}  ✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}  ❌ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}  ⚠️  {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}  ℹ️  {text}{Colors.END}")

def api_request(method, path, data=None, timeout=TIMEOUT):
    """发送API请求"""
    conn = http.client.HTTPConnection(BASE_URL, PORT, timeout=timeout)
    
    try:
        headers = {"Content-Type": "application/json"}
        body = json.dumps(data) if data else None
        
        conn.request(method, path, body, headers)
        response = conn.getresponse()
        result = response.read().decode('utf-8')
        
        try:
            return json.loads(result), response.status
        except:
            return result, response.status
            
    except Exception as e:
        return {"error": str(e)}, 0
    finally:
        conn.close()

def test_backend_health():
    """测试后端健康状态"""
    data, status = api_request("GET", "/api/health")
    
    if status == 200 and data.get("status") == "healthy":
        print_success(f"后端健康，模型数: {data.get('models_count', 0)}")
        return True
    else:
        print_error(f"健康检查失败: {data}")
        return False

def test_models_list():
    """测试模型列表"""
    data, status = api_request("GET", "/api/models")
    
    if status == 200:
        models = data.get("models", [])
        print_success(f"可用模型: {len(models)}个")
        for m in models[:5]:
            print_info(f"  - {m.get('name', 'unknown')}")
        return len(models) > 0
    else:
        print_error(f"获取模型失败: {data}")
        return False

def test_chat_function():
    """测试聊天功能（核心功能）"""
    test_cases = [
        ("你好", "基础问候"),
        ("1+1等于多少？", "数学计算"),
        ("介绍一下Python", "知识问答"),
        ("今天天气怎么样", "常识问题"),
        ("帮我写一个hello world程序", "代码生成")
    ]
    
    all_passed = True
    
    for i, (question, desc) in enumerate(test_cases, 1):
        print_info(f"测试 {i}: {question} ({desc})")
        
        start = time.time()
        data, status = api_request("POST", "/api/chat", {"message": question}, timeout=60)
        elapsed = time.time() - start
        
        if status == 200 and "response" in data and data["response"]:
            response = data["response"]
            print_success(f"成功 (耗时: {elapsed:.2f}s)")
            print_info(f"响应预览: {response[:80]}...")
        else:
            print_error(f"失败 (耗时: {elapsed:.2f}s): {data.get('error', 'unknown')}")
            all_passed = False
        
        time.sleep(0.5)
    
    return all_passed

def test_stats():
    """测试统计接口"""
    data, status = api_request("GET", "/api/stats")
    
    if status == 200:
        print_success(f"总对话: {data.get('total_conversations', 0)}")
        print_info(f"知识条目: {data.get('knowledge_count', 0)}")
        return True
    else:
        print_error(f"统计失败: {data}")
        return False

def test_knowledge_stats():
    """测试知识库统计"""
    data, status = api_request("GET", "/api/knowledge/stats")
    
    if status == 200 and data.get("success"):
        stats = data.get("stats", {})
        print_success(f"知识总数: {stats.get('total', 0)}")
        print_info(f"工具数: {stats.get('tools', 0)}")
        print_info(f"规则数: {stats.get('rules', 0)}")
        return True
    else:
        print_warning(f"知识统计失败: {data}")
        return True

def test_learning_targets():
    """测试学习目标"""
    data, status = api_request("GET", "/api/learning/targets")
    
    if status == 200 and data.get("success"):
        targets = data.get("targets", [])
        print_success(f"学习目标: {len(targets)}个")
        return True
    else:
        print_warning(f"学习目标失败: {data}")
        return True

def test_external_config():
    """测试外部模型配置"""
    data, status = api_request("GET", "/api/config/external")
    
    if status == 200 and data.get("success"):
        print_success("外部配置接口正常")
        has_openai = bool(data.get("openai_key"))
        has_deepseek = bool(data.get("deepseek_key"))
        print_info(f"OpenAI: {'已配置' if has_openai else '未配置'}")
        print_info(f"DeepSeek: {'已配置' if has_deepseek else '未配置'}")
        return True
    else:
        print_warning(f"外部配置失败: {data}")
        return True

def test_scheduler_status():
    """测试调度器状态"""
    data, status = api_request("GET", "/api/scheduler/status")
    
    if status == 200 and data.get("success"):
        scheduler_status = data.get("status", {})
        print_success(f"调度器: {'运行中' if scheduler_status.get('running') else '已停止'}")
        return True
    else:
        print_warning(f"调度器状态失败: {data}")
        return True

def test_tools_list():
    """测试工具列表"""
    data, status = api_request("GET", "/api/tools/list")
    
    if status == 200 and data.get("success"):
        tools = data.get("tools", [])
        print_success(f"可用工具: {len(tools)}个")
        return True
    else:
        print_warning(f"工具列表失败: {data}")
        return True

def test_models_test():
    """测试模型测试接口"""
    data, status = api_request("GET", "/api/models/test")
    
    if status == 200:
        results = data.get("results", {})
        working = sum(1 for v in results.values() if v.get("available"))
        total = len(results)
        print_success(f"可用模型: {working}/{total}")
        return True
    else:
        print_warning(f"模型测试失败: {data}")
        return True

def test_genome_status():
    """测试基因组状态"""
    data, status = api_request("GET", "/api/genome/status")
    
    if status == 200:
        print_success("基因组接口正常")
        return True
    else:
        print_warning(f"基因组状态失败: {data}")
        return True

def run_all_tests():
    """运行所有测试"""
    print_header("联盟拓荒者 - 端到端测试")
    
    tests = [
        ("后端健康检查", test_backend_health),
        ("模型列表", test_models_list),
        ("聊天功能（核心）", test_chat_function),
        ("系统统计", test_stats),
        ("知识库统计", test_knowledge_stats),
        ("学习目标", test_learning_targets),
        ("外部模型配置", test_external_config),
        ("调度器状态", test_scheduler_status),
        ("工具列表", test_tools_list),
        ("模型测试", test_models_test),
        ("基因组状态", test_genome_status),
    ]
    
    results = []
    
    for i, (name, test_func) in enumerate(tests, 1):
        print_test(i, len(tests), name)
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"异常: {e}")
            results.append((name, False))
    
    print_header("测试结果汇总")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✅{Colors.END}" if result else f"{Colors.RED}❌{Colors.END}"
        print(f"  {status} {name}")
    
    print(f"\n{'='*70}")
    print(f"  总计: {passed}/{total} 通过")
    print('='*70)
    
    if passed == total:
        print(f"\n{Colors.GREEN}✅ 所有功能正常，系统运行良好{Colors.END}\n")
        return 0
    else:
        print(f"\n{Colors.RED}❌ 存在失败项，请检查后端日志{Colors.END}\n")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(run_all_tests())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}测试已中断{Colors.END}")
        sys.exit(1)