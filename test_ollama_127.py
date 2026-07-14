#!/usr/bin/env python
"""测试Ollama适配器 - 使用127.0.0.1"""
import sys
sys.path.insert(0, r'C:\Users\Administrator\alliance_pioneer')

from adapters.llm.ollama_adapter import ollama_chat_request

print("=== 测试ollama_chat_request (127.0.0.1) ===")
try:
    result = ollama_chat_request(
        base_url="http://127.0.0.1:11434",
        model="qwen2.5:7b",
        prompt="测试：1+1等于几？",
        timeout=60
    )
    print(f"成功: {result.get('content', '')[:100]}")
except Exception as e:
    print(f"失败: {e}")
    import traceback
    traceback.print_exc()