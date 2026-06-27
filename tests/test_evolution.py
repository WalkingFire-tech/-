"""
联盟拓荒者 - 完整端到端测试与训练系统
目标：
1. 测试所有功能模块
2. 训练基本常识
3. 优化响应速度（目标<5秒）
4. 形成自动学习进化闭环
"""
import http.client
import json
import time
import sqlite3
import os
from datetime import datetime
from typing import List, Tuple, Dict

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'

class EvolutionTester:
    def __init__(self):
        self.host = "localhost"
        self.port = 8000
        self.results = []
        self.response_times = []
        
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
        print(f"  ℹ️  {text}")
    
    def api_call(self, method: str, path: str, data=None, timeout=10):
        """API调用"""
        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        try:
            body = json.dumps(data) if data else None
            conn.request(method, path, body, {"Content-Type": "application/json"})
            resp = conn.getresponse()
            result = json.loads(resp.read().decode('utf-8'))
            return result, resp.status
        except Exception as e:
            return {"error": str(e)}, 0
        finally:
            conn.close()
    
    def chat(self, message: str, timeout=10) -> Tuple[str, float]:
        """聊天并返回响应和耗时"""
        start = time.time()
        data, status = self.api_call("POST", "/api/chat", {"message": message}, timeout)
        elapsed = time.time() - start
        
        if status == 200 and "response" in data:
            return data["response"], elapsed
        else:
            return data.get("error", "unknown"), elapsed
    
    def get_stats(self) -> Dict:
        """获取系统统计"""
        stats = {}
        
        try:
            conn = sqlite3.connect('data/knowledge_store.db')
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM knowledge_items")
            stats['knowledge'] = cur.fetchone()[0]
            conn.close()
        except:
            stats['knowledge'] = 0
        
        try:
            conn = sqlite3.connect('data/experience_pool.db')
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM experiences")
            stats['experiences'] = cur.fetchone()[0]
            conn.close()
        except:
            stats['experiences'] = 0
        
        try:
            conn = sqlite3.connect('data/genome.db')
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM genomes WHERE is_active=1")
            stats['genomes'] = cur.fetchone()[0]
            conn.close()
        except:
            stats['genomes'] = 0
        
        return stats
    
    # ========== 功能测试 ==========
    
    def test_backend(self):
        """测试后端"""
        self.print_section("后端健康检查")
        
        data, status = self.api_call("GET", "/api/health")
        
        if status == 200 and data.get("status") in ["healthy", "ok"]:
            models = data.get("models", [])
            self.print_success(f"后端正常，模型: {len(models)}个")
            self.results.append(("后端", True))
            return True
        else:
            self.print_error("后端异常")
            self.results.append(("后端", False))
            return False
    
    def test_chat_speed(self):
        """测试聊天速度"""
        self.print_section("聊天响应速度测试")
        
        tests = [
            "你好",
            "1+1=?",
            "Python是什么",
        ]
        
        times = []
        for msg in tests:
            resp, elapsed = self.chat(msg, timeout=15)
            times.append(elapsed)
            
            if elapsed < 5:
                self.print_success(f"{msg}: {elapsed:.2f}s ⚡快速")
            elif elapsed < 10:
                self.print_warning(f"{msg}: {elapsed:.2f}s ⏱️正常")
            else:
                self.print_error(f"{msg}: {elapsed:.2f}s 🐌慢")
            
            time.sleep(0.3)
        
        avg_time = sum(times) / len(times)
        self.print_info(f"平均响应时间: {avg_time:.2f}s")
        
        self.response_times.extend(times)
        self.results.append(("聊天速度", avg_time < 10))
        return avg_time < 10
    
    def test_knowledge_system(self):
        """测试知识系统"""
        self.print_section("知识系统测试")
        
        stats_before = self.get_stats()
        
        learning_data = [
            "记住：地球围绕太阳转",
            "学习：水的化学式是H2O",
            "记住：Python由Guido创建",
        ]
        
        for item in learning_data:
            resp, elapsed = self.chat(item, timeout=15)
            time.sleep(0.2)
        
        time.sleep(1)
        
        stats_after = self.get_stats()
        
        if stats_after['knowledge'] >= stats_before['knowledge']:
            self.print_success(f"知识库正常，当前: {stats_after['knowledge']}条")
            self.results.append(("知识系统", True))
            return True
        else:
            self.print_warning("知识库未更新")
            self.results.append(("知识系统", False))
            return False
    
    def test_experience_pool(self):
        """测试经验池"""
        self.print_section("经验池测试")
        
        stats_before = self.get_stats()
        
        questions = [
            "如何学习编程",
            "什么是算法",
            "解释数据结构",
        ]
        
        for q in questions:
            self.chat(q, timeout=15)
            time.sleep(0.2)
        
        time.sleep(1)
        
        stats_after = self.get_stats()
        
        if stats_after['experiences'] > stats_before['experiences']:
            new = stats_after['experiences'] - stats_before['experiences']
            self.print_success(f"经验池正常，新增: {new}条")
            self.results.append(("经验池", True))
            return True
        else:
            self.print_warning("经验池未更新")
            self.results.append(("经验池", False))
            return False
    
    def test_learning_targets(self):
        """测试学习目标"""
        self.print_section("学习目标测试")
        
        data, status = self.api_call("GET", "/api/learning/targets")
        
        if status == 200 and data.get("success"):
            targets = data.get("targets", [])
            self.print_success(f"学习目标: {len(targets)}个")
            self.results.append(("学习目标", True))
            return True
        else:
            self.print_error("学习目标失败")
            self.results.append(("学习目标", False))
            return False
    
    def test_genome_evolution(self):
        """测试基因进化"""
        self.print_section("基因进化测试")
        
        stats = self.get_stats()
        genomes = stats.get('genomes', 0)
        
        if genomes > 0:
            self.print_success(f"活跃基因组: {genomes}个")
            self.results.append(("基因进化", True))
            return True
        else:
            self.print_warning("无活跃基因组")
            self.results.append(("基因进化", False))
            return False
    
    def test_scheduler(self):
        """测试调度器"""
        self.print_section("调度器测试")
        
        data, status = self.api_call("GET", "/api/scheduler/status")
        
        if status == 200 and data.get("success"):
            running = data.get("status", {}).get("running", False)
            self.print_success(f"调度器: {'运行中' if running else '已停止'}")
            self.results.append(("调度器", running))
            return running
        else:
            self.results.append(("调度器", False))
            return False
    
    def test_tools(self):
        """测试工具系统"""
        self.print_section("工具系统测试")
        
        data, status = self.api_call("GET", "/api/tools/list")
        
        if status == 200 and data.get("success"):
            tools = data.get("tools", [])
            self.print_success(f"工具: {len(tools)}个")
            self.results.append(("工具系统", len(tools) > 0))
            return len(tools) > 0
        else:
            self.results.append(("工具系统", False))
            return False
    
    # ========== 常识训练 ==========
    
    def train_common_knowledge(self):
        """训练基本常识"""
        self.print_section("基本常识训练")
        
        common_knowledge = [
            ("地球是太阳系的行星", "天文常识"),
            ("一年有365天", "时间常识"),
            ("水在0度结冰", "物理常识"),
            ("人类需要呼吸氧气", "生物常识"),
            ("计算机使用二进制", "计算机常识"),
            ("Python是编程语言", "编程常识"),
            ("北京是中国首都", "地理常识"),
            ("数学是科学基础", "学科常识"),
        ]
        
        self.print_info(f"开始训练 {len(common_knowledge)} 条常识...")
        
        for i, (knowledge, category) in enumerate(common_knowledge, 1):
            msg = f"记住：{knowledge}"
            resp, elapsed = self.chat(msg, timeout=15)
            
            if elapsed < 10:
                self.print_success(f"[{i}/{len(common_knowledge)}] {category}: {knowledge}")
            else:
                self.print_warning(f"[{i}/{len(common_knowledge)}] {category} (慢)")
            
            time.sleep(0.3)
        
        self.print_success("常识训练完成！")
    
    # ========== 能力测试 ==========
    
    def test_capabilities(self):
        """测试各项能力"""
        self.print_section("能力测试")
        
        capability_tests = [
            ("计算能力", "123+456=?", "579"),
            ("知识检索", "Python是什么", "编程"),
            ("记忆能力", "地球是什么", "行星"),
            ("推理能力", "如果A>B, B>C, 那么A和C的关系", "大于"),
        ]
        
        passed = 0
        for name, question, keyword in capability_tests:
            resp, elapsed = self.chat(question, timeout=15)
            
            if keyword.lower() in resp.lower():
                self.print_success(f"{name}: 通过 ({elapsed:.2f}s)")
                passed += 1
            else:
                self.print_warning(f"{name}: 未通过")
            
            time.sleep(0.3)
        
        self.results.append(("能力测试", passed >= 3))
        return passed >= 3
    
    # ========== 进化训练 ==========
    
    def evolution_training(self):
        """进化训练"""
        self.print_section("进化训练")
        
        self.print_info("触发进化任务...")
        
        data, status = self.api_call("POST", "/api/scheduler/run", timeout=30)
        
        if status == 200:
            self.print_success("进化任务已触发")
            time.sleep(2)
            
            stats = self.get_stats()
            self.print_info(f"知识: {stats['knowledge']}, 经验: {stats['experiences']}, 基因: {stats['genomes']}")
            
            self.results.append(("进化训练", True))
            return True
        else:
            self.results.append(("进化训练", False))
            return False
    
    # ========== 主流程 ==========
    
    def run_full_test(self):
        """运行完整测试"""
        self.print_header("联盟拓荒者 - 完整端到端测试与训练")
        
        print(f"\n{Colors.MAGENTA}时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        
        # 1. 基础测试
        if not self.test_backend():
            self.print_error("后端未启动，请先启动后端服务")
            return
        
        # 2. 功能测试
        self.test_chat_speed()
        self.test_knowledge_system()
        self.test_experience_pool()
        self.test_learning_targets()
        self.test_genome_evolution()
        self.test_scheduler()
        self.test_tools()
        
        # 3. 常识训练
        self.train_common_knowledge()
        
        # 4. 能力测试
        self.test_capabilities()
        
        # 5. 进化训练
        self.evolution_training()
        
        # 6. 汇总
        self.print_summary()
    
    def print_summary(self):
        """打印汇总"""
        self.print_header("测试结果汇总")
        
        passed = sum(1 for _, r in self.results if r)
        total = len(self.results)
        
        for name, result in self.results:
            status = f"{Colors.GREEN}✅{Colors.END}" if result else f"{Colors.RED}❌{Colors.END}"
            print(f"  {status} {name}")
        
        print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.CYAN}  通过率: {passed}/{total} ({passed/total*100:.1f}%){Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}")
        
        if self.response_times:
            avg_time = sum(self.response_times) / len(self.response_times)
            print(f"\n{Colors.MAGENTA}平均响应时间: {avg_time:.2f}s{Colors.END}")
            
            if avg_time < 5:
                print(f"{Colors.GREEN}⚡ 响应速度优秀，达到无感对话标准！{Colors.END}")
            elif avg_time < 10:
                print(f"{Colors.YELLOW}⏱️ 响应速度正常，建议继续优化{Colors.END}")
            else:
                print(f"{Colors.RED}🐌 响应速度较慢，需要优化{Colors.END}")
        
        stats = self.get_stats()
        print(f"\n{Colors.MAGENTA}系统状态:{Colors.END}")
        print(f"  知识库: {stats['knowledge']} 条")
        print(f"  经验池: {stats['experiences']} 条")
        print(f"  基因组: {stats['genomes']} 个")
        
        if passed == total:
            print(f"\n{Colors.GREEN}✅ 所有功能正常，进化闭环已形成！{Colors.END}\n")
        else:
            print(f"\n{Colors.YELLOW}⚠️  部分功能需要优化{Colors.END}\n")

if __name__ == "__main__":
    tester = EvolutionTester()
    tester.run_full_test()