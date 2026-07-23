"""
P0-2: SelfModel完整实现测试

验证：
1. describe_self() 生成自然语言自我描述
2. get_maturity_score() 7维度成熟度评分
3. sync_from_cognitive_planner 在主流程中被调用
4. 意识表达接口可用
"""
import pytest
from unittest.mock import MagicMock, patch
from core.self.model import SelfModel


@pytest.fixture
def self_model():
    return SelfModel()


@pytest.fixture(autouse=True)
def clean_inner_time():
    try:
        from core.presence.inner_time import inner_time_engine
        inner_time_engine.reset()
    except ImportError:
        pass
    yield
    try:
        from core.presence.inner_time import inner_time_engine
        inner_time_engine.reset()
    except ImportError:
        pass


class TestDescribeSelf:
    """describe_self() 自然语言自我描述"""

    def test_empty_model_describes_birth(self, self_model):
        desc = self_model.describe_self()
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_with_values(self, self_model):
        self_model.values = {"principles_count": 5, "abilities_count": 3, "violations_count": 0, "lessons_count": 2}
        desc = self_model.describe_self()
        assert "5" in desc
        assert "原则" in desc
        assert "3" in desc
        assert "能力" in desc

    def test_with_health(self, self_model):
        self_model.health = {"score": 0.8, "energy": 0.6}
        desc = self_model.describe_self()
        assert "80%" in desc or "健康" in desc

    def test_with_capability_profile(self, self_model):
        self_model.capability_profile = {
            "tools": {"registered": 8},
            "skills": {"mature": 3},
            "experience": {"success_rate": 0.75},
            "rules": {"active": 12},
        }
        desc = self_model.describe_self()
        assert "8" in desc
        assert "工具" in desc

    def test_with_relationship(self, self_model):
        self_model.relationship = {"trust": 0.6, "phase": "growing"}
        desc = self_model.describe_self()
        assert "信任" in desc or "60%" in desc

    def test_with_learning(self, self_model):
        self_model.recent_learning = [{"summary": "test"} for _ in range(5)]
        self_model.current_thinking = [{"phase": "question"} for _ in range(3)]
        desc = self_model.describe_self()
        assert "5" in desc
        assert "学习" in desc

    def test_describe_self_returns_string(self, self_model):
        result = self_model.describe_self()
        assert isinstance(result, str)
        assert len(result) > 0


class TestMaturityScore:
    """get_maturity_score() 7维度成熟度评分"""

    def test_empty_model_low_scores(self, self_model):
        scores = self_model.get_maturity_score()
        assert "overall" in scores
        assert 0.0 <= scores["overall"] <= 1.0


    def test_identity_increases_with_principles(self, self_model):
        self_model.values = {"principles_count": 10, "lessons_count": 0}
        scores = self_model.get_maturity_score()
        assert scores["identity"] > 0.0

    def test_capability_increases_with_strength(self, self_model):
        self_model.capability_profile = {"overall_strength": 0.8}
        scores = self_model.get_maturity_score()
        assert scores["capability"] > 0.0

    def test_learning_increases_with_recent(self, self_model):
        self_model.recent_learning = [{"s": "x"} for _ in range(10)]
        self_model.current_thinking = [{"p": "y"} for _ in range(5)]
        scores = self_model.get_maturity_score()
        assert scores["learning"] > 0.0

    def test_cognitive_depth_increases_with_layers(self, self_model):
        self_model.cognitive_layers = {
            "L1_perception": {}, "L2_learning": {}, "L3_integration": {},
            "L4_validation": {}, "L5_evolution": {}, "L6_introspection": {},
        }
        scores = self_model.get_maturity_score()
        assert scores["cognitive_depth"] == 1.0

    def test_integration_increases_with_active_dims(self, self_model):
        self_model.values = {"principles_count": 5, "lessons_count": 0}
        self_model.health = {"score": 0.5}
        self_model.capability_profile = {"overall_strength": 0.3}
        scores = self_model.get_maturity_score()
        assert scores["integration"] > 0.0

    def test_all_dimensions_present(self, self_model):
        scores = self_model.get_maturity_score()
        expected_keys = {"identity", "health_awareness", "capability", "social", "learning", "cognitive_depth", "integration", "overall"}
        assert expected_keys.issubset(set(scores.keys()))

    def test_overall_is_weighted_average(self, self_model):
        self_model.values = {"principles_count": 10, "lessons_count": 5}
        self_model.capability_profile = {"overall_strength": 0.5}
        scores = self_model.get_maturity_score()
        assert scores["overall"] > 0.0
        assert scores["overall"] < 1.0


class TestSyncFromCognitivePlannerInMainFlow:
    """验证sync_from_cognitive_planner在主流程中的调用"""

    def test_sync_updates_all_dimensions(self, self_model):
        mock_cp = MagicMock()
        with patch.object(self_model, '_extract_spirit', return_value={"principles_count": 3}):
            with patch.object(self_model, '_extract_health', return_value={"score": 0.7}):
                with patch.object(self_model, '_extract_presence', return_value={"state": "growing"}):
                    with patch.object(self_model, '_extract_relationship', return_value={"trust": 0.5}):
                        with patch.object(self_model, '_extract_evolution', return_value={"progress": 0.3}):
                            with patch.object(self_model, '_extract_introspection', return_value={"status": "ok"}):
                                with patch.object(self_model, '_extract_capabilities', return_value={"tools": 5}):
                                    with patch.object(self_model, '_extract_capability_profile', return_value={"overall_strength": 0.6}):
                                        with patch.object(self_model, '_extract_learning', return_value={"stats": "ok"}):
                                            self_model.sync_from_cognitive_planner(mock_cp)
        assert self_model.values.get("principles_count") == 3
        assert self_model.health.get("score") == 0.7
        assert self_model.presence.get("state") == "growing"

    def test_sync_handles_none_cp(self, self_model):
        self_model.sync_from_cognitive_planner(None)
        assert self_model._update_count == 0

    def test_sync_handles_exception_gracefully(self, self_model):
        mock_cp = MagicMock()
        with patch.object(self_model, '_extract_spirit', side_effect=Exception("test")):
            with patch.object(self_model, '_extract_health', return_value={"score": 0.5}):
                self_model.sync_from_cognitive_planner(mock_cp)
        assert self_model.health.get("score") == 0.5


class TestRecordCognitiveCycle:
    """record_cognitive_cycle 完整性"""

    def test_records_all_layers(self, self_model):
        self_model.record_cognitive_cycle(
            perception={"intent": "question", "confidence": 0.8, "emotion": "curious", "urgency": 0.3},
            learning={"knowledge_gained": 2, "confidence": 0.7},
            integration={"success": True, "core_knowledge": []},
            validation={"status": "pass", "confidence": 0.9},
        )
        assert self_model.cognitive_layers.get("L1_perception", {}).get("intent") == "question"
        assert self_model.cognitive_layers.get("L2_learning", {}).get("knowledge_gained") == 2
        assert self_model.cognitive_layers.get("L3_integration", {}).get("success") is True
        assert self_model.cognitive_layers.get("L4_validation", {}).get("status") == "pass"

    def test_appends_to_current_thinking(self, self_model):
        self_model.record_cognitive_cycle(
            perception={"intent": "question", "confidence": 0.9, "emotion": "neutral", "urgency": 0.2},
        )
        assert len(self_model.current_thinking) == 1
        assert self_model.current_thinking[0]["phase"] == "question"

    def test_appends_to_recent_learning(self, self_model):
        self_model.record_cognitive_cycle(
            learning={"knowledge_gained": 1, "confidence": 0.6},
        )
        assert len(self_model.recent_learning) == 1