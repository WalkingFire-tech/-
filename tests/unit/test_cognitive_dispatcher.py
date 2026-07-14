#!/usr/bin/env python
"""测试认知调度器"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.cognitive_dispatcher import CognitiveDispatcher


class TestCognitiveDispatcher:
    """测试认知调度器"""

    @pytest.fixture
    def dispatcher(self):
        """创建调度器实例"""
        return CognitiveDispatcher()

    def test_init(self, dispatcher):
        """测试初始化"""
        assert dispatcher is not None
        assert dispatcher.cache_ttl == 300

    @patch('core.tool_registry.tool_registry')
    def test_dispatch_simple_query(self, mock_tool_registry, dispatcher):
        """测试简单查询的调度"""
        # Mock工具和模型
        mock_tool = MagicMock()
        mock_tool.name = "calculator"
        mock_tool.description = "数学计算工具"
        mock_tool_registry.get_all_tools.return_value = [mock_tool]

        mock_model = MagicMock()
        mock_model.name = "gpt-4"
        mock_model.description = "GPT-4模型"
        mock_tool_registry.get_all_models.return_value = [mock_model]

        result = dispatcher.dispatch("1+1等于几？", {})
        assert result is not None
        assert "intent_type" in result
        assert "confidence" in result

    @patch('core.tool_registry.tool_registry')
    def test_dispatch_with_history(self, mock_tool_registry, dispatcher):
        """测试带历史记录的调度"""
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "测试工具"
        mock_tool_registry.get_all_tools.return_value = [mock_tool]

        mock_model = MagicMock()
        mock_model.name = "test_model"
        mock_model.description = "测试模型"
        mock_tool_registry.get_all_models.return_value = [mock_model]

        context = {
            "history": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！有什么可以帮助你的？"}
            ]
        }

        result = dispatcher.dispatch("我想计算", context)
        assert result is not None

    @patch('core.tool_registry.tool_registry')
    def test_cache_hit(self, mock_tool_registry, dispatcher):
        """测试缓存命中"""
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "测试工具"
        mock_tool_registry.get_all_tools.return_value = [mock_tool]

        mock_model = MagicMock()
        mock_model.name = "test_model"
        mock_model.description = "测试模型"
        mock_tool_registry.get_all_models.return_value = [mock_model]

        # 第一次调用
        result1 = dispatcher.dispatch("测试查询", {})
        # 第二次调用（应该命中缓存）
        result2 = dispatcher.dispatch("测试查询", {})

        assert result1 is not None
        assert result2 is not None

    @patch('core.tool_registry.tool_registry')
    def test_confidence_scoring(self, mock_tool_registry, dispatcher):
        """测试置信度评分"""
        mock_tool = MagicMock()
        mock_tool.name = "calculator"
        mock_tool.description = "数学计算工具"
        mock_tool_registry.get_all_tools.return_value = [mock_tool]

        mock_model = MagicMock()
        mock_model.name = "gpt-4"
        mock_model.description = "GPT-4模型"
        mock_tool_registry.get_all_models.return_value = [mock_model]

        result = dispatcher.dispatch("1+1等于几？", {})
        confidence = result.get("confidence", 0)
        assert 0 <= confidence <= 1

    @patch('core.tool_registry.tool_registry')
    def test_route_decision(self, mock_tool_registry, dispatcher):
        """测试路由决策"""
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "测试工具"
        mock_tool_registry.get_all_tools.return_value = [mock_tool]

        mock_model = MagicMock()
        mock_model.name = "test_model"
        mock_model.description = "测试模型"
        mock_tool_registry.get_all_models.return_value = [mock_model]

        result = dispatcher.dispatch("测试查询", {})
        assert "route" in result
        assert result["route"] in ["fast", "slow", "tool", "knowledge"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])