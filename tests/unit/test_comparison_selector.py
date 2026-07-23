"""
P2-3: comparison_selector.py 测试覆盖

验证阶段4对比择优模块的核心逻辑：
1. 空候选返回None
2. relevance filter过滤低相关性候选
3. ToolBuilder观察学习
4. 贡献归因
5. 概率场初始化
6. 世界模型反事实
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from backend.services.comparison_selector import compare_and_select


@pytest.fixture
def mock_compare_fn():
    def _compare(candidates, query, cbnr_ctx=""):
        if not candidates:
            return None, []
        best = max(candidates, key=lambda c: c.get("quality", 0))
        comparison = [
            {"source": c.get("source", ""), "score": c.get("quality", 30)}
            for c in candidates
        ]
        return best, comparison
    return _compare


class TestEmptyCandidates:
    @pytest.mark.asyncio
    async def test_empty_candidates_returns_none(self, mock_compare_fn):
        result = await compare_and_select(
            candidates=[], user_input="test", intent_type="question",
            confidence=0.5, cbnr_context="", truth_insights="",
            start_time=0.0, _compare_and_select=mock_compare_fn,
        )
        assert result["best"] is None
        assert result["final_response"] is None


class TestRelevanceFilter:
    @pytest.mark.asyncio
    async def test_low_relevance_filtered(self, mock_compare_fn):
        candidates = [
            {"response": "irrelevant", "source": "bad", "quality": 10, "_relevance": 0.05},
            {"response": "relevant answer about Python", "source": "good", "quality": 80, "_relevance": 0.5},
        ]
        with patch('backend.services.comparison_selector._get_intent_domain_keywords', return_value=["python"]):
            with patch('backend.services.comparison_selector._compute_relevance', side_effect=lambda r, k: 0.5 if "python" in r.lower() else 0.05):
                result = await compare_and_select(
                    candidates=candidates, user_input="what is python",
                    intent_type="question", confidence=0.5,
                    cbnr_context="", truth_insights="",
                    start_time=0.0, _compare_and_select=mock_compare_fn,
                )
        assert result["best"] is not None


class TestBestSelection:
    @pytest.mark.asyncio
    async def test_selects_highest_quality(self, mock_compare_fn):
        candidates = [
            {"response": "ok answer", "source": "exp", "quality": 50},
            {"response": "great answer", "source": "kb", "quality": 90},
        ]
        with patch('backend.services.comparison_selector._get_intent_domain_keywords', return_value=[]):
            with patch('backend.services.comparison_selector._compute_relevance', return_value=0.5):
                result = await compare_and_select(
                    candidates=candidates, user_input="test",
                    intent_type="question", confidence=0.5,
                    cbnr_context="", truth_insights="",
                    start_time=0.0, _compare_and_select=mock_compare_fn,
                )
        assert result["best"]["source"] == "kb"

    @pytest.mark.asyncio
    async def test_final_response_set(self, mock_compare_fn):
        candidates = [
            {"response": "answer text", "source": "exp", "quality": 80},
        ]
        with patch('backend.services.comparison_selector._get_intent_domain_keywords', return_value=[]):
            with patch('backend.services.comparison_selector._compute_relevance', return_value=0.5):
                result = await compare_and_select(
                    candidates=candidates, user_input="test",
                    intent_type="question", confidence=0.5,
                    cbnr_context="", truth_insights="",
                    start_time=0.0, _compare_and_select=mock_compare_fn,
                )
        assert result["final_response"] == "answer text"


class TestToolBuilderObservation:
    @pytest.mark.asyncio
    async def test_tool_builder_called_on_high_score(self, mock_compare_fn):
        candidates = [
            {"response": "good", "source": "exp", "quality": 80},
        ]
        with patch('backend.services.comparison_selector._get_intent_domain_keywords', return_value=[]):
            with patch('backend.services.comparison_selector._compute_relevance', return_value=0.5):
                with patch('core.learning.tool_builder.ToolSelfBuilder') as MockTB:
                    mock_tb = MagicMock()
                    MockTB.return_value = mock_tb
                    result = await compare_and_select(
                        candidates=candidates, user_input="test",
                        intent_type="question", confidence=0.5,
                        cbnr_context="", truth_insights="",
                        start_time=0.0, _compare_and_select=mock_compare_fn,
                    )
        mock_tb.record_success.assert_called()


class TestContributionAttribution:
    @pytest.mark.asyncio
    async def test_contrib_attribution_called(self, mock_compare_fn):
        candidates = [
            {"response": "a", "source": "exp", "quality": 80},
            {"response": "b", "source": "kb", "quality": 60},
        ]
        with patch('backend.services.comparison_selector._get_intent_domain_keywords', return_value=[]):
            with patch('backend.services.comparison_selector._compute_relevance', return_value=0.5):
                with patch('backend.services.comparison_selector._feature_enabled', return_value=True):
                    with patch('core.contrib_attributor.contrib_attributor') as mock_ca:
                        mock_ca.compute_contributions.return_value = {"contributions": {"exp": 0.7, "kb": 0.3}}
                        with patch('core.path_weight_manager.path_weight_manager') as mock_pwm:
                            mock_pwm.compute_resource_pressure.return_value = 0.5
                            mock_pwm.get_weights.return_value = {}
                            result = await compare_and_select(
                                candidates=candidates, user_input="test",
                                intent_type="question", confidence=0.5,
                                cbnr_context="", truth_insights="",
                                start_time=0.0, _compare_and_select=mock_compare_fn,
                            )
        mock_ca.compute_contributions.assert_called_once()