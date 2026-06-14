#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试历史对话功能修复"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("测试历史对话功能修复")
print("=" * 60)

# 测试1: 意图识别
print("\n[测试1] 意图识别 - memory意图")
from core.services.intent_parser import IntentParser
parser = IntentParser()

test_cases = [
    "回顾历史对话",
    "历史对话",
    "之前的对话",
    "回顾对话",
    "历史问题",
    "记住这个",
    "之前我们聊过什么"
]

for question in test_cases:
    intent = parser.parse(question)
    status = "✓" if intent.type == "memory" else "✗"
    print(f"  {status} '{question}' -> {intent.type}")

# 测试2: CampfireLogger读取
print("\n[测试2] CampfireLogger读取历史对话")
from infrastructure.logger import CampfireLogger
logger = CampfireLogger()

context = logger.get_recent_context(rounds=5)
if context:
    lines = context.split('\n')
    print(f"  ✓ 读取到 {len(lines)} 行对话")
    print(f"  前3行预览:")
    for line in lines[:3]:
        print(f"    {line[:60]}...")
else:
    print("  ! 暂无历史对话记录")

# 测试3: Planner处理memory意图
print("\n[测试3] Planner处理memory意图")
try:
    from core.services.planner import Planner
    from core.services.intent_parser import Intent
    
    planner = Planner()
    
    # 创建memory意图
    intent = Intent(
        type="memory",
        raw_text="回顾历史对话",
        confidence=0.9
    )
    
    response = planner._handle_memory_query(intent)
    
    if "历史对话" in response or "暂无" in response:
        print("  ✓ 成功处理memory意图")
        print(f"  响应预览: {response[:100]}...")
    else:
        print("  ✗ 响应内容不符合预期")
        
except Exception as e:
    print(f"  ✗ 错误: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("\n建议:")
print("1. 重启系统: taskkill /F /IM python.exe; start.bat")
print("2. 测试问题: '回顾历史对话'")
print("3. 预期结果: 显示最近10轮对话历史")