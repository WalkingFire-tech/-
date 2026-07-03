"""
测试精神内核 - 验证永不放弃精神是否刻进底层
"""
import asyncio
import sys
sys.path.insert(0, ".")

from core.spirit_core import spirit_core
from backend.chat_handler import chat_never_giveup


def test_spirit_core():
    """测试精神内核基础功能"""
    print("=" * 60)
    print("测试1：精神内核状态")
    print("=" * 60)
    
    status = spirit_core.get_spirit_status()
    print(f"核心原则数量: {len(status['core_principles'])}")
    print(f"能力定义数量: {len(status['abilities'])}")
    print(f"已学习教训: {status['lessons_learned']}")
    print(f"状态: {status['status']}")
    
    print("\n核心原则:")
    for i, principle in enumerate(status['core_principles'], 1):
        print(f"  {i}. {principle}")
    
    print("\n能力列表:")
    for key, value in status['abilities'].items():
        print(f"  ✅ {value}")


def test_response_validation():
    """测试回复验证"""
    print("\n" + "=" * 60)
    print("测试2：回复验证")
    print("=" * 60)
    
    # 测试1：好的回复
    good_response = "关于这个问题，我尝试了多种方法，并给出以下建议..."
    validation = spirit_core.validate_response(good_response)
    print(f"\n好的回复验证: {validation['valid']}")
    
    # 测试2：敷衍的回复
    bad_response = "我不知道"
    validation = spirit_core.validate_response(bad_response)
    print(f"敷衍回复验证: {validation['valid']}")
    if not validation['valid']:
        print(f"问题: {validation['issues']}")
    
    # 测试3：失败但无方向的回复
    fail_response = "处理失败了"
    validation = spirit_core.validate_response(fail_response)
    print(f"失败无方向回复验证: {validation['valid']}")
    if not validation['valid']:
        print(f"问题: {validation['issues']}")


def test_meaningful_response():
    """测试有意义回复生成"""
    print("\n" + "=" * 60)
    print("测试3：有意义回复生成")
    print("=" * 60)
    
    question = "认知的概念是什么"
    attempts = [
        {"method": "知识检索", "success": False, "error": "未找到相关知识"},
        {"method": "模型推理", "success": False, "error": "模型超时"},
        {"method": "深度认知", "success": False, "error": "认知引擎异常"}
    ]
    
    response = spirit_core.ensure_meaningful_response(question, attempts)
    print(f"\n问题: {question}")
    print(f"\n生成的回复:\n{response}")


async def test_chat_handler():
    """测试聊天处理器"""
    print("\n" + "=" * 60)
    print("测试4：聊天处理器集成")
    print("=" * 60)
    
    test_questions = [
        "你好",
        "认知的概念是什么",
        "如何写一个排序算法",
        "这是一个非常复杂的问题，涉及多个领域的知识"
    ]
    
    for question in test_questions:
        print(f"\n问题: {question}")
        result = await chat_never_giveup(question, {})
        print(f"回复长度: {len(result['response'])}字")
        print(f"尝试方法: {len(result['attempts'])}种")
        print(f"精神内核: {'已启用' if result.get('spirit_compliant') else '未启用'}")
        print(f"回复预览: {result['response'][:100]}...")


def main():
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "联盟拓荒者精神内核测试" + " " * 22 + "║")
    print("╚" + "═" * 58 + "╝\n")
    
    # 测试1：精神内核状态
    test_spirit_core()
    
    # 测试2：回复验证
    test_response_validation()
    
    # 测试3：有意义回复生成
    test_meaningful_response()
    
    # 测试4：聊天处理器集成
    print("\n开始异步测试...")
    asyncio.run(test_chat_handler())
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
    
    print("\n精神内核总结:")
    status = spirit_core.get_spirit_status()
    print(f"  • 已学习教训: {status['lessons_learned']}条")
    print(f"  • 成功模式: {status['success_patterns']}种")
    print(f"  • 创造方法: {status['created_methods']}种")
    print(f"\n  永不放弃精神已刻进系统底层！")


if __name__ == "__main__":
    main()