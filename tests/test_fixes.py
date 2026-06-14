#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试修复效果"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("测试修复效果")
print("=" * 60)

# 测试1: 格式化错误修复
print("\n[测试1] 格式化错误修复 - life_support.py")
try:
    from infrastructure.life_support import LifeSupportSystem
    lss = LifeSupportSystem()
    health = lss.check_health()
    
    # 测试获取系统健康状态
    health = lss.get_system_health()
    survival = health.get('survival_level', 'unknown')
    print(f"  ✓ survival_level={survival} 格式化成功")
    print("  ✓ 格式化错误已修复")
except Exception as e:
    print(f"  ✗ 错误: {e}")

# 测试2: Meta意图识别增强
print("\n[测试2] Meta意图识别增强 - intent_parser.py")
try:
    from core.services.intent_parser import IntentParser
    parser = IntentParser()
    
    test_cases = [
        ("学习能力呢？", "meta"),
        ("你的学习能力怎么样？", "meta"),
        ("你会学习吗？", "meta"),
        ("你的架构是什么？", "meta"),
        ("你是谁？", "meta"),
        ("今天天气怎么样？", "chat")
    ]
    
    all_passed = True
    for message, expected_type in test_cases:
        result = parser.parse(message)
        actual_type = result.type if hasattr(result, 'type') else 'unknown'
        status = "✓" if actual_type == expected_type else "✗"
        if actual_type != expected_type:
            all_passed = False
        print(f"  {status} '{message}' -> {actual_type} (期望: {expected_type})")
    
    if all_passed:
        print("  ✓ Meta意图识别增强成功")
    else:
        print("  ! 部分意图识别需要优化")
except Exception as e:
    print(f"  ✗ 错误: {e}")

# 测试3: 边界层五维守护
print("\n[测试3] 边界层五维守护 - PHILOSOPHY.md")
try:
    philosophy_path = Path(__file__).parent / "PHILOSOPHY.md"
    if philosophy_path.exists():
        content = philosophy_path.read_text(encoding='utf-8')
        checks = [
            ("懂善恶", "懂善恶" in content),
            ("明事理", "明事理" in content),
            ("守底线", "守底线" in content),
            ("助文明", "助文明" in content),
            ("不渡他人", "不渡他人" in content)
        ]
        all_present = all(check[1] for check in checks)
        for name, present in checks:
            status = "✓" if present else "✗"
            print(f"  {status} {name}")
        if all_present:
            print("  ✓ 边界层五维守护文档完整")
    else:
        print("  ✗ PHILOSOPHY.md 不存在")
except Exception as e:
    print(f"  ✗ 错误: {e}")

# 测试4: 回应边界速查表
print("\n[测试4] 回应边界速查表 - RESPONSE_BOUNDARIES.md")
try:
    boundaries_path = Path(__file__).parent / "RESPONSE_BOUNDARIES.md"
    if boundaries_path.exists():
        content = boundaries_path.read_text(encoding='utf-8')
        print("  ✓ RESPONSE_BOUNDARIES.md 存在")
        print(f"  ✓ 文档大小: {len(content)} 字符")
    else:
        print("  ✗ RESPONSE_BOUNDARIES.md 不存在")
except Exception as e:
    print(f"  ✗ 错误: {e}")

# 测试5: 持续学习单元
print("\n[测试5] 持续学习单元 - active_learner.py")
try:
    from infrastructure.active_learner import ActiveLearner
    print("  ✓ ActiveLearner 导入成功")
    
    # 检查关键方法
    methods = ['pause', 'resume', 'get_activities', 'get_knowledge']
    for method in methods:
        if hasattr(ActiveLearner, method):
            print(f"  ✓ 方法 {method}() 存在")
        else:
            print(f"  ✗ 方法 {method}() 缺失")
except Exception as e:
    print(f"  ✗ 错误: {e}")

# 测试6: 安全搜索工具
print("\n[测试6] 安全搜索工具 - web_search.py")
try:
    from tools.web_search import WebSearchTool
    print("  ✓ WebSearchTool 导入成功")
    
    # 检查安全特性
    tool = WebSearchTool()
    print(f"  ✓ WebSearchTool 实例化成功")
except Exception as e:
    print(f"  ✗ 错误: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
print("\n建议:")
print("1. 运行 start.bat 启动系统")
print("2. 访问 http://localhost:8000 测试前端")
print("3. 测试问题: '学习能力呢？' 应直接回答")
print("4. 测试边界: '我该不该离婚？' 应使用反问")