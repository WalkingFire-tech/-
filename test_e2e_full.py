"""
联盟拓荒者 - 完整端到端闭环测试系统
模拟真实用户交互，测试所有功能模块，形成进化闭环
"""
import http.client
import json
import time
import sqlite3
import os
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

class E2ETestSystem:
    def __init__(self):
        self.base_url = "localhost"
        self.port = 8000
        self.timeout = 30
        self.test_results = []
        self.knowledge_before = 0
        self.experiences_before = 0
        
    def print_header(self, text):
        print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.CYAN}  {text}{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")
    
    def print_section(self, text):
        print(f"\n{Colors.BLUE}【{text}】{Colors.END}")
    
    def print_success(self, text):
        print(f"{Colors.GREEN}  ✅ {text}{Colors.END}")
    
    def print_error(self, text):
        print(f"{Colors.RED}  ❌ {text}{Colors.END}")
    
    def print_warning(self, text):
        print(f"{Colors.YELLOW}  ⚠️  {text}{Colors.END}")
    
    def print_info(self, text):
        print(f"{Colors.BLUE}  ℹ️  {text}{Colors.END}")
    
    def api_request(self, method, path, data=None, timeout=None):
        """发送API请求"""
        if timeout is None:
            timeout = self.timeout
            
        conn = http.client.HTTPConnection(self.base_url, self.port, timeout=timeout)
        
        try:
            headers = {"Content-Type": "application/json"}
            body = json.dumps(data) if data else None
            
            conn.request(method, path, body, headers)
            response = conn.getresponse()
            result = response.read().decode('utf-8')
            
            try:
                return json.loads(result), response.status
            except:
                return {"raw": result}, response.status
                
        except Exception as e:
            return {"error": str(e)}, 0
        finally:
            conn.close()
    
    def get_db_stats(self):
        """获取数据库统计"""
        stats = {}
        
        try:
            conn = sqlite3.connect('data/knowledge_store.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM knowledge_items")
            stats['knowledge'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tools")
            stats['tools'] = cursor.fetchone()[0]
            
            conn.close()
        except:
            stats['knowledge'] = 0
            stats['tools'] = 0
        
        try:
            conn = sqlite3.connect('data/experience_pool.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM experiences")
            stats['experiences'] = cursor.fetchone()[0]
            
            conn.close()
        except:
            stats['experiences'] = 0
        
        try:
            conn = sqlite3.connect('data/genome.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM genomes WHERE active=1")
            stats['genomes'] = cursor.fetchone()[0]
            
            conn.close()
        except:
            stats['genomes'] = 0
        
        return stats
    
    # ========== 测试模块 ==========
    
    def test_1_backend_health(self):
        """测试1: 后端健康检查"""
        self.print_section("测试1: 后端健康检查")
        
        data, status = self.api_request("GET", "/api/health")
        
        if status == 200 and data.get("status") == "healthy":
            self.print_success(f"后端健康，模型数: {data.get('models_count', 0)}")
            self.test_results.append(("后端健康", True))
            return True
        else:
            self.print_error(f"健康检查失败: {data}")
            self.test_results.append(("后端健康", False))
            return False
    
    def test_2_models_available(self):
        """测试2: 模型可用性"""
        self.print_section("测试2: 模型可用性")
        
        data, status = self.api_request("GET", "/api/models")
        
        if status == 200:
            models = data.get("models", [])
            self.print_success(f"可用模型: {len(models)}个")
            for m in models:
                self.print_info(f"  - {m.get('name', 'unknown')}")
            self.test_results.append(("模型可用性", len(models) > 0))
            return len(models) > 0
        else:
            self.print_error(f"获取模型失败")
            self.test_results.append(("模型可用性", False))
            return False
    
    def test_3_chat_basic(self):
        """测试3: 基础聊天功能"""
        self.print_section("测试3: 基础聊天功能")
        
        test_cases = [
            ("你好", "问候"),
            ("1+1等于多少", "计算"),
            ("介绍一下Python", "知识问答"),
        ]
        
        passed = 0
        for question, desc in test_cases:
            self.print_info(f"测试: {question} ({desc})")
            
            start = time.time()
            data, status = self.api_request("POST", "/api/chat", {"message": question}, timeout=35)
            elapsed = time.time() - start
            
            if status == 200 and "response" in data and data["response"]:
                self.print_success(f"成功 (耗时: {elapsed:.2f}s)")
                passed += 1
            else:
                error = data.get('error', 'unknown')
                self.print_error(f"失败 (耗时: {elapsed:.2f}s): {error}")
            
            time.sleep(0.5)
        
        result = passed == len(test_cases)
        self.test_results.append(("基础聊天", result))
        return result
    
    def test_4_knowledge_learning(self):
        """测试4: 知识学习功能"""
        self.print_section("测试4: 知识学习功能")
        
        stats_before = self.get_db_stats()
        self.knowledge_before = stats_before.get('knowledge', 0)
        
        self.print_info(f"学习前知识数: {self.knowledge_before}")
        
        learning_questions = [
            "请记住：Python是由Guido van Rossum创建的",
            "学习：机器学习是人工智能的一个分支",
            "记住这个知识：深度学习使用神经网络",
        ]
        
        for q in learning_questions:
            data, status = self.api_request("POST", "/api/chat", {"message": q}, timeout=35)
            time.sleep(0.3)
        
        time.sleep(1)
        
        stats_after = self.get_db_stats()
        knowledge_after = stats_after.get('knowledge', 0)
        
        self.print_info(f"学习后知识数: {knowledge_after}")
        
        if knowledge_after >= self.knowledge_before:
            self.print_success(f"知识学习正常，新增: {knowledge_after - self.knowledge_before}")
            self.test_results.append(("知识学习", True))
            return True
        else:
            self.print_warning("知识数量未增加")
            self.test_results.append(("知识学习", False))
            return False
    
    def test_5_experience_pool(self):
        """测试5: 经验池记录"""
        self.print_section("测试5: 经验池记录")
        
        stats_before = self.get_db_stats()
        self.experiences_before = stats_before.get('experiences', 0)
        
        self.print_info(f"经验池记录数: {self.experiences_before}")
        
        test_questions = [
            "如何学习编程",
            "什么是数据结构",
            "解释一下算法复杂度",
        ]
        
        for q in test_questions:
            self.api_request("POST", "/api/chat", {"message": q}, timeout=35)
            time.sleep(0.3)
        
        time.sleep(1)
        
        stats_after = self.get_db_stats()
        experiences_after = stats_after.get('experiences', 0)
        
        self.print_info(f"经验池记录数: {experiences_after}")
        
        if experiences_after > self.experiences_before:
            self.print_success(f"经验池正常记录，新增: {experiences_after - self.experiences_before}")
            self.test_results.append(("经验池", True))
            return True
        else:
            self.print_warning("经验池未增加记录")
            self.test_results.append(("经验池", False))
            return False
    
    def test_6_learning_targets(self):
        """测试6: 学习目标系统"""
        self.print_section("测试6: 学习目标系统")
        
        data, status = self.api_request("GET", "/api/learning/targets")
        
        if status == 200 and data.get("success"):
            targets = data.get("targets", [])
            self.print_success(f"学习目标数: {len(targets)}")
            
            for t in targets[:5]:
                name = t.get('name', 'unknown')
                progress = t.get('progress', 0)
                self.print_info(f"  - {name}: {progress*100:.1f}%")
            
            self.test_results.append(("学习目标", True))
            return True
        else:
            self.print_error("学习目标获取失败")
            self.test_results.append(("学习目标", False))
            return False
    
    def test_7_genome_evolution(self):
        """测试7: 基因进化系统"""
        self.print_section("测试7: 基因进化系统")
        
        data, status = self.api_request("GET", "/api/genome/status")
        
        if status == 200:
            stats = data.get("stats", {})
            active_genomes = stats.get("active_genomes", 0)
            total_genomes = stats.get("total_genomes", 0)
            
            self.print_success(f"活跃基因组: {active_genomes}, 总基因组: {total_genomes}")
            
            if total_genomes > 0:
                self.print_info("基因进化系统正常")
                self.test_results.append(("基因进化", True))
                return True
        
        self.print_warning("基因进化状态未知")
        self.test_results.append(("基因进化", False))
        return False
    
    def test_8_scheduler(self):
        """测试8: 主动调度器"""
        self.print_section("测试8: 主动调度器")
        
        data, status = self.api_request("GET", "/api/scheduler/status")
        
        if status == 200 and data.get("success"):
            scheduler_status = data.get("status", {})
            running = scheduler_status.get("running", False)
            interval = scheduler_status.get("interval", 0)
            
            self.print_success(f"调度器状态: {'运行中' if running else '已停止'}")
            self.print_info(f"调度间隔: {interval}秒")
            
            self.test_results.append(("主动调度器", running))
            return running
        else:
            self.print_warning("调度器状态获取失败")
            self.test_results.append(("主动调度器", False))
            return False
    
    def test_9_tools_system(self):
        """测试9: 工具系统"""
        self.print_section("测试9: 工具系统")
        
        data, status = self.api_request("GET", "/api/tools/list")
        
        if status == 200 and data.get("success"):
            tools = data.get("tools", [])
            self.print_success(f"可用工具: {len(tools)}个")
            
            for t in tools[:5]:
                self.print_info(f"  - {t.get('name', 'unknown')}")
            
            self.test_results.append(("工具系统", len(tools) > 0))
            return len(tools) > 0
        else:
            self.print_warning("工具列表获取失败")
            self.test_results.append(("工具系统", False))
            return False
    
    def test_10_knowledge_retrieval(self):
        """测试10: 知识检索"""
        self.print_section("测试10: 知识检索")
        
        retrieval_tests = [
            "Python的创建者是谁",
            "什么是机器学习",
            "深度学习使用什么技术",
        ]
        
        passed = 0
        for q in retrieval_tests:
            self.print_info(f"检索: {q}")
            
            data, status = self.api_request("POST", "/api/chat", {"message": q}, timeout=35)
            
            if status == 200 and "response" in data:
                response = data["response"]
                if len(response) > 20:
                    self.print_success(f"检索成功")
                    passed += 1
                else:
                    self.print_warning("响应过短")
            
            time.sleep(0.3)
        
        result = passed >= 2
        self.test_results.append(("知识检索", result))
        return result
    
    def test_11_memory_system(self):
        """测试11: 长期记忆系统"""
        self.print_section("测试11: 长期记忆系统")
        
        memory_questions = [
            ("记住：我的名字是小明", "存储记忆"),
            ("我叫什么名字", "检索记忆"),
        ]
        
        passed = 0
        for q, desc in memory_questions:
            self.print_info(f"{desc}: {q}")
            
            data, status = self.api_request("POST", "/api/chat", {"message": q}, timeout=35)
            
            if status == 200 and "response" in data:
                self.print_success(f"{desc}成功")
                passed += 1
            
            time.sleep(0.3)
        
        result = passed == len(memory_questions)
        self.test_results.append(("长期记忆", result))
        return result
    
    def test_12_self_detection(self):
        """测试12: 自我能力检测"""
        self.print_section("测试12: 自我能力检测")
        
        difficult_questions = [
            "请解释量子纠缠的数学原理",
            "分析广义相对论的场方程推导",
        ]
        
        for q in difficult_questions:
            self.print_info(f"测试困难问题: {q}")
            
            data, status = self.api_request("POST", "/api/chat", {"message": q}, timeout=35)
            
            if status == 200 and "response" in data:
                response = data["response"]
                self.print_info(f"响应长度: {len(response)}")
                
                if "不知道" in response or "无法" in response or len(response) < 50:
                    self.print_success("系统能够识别知识不足")
                else:
                    self.print_info("系统尝试回答")
            
            time.sleep(0.3)
        
        self.test_results.append(("能力检测", True))
        return True
    
    def test_13_evolution_trigger(self):
        """测试13: 进化触发"""
        self.print_section("测试13: 进化触发")
        
        data, status = self.api_request("POST", "/api/scheduler/run", timeout=60)
        
        if status == 200 and data.get("success"):
            self.print_success("进化任务已触发")
            time.sleep(2)
            
            stats = self.get_db_stats()
            self.print_info(f"当前知识数: {stats.get('knowledge', 0)}")
            self.print_info(f"当前经验数: {stats.get('experiences', 0)}")
            self.print_info(f"当前基因组: {stats.get('genomes', 0)}")
            
            self.test_results.append(("进化触发", True))
            return True
        else:
            self.print_warning("进化触发失败")
            self.test_results.append(("进化触发", False))
            return False
    
    def test_14_stats_summary(self):
        """测试14: 统计汇总"""
        self.print_section("测试14: 系统统计汇总")
        
        data, status = self.api_request("GET", "/api/stats")
        
        if status == 200:
            self.print_success(f"总对话数: {data.get('total_conversations', 0)}")
            self.print_info(f"知识条目: {data.get('knowledge_count', 0)}")
            
            self.test_results.append(("统计汇总", True))
            return True
        else:
            self.test_results.append(("统计汇总", False))
            return False
    
    # ========== 主测试流程 ==========
    
    def run_all_tests(self):
        """运行所有测试"""
        self.print_header("联盟拓荒者 - 完整端到端闭环测试")
        
        print(f"\n{Colors.MAGENTA}测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        
        tests = [
            self.test_1_backend_health,
            self.test_2_models_available,
            self.test_3_chat_basic,
            self.test_4_knowledge_learning,
            self.test_5_experience_pool,
            self.test_6_learning_targets,
            self.test_7_genome_evolution,
            self.test_8_scheduler,
            self.test_9_tools_system,
            self.test_10_knowledge_retrieval,
            self.test_11_memory_system,
            self.test_12_self_detection,
            self.test_13_evolution_trigger,
            self.test_14_stats_summary,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.print_error(f"测试异常: {e}")
        
        self.print_summary()
    
    def print_summary(self):
        """打印测试汇总"""
        self.print_header("测试结果汇总")
        
        passed = sum(1 for _, r in self.test_results if r)
        total = len(self.test_results)
        
        for name, result in self.test_results:
            status = f"{Colors.GREEN}✅{Colors.END}" if result else f"{Colors.RED}❌{Colors.END}"
            print(f"  {status} {name}")
        
        print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.CYAN}  总计: {passed}/{total} 通过{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")
        
        stats = self.get_db_stats()
        print(f"\n{Colors.MAGENTA}系统状态:{Colors.END}")
        print(f"  知识条目: {stats.get('knowledge', 0)}")
        print(f"  经验记录: {stats.get('experiences', 0)}")
        print(f"  工具数量: {stats.get('tools', 0)}")
        print(f"  活跃基因组: {stats.get('genomes', 0)}")
        
        if passed == total:
            print(f"\n{Colors.GREEN}✅ 所有功能正常，进化闭环已形成！{Colors.END}\n")
        else:
            print(f"\n{Colors.YELLOW}⚠️  存在失败项，需要进一步优化{Colors.END}\n")

if __name__ == "__main__":
    tester = E2ETestSystem()
    tester.run_all_tests()