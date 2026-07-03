"""
联盟拓荒者端到端全方位测试套件
测试所有核心功能，确保系统稳定运行
"""
import asyncio
import sys
import time
import json
from typing import Dict, Any, List
from loguru import logger

sys.path.insert(0, ".")


class ComprehensiveTestSuite:
    """全方位测试套件"""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        
    def record_test(self, category: str, name: str, success: bool, 
                    message: str = "", details: Any = None):
        """记录测试结果"""
        result = {
            "category": category,
            "name": name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": time.time()
        }
        self.test_results.append(result)
        
        if success:
            self.passed += 1
            print(f"  ✅ {name}: {message}")
        else:
            self.failed += 1
            print(f"  ❌ {name}: {message}")
        
        if details:
            logger.debug(f"测试详情: {details}")
    
    # ========== 1. 精神内核测试 ==========
    def test_spirit_core(self):
        """测试精神内核"""
        print("\n" + "=" * 60)
        print("测试类别1：精神内核")
        print("=" * 60)
        
        try:
            from core.spirit_core import SpiritCore, spirit_core
            
            # 测试1.1：精神内核加载
            self.record_test(
                "精神内核", "加载精神内核", True,
                "SpiritCore类和全局实例加载成功"
            )
            
            # 测试1.2：核心原则定义
            status = spirit_core.get_spirit_status()
            self.record_test(
                "精神内核", "核心原则定义", 
                len(status['core_principles']) == 5,
                f"定义了{len(status['core_principles'])}条核心原则"
            )
            
            # 测试1.3：能力定义
            self.record_test(
                "精神内核", "能力定义",
                len(status['abilities']) == 10,
                f"定义了{len(status['abilities'])}种能力"
            )
            
            # 测试1.4：回复验证 - 好的回复
            good_response = "关于这个问题，我尝试了多种方法，并给出以下建议：1. 查阅资料 2. 分解问题"
            validation = spirit_core.validate_response(good_response)
            self.record_test(
                "精神内核", "验证好的回复",
                validation['valid'],
                "好的回复验证通过"
            )
            
            # 测试1.5：回复验证 - 敷衍回复
            bad_response = "我不知道"
            validation = spirit_core.validate_response(bad_response)
            self.record_test(
                "精神内核", "拒绝敷衍回复",
                not validation['valid'],
                f"敷衍回复被正确拒绝: {validation['issues'][0] if validation['issues'] else ''}"
            )
            
            # 测试1.6：有意义回复生成
            question = "测试问题"
            attempts = [
                {"method": "方法1", "success": False, "error": "错误1"},
                {"method": "方法2", "success": False, "error": "错误2"}
            ]
            response = spirit_core.ensure_meaningful_response(question, attempts)
            self.record_test(
                "精神内核", "生成有意义回复",
                len(response) > 50 and "建议" in response,
                f"生成了{len(response)}字的有意义回复"
            )
            
        except Exception as e:
            self.record_test("精神内核", "精神内核测试", False, f"异常: {str(e)}")
    
    # ========== 2. 永不放弃引擎测试 ==========
    async def test_never_give_up_engine(self):
        """测试永不放弃引擎"""
        print("\n" + "=" * 60)
        print("测试类别2：永不放弃引擎")
        print("=" * 60)
        
        try:
            from core.never_give_up import NeverGiveUpEngine
            
            # 测试2.1：引擎初始化
            engine = NeverGiveUpEngine()
            self.record_test(
                "永不放弃引擎", "引擎初始化", True,
                "NeverGiveUpEngine初始化成功"
            )
            
            # 测试2.2：简单问题解决
            result = await engine.solve("你好", {})
            self.record_test(
                "永不放弃引擎", "解决简单问题",
                result.get('answer') is not None,
                f"生成了答案，置信度: {result.get('confidence', 0):.0%}"
            )
            
            # 测试2.3：复杂问题解决
            result = await engine.solve("认知的概念是什么", {})
            self.record_test(
                "永不放弃引擎", "解决复杂问题",
                result.get('answer') is not None and len(result.get('answer', '')) > 20,
                f"尝试了{len(result.get('attempts', []))}种方法"
            )
            
            # 测试2.4：失败回复有意义
            result = await engine.solve("这是一个不存在的问题xyz123", {})
            has_direction = "建议" in result.get('answer', '') or "方向" in result.get('answer', '')
            self.record_test(
                "永不放弃引擎", "失败回复有意义",
                has_direction,
                "失败回复包含处理方向"
            )
            
        except Exception as e:
            self.record_test("永不放弃引擎", "永不放弃引擎测试", False, f"异常: {str(e)}")
    
    # ========== 3. 聊天处理器测试 ==========
    async def test_chat_handler(self):
        """测试聊天处理器"""
        print("\n" + "=" * 60)
        print("测试类别3：聊天处理器")
        print("=" * 60)
        
        try:
            from backend.chat_handler import chat_never_giveup
            
            # 测试3.1：问候语处理
            result = await chat_never_giveup("你好", {})
            self.record_test(
                "聊天处理器", "问候语处理",
                "你好" in result.get('response', '') or "服务" in result.get('response', ''),
                f"回复长度: {len(result.get('response', ''))}字"
            )
            
            # 测试3.2：确认语处理
            result = await chat_never_giveup("好的", {})
            self.record_test(
                "聊天处理器", "确认语处理",
                "明白" in result.get('response', '') or "好的" in result.get('response', ''),
                "确认语正确响应"
            )
            
            # 测试3.3：概念问题
            result = await chat_never_giveup("认知的概念是什么", {})
            self.record_test(
                "聊天处理器", "概念问题处理",
                len(result.get('response', '')) > 20,
                f"尝试了{len(result.get('attempts', []))}种方法"
            )
            
            # 测试3.4：代码问题
            result = await chat_never_giveup("如何写一个排序算法", {})
            self.record_test(
                "聊天处理器", "代码问题处理",
                len(result.get('response', '')) > 20,
                f"回复包含{'代码' if '代码' in result.get('response', '') else '相关'}内容"
            )
            
            # 测试3.5：精神内核集成
            result = await chat_never_giveup("测试问题", {})
            self.record_test(
                "聊天处理器", "精神内核集成",
                result.get('spirit_compliant', False),
                "回复已通过精神内核验证"
            )
            
            # 测试3.6：尝试方法记录
            result = await chat_never_giveup("复杂问题测试", {})
            self.record_test(
                "聊天处理器", "尝试方法记录",
                len(result.get('attempts', [])) > 0,
                f"记录了{len(result.get('attempts', []))}种尝试方法"
            )
            
        except Exception as e:
            self.record_test("聊天处理器", "聊天处理器测试", False, f"异常: {str(e)}")
    
    # ========== 4. 认知调度器测试 ==========
    def test_cognitive_dispatcher(self):
        """测试认知调度器"""
        print("\n" + "=" * 60)
        print("测试类别4：认知调度器")
        print("=" * 60)
        
        try:
            from core.cognitive_dispatcher import CognitiveDispatcher
            
            dispatcher = CognitiveDispatcher()
            
            # 测试4.1：问候语路由
            result = dispatcher.dispatch(user_query="你好")
            self.record_test(
                "认知调度器", "问候语路由",
                result.get('intent_type') == 'greeting',
                f"意图: {result.get('intent_type')}, 路由: {result.get('route')}"
            )
            
            # 测试4.2：确认语路由
            result = dispatcher.dispatch(user_query="好的")
            self.record_test(
                "认知调度器", "确认语路由",
                result.get('intent_type') == 'confirmation',
                f"意图: {result.get('intent_type')}"
            )
            
            # 测试4.3：简单查询路由
            result = dispatcher.dispatch(user_query="认知是什么")
            self.record_test(
                "认知调度器", "简单查询路由",
                result.get('route') in ['fast', 'slow'],
                f"路由决策: {result.get('route')}"
            )
            
            # 测试4.4：复杂查询路由
            result = dispatcher.dispatch(user_query="请详细解释认知科学的发展历史和主要理论")
            self.record_test(
                "认知调度器", "复杂查询路由",
                result.get('route') in ['fast', 'slow'],
                f"复杂问题路由: {result.get('route')}"
            )
            
        except Exception as e:
            self.record_test("认知调度器", "认知调度器测试", False, f"异常: {str(e)}")
    
    # ========== 5. 数据库测试 ==========
    def test_databases(self):
        """测试数据库"""
        print("\n" + "=" * 60)
        print("测试类别5：数据库")
        print("=" * 60)
        
        import sqlite3
        import os
        
        # 测试5.1：知识库数据库
        try:
            if os.path.exists("data/knowledge_store.db"):
                conn = sqlite3.connect("data/knowledge_store.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM knowledge")
                count = cursor.fetchone()[0]
                conn.close()
                self.record_test(
                    "数据库", "知识库数据库",
                    True,
                    f"知识库包含{count}条记录"
                )
            else:
                self.record_test(
                    "数据库", "知识库数据库",
                    False,
                    "知识库数据库不存在"
                )
        except Exception as e:
            self.record_test("数据库", "知识库数据库", False, f"异常: {str(e)}")
        
        # 测试5.2：经验池数据库
        try:
            if os.path.exists("data/experience_pool.db"):
                conn = sqlite3.connect("data/experience_pool.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM experiences")
                count = cursor.fetchone()[0]
                conn.close()
                self.record_test(
                    "数据库", "经验池数据库",
                    True,
                    f"经验池包含{count}条记录"
                )
            else:
                self.record_test(
                    "数据库", "经验池数据库",
                    False,
                    "经验池数据库不存在"
                )
        except Exception as e:
            self.record_test("数据库", "经验池数据库", False, f"异常: {str(e)}")
        
        # 测试5.3：任务数据库
        try:
            if os.path.exists("data/tasks.db"):
                conn = sqlite3.connect("data/tasks.db")
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tasks")
                count = cursor.fetchone()[0]
                conn.close()
                self.record_test(
                    "数据库", "任务数据库",
                    True,
                    f"任务库包含{count}条记录"
                )
            else:
                self.record_test(
                    "数据库", "任务数据库",
                    False,
                    "任务数据库不存在"
                )
        except Exception as e:
            self.record_test("数据库", "任务数据库", False, f"异常: {str(e)}")
    
    # ========== 6. 文件结构测试 ==========
    def test_file_structure(self):
        """测试文件结构"""
        print("\n" + "=" * 60)
        print("测试类别6：文件结构")
        print("=" * 60)
        
        import os
        
        # 核心文件
        core_files = [
            "core/spirit_core.py",
            "core/never_give_up.py",
            "core/cognitive_dispatcher.py",
            "core/metacognitive_executor.py",
            "core/orchestrator.py",
            "core/cognitive_loop.py"
        ]
        
        for file in core_files:
            exists = os.path.exists(file)
            self.record_test(
                "文件结构", f"核心文件: {file}",
                exists,
                "存在" if exists else "不存在"
            )
        
        # 后端文件
        backend_files = [
            "backend/main_fast.py",
            "backend/chat_handler.py"
        ]
        
        for file in backend_files:
            exists = os.path.exists(file)
            self.record_test(
                "文件结构", f"后端文件: {file}",
                exists,
                "存在" if exists else "不存在"
            )
        
        # 数据目录
        data_dir_exists = os.path.exists("data")
        self.record_test(
            "文件结构", "数据目录",
            data_dir_exists,
            "存在" if data_dir_exists else "不存在"
        )
    
    # ========== 7. 端到端流程测试 ==========
    async def test_end_to_end(self):
        """端到端流程测试"""
        print("\n" + "=" * 60)
        print("测试类别7：端到端流程")
        print("=" * 60)
        
        try:
            from backend.chat_handler import chat_never_giveup
            
            test_cases = [
                ("你好", "问候语"),
                ("认知的概念是什么", "概念问题"),
                ("如何写一个排序算法", "代码问题"),
                ("为什么天空是蓝色的", "原因问题"),
                ("这是一个测试问题", "通用问题")
            ]
            
            for question, category in test_cases:
                result = await chat_never_giveup(question, {})
                
                # 验证回复存在
                has_response = result.get('response') is not None and len(result.get('response', '')) > 0
                
                # 验证尝试记录
                has_attempts = len(result.get('attempts', [])) > 0
                
                # 验证精神内核
                spirit_compliant = result.get('spirit_compliant', False)
                
                # 综合判断
                success = has_response and has_attempts
                
                self.record_test(
                    "端到端流程", f"{category}流程",
                    success,
                    f"回复{len(result.get('response', ''))}字, {len(result.get('attempts', []))}种方法, 精神内核{'✓' if spirit_compliant else '✗'}"
                )
                
        except Exception as e:
            self.record_test("端到端流程", "端到端流程测试", False, f"异常: {str(e)}")
    
    # ========== 8. 性能测试 ==========
    async def test_performance(self):
        """性能测试"""
        print("\n" + "=" * 60)
        print("测试类别8：性能")
        print("=" * 60)
        
        try:
            from backend.chat_handler import chat_never_giveup
            
            # 测试响应时间
            test_questions = [
                "你好",
                "认知是什么",
                "如何写代码",
                "这是一个测试"
            ]
            
            times = []
            for question in test_questions:
                start = time.time()
                result = await chat_never_giveup(question, {})
                elapsed = time.time() - start
                times.append(elapsed)
            
            avg_time = sum(times) / len(times)
            max_time = max(times)
            
            self.record_test(
                "性能", "平均响应时间",
                avg_time < 5.0,
                f"平均{avg_time:.2f}秒 (目标<5秒)"
            )
            
            self.record_test(
                "性能", "最大响应时间",
                max_time < 10.0,
                f"最大{max_time:.2f}秒 (目标<10秒)"
            )
            
        except Exception as e:
            self.record_test("性能", "性能测试", False, f"异常: {str(e)}")
    
    # ========== 生成测试报告 ==========
    def generate_report(self) -> str:
        """生成测试报告"""
        report = []
        report.append("\n" + "╔" + "═" * 68 + "╗")
        report.append("║" + " " * 20 + "测试报告总结" + " " * 36 + "║")
        report.append("╚" + "═" * 68 + "╝")
        
        # 统计
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        report.append(f"\n📊 测试统计:")
        report.append(f"   • 总测试数: {total}")
        report.append(f"   • 通过: {self.passed} ✅")
        report.append(f"   • 失败: {self.failed} ❌")
        report.append(f"   • 通过率: {pass_rate:.1f}%")
        
        # 分类统计
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'passed': 0, 'failed': 0}
            if result['success']:
                categories[cat]['passed'] += 1
            else:
                categories[cat]['failed'] += 1
        
        report.append(f"\n📋 分类统计:")
        for cat, stats in categories.items():
            total_cat = stats['passed'] + stats['failed']
            rate = (stats['passed'] / total_cat * 100) if total_cat > 0 else 0
            report.append(f"   • {cat}: {stats['passed']}/{total_cat} ({rate:.0f}%)")
        
        # 失败详情
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            report.append(f"\n❌ 失败测试详情:")
            for test in failed_tests:
                report.append(f"   • [{test['category']}] {test['name']}: {test['message']}")
        
        # 结论
        report.append(f"\n🎯 结论:")
        if pass_rate >= 90:
            report.append("   ✅ 系统运行良好，所有核心功能正常")
        elif pass_rate >= 70:
            report.append("   ⚠️ 系统基本可用，部分功能需要修复")
        else:
            report.append("   ❌ 系统存在严重问题，需要立即修复")
        
        report.append("\n" + "=" * 70)
        
        return "\n".join(report)
    
    # ========== 运行所有测试 ==========
    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "╔" + "═" * 68 + "╗")
        print("║" + " " * 15 + "联盟拓荒者端到端全方位测试" + " " * 24 + "║")
        print("╚" + "═" * 68 + "╝")
        
        start_time = time.time()
        
        # 运行所有测试
        self.test_spirit_core()
        await self.test_never_give_up_engine()
        await self.test_chat_handler()
        self.test_cognitive_dispatcher()
        self.test_databases()
        self.test_file_structure()
        await self.test_end_to_end()
        await self.test_performance()
        
        elapsed = time.time() - start_time
        
        # 生成报告
        report = self.generate_report()
        print(report)
        print(f"\n⏱️ 总耗时: {elapsed:.2f}秒")
        
        # 保存报告到文件
        with open("test_report.json", "w", encoding="utf-8") as f:
            json.dump({
                "summary": {
                    "total": self.passed + self.failed,
                    "passed": self.passed,
                    "failed": self.failed,
                    "pass_rate": (self.passed / (self.passed + self.failed) * 100) if (self.passed + self.failed) > 0 else 0,
                    "elapsed": elapsed
                },
                "results": self.test_results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 详细报告已保存到: test_report.json")
        
        return self.passed, self.failed


async def main():
    """主函数"""
    suite = ComprehensiveTestSuite()
    passed, failed = await suite.run_all_tests()
    
    # 返回退出码
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)