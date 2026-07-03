"""
端到端教学式测试 - 让系统自动学习和进化
目标：通过大量对话积累经验，触发归纳总结成功
"""
import requests
import time
import json
import sqlite3
from datetime import datetime

BASE_URL = "http://localhost:8000"

class EvolutionTest:
    def __init__(self):
        self.test_count = 0
        self.success_count = 0
        self.learning_events = []
        
    def chat(self, message: str) -> dict:
        """发送消息"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/chat",
                json={"message": message},
                timeout=120
            )
            return response.json() if response.status_code == 200 else {}
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return {}
    
    def check_stats(self) -> dict:
        """检查系统统计"""
        try:
            # 知识库
            conn = sqlite3.connect("data/knowledge_store.db")
            
            cursor = conn.execute("SELECT COUNT(*) FROM knowledge_items")
            knowledge_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM experiences")
            experience_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM learning_rules")
            rules_count = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT intent_type, COUNT(*) as cnt, AVG(quality_score) as avg_q
                FROM experiences
                GROUP BY intent_type
                ORDER BY cnt DESC
            """)
            intent_stats = cursor.fetchall()
            
            conn.close()
            
            return {
                "knowledge": knowledge_count,
                "experience": experience_count,
                "rules": rules_count,
                "intents": intent_stats
            }
        except Exception as e:
            return {"error": str(e)}
    
    def print_stats(self):
        """打印统计"""
        stats = self.check_stats()
        
        print("\n" + "="*60)
        print("📊 系统状态")
        print("="*60)
        print(f"知识库: {stats.get('knowledge', 0)}条")
        print(f"经验池: {stats.get('experience', 0)}条")
        print(f"学习规则: {stats.get('rules', 0)}条")
        
        if stats.get('intents'):
            print("\n意图分布:")
            for intent, count, avg_q in stats['intents'][:5]:
                print(f"  {intent}: {count}次, 平均质量: {avg_q:.1f}")
        
        print("="*60)
    
    def run_test_round(self, category: str, questions: list):
        """运行一轮测试"""
        print(f"\n{'='*60}")
        print(f"📚 测试类别: {category}")
        print(f"{'='*60}")
        
        for i, question in enumerate(questions, 1):
            self.test_count += 1
            
            print(f"\n[{i}/{len(questions)}] 用户: {question}")
            
            start = time.time()
            result = self.chat(question)
            duration = time.time() - start
            
            response = result.get('response', '')
            model = result.get('model_used', 'unknown')
            intent = result.get('intent', 'unknown')
            
            if response:
                self.success_count += 1
                print(f"✅ 响应 ({duration:.1f}s)")
                print(f"   意图: {intent}, 模型: {model}")
                print(f"   回答: {response[:100]}...")
            else:
                print(f"❌ 无响应")
            
            time.sleep(0.5)  # 避免过快
    
    def run_evolution_cycle(self):
        """运行进化周期"""
        print("\n" + "="*70)
        print("🧬 开始端到端进化测试")
        print("="*70)
        
        # 初始状态
        print("\n【初始状态】")
        self.print_stats()
        
        # 第1轮：基础知识问题
        self.run_test_round("基础知识", [
            "什么是人工智能？",
            "机器学习和深度学习有什么区别？",
            "什么是神经网络？",
            "Python有哪些优点？",
            "什么是面向对象编程？",
        ])
        
        # 第2轮：技术问题
        self.run_test_round("技术问题", [
            "如何实现一个单例模式？",
            "什么是RESTful API？",
            "如何优化数据库查询？",
            "什么是微服务架构？",
            "如何处理并发问题？",
        ])
        
        # 第3轮：实际问题
        self.run_test_round("实际问题", [
            "我的代码运行很慢，如何优化？",
            "如何防止SQL注入攻击？",
            "怎样设计一个用户认证系统？",
            "如何处理大数据量的分页？",
            "什么是设计模式中的工厂模式？",
        ])
        
        # 第4轮：重复问题（测试学习效果）
        self.run_test_round("重复问题（测试学习）", [
            "什么是人工智能？",  # 重复
            "如何实现一个单例模式？",  # 重复
            "Python有哪些优点？",  # 重复
        ])
        
        # 第5轮：变体问题（测试泛化）
        self.run_test_round("变体问题（测试泛化）", [
            "AI是什么意思？",
            "单例模式怎么实现？",
            "Python语言的特点是什么？",
            "深度学习和机器学习哪个更先进？",
            "如何提高代码性能？",
        ])
        
        # 第6轮：复杂问题
        self.run_test_round("复杂问题", [
            "请解释一下分布式系统的CAP定理",
            "如何设计一个高可用的系统架构？",
            "什么是领域驱动设计（DDD）？",
            "如何实现数据的最终一致性？",
            "微服务和SOA有什么区别？",
        ])
        
        # 第7轮：对话式问题
        self.run_test_round("对话式问题", [
            "你好",
            "谢谢你的回答",
            "能详细解释一下吗？",
            "还有其他方法吗？",
            "这个方案有什么优缺点？",
        ])
        
        # 最终状态
        print("\n【最终状态】")
        self.print_stats()
        
        # 测试总结
        print("\n" + "="*70)
        print("📊 测试总结")
        print("="*70)
        print(f"总测试数: {self.test_count}")
        print(f"成功响应: {self.success_count}")
        print(f"成功率: {self.success_count/self.test_count*100:.1f}%")
        
        # 检查学习效果
        stats = self.check_stats()
        print(f"\n学习成果:")
        print(f"  知识增长: {stats.get('knowledge', 0)}条")
        print(f"  经验积累: {stats.get('experience', 0)}条")
        print(f"  规则生成: {stats.get('rules', 0)}条")
        
        # 判断是否达到进化目标
        if stats.get('experience', 0) >= 50:
            print("\n✅ 已积累足够经验，触发归纳总结...")
            self.trigger_induction()
        
        print("="*70)
    
    def trigger_induction(self):
        """触发归纳总结"""
        try:
            # 通过特殊问题触发归纳
            result = self.chat("系统状态报告")
            print("\n" + "="*60)
            print("📊 归纳总结结果")
            print("="*60)
            
            # 检查学习规则
            conn = sqlite3.connect("data/knowledge_store.db")
            cursor = conn.execute("""
                SELECT trigger_pattern, action, confidence, source
                FROM learning_rules
                ORDER BY confidence DESC
                LIMIT 10
            """)
            rules = cursor.fetchall()
            
            if rules:
                print(f"\n✅ 发现 {len(rules)} 条学习规则:")
                for i, (pattern, action, conf, source) in enumerate(rules, 1):
                    print(f"\n规则{i}:")
                    print(f"  触发: {pattern[:60]}...")
                    print(f"  动作: {action[:60]}...")
                    print(f"  置信度: {conf:.2f}")
                    print(f"  来源: {source}")
            else:
                print("\n⚠️ 暂未发现显著模式")
                print("建议: 继续积累更多经验数据")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ 归纳总结失败: {e}")


if __name__ == "__main__":
    tester = EvolutionTest()
    tester.run_evolution_cycle()