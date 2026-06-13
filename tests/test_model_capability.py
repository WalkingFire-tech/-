"""
能力矩阵单元测试
"""
import pytest
import sqlite3
import tempfile
import os
from infrastructure.model_capability import ModelCapability


class TestModelCapability:
    """能力矩阵测试套件"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        # 使用临时数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.capability = ModelCapability(db_path=self.db_path)
    
    def teardown_method(self):
        """每个测试方法后执行"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_register_model(self):
        """测试模型注册"""
        self.capability.register_model("test_model")
        
        # 验证注册成功
        caps = self.capability.get_model_capabilities("test_model")
        assert caps is not None, "模型应该被注册"
        assert len(caps) > 0, "应该有能力维度"
    
    def test_register_model_with_custom_capabilities(self):
        """测试自定义能力注册"""
        custom_caps = {
            'coding': 0.9,
            'reasoning': 0.8,
            'math': 0.7
        }
        
        self.capability.register_model("custom_model", custom_caps)
        
        caps = self.capability.get_model_capabilities("custom_model")
        assert caps['coding'] == 0.9, f"coding能力应为0.9，实际{caps.get('coding')}"
        assert caps['reasoning'] == 0.8, f"reasoning能力应为0.8，实际{caps.get('reasoning')}"
    
    def test_update_capability(self):
        """测试能力更新"""
        self.capability.register_model("update_model")
        
        # 更新能力
        self.capability.update_capability("update_model", "coding", 0.95)
        
        caps = self.capability.get_model_capabilities("update_model")
        assert caps['coding'] >= 0.9, f"coding能力应提升到>=0.9，实际{caps.get('coding')}"
    
    def test_update_from_feedback_success(self):
        """测试成功反馈更新"""
        self.capability.register_model("feedback_model")
        
        # 模拟成功调用
        self.capability.update_from_feedback(
            model_name="feedback_model",
            task_type="code",
            success=True,
            quality_score=0.9
        )
        
        caps = self.capability.get_model_capabilities("feedback_model")
        # 成功调用应该提升能力
        assert caps.get('coding', 0) > 0.7, "成功调用应提升能力"
    
    def test_update_from_feedback_failure(self):
        """测试失败反馈更新"""
        self.capability.register_model("fail_model")
        
        # 先提升能力
        self.capability.update_capability("fail_model", "coding", 0.9)
        
        # 模拟失败调用
        self.capability.update_from_feedback(
            model_name="fail_model",
            task_type="code",
            success=False,
            quality_score=0.3
        )
        
        caps = self.capability.get_model_capabilities("fail_model")
        # 失败调用应该降低能力（但不会太低）
        assert caps.get('coding', 0) < 0.9, "失败调用应降低能力"
    
    def test_get_best_model_for_task(self):
        """测试最佳模型选择"""
        # 注册多个模型
        self.capability.register_model("model_a", {'coding': 0.9, 'reasoning': 0.7})
        self.capability.register_model("model_b", {'coding': 0.7, 'reasoning': 0.9})
        
        # 选择代码任务最佳模型
        best = self.capability.get_best_model_for_task("code")
        assert best in ["model_a", "model_b"], f"应返回有效模型，实际{best}"
    
    def test_task_dimension_mapping(self):
        """测试任务维度映射"""
        # 代码任务应该侧重coding维度
        code_dims = self.capability.get_task_dimensions("code")
        assert 'coding' in code_dims, "代码任务应包含coding维度"
        assert code_dims['coding'] > 0.3, "coding维度权重应较高"
        
        # 数学任务应该侧重math维度
        math_dims = self.capability.get_task_dimensions("math")
        assert 'math' in math_dims, "数学任务应包含math维度"
    
    def test_capability_decay(self):
        """测试能力衰减（时效性）"""
        self.capability.register_model("decay_model", {'coding': 0.9})
        
        # 模拟时间流逝（通过多次更新）
        for i in range(10):
            self.capability.update_capability("decay_model", "coding", 0.7)
        
        caps = self.capability.get_model_capabilities("decay_model")
        # 能力应该趋于稳定
        assert 0.5 < caps.get('coding', 0) < 0.95, "能力应在合理范围"
    
    def test_export_stats(self):
        """测试统计导出"""
        self.capability.register_model("stat_model")
        
        stats = self.capability.export_stats()
        
        assert 'total_models' in stats, "应包含total_models"
        assert stats['total_models'] >= 1, "至少有1个模型"
    
    def test_multiple_models_comparison(self):
        """测试多模型比较"""
        models = {
            "fast_model": {'speed': 0.9, 'coding': 0.7},
            "quality_model": {'speed': 0.5, 'coding': 0.95},
            "balanced_model": {'speed': 0.7, 'coding': 0.8}
        }
        
        for name, caps in models.items():
            self.capability.register_model(name, caps)
        
        # 选择速度优先
        fast_best = self.capability.get_best_model_for_task(
            "code",
            weights={'speed': 0.8, 'coding': 0.2}
        )
        
        # 选择质量优先
        quality_best = self.capability.get_best_model_for_task(
            "code",
            weights={'speed': 0.2, 'coding': 0.8}
        )
        
        # 两者可能不同（取决于具体实现）
        assert fast_best in models.keys(), "应返回有效模型"
        assert quality_best in models.keys(), "应返回有效模型"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])