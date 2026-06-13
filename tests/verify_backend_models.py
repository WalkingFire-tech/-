"""验证后端模型加载"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("验证后端模型加载配置")
print("=" * 60)

# 读取backend/main.py
with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查模型加载代码
models_to_check = ['mindchat', 'qwen2.5-coder:1.5b', 'deepcoder']

print("\n模型加载代码检查:")
for model in models_to_check:
    if model in content:
        # 找到模型名称的上下文
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if model in line and 'OllamaAdapter' in line:
                print(f"  ✓ {model}: {line.strip()}")
                break
    else:
        print(f"  ✗ {model}: 未找到")

# 统计OllamaAdapter调用次数
ollama_count = content.count('OllamaAdapter')
print(f"\nOllamaAdapter调用次数: {ollama_count}次")

# 检查远程模型
print("\n远程模型检查:")
if 'OPENAI_API_KEY' in content:
    print("  ✓ OpenAI API配置存在")
if 'DEEPSEEK_API_KEY' in content:
    print("  ✓ DeepSeek API配置存在")

print("\n" + "=" * 60)
print("配置验证完成")
print("\n预期加载的模型:")
print("  1. mindchat (Ollama)")
print("  2. qwen2.5-coder:1.5b (Ollama, 别名: code_light)")
print("  3. deepcoder (Ollama)")
print("  4. remote_gpt4 (如果OPENAI_API_KEY存在)")
print("  5. deepseek-chat (如果DEEPSEEK_API_KEY或OPENAI_API_KEY存在)")