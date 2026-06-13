"""测试加载所有Ollama模型"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from adapters.llm.ollama_adapter import OllamaAdapter

models = []

print("测试加载Ollama模型:")
print("=" * 60)

# 测试mindchat
try:
    adapter = OllamaAdapter('mindchat')
    models.append(('mindchat', adapter))
    print("✓ mindchat 加载成功")
except Exception as e:
    print(f"✗ mindchat 加载失败: {e}")

# 测试qwen2.5-coder:1.5b
try:
    adapter = OllamaAdapter('qwen2.5-coder:1.5b')
    models.append(('qwen2.5-coder:1.5b', adapter))
    print("✓ qwen2.5-coder:1.5b 加载成功")
except Exception as e:
    print(f"✗ qwen2.5-coder:1.5b 加载失败: {e}")

# 测试deepcoder
try:
    adapter = OllamaAdapter('deepcoder')
    models.append(('deepcoder', adapter))
    print("✓ deepcoder 加载成功")
except Exception as e:
    print(f"✗ deepcoder 加载失败: {e}")

print("=" * 60)
print(f"\n成功加载: {len(models)}个模型")
print(f"模型列表: {[name for name, _ in models]}")