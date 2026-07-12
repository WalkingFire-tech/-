"""
快速基准测试 - 评估模型真实能力
替换基于名称的推断值
"""
import asyncio
import time
from typing import Dict, List
from loguru import logger


class QuickBenchmark:
    """快速基准测试 - 评估模型真实能力"""
    
    TEST_CASES = {
        'coding': [
            "写一个Python函数计算斐波那契数列",
            "实现快速排序算法",
            "写一个函数检查字符串是否为回文"
        ],
        'reasoning': [
            "如果所有A都是B，有些B是C，那么有些A是C吗？",
            "解释递归和迭代的区别",
            "什么是时间复杂度？"
        ],
        'math': [
            "计算 25 * 4 + 18 / 3",
            "解释什么是质数",
            "计算斐波那契数列的第10项"
        ],
        'creative': [
            "写一个关于AI的短故事",
            "用比喻解释机器学习",
            "创作一首关于编程的诗"
        ]
    }
    
    def __init__(self):
        self.results = {}
    
    async def evaluate_model(self, model_name: str, adapter) -> Dict[str, float]:
        """评估单个模型的能力
        
        Args:
            model_name: 模型名称
            adapter: 模型适配器
        
        Returns:
            能力评分字典
        """
        logger.info(f"开始评估模型: {model_name}")
        
        capabilities = {}
        
        for dimension, test_cases in self.TEST_CASES.items():
            scores = []
            
            for test_case in test_cases:
                try:
                    start = time.time()
                    response = adapter.generate(test_case)
                    
                    if isinstance(response, tuple):
                        response = response[0]
                    
                    duration = time.time() - start
                    
                    # 评估质量
                    quality = self._evaluate_response(response, dimension)
                    
                    # 综合得分：质量 * 速度因子
                    speed_factor = max(0.5, min(1.0, 10.0 / max(duration, 0.1)))
                    score = quality * 0.8 + speed_factor * 0.2
                    
                    scores.append(score)
                    
                except Exception as e:
                    logger.warning(f"测试失败: {dimension} - {e}")
                    scores.append(0.3)  # 失败给低分
            
            # 平均得分
            if scores:
                capabilities[dimension] = sum(scores) / len(scores)
            else:
                capabilities[dimension] = 0.5
        
        # 添加速度维度
        capabilities['speed'] = self._evaluate_speed(adapter)
        
        logger.info(f"模型 {model_name} 评估完成: {capabilities}")
        
        return capabilities
    
    def _evaluate_response(self, response: str, dimension: str) -> float:
        """评估响应质量"""
        if not response:
            return 0.0
        
        score = 0.5
        
        # 长度评估
        if len(response) > 50:
            score += 0.1
        if len(response) > 200:
            score += 0.1
        
        # 维度特定评估
        if dimension == 'coding':
            if 'def ' in response or '```' in response:
                score += 0.2
            if 'return' in response:
                score += 0.1
        
        elif dimension == 'reasoning':
            if any(word in response for word in ['因为', '所以', '因此', '因为', '所以']):
                score += 0.15
            if len(response) > 100:
                score += 0.1
        
        elif dimension == 'math':
            if any(char.isdigit() for char in response):
                score += 0.1
            if '结果' in response or '=' in response:
                score += 0.1
        
        elif dimension == 'creative':
            if len(response) > 100:
                score += 0.2
            if any(word in response for word in ['故事', '就像', '如同']):
                score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _evaluate_speed(self, adapter) -> float:
        """评估模型速度"""
        try:
            start = time.time()
            adapter.generate("测试")
            duration = time.time() - start
            
            # 速度得分：越快越高
            if duration < 1:
                return 0.95
            elif duration < 3:
                return 0.85
            elif duration < 5:
                return 0.7
            elif duration < 10:
                return 0.5
            else:
                return 0.3
        
        except Exception:
            return 0.5
    
    async def benchmark_all_models(self, adapters: Dict) -> Dict[str, Dict[str, float]]:
        """评估所有模型
        
        Args:
            adapters: 模型适配器字典
        
        Returns:
            模型能力矩阵
        """
        print("\n" + "=" * 70)
        print("快速基准测试 - 评估模型真实能力")
        print("=" * 70)
        
        all_capabilities = {}
        
        for model_name, adapter in adapters.items():
            print(f"\n评估模型: {model_name}")
            capabilities = await self.evaluate_model(model_name, adapter)
            all_capabilities[model_name] = capabilities
            
            # 打印结果
            print(f"  能力评分:")
            for dim, score in capabilities.items():
                print(f"    {dim:12}: {score:.3f}")
        
        return all_capabilities
    
    def update_capability_matrix(self, capabilities: Dict[str, Dict[str, float]]):
        """更新能力矩阵
        
        Args:
            capabilities: 模型能力矩阵
        """
        from infrastructure.model_capability import model_capability
        
        print("\n更新能力矩阵...")
        
        for model_name, caps in capabilities.items():
            model_capability.register_model(model_name, caps)
            print(f"  已更新: {model_name}")
        
        print("\n✓ 能力矩阵更新完成")


async def main():
    """主测试流程"""
    from adapters.llm.mock_adapter import MockAdapter
    
    # 模拟适配器（实际使用时替换为真实模型）
    adapters = {
        'mock_model': MockAdapter()
    }
    
    benchmark = QuickBenchmark()
    capabilities = await benchmark.benchmark_all_models(adapters)
    benchmark.update_capability_matrix(capabilities)
    
    print("\n" + "=" * 70)
    print("基准测试完成")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())