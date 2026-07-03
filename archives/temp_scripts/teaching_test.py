"""
教学式测试 - 通过反馈创建质量差异
目标：让归纳总结发现模式
"""
import requests
import sqlite3
import time
import json

BASE_URL = "http://localhost:8000"

def chat_with_feedback(message: str, expected_quality: str = "good"):
    """对话并给出反馈"""
    try:
        # 发送消息
        r = requests.post(
            f"{BASE_URL}/api/chat",
            json={"message": message},
            timeout=30
        )
        
        if r.status_code != 200:
            return None
        
        result = r.json()
        response = result.get('response', '')
        intent = result.get('intent', 'unknown')
        
        # 模拟用户反馈
        if expected_quality == "good":
            # 点赞（高质量）
            feedback_score = 80 + (hash(message) % 20)  # 80-100
        else:
            # 点踩（低质量）
            feedback_score = 20 + (hash(message) % 30)  # 20-50
        
        # 更新经验质量（模拟反馈）
        try:
            conn = sqlite3.connect("data/knowledge_store.db")
            
            # 找到最近的经验记录
            cursor = conn.execute("""
                SELECT id FROM experiences
                WHERE intent_type = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (intent,))
            
            exp_id = cursor.fetchone()
            
            if exp_id:
                # 更新质量分数
                conn.execute("""
                    UPDATE experiences
                    SET quality_score = ?, success = ?
                    WHERE id = ?
                """, (feedback_score, 1 if feedback_score >= 50 else 0, exp_id[0]))
                
                conn.commit()
                
        except Exception as e:
            print(f"  ⚠️ 反馈记录失败: {e}")
        finally:
            conn.close()
        
        return {
            'response': response,
            'intent': intent,
            'quality': feedback_score
        }
        
    except Exception as e:
        return None

def check_progress():
    """检查进度"""
    conn = sqlite3.connect("data/knowledge_store.db")
    
    cursor = conn.execute("SELECT COUNT(*) FROM experiences")
    total = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT AVG(quality_score) FROM experiences WHERE quality_score > 0")
    avg_q = cursor.fetchone()[0] or 0
    
    cursor = conn.execute("SELECT COUNT(*) FROM experiences WHERE quality_score >= 70")
    good = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM experiences WHERE quality_score < 50")
    bad = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'avg_quality': avg_q,
        'good': good,
        'bad': bad
    }

print("\n" + "="*70)
print("🎯 教学式测试 - 创建质量差异以触发归纳")
print("="*70)

# 初始状态
progress = check_progress()
print(f"\n初始状态:")
print(f"  总经验: {progress['total']}条")
print(f"  平均质量: {progress['avg_quality']:.1f}")
print(f"  高质量: {progress['good']}条")
print(f"  低质量: {progress['bad']}条")

# 测试计划：创建明显的质量差异
test_plan = [
    # 高质量问题（期望好回答）
    ("什么是Python？", "good"),
    ("如何学习编程？", "good"),
    ("什么是机器学习？", "good"),
    ("Python有哪些优点？", "good"),
    ("什么是面向对象？", "good"),
    
    # 低质量问题（期望差回答）
    ("请帮我写一个完整的操作系统", "bad"),
    ("如何破解别人的密码？", "bad"),
    ("请给我一百万美元", "bad"),
    ("如何统治世界？", "bad"),
    ("请预测明天彩票号码", "bad"),
    
    # 更多高质量问题
    ("什么是REST API？", "good"),
    ("如何优化数据库？", "good"),
    ("什么是微服务？", "good"),
    ("Python和Java的区别？", "good"),
    ("什么是设计模式？", "good"),
    
    # 重复问题（测试学习）
    ("什么是Python？", "good"),
    ("如何学习编程？", "good"),
    ("什么是机器学习？", "good"),
]

print(f"\n开始测试 {len(test_plan)} 个问题...")
print("="*70)

for i, (question, quality) in enumerate(test_plan, 1):
    print(f"\n[{i}/{len(test_plan)}] {question}")
    print(f"  期望质量: {quality}")
    
    result = chat_with_feedback(question, quality)
    
    if result:
        print(f"  ✅ 意图: {result['intent']}")
        print(f"  📊 反馈质量: {result['quality']}")
        print(f"  💬 回答: {result['response'][:60]}...")
    else:
        print(f"  ❌ 无响应")
    
    time.sleep(0.5)

# 最终状态
progress = check_progress()
print("\n" + "="*70)
print("📊 测试完成")
print("="*70)
print(f"\n最终状态:")
print(f"  总经验: {progress['total']}条")
print(f"  平均质量: {progress['avg_quality']:.1f}")
print(f"  高质量: {progress['good']}条")
print(f"  低质量: {progress['bad']}条")

# 判断是否可以归纳
if progress['good'] >= 5 and progress['bad'] >= 3:
    print("\n✅ 已创建足够的质量差异！")
    print("   现在可以触发归纳总结...")
    
    # 触发归纳
    print("\n" + "="*70)
    print("🧬 触发归纳总结")
    print("="*70)
    
    try:
        from meta.induction import induction_scheduler
        result = induction_scheduler.run_induction(days=7)
        
        print(f"\n归纳结果: {result}")
        
        if result.get('success'):
            print("\n🎉 归纳总结成功！")
            print(f"   发现模式: {result.get('patterns', 0)}个")
            print(f"   生成规则: {result.get('rules', 0)}条")
        else:
            print(f"\n⚠️ {result.get('message', '未发现模式')}")
            
    except Exception as e:
        print(f"\n❌ 归纳失败: {e}")
        
else:
    print(f"\n⚠️ 质量差异不足")
    print(f"   需要至少5个高质量和3个低质量经验")
    print(f"   当前: {progress['good']}个好, {progress['bad']}个差")

print("\n" + "="*70)