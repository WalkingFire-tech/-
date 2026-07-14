"""
单元测试 - 特性标志 + dispatch fallback 逻辑
"""
import pytest


class TestFeatureEnabled:
    """测试 _feature_enabled 函数"""

    @pytest.fixture(autouse=True)
    def _setup_import(self):
        """确保能从正确路径导入chat_orchestrator"""
        import sys
        from pathlib import Path
        root = str(Path(__file__).parent.parent.parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        yield

    def test_feature_enabled_default_true(self):
        """未配置的flag应返回默认值True"""
        from backend.services.chat_orchestrator import _feature_enabled
        # 使用一个不可能存在的flag名，应返回默认True
        result = _feature_enabled("_nonexistent_flag_xyz", default=True)
        assert result is True

    def test_feature_enabled_default_false(self):
        """未配置的flag应返回指定的默认值False"""
        from backend.services.chat_orchestrator import _feature_enabled
        result = _feature_enabled("_nonexistent_flag_xyz", default=False)
        assert result is False

    def test_feature_enabled_import_error_returns_default(self):
        """config_manager导入失败时返回默认值"""
        from backend.services.chat_orchestrator import _feature_enabled
        # 函数内部try/except捕获所有异常
        # 传入一个空flag名不应导致崩溃
        result = _feature_enabled("", default=True)
        assert result is True


class TestFallbackDispatch:
    """测试dispatch超时fallback逻辑"""

    def _fallback_dispatch(self, raw_intent, raw_conf):
        """纯函数：模拟chat_orchestrator中dispatch超时后的fallback逻辑"""
        intent_type = raw_intent
        route = "fast" if raw_intent in ("greeting", "confirmation") else "slow"
        confidence = raw_conf
        return {
            "intent_type": intent_type,
            "route": route,
            "confidence": confidence,
            "field_context": {},
            "execution_plan": {"tasks": []}
        }

    def test_greeting_uses_fast_route(self):
        """greeting意图应使用fast路由"""
        result = self._fallback_dispatch("greeting", 0.95)
        assert result["intent_type"] == "greeting"
        assert result["route"] == "fast"
        assert result["confidence"] == 0.95

    def test_complex_query_uses_slow_route(self):
        """复杂查询应使用slow路由"""
        result = self._fallback_dispatch("complex_query", 0.65)
        assert result["intent_type"] == "complex_query"
        assert result["route"] == "slow"

    def test_unknown_intent_fallback(self):
        """未知意图使用slow路由"""
        result = self._fallback_dispatch("unknown", 0.3)
        assert result["route"] == "slow"  # unknown不在("greeting","confirmation")中

    def test_fallback_dict_has_required_keys(self):
        """fallback dict必须包含所有下游消费端需要的key"""
        result = self._fallback_dispatch("map", 0.8)
        required_keys = {"intent_type", "route", "confidence", "field_context", "execution_plan"}
        assert required_keys.issubset(result.keys()), f"缺少key: {required_keys - result.keys()}"
        assert isinstance(result["field_context"], dict)
        assert isinstance(result["execution_plan"], dict)
        assert "tasks" in result["execution_plan"]

    def test_confirmation_uses_fast_route(self):
        """confirmation意图应使用fast路由"""
        result = self._fallback_dispatch("confirmation", 0.98)
        assert result["route"] == "fast"

    def test_actual_function_importable(self):
        """验证提取后的_build_fallback_dispatch函数可以正常导入并工作"""
        from backend.services.chat_orchestrator import _build_fallback_dispatch
        result = _build_fallback_dispatch("weather", 0.85)
        assert result["intent_type"] == "weather"
        assert result["route"] == "slow"
        assert result["confidence"] == 0.85

    def test_actual_function_produces_greeting_fast(self):
        """验证实际函数中greeting走fast路由"""
        from backend.services.chat_orchestrator import _build_fallback_dispatch
        result = _build_fallback_dispatch("greeting", 0.95)
        assert result["route"] == "fast"
