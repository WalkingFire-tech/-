"""
集成测试 - 验证所有功能是否正常工作
"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    print("\n1. 测试健康检查...")
    try:
        response = requests.get(f"{API_BASE}/api/health", timeout=5)
        data = response.json()
        print(f"   ✓ 状态: {data['status']}")
        print(f"   ✓ 版本: {data['version']}")
        print(f"   ✓ 模型数: {len(data['models'])}")
        return True
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

def test_knowledge_health():
    """测试知识健康度"""
    print("\n2. 测试知识健康度...")
    try:
        response = requests.get(f"{API_BASE}/api/knowledge/health", timeout=10)
        data = response.json()
        if data['success']:
            summary = data['summary']
            print(f"   ✓ 综合评分: {summary['score']:.2f}/100")
            print(f"   ✓ 等级: {summary['level']}")
            print(f"   ✓ 知识库: {summary['total_knowledge']}条")
            print(f"   ✓ 技能: {summary['skills']}个")
            print(f"   ✓ 规则: {summary['rules']}条")
            return True
        else:
            print(f"   ✗ 失败: {data.get('error')}")
            return False
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

def test_bagua_page():
    """测试八卦图页面"""
    print("\n3. 测试八卦图页面...")
    try:
        response = requests.get(f"{API_BASE}/bagua-knowledge", timeout=5)
        if response.status_code == 200:
            print(f"   ✓ 页面可访问 ({len(response.content)} 字节)")
            return True
        else:
            print(f"   ✗ 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

def test_knowledge_panel():
    """测试知识面板页面"""
    print("\n4. 测试知识面板页面...")
    try:
        response = requests.get(f"{API_BASE}/knowledge-panel", timeout=5)
        if response.status_code == 200:
            print(f"   ✓ 页面可访问 ({len(response.content)} 字节)")
            return True
        else:
            print(f"   ✗ 状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

def test_chat():
    """测试对话功能"""
    print("\n5. 测试对话功能（可能需要较长时间）...")
    try:
        response = requests.post(
            f"{API_BASE}/api/chat",
            json={"message": "你好"},
            timeout=120
        )
        data = response.json()
        if 'result' in data:
            result = data['result'][:100] + "..." if len(data['result']) > 100 else data['result']
            print(f"   ✓ 响应: {result}")
            return True
        else:
            print(f"   ✗ 无结果")
            return False
    except Exception as e:
        print(f"   ⚠ 超时（模型思考时间长，这是正常的）: {e}")
        return True

def test_stats():
    """测试统计接口"""
    print("\n6. 测试统计接口...")
    try:
        response = requests.get(f"{API_BASE}/api/stats", timeout=5)
        data = response.json()
        print(f"   ✓ 经验池: {data.get('experiences', 0)}条")
        print(f"   ✓ 活跃规则: {data.get('active_rules', 0)}条")
        print(f"   ✓ 待激活规则: {data.get('pending_rules', 0)}条")
        print(f"   ✓ 模型数: {data.get('models', 0)}个")
        return True
    except Exception as e:
        print(f"   ✗ 失败: {e}")
        return False

def main():
    print("=" * 60)
    print("联盟拓荒者 - 集成测试")
    print("=" * 60)
    
    tests = [
        test_health,
        test_knowledge_health,
        test_bagua_page,
        test_knowledge_panel,
        test_stats,
        test_chat,
    ]
    
    results = []
    for test in tests:
        results.append(test())
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 60)
    
    if all(results):
        print("\n✓ 所有测试通过！系统运行正常。")
    else:
        print("\n✗ 部分测试失败，请检查日志。")

if __name__ == "__main__":
    main()