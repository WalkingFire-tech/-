"""
基准测试 - 验证联邦调度与任务分解的效果
对比单模型 vs 联邦调度 vs 分解融合的效果
"""
import json
import time
import asyncio
from pathlib import Path
from typing import List, Dict
from loguru import logger


class BenchmarkTest:
    """基准测试框架"""
    
    def __init__(self):
        self.test_cases = self._load_test_cases()
        self.results = []
    
    def _load_test_cases(self) -> List[Dict]:
        """加载测试用例"""
        test_file = Path("tests/complex_tasks.json")
        
        if test_file.exists():
            with open(test_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 默认测试集
        return [
            {
                "id": 1,
                "input": "写一个快速排序算法的Python实现，并解释其时间复杂度，同时比较递归和迭代版本的性能。",
                "expected_subtasks": ["代码实现", "时间复杂度解释", "性能比较"],
                "category": "code+explanation",
                "eval_method": "quality"
            },
            {
                "id": 2,
                "input": "计算斐波那契数列的前10项，并分析其增长规律。",
                "expected_subtasks": ["计算", "分析"],
                "category": "calculation+analysis",
                "eval_method": "quality"
            },
            {
                "id": 3,
                "input": "分析Python和Java的区别，并给出学习建议。",
                "expected_subtasks": ["对比分析", "建议"],
                "category": "analysis",
                "eval_method": "quality"
            },
            {
                "id": 4,
                "input": "实现一个用户登录功能，包括前端表单验证、后端API接口和数据库存储。",
                "expected_subtasks": ["前端", "后端", "数据库"],
                "category": "code",
                "eval_method": "quality"
            },
            {
                "id": 5,
                "input": "写一个冒泡排序",
                "expected_subtasks": ["代码实现"],
                "category": "simple",
                "eval_method": "quality"
            }
        ]
    
    def evaluate_quality(self, response: str, task_type: str) -> float:
        """评估响应质量"""
        if not response:
            return 0.0
        
        score = 0.5
        
        # 长度评估
        if len(response) > 100:
            score += 0.1
        if len(response) > 300:
            score += 0.1
        if len(response) > 500:
            score += 0.1
        
        # 代码检测
        if '```' in response or 'def ' in response:
            score += 0.15
        
        # 结构检测
        if any(marker in response for marker in ['###', '1.', '首先', '第一']):
            score += 0.1
        
        # 错误检测
        if '错误' in response or 'error' in response.lower():
            score -= 0.2
        
        # 任务类型特定评估
        if task_type == "code":
            if 'def ' in response and 'return' in response:
                score += 0.1
        elif task_type == "analysis":
            if any(word in response for word in ['优点', '缺点', '区别', '差异']):
                score += 0.1
        
        return max(0.0, min(1.0, score))
    
    async def run_single_model(self, test_case: Dict, adapter) -> Dict:
        """单模型测试"""
        start = time.time()
        
        try:
            response = adapter.generate(test_case['input'])
            if isinstance(response, tuple):
                response = response[0]
            
            duration = time.time() - start
            quality = self.evaluate_quality(response, test_case['category'])
            
            return {
                'mode': 'single_model',
                'test_id': test_case['id'],
                'response': response,
                'duration': duration,
                'quality': quality,
                'success': True
            }
        except Exception as e:
            return {
                'mode': 'single_model',
                'test_id': test_case['id'],
                'error': str(e),
                'duration': time.time() - start,
                'quality': 0.0,
                'success': False
            }
    
    async def run_federated(self, test_case: Dict, adapters: Dict) -> Dict:
        """联邦调度测试"""
        start = time.time()
        
        try:
            from infrastructure.parallel_scheduler import parallel_scheduler
            
            result = await parallel_scheduler.federated_call(
                prompt=test_case['input'],
                task_type=test_case['category'],
                adapters=adapters,
                top_k=2
            )
            
            best = result.get('best', {})
            response = best.get('response', '')
            
            duration = time.time() - start
            quality = self.evaluate_quality(response, test_case['category'])
            
            return {
                'mode': 'federated',
                'test_id': test_case['id'],
                'response': response,
                'duration': duration,
                'quality': quality,
                'models_used': result.get('stats', {}).get('successful', 0),
                'success': True
            }
        except Exception as e:
            return {
                'mode': 'federated',
                'test_id': test_case['id'],
                'error': str(e),
                'duration': time.time() - start,
                'quality': 0.0,
                'success': False
            }
    
    async def run_decompose_fuse(self, test_case: Dict, adapters: Dict) -> Dict:
        """分解融合测试"""
        start = time.time()
        
        try:
            from infrastructure.task_decomposer import task_decomposer
            from infrastructure.result_fusion import result_fusion
            
            # 分解
            subtasks = task_decomposer.detect_subtasks(test_case['input'])
            
            if len(subtasks) <= 1:
                # 无法分解，使用联邦调度
                return await self.run_federated(test_case, adapters)
            
            # 执行子任务
            results = []
            for subtask in subtasks:
                # 简化：使用第一个可用模型
                adapter = next(iter(adapters.values()))
                try:
                    result = adapter.generate(subtask['description'])
                    if isinstance(result, tuple):
                        result = result[0]
                    results.append(result)
                except:
                    results.append("")
            
            # 融合
            summary_model = adapters.get('mindchat') or next(iter(adapters.values()))
            fused = result_fusion.fuse(
                subtasks=subtasks,
                results=results,
                original_intent=test_case['input'],
                strategy='auto',
                summary_model=summary_model
            )
            
            duration = time.time() - start
            quality = self.evaluate_quality(fused, test_case['category'])
            
            return {
                'mode': 'decompose_fuse',
                'test_id': test_case['id'],
                'response': fused,
                'duration': duration,
                'quality': quality,
                'subtasks': len(subtasks),
                'success': True
            }
        except Exception as e:
            return {
                'mode': 'decompose_fuse',
                'test_id': test_case['id'],
                'error': str(e),
                'duration': time.time() - start,
                'quality': 0.0,
                'success': False
            }
    
    async def run_benchmark(self, adapters: Dict) -> Dict:
        """运行完整基准测试"""
        print("\n" + "=" * 70)
        print("基准测试开始")
        print("=" * 70)
        
        results = {
            'single_model': [],
            'federated': [],
            'decompose_fuse': []
        }
        
        # 选择测试模型
        test_adapter = adapters.get('mindchat') or next(iter(adapters.values()))
        
        for test_case in self.test_cases:
            print(f"\n测试 {test_case['id']}: {test_case['input'][:50]}...")
            
            # 单模型
            print("  运行: 单模型...")
            result_single = await self.run_single_model(test_case, test_adapter)
            results['single_model'].append(result_single)
            print(f"    质量: {result_single['quality']:.2f}, 耗时: {result_single['duration']:.2f}s")
            
            # 联邦调度
            print("  运行: 联邦调度...")
            result_federated = await self.run_federated(test_case, adapters)
            results['federated'].append(result_federated)
            print(f"    质量: {result_federated['quality']:.2f}, 耗时: {result_federated['duration']:.2f}s")
            
            # 分解融合
            print("  运行: 分解融合...")
            result_decompose = await self.run_decompose_fuse(test_case, adapters)
            results['decompose_fuse'].append(result_decompose)
            print(f"    质量: {result_decompose['quality']:.2f}, 耗时: {result_decompose['duration']:.2f}s")
        
        # 统计分析
        stats = self._analyze_results(results)
        
        return stats
    
    def _analyze_results(self, results: Dict) -> Dict:
        """分析测试结果"""
        stats = {}
        
        for mode, mode_results in results.items():
            if not mode_results:
                continue
            
            qualities = [r['quality'] for r in mode_results if r['success']]
            durations = [r['duration'] for r in mode_results if r['success']]
            success_count = sum(1 for r in mode_results if r['success'])
            
            stats[mode] = {
                'avg_quality': sum(qualities) / len(qualities) if qualities else 0,
                'avg_duration': sum(durations) / len(durations) if durations else 0,
                'success_rate': success_count / len(mode_results),
                'total_tests': len(mode_results)
            }
        
        return stats
    
    def print_summary(self, stats: Dict):
        """打印测试总结"""
        print("\n" + "=" * 70)
        print("基准测试总结")
        print("=" * 70)
        
        print("\n模式对比:")
        print(f"{'模式':<20} {'平均质量':<12} {'平均耗时':<12} {'成功率':<10}")
        print("-" * 60)
        
        for mode, stat in stats.items():
            print(f"{mode:<20} {stat['avg_quality']:<12.3f} {stat['avg_duration']:<12.2f}s {stat['success_rate']:<10.1%}")
        
        # 计算提升
        if 'single_model' in stats and 'federated' in stats:
            quality_lift = (stats['federated']['avg_quality'] - stats['single_model']['avg_quality']) / stats['single_model']['avg_quality'] * 100
            print(f"\n联邦调度质量提升: {quality_lift:+.1f}%")
        
        if 'single_model' in stats and 'decompose_fuse' in stats:
            quality_lift = (stats['decompose_fuse']['avg_quality'] - stats['single_model']['avg_quality']) / stats['single_model']['avg_quality'] * 100
            print(f"分解融合质量提升: {quality_lift:+.1f}%")


async def main():
    """主测试流程"""
    print("=" * 70)
    print("联邦调度与任务分解基准测试")
    print("=" * 70)
    
    # 模拟适配器（实际使用时从main.py获取）
    from adapters.llm.mock_adapter import MockAdapter
    
    adapters = {
        'mock': MockAdapter()
    }
    
    benchmark = BenchmarkTest()
    stats = await benchmark.run_benchmark(adapters)
    benchmark.print_summary(stats)


if __name__ == "__main__":
    asyncio.run(main())