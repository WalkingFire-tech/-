"""
端到端验证：测试完整聊天流程
"""
import sys
import asyncio
import time
sys.path.insert(0, ".")

async def test_chat():
    print("╔════════════════════════════════════════════════════════╗")
    print("║       端到端验证：完整聊天流程测试                      ║")
    print("╚════════════════════════════════════════════════════════╝\n")
    
    from backend.chat_handler import chat_never_giveup
    
    test_cases = [
        ("你好", "问候语"),
        ("认知的概念是什么", "概念问题"),
        ("如何提升学习能力", "方法问题"),
        ("为什么天空是蓝色的", "原因问题"),
        ("写一个Python排序函数", "代码问题")
    ]
    
    for question, category in test_cases:
        print(f"\n{'='*60}")
        print(f"测试: {category} - '{question}'")
        print(f"{'='*60}")
        
        start = time.time()
        try:
            result = await asyncio.wait_for(
                chat_never_giveup(question, {}),
                timeout=25.0
            )
            elapsed = time.time() - start
            
            response = result.get('response', '')
            attempts = result.get('attempts', [])
            spirit = result.get('spirit_compliant', False)
            
            print(f"  ✅ 完成: {elapsed:.1f}秒")
            print(f"  回复长度: {len(response)}字")
            print(f"  尝试方法: {len(attempts)}种")
            print(f"  精神内核: {'✓' if spirit else '✗'}")
            print(f"  回复预览: {response[:80]}...")
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start
            print(f"  ❌ 超时: {elapsed:.1f}秒")
        except Exception as e:
            print(f"  ❌ 异常: {str(e)[:50]}")
    
    print(f"\n{'='*60}")
    print("✅ 端到端验证完成")
    print(f"{'='*60}")

asyncio.run(test_chat())