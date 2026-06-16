"""测试系统基本功能"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("  系统基本功能测试")
print("=" * 60)

# 测试1: 检查环境变量
print("\n[1/5] 检查外脑API配置...")
import os
from dotenv import load_dotenv
load_dotenv()

api_keys = {
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
}

for key, value in api_keys.items():
    if value and value != "sk-your-openai-key-here" and value != "sk-your-deepseek-key-here":
        print(f"  ✅ {key}: 已配置")
    else:
        print(f"  ⚠️  {key}: 未配置")

# 测试2: 检查Ollama
print("\n[2/5] 检查Ollama服务...")
try:
    import requests
    response = requests.get("http://localhost:11434/api/tags", timeout=2)
    if response.status_code == 200:
        models = response.json().get('models', [])
        print(f"  ✅ Ollama可用，模型数: {len(models)}")
        for m in models[:3]:
            print(f"     - {m['name']}")
    else:
        print(f"  ⚠️  Ollama响应异常: {response.status_code}")
except Exception as e:
    print(f"  ⚠️  Ollama未启动: {e}")

# 测试3: 测试Mock适配器
print("\n[3/5] 测试Mock适配器...")
try:
    from adapters.llm.mock_adapter import MockAdapter
    mock = MockAdapter()
    response = mock.generate("测试问题")
    print(f"  ✅ Mock适配器正常")
    print(f"     响应: {response[:50]}...")
except Exception as e:
    print(f"  ❌ Mock适配器失败: {e}")

# 测试4: 测试意图解析
print("\n[4/5] 测试意图解析...")
try:
    from core.services.intent_parser import IntentParser
    parser = IntentParser()
    intent = parser.parse("你好")
    print(f"  ✅ 意图解析正常")
    print(f"     意图: {intent.type}, 置信度: {intent.confidence:.2f}")
except Exception as e:
    print(f"  ❌ 意图解析失败: {e}")

# 测试5: 测试知识检索
print("\n[5/5] 测试知识检索...")
try:
    from core.learning import enhanced_learner
    result = enhanced_learner.retrieve_knowledge("Python")
    if result:
        print(f"  ✅ 知识检索正常")
        print(f"     置信度: {result.get('confidence', 0):.2f}")
    else:
        print(f"  ✅ 知识检索正常（无匹配）")
except Exception as e:
    print(f"  ❌ 知识检索失败: {e}")

print("\n" + "=" * 60)
print("  测试完成")
print("=" * 60)

print("\n启动建议:")
print("  1. 启动Ollama: ollama serve")
print("  2. 配置外脑: 编辑.env文件，填入API密钥")
print("  3. 启动服务: python backend/main.py")