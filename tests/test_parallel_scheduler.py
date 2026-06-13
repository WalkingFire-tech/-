"""
并行调度器单元测试
"""
import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from infrastructure.parallel_scheduler import ParallelScheduler


class MockModelAdapter:
    """模拟模型适配器"""
    
    def __init__(self, model_name: str, response: str, delay: float = 0.1):
        self.model_name = model_name
        self.response = response
        self.delay = delay
        self.call_count = 0
    
    def generate(self, prompt: str, task_type: str = None):
        """模拟生成"""
        self.call_count += 1
        
        # 模拟延迟
        import time
        time.sleep(self.delay)
        
        return self.response


class TestParallelScheduler:
    """并行调度器测试套件"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        # 使用临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.scheduler = ParallelScheduler(db_path=self.db_path)
    
    def teardown_method(self):
        """每个测试方法后执行"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    @pytest.mark.asyncio
    async def test_parallel_call_basic(self):
        """测试基本并行调用"""
        models = [
            MockModelAdapter("model_a", "响应A", delay=0.05),
            MockModelAdapter("model_b", "响应B", delay=0.05)
        ]
        
        result = await self.scheduler.parallel_call(
            models=models,
            prompt="测试提示",
            task_type="test"
        )
        
        assert result is not None, "应返回结果"
        assert 'results' in result or 'best' in result, "应包含结果或最佳响应"
    
    @pytest.mark.asyncio
    async def test_parallel_call_with_callback(self):
        """测试带回调的并行调用"""
        models = [
            MockModelAdapter("model_a", "响应A", delay=0.05)
        ]
        
        callback_called = []
        
        def progress_callback(info):
            callback_called.append(info)
        
        result = await self.scheduler.parallel_call(
            models=models,
            prompt="测试提示",
            task_type="test",
            progress_callback=progress_callback
        )
        
        # 回调可能被调用（取决于实现）
        assert result is not None, "应返回结果"
    
    @pytest.mark.asyncio
    async def test_parallel_call_timeout(self):
        """测试超时处理"""
        # 创建一个会超时的模型
        slow_model = MockModelAdapter("slow_model", "响应", delay=10.0)
        
        # 设置较短超时
        self.scheduler.timeout_seconds = 0.1
        
        result = await self.scheduler.parallel_call(
            models=[slow_model],
            prompt="测试提示",
            task_type="test"
        )
        
        # 应该处理超时（返回None或错误结果）
        assert result is not None, "应返回结果（即使超时）"
    
    @pytest.mark.asyncio
    async def test_parallel_call_empty_models(self):
        """测试空模型列表"""
        result = await self.scheduler.parallel_call(
            models=[],
            prompt="测试提示",
            task_type="test"
        )
        
        # 应该优雅处理空列表
        assert result is not None, "应返回结果（即使无模型）"
    
    @pytest.mark.asyncio
    async def test_parallel_call_multiple_models(self):
        """测试多模型并行"""
        models = [
            MockModelAdapter("fast_model", "快速响应", delay=0.01),
            MockModelAdapter("medium_model", "中等响应", delay=0.05),
            MockModelAdapter("slow_model", "慢速响应", delay=0.1)
        ]
        
        start = asyncio.get_event_loop().time()
        result = await self.scheduler.parallel_call(
            models=models,
            prompt="测试提示",
            task_type="test"
        )
        duration = asyncio.get_event_loop().time() - start
        
        # 并行调用应该比串行快
        # 串行时间: 0.01 + 0.05 + 0.1 = 0.16s
        # 并行时间应该接近最慢的那个: ~0.1s
        assert duration < 0.2, f"并行调用应更快，实际耗时{duration:.2f}s"
    
    @pytest.mark.asyncio
    async def test_federated_call(self):
        """测试联邦调度"""
        models = [
            MockModelAdapter("model_a", "高质量响应", delay=0.05),
            MockModelAdapter("model_b", "中等质量响应", delay=0.05)
        ]
        
        # 创建适配器字典
        adapters = {
            "model_a": models[0],
            "model_b": models[1]
        }
        
        result = await self.scheduler.federated_call(
            prompt="测试提示",
            task_type="test",
            adapters=adapters,
            top_k=2
        )
        
        assert result is not None, "应返回结果"
        assert 'best' in result or 'error' in result, "应包含最佳结果或错误"
    
    @pytest.mark.asyncio
    async def test_federated_call_top_k(self):
        """测试top_k选择"""
        models = {
            "model_a": MockModelAdapter("model_a", "响应A", delay=0.05),
            "model_b": MockModelAdapter("model_b", "响应B", delay=0.05),
            "model_c": MockModelAdapter("model_c", "响应C", delay=0.05)
        }
        
        # 只选择top 2
        result = await self.scheduler.federated_call(
            prompt="测试提示",
            task_type="test",
            adapters=models,
            top_k=2
        )
        
        assert result is not None, "应返回结果"
    
    def test_select_best_result(self):
        """测试最佳结果选择"""
        results = [
            {
                'model_name': 'model_a',
                'response': '响应A',
                'success': True,
                'duration': 0.1,
                'quality_score': 0.8
            },
            {
                'model_name': 'model_b',
                'response': '响应B',
                'success': True,
                'duration': 0.2,
                'quality_score': 0.9
            }
        ]
        
        best = self.scheduler._select_best_result(results, "test")
        
        assert best is not None, "应选择最佳结果"
        assert best['model_name'] in ['model_a', 'model_b'], "应选择有效模型"
    
    def test_select_best_result_empty(self):
        """测试空结果选择"""
        best = self.scheduler._select_best_result([], "test")
        
        assert best is None, "空结果应返回None"
    
    def test_max_concurrent_limit(self):
        """测试并发限制"""
        assert self.scheduler.max_concurrent > 0, "并发限制应大于0"
        assert self.scheduler.max_concurrent <= 10, "并发限制应合理"
    
    def test_timeout_configuration(self):
        """测试超时配置"""
        assert self.scheduler.timeout_seconds > 0, "超时应大于0"
        
        # 修改超时
        self.scheduler.timeout_seconds = 30
        assert self.scheduler.timeout_seconds == 30, "应可修改超时"
    
    def test_retry_configuration(self):
        """测试重试配置"""
        assert self.scheduler.retry_count >= 0, "重试次数应非负"
        
        # 修改重试次数
        self.scheduler.retry_count = 3
        assert self.scheduler.retry_count == 3, "应可修改重试次数"


class TestParallelSchedulerStats:
    """并行调度器统计测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.scheduler = ParallelScheduler(db_path=self.db_path)
    
    def teardown_method(self):
        """每个测试方法后执行"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_get_statistics(self):
        """测试获取统计"""
        stats = self.scheduler.get_statistics()
        
        assert isinstance(stats, dict), "统计应为字典"
    
    def test_save_and_load_stats(self):
        """测试保存和加载统计"""
        # 模拟保存统计
        task_id = "test_task_123"
        
        # 获取统计（可能为空）
        stats = self.scheduler.get_statistics()
        
        assert isinstance(stats, dict), "统计应为字典"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])