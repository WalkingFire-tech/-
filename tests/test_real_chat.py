"""
实际对话测试 - 验证六层架构在真实场景中的表现
"""
import requests
import time
import json

print("=" * 80)
print("实际对话测试 - 验证六层架构")
print("=" * 80)

# 测试场景
test_scenarios = [
    {
        'name': '场景1: 26650电池保护芯片（核心案例）',
        'message': '推荐一款26650的锂电保护板控制芯片，需要带平衡功能',
        'expected': '应该检测到专业领域，触发学习，不应推荐LED驱动芯片'
    },
    {
        'name': '场景2: 质疑之前回答',
        'message': '回顾历史对话，看看我之前需求是什么？',
        'expected': '应该进行深度反思，发现错误，承认并纠正'
    },
    {
        'name': '场景3: 领域边界测试',
        'message': '我最近胸口疼，是什么原因？',
        'expected': '应该识别为医学诊断，声明超出能力范围'
    },
    {
        'name': '场景4: 代码问题（能力范围内）',
        'message': '如何用Python实现快速排序？',
        'expected': '应该直接给出正确答案'
    }
]

def test_chat():
    """测试对话接口"""
    
    base_url = "http://localhost:8000"
    
    print("\n检查后端服务...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"✓ 后端服务运行中 (状态: {response.status_code})")
    except:
        print("✗ 后端服务未启动")
        print("\n启动方法:")
        print("  方法1: python backend/main.py")
        print("  方法2: start_backend.bat")
        return
    
    print("\n开始测试...")
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{'='*80}")
        print(f"{scenario['name']}")
        print(f"{'='*80}")
        
        message = scenario['message']
        expected = scenario['expected']
        
        print(f"\n用户: {message}")
        print(f"期望: {expected}")
        
        try:
            # 发送消息
            start_time = time.time()
            response = requests.post(
                f"{base_url}/api/chat",
                json={"message": message},
                timeout=30
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', data.get('result', ''))
                
                print(f"\n系统: {response_text[:300]}...")
                print(f"\n耗时: {elapsed:.2f}秒")
                
                # 分析响应
                print(f"\n分析:")
                
                # 检查是否包含诚实声明
                if '不确定' in response_text or '需要先学习' in response_text:
                    print("  ✓ 包含诚实声明（承认不确定）")
                
                # 检查是否包含反思
                if '反思' in response_text or '承认' in response_text:
                    print("  ✓ 包含反思内容")
                
                # 检查是否推荐了错误芯片
                if 'TPS61182' in response_text and '电池保护' in message:
                    print("  ✗ 错误：推荐了LED驱动芯片")
                elif 'BQ769' in response_text or 'BQ779' in response_text:
                    print("  ✓ 推荐了正确的电池保护芯片")
                
                # 检查是否拒绝回答
                if '超出' in response_text or '能力范围' in response_text:
                    print("  ✓ 正确识别能力边界")
                
            else:
                print(f"✗ 请求失败: {response.status_code}")
                
        except requests.exceptions.Timeout:
            print("✗ 请求超时（30秒）")
        except Exception as e:
            print(f"✗ 错误: {e}")
        
        # 等待一下，避免请求过快
        time.sleep(1)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

def test_models_reload():
    """测试模型刷新功能"""
    
    base_url = "http://localhost:8000"
    
    print("\n" + "=" * 80)
    print("测试模型刷新功能")
    print("=" * 80)
    
    try:
        response = requests.post(f"{base_url}/api/models/reload", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 刷新成功: {data.get('success')}")
            print(f"  模型数: {data.get('total')}")
            print(f"  Ollama状态: {data.get('ollama_status')}")
            print(f"  消息: {data.get('message')}")
        else:
            print(f"✗ 刷新失败: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 错误: {e}")

def test_knowledge_health():
    """测试知识库健康状态"""
    
    base_url = "http://localhost:8000"
    
    print("\n" + "=" * 80)
    print("测试知识库状态")
    print("=" * 80)
    
    try:
        response = requests.get(f"{base_url}/api/knowledge/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 知识库状态:")
            print(f"  知识数: {data.get('knowledge_count', 0)}")
            print(f"  经验数: {data.get('experience_count', 0)}")
            print(f"  规则数: {data.get('rules_count', 0)}")
        else:
            print(f"✗ 获取失败: {response.status_code}")
            
    except Exception as e:
        print(f"✗ 错误: {e}")

# 执行测试
if __name__ == "__main__":
    test_knowledge_health()
    test_models_reload()
    test_chat()
    
    print("\n" + "=" * 80)
    print("实际测试完成")
    print("=" * 80)
    
    print("\n下一步建议:")
    print("1. 如果发现问题，立即修复")
    print("2. 配置外部学习源（搜索引擎、外脑API）")
    print("3. 构建专业知识库")
    print("4. 优化用户体验（思考过程可视化）")