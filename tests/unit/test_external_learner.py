#!/usr/bin/env python
"""测试外部学习器DeepSeek API支持"""
import sys
import os
import json
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.external_learner import ExternalLearner


class TestExternalLearner:
    """测试外部学习器"""

    def test_init_with_deepseek_config(self):
        """测试使用DeepSeek配置初始化"""
        with patch('builtins.open', create=True) as mock_open:
            config = {
                "deepseek_api_key": "test-key-123",
                "openai_api_key": ""
            }
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(config)
            mock_open.return_value.__enter__.return_value = mock_file

            learner = ExternalLearner()
            assert learner.llm_api_key == "test-key-123"
            assert learner.llm_model == "deepseek-chat"
            assert "deepseek" in learner.llm_base_url

    def test_init_with_openai_config(self):
        """测试使用OpenAI配置初始化"""
        with patch('builtins.open', create=True) as mock_open:
            config = {
                "deepseek_api_key": "",
                "openai_api_key": "sk-test-456"
            }
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(config)
            mock_open.return_value.__enter__.return_value = mock_file

            learner = ExternalLearner()
            assert learner.llm_api_key == "sk-test-456"
            assert learner.llm_model == "gpt-4"
            assert "openai" in learner.llm_base_url

    def test_init_without_api_key(self):
        """测试没有API密钥时的初始化"""
        with patch('builtins.open', create=True) as mock_open:
            config = {
                "deepseek_api_key": "",
                "openai_api_key": ""
            }
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(config)
            mock_open.return_value.__enter__.return_value = mock_file

            learner = ExternalLearner()
            assert learner.llm_api_key == ""
            assert learner.llm_model == "gpt-4"

    @patch('requests.post')
    def test_ask_llm_deepseek_success(self, mock_post):
        """测试DeepSeek API调用成功"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "1+1=2"
                }
            }]
        }
        mock_post.return_value = mock_response

        with patch('builtins.open', create=True) as mock_open:
            config = {
                "deepseek_api_key": "test-key",
                "openai_api_key": ""
            }
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(config)
            mock_open.return_value.__enter__.return_value = mock_file

            learner = ExternalLearner()

        result = learner.ask_llm("1+1等于几？", "你是一个数学助手")
        assert result == "1+1=2"
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "deepseek.com" in call_args[0][0]
        assert call_args[1]['headers']['Authorization'] == 'Bearer test-key'
        assert call_args[1]['verify'] == False

    @patch('requests.post')
    def test_ask_llm_fallback_to_ollama(self, mock_post):
        """测试API失败时降级到Ollama"""
        mock_post.side_effect = Exception("API error")

        with patch('builtins.open', create=True) as mock_open:
            config = {
                "deepseek_api_key": "",
                "openai_api_key": ""
            }
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(config)
            mock_open.return_value.__enter__.return_value = mock_file

            learner = ExternalLearner()

        result = learner.ask_llm("测试", "test")
        # 应该返回错误信息，因为Ollama也不可用
        assert "无可用LLM" in result or result == ""

    def test_search_web_local_fallback(self):
        """测试本地知识库降级"""
        learner = ExternalLearner()
        learner.search_api_key = ""

        # 应该降级到本地搜索
        results = learner.search_web("测试查询")
        # 结果可能是空列表或本地搜索结果
        assert isinstance(results, list)

    @patch('requests.post')
    def test_deep_research(self, mock_post):
        """测试深度研究"""
        mock_post.side_effect = Exception("API error")

        with patch('builtins.open', create=True) as mock_open:
            config = {
                "deepseek_api_key": "",
                "openai_api_key": ""
            }
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(config)
            mock_open.return_value.__enter__.return_value = mock_file

            learner = ExternalLearner()

        result = learner.deep_research("测试问题")
        assert isinstance(result, dict)
        # 应该包含问题或分析结果
        assert "question" in result or "analysis" in result

    @patch('requests.post')
    def test_analyze_conversation_parsing(self, mock_post):
        """测试对话解析分析"""
        mock_post.side_effect = Exception("API error")

        with patch('builtins.open', create=True) as mock_open:
            config = {
                "deepseek_api_key": "",
                "openai_api_key": ""
            }
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(config)
            mock_open.return_value.__enter__.return_value = mock_file

            learner = ExternalLearner()

        result = learner.analyze_conversation_parsing("你好", "测试上下文")
        assert isinstance(result, dict)
        # 应该包含intent字段
        assert "intent" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])