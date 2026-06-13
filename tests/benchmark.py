"""
性能基准测试
"""
import time
import statistics
import asyncio
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from loguru import logger


class Benchmark:
    """性能基准测试"""
    
    def __init__(self):
        self.results = {}
    
    def measure(self, func, *args, iterations=10, **kwargs):
        """测量函数执行时间"""
        times = []
        
        for i in range(iterations):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                times.append(elapsed)
            except Exception as e:
                logger.error(f"迭代 {i} 失败: {e}")
        
        if not times:
            return None
        
        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "min": min(times),
            "max": max(times),
            "iterations": len(times)
        }
    
    async def measure_async(self, func, *args, iterations=10, **kwargs):
        """测量异步函数执行时间"""
        times = []
        
        for i in range(iterations):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start
                times.append(elapsed)
            except Exception as e:
                logger.error(f"迭代 {i} 失败: {e}")
        
        if not times:
            return None
        
        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
            "min": min(times),
            "max": max(times),
            "iterations": len(times)
        }
    
    def benchmark_learning(self):
        """测试学习性能"""
        logger.info("=" * 50)
        logger.info("测试：学习性能")
        logger.info("=" * 50)
        
        try:
            from infrastructure.active_learner import active_learner, LearningTrigger
            
            async def trigger_learning():
                return await active_learner.trigger_learning(
                    LearningTrigger.MANUAL,
                    "test benchmark query"
                )
            
            result = asyncio.run(self.measure_async(trigger_learning, iterations=3))
            
            if result:
                self.results["learning"] = result
                logger.info(f"平均时间: {result['mean']:.2f}s")
                logger.info(f"中位数: {result['median']:.2f}s")
                logger.info(f"标准差: {result['stdev']:.2f}s")
                return True
            
        except Exception as e:
            logger.error(f"学习性能测试失败: {e}")
        
        return False
    
    def benchmark_search(self):
        """测试搜索性能"""
        logger.info("\n" + "=" * 50)
        logger.info("测试：搜索性能")
        logger.info("=" * 50)
        
        try:
            from tools.web_search import QuickSearchTool
            
            search_tool = QuickSearchTool()
            
            def search():
                return search_tool.execute(query="Python async")
            
            result = self.measure(search, iterations=3)
            
            if result:
                self.results["search"] = result
                logger.info(f"平均时间: {result['mean']:.2f}s")
                logger.info(f"中位数: {result['median']:.2f}s")
                logger.info(f"标准差: {result['stdev']:.2f}s")
                return True
            
        except Exception as e:
            logger.error(f"搜索性能测试失败: {e}")
        
        return False
    
    def benchmark_intent_parsing(self):
        """测试意图解析性能"""
        logger.info("\n" + "=" * 50)
        logger.info("测试：意图解析性能")
        logger.info("=" * 50)
        
        try:
            from core.services.intent_parser import IntentParser
            
            parser = IntentParser()
            
            def parse():
                return parser.parse("计算 2+3*4")
            
            result = self.measure(parse, iterations=100)
            
            if result:
                self.results["intent_parsing"] = result
                logger.info(f"平均时间: {result['mean']*1000:.2f}ms")
                logger.info(f"中位数: {result['median']*1000:.2f}ms")
                logger.info(f"标准差: {result['stdev']*1000:.2f}ms")
                return True
            
        except Exception as e:
            logger.error(f"意图解析性能测试失败: {e}")
        
        return False
    
    def benchmark_rule_matching(self):
        """测试规则匹配性能"""
        logger.info("\n" + "=" * 50)
        logger.info("测试：规则匹配性能")
        logger.info("=" * 50)
        
        try:
            from infrastructure.reflex_engine import reflex_engine
            
            def match():
                return reflex_engine.match_rules(
                    "code_generation",
                    {"raw_input": "写一个Python函数"}
                )
            
            result = self.measure(match, iterations=100)
            
            if result:
                self.results["rule_matching"] = result
                logger.info(f"平均时间: {result['mean']*1000:.2f}ms")
                logger.info(f"中位数: {result['median']*1000:.2f}ms")
                logger.info(f"标准差: {result['stdev']*1000:.2f}ms")
                return True
            
        except Exception as e:
            logger.error(f"规则匹配性能测试失败: {e}")
        
        return False
    
    def benchmark_database(self):
        """测试数据库性能"""
        logger.info("\n" + "=" * 50)
        logger.info("测试：数据库性能")
        logger.info("=" * 50)
        
        try:
            from infrastructure.model_stats import ModelStats
            
            stats = ModelStats()
            
            def query():
                return stats.get_model_stats("mindchat")
            
            result = self.measure(query, iterations=100)
            
            if result:
                self.results["database"] = result
                logger.info(f"平均时间: {result['mean']*1000:.2f}ms")
                logger.info(f"中位数: {result['median']*1000:.2f}ms")
                logger.info(f"标准差: {result['stdev']*1000:.2f}ms")
                return True
            
        except Exception as e:
            logger.error(f"数据库性能测试失败: {e}")
        
        return False
    
    def generate_report(self):
        """生成性能报告"""
        logger.info("\n" + "=" * 70)
        logger.info("性能基准测试报告")
        logger.info("=" * 70)
        
        for test_name, result in self.results.items():
            logger.info(f"\n{test_name}:")
            if result['mean'] < 1:
                logger.info(f"  平均: {result['mean']*1000:.2f}ms")
                logger.info(f"  中位数: {result['median']*1000:.2f}ms")
                logger.info(f"  范围: [{result['min']*1000:.2f}ms, {result['max']*1000:.2f}ms]")
            else:
                logger.info(f"  平均: {result['mean']:.2f}s")
                logger.info(f"  中位数: {result['median']:.2f}s")
                logger.info(f"  范围: [{result['min']:.2f}s, {result['max']:.2f}s]")
        
        # 保存报告
        report_path = ROOT_DIR / "docs" / "BENCHMARK_REPORT.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# 性能基准测试报告\n\n")
            f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for test_name, result in self.results.items():
                f.write(f"## {test_name}\n\n")
                if result['mean'] < 1:
                    f.write(f"- 平均时间: {result['mean']*1000:.2f}ms\n")
                    f.write(f"- 中位数: {result['median']*1000:.2f}ms\n")
                    f.write(f"- 标准差: {result['stdev']*1000:.2f}ms\n")
                    f.write(f"- 范围: [{result['min']*1000:.2f}ms, {result['max']*1000:.2f}ms]\n")
                else:
                    f.write(f"- 平均时间: {result['mean']:.2f}s\n")
                    f.write(f"- 中位数: {result['median']:.2f}s\n")
                    f.write(f"- 标准差: {result['stdev']:.2f}s\n")
                    f.write(f"- 范围: [{result['min']:.2f}s, {result['max']:.2f}s]\n")
                f.write(f"- 迭代次数: {result['iterations']}\n\n")
        
        logger.info(f"\n报告已保存到: {report_path}")


def main():
    """运行性能基准测试"""
    benchmark = Benchmark()
    
    # 运行所有测试
    benchmark.benchmark_intent_parsing()
    benchmark.benchmark_rule_matching()
    benchmark.benchmark_database()
    benchmark.benchmark_search()
    benchmark.benchmark_learning()
    
    # 生成报告
    benchmark.generate_report()


if __name__ == "__main__":
    main()