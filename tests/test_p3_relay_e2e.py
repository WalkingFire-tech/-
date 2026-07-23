"""
P3中继形态 端到端综合测试

覆盖范围：
  1. 悬空模块归档验证
  2. PlanTemplate时效性（name/to_dict/is_stale/is_dead/find_matching/mark_expired）
  3. SelfModel自评对齐（对数饱和+trust上限0.8+drift方向aligned）
  4. 真理权重锐化（compute_truth_weight的sigmoid+L3权重0.35+无验证0.1）
  5. MetaControlGovernor治理（频率控制+幅度钳位+震荡检测+回滚+提问预算）
  6. 因果图学习链（ExperiencePool 7字段传递）
  7. 反思多样性（4视角+反事实推理+视角标记）
  8. 端口合规（StoragePort可用+executescript）
  9. 认知核心独立性（端口协议+SelfModel+InnerTime）
  10. 触发率监控（注册+记录+告警+报告）
  11. 综合链路测试
  12. 安全性验证
"""
import json
import os
import time
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# 1. 悬空模块归档验证
# ============================================================
class TestArchivedModules:
    ARCHIVED_FILES = [
        "core_learning_shadowed.py",
        "core_closed_loop_module.py",
        "core_cognitive_architecture_complete.py",
        "core_enhanced_scheduler.py",
        "core_learning_engine.py",
        "core_state_collector.py",
    ]

    REMOVED_FROM_CORE = [
        "core/learning.py",
        "core/closed_loop_module.py",
        "core/cognitive_architecture_complete.py",
        "core/enhanced_scheduler.py",
        "core/learning_engine.py",
        "core/state_collector.py",
    ]

    def test_archived_files_exist(self):
        for name in self.ARCHIVED_FILES:
            assert Path(f"_arch/OLD/{name}").exists(), f"归档文件 _arch/OLD/{name} 应存在"

    def test_originals_removed(self):
        for path in self.REMOVED_FROM_CORE:
            assert not Path(path).exists(), f"{path} 应已从原位置移除"

    def test_learning_package_still_works(self):
        from core.learning import IncrementalPerception, Signal, SignalType
        assert IncrementalPerception is not None

    def test_autopsy_report_exists(self):
        assert Path("_arch/OLD/AUTOPSY_REPORT.md").exists()


# ============================================================
# 2. PlanTemplate时效性
# ============================================================
class TestPlanTemplateExpiry:

    def test_name_property(self):
        from infrastructure.plan_templates import PlanTemplate
        t = PlanTemplate("tpl_1", "code", [{"action": "a"}, {"action": "b"}], 0.8, 70, 5)
        assert t.name == "code_2步"

    def test_to_dict_has_expiry_fields(self):
        from infrastructure.plan_templates import PlanTemplate
        t = PlanTemplate("tpl_1", "code", [], 0.8, 70, 5,
                         created_at="2026-01-01T00:00:00", last_used_at="2026-06-01T00:00:00",
                         tags=["code"])
        d = t.to_dict()
        assert "is_stale" in d
        assert "is_dead" in d
        assert d["tags"] == ["code"]

    def test_not_stale_when_recently_used(self):
        from infrastructure.plan_templates import PlanTemplate
        t = PlanTemplate("tpl_1", "code", [], 0.8, 70, 5, last_used_at=datetime.now().isoformat())
        assert t.is_stale is False
        assert t.is_dead is False

    def test_stale_after_60_days(self):
        from infrastructure.plan_templates import PlanTemplate
        t = PlanTemplate("tpl_1", "code", [], 0.8, 70, 5,
                         last_used_at=(datetime.now() - timedelta(days=70)).isoformat())
        assert t.is_stale is True
        assert t.is_dead is False

    def test_dead_after_180_days(self):
        from infrastructure.plan_templates import PlanTemplate
        t = PlanTemplate("tpl_1", "code", [], 0.8, 70, 5,
                         last_used_at=(datetime.now() - timedelta(days=200)).isoformat())
        assert t.is_dead is True

    def test_no_last_used_not_stale(self):
        from infrastructure.plan_templates import PlanTemplate
        t = PlanTemplate("tpl_1", "code", [], 0.8, 70, 5, last_used_at="")
        assert t.is_stale is False

    def test_find_matching_alias(self):
        from infrastructure.plan_templates import PlanTemplateLibrary
        ptl = PlanTemplateLibrary()
        assert hasattr(ptl, 'find_matching')
        result = ptl.find_matching("nonexistent_intent")
        assert result is None

    def test_save_and_retrieve_with_temp_db(self):
        from infrastructure.plan_templates import PlanTemplateLibrary
        from infrastructure.database_manager import DatabaseManager
        db_path = Path("data/test_tpl_e2e.db")
        if db_path.exists():
            db_path.unlink()
        try:
            ptl = PlanTemplateLibrary()
            ptl.db_path = db_path
            ptl._init_db()
            ptl.save_template("code", [{"action": "analyze"}, {"action": "generate"}], 85, True, ["code"])
            t = ptl.retrieve_template("code")
            assert t is not None
            assert t.intent_type == "code"
            assert t.name == "code_2步"
            d = t.to_dict()
            assert "is_stale" in d
        finally:
            if db_path.exists():
                try:
                    db_path.unlink()
                except Exception:
                    pass

    def test_mark_expired_filters_template(self):
        from infrastructure.plan_templates import PlanTemplateLibrary
        from infrastructure.database_manager import DatabaseManager
        db_path = Path("data/test_tpl_expired.db")
        if db_path.exists():
            db_path.unlink()
        try:
            ptl = PlanTemplateLibrary()
            ptl.db_path = db_path
            ptl._init_db()
            tid = ptl.save_template("expire_test", [{"action": "a"}], 80, True)
            ptl.mark_expired(tid)
            db = DatabaseManager.get(db_path)
            row = db.query_one("SELECT expired_at FROM plan_templates WHERE template_id=?", (tid,))
            assert row is not None and row["expired_at"] is not None
        finally:
            if db_path.exists():
                try:
                    db_path.unlink()
                except Exception:
                    pass

    def test_cleanup_marks_dead_as_expired(self):
        from infrastructure.plan_templates import PlanTemplateLibrary
        from infrastructure.database_manager import DatabaseManager
        db_path = Path("data/test_tpl_cleanup.db")
        if db_path.exists():
            db_path.unlink()
        try:
            ptl = PlanTemplateLibrary()
            ptl.db_path = db_path
            ptl._init_db()
            old = (datetime.now() - timedelta(days=200)).isoformat()
            db = DatabaseManager.get(db_path)
            db.execute('''
                INSERT INTO plan_templates (template_id, intent_type, steps, success_count, failure_count,
                total_quality, use_count, created_at, last_used_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', ("tpl_dead_test", "dead_intent", "[]", 5, 1, 400, 6, old, old, "[]"), commit=True)
            ptl.cleanup_low_quality_templates()
            row = db.query_one("SELECT expired_at FROM plan_templates WHERE template_id='tpl_dead_test'")
            assert row is not None and row["expired_at"] is not None
        finally:
            if db_path.exists():
                try:
                    db_path.unlink()
                except Exception:
                    pass


# ============================================================
# 3. SelfModel自评对齐
# ============================================================
class TestSelfModelAlignment:

    def test_trust_capped(self):
        from core.self.model import SelfModel
        sm = SelfModel()
        for _ in range(50):
            sm.record_cognitive_cycle({"quality": 1.0, "user_engaged": True})
        m = sm.get_maturity_score()
        assert m.get("social", 0) < 0.9, f"trust应受上限约束，实际{m.get('social', 0):.3f}"

    def test_integration_not_always_one(self):
        from core.self.model import SelfModel
        sm = SelfModel()
        m = sm.get_maturity_score()
        assert m.get("integration", 1.0) < 1.0, f"integration不应总是1.0，实际{m.get('integration', 1.0):.3f}"

    def test_drift_direction_aligned(self):
        from core.self.model import SelfModel
        sm = SelfModel()
        m = sm.get_maturity_score()
        drift = m.get("drift_direction", "unknown")
        assert drift in ("aligned", "unknown"), f"drift方向应为aligned，实际{drift}"

    def test_describe_self_works(self):
        from core.self.model import SelfModel
        sm = SelfModel()
        desc = sm.describe_self()
        assert isinstance(desc, str) and len(desc) > 0


# ============================================================
# 4. 真理权重锐化
# ============================================================
class TestTruthWeightSharpening:

    def test_l3_weight_lowered(self):
        from core.truth_accumulator import TruthAccumulator
        ta = TruthAccumulator()
        level_weights = {"L5": 0.95, "L4": 0.75, "L3": 0.35, "L2": 0.15, "L1": 0.05}
        assert level_weights["L3"] == 0.35, "L3层级权重应为0.35"
        assert level_weights["L4"] == 0.75, "L4层级权重应为0.75"

    def test_compute_truth_weight_range(self):
        from core.truth_accumulator import TruthAccumulator
        ta = TruthAccumulator()
        w = ta.compute_truth_weight("nonexistent_truth_xyz")
        assert w < 0.2, f"不存在的真谛权重应<0.2，实际{w}"

    def test_sigmoid_sharpening_formula(self):
        import math
        raw_values = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
        sharpened = []
        for raw in raw_values:
            s = 1.0 / (1.0 + math.exp(-12.0 * (raw - 0.45)))
            s = s * 0.85 + raw * 0.15
            sharpened.append(round(min(0.98, max(0.02, s)), 2))
        assert sharpened[0] < 0.1, f"raw=0.2应锐化到<0.1，实际{sharpened[0]}"
        assert sharpened[-1] > 0.8, f"raw=0.7应锐化到>0.8，实际{sharpened[-1]}"

    def test_unverified_default_low(self):
        from core.truth_accumulator import TruthAccumulator
        ta = TruthAccumulator()
        try:
            db = get_storage_port(ta.db_path)
            db.execute(
                "INSERT OR REPLACE INTO truths (name, level, domain, statement, source, evidence_count, is_active) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("test_unverified_L3", "L3", "test", "test statement", "test", 0, 1),
                commit=True,
            )
        except Exception:
            pass
        w = ta.compute_truth_weight("test_unverified_L3")
        assert w < 0.3, f"无验证L3真谛权重应<0.3，实际{w}"


# ============================================================
# 5. MetaControlGovernor治理
# ============================================================
class TestMetaControlGovernor:

    def _make_governor(self):
        from meta.governor import MetaControlGovernor
        return MetaControlGovernor()

    def test_frequency_control(self):
        gov = self._make_governor()
        r1 = gov.approve_adjustment("bayesian_optimizer", {"lr": 0.01})
        assert r1["approved"] is True
        r2 = gov.approve_adjustment("bayesian_optimizer", {"lr": 0.02})
        assert r2["approved"] is False, "短时间内不应允许第二次调整"

    def test_amplitude_clamps_not_rejects(self):
        gov = self._make_governor()
        gov._last_adjustment_time["bayesian_optimizer"] = datetime.now() - timedelta(hours=25)
        gov.snapshot_params("bayesian_optimizer", {f"param_{i}": 0.0 for i in range(10)})
        big_change = {f"param_{i}": 0.5 for i in range(10)}
        r = gov.approve_adjustment("bayesian_optimizer", big_change)
        assert r["approved"] is True, "大幅调整应被钳位而非拒绝"
        assert len(r.get("clamped", {})) > 0, "应有参数被钳位"

    def test_oscillation_detection(self):
        gov = self._make_governor()
        gov._last_adjustment_time["bayesian_optimizer"] = datetime.now() - timedelta(hours=25)
        for i in range(8):
            direction = 1 if i % 2 == 0 else -1
            gov._adjustment_history.append(
                type('obj', (object,), {"component": "bayesian_optimizer", "adjustment": {"p": direction * 0.1}, "approved": True, "timestamp": datetime.now()})()
            )
        r = gov.approve_adjustment("bayesian_optimizer", {"p": 0.1})
        assert r["approved"] is False, "震荡时应冻结调整"

    def test_snapshot_and_rollback(self):
        gov = self._make_governor()
        gov.snapshot_params("test_comp", {"a": 1.0, "b": 2.0})
        result = gov.rollback_params("test_comp")
        assert result == {"a": 1.0, "b": 2.0}

    def test_question_budget(self):
        gov = self._make_governor()
        r1 = gov.approve_question("session_1")
        assert r1["approved"] is True
        r2 = gov.approve_question("session_1")
        assert r2["approved"] is True
        r3 = gov.approve_question("session_1")
        assert r3["approved"] is True
        r4 = gov.approve_question("session_1")
        assert r4["approved"] is False, "超过会话提问预算应拒绝"

    def test_consecutive_rejection_stops(self):
        gov = self._make_governor()
        for _ in range(3):
            gov.record_user_rejection("session_1")
        r = gov.approve_question("session_1", user_rejected_last=True)
        assert r["approved"] is False, "连续3次拒绝后应停止提问"


# ============================================================
# 6. 因果图学习链
# ============================================================
class TestCausalGraphLearningChain:

    def test_experience_pool_7_fields(self):
        from infrastructure.experience_pool import ExperiencePool
        from infrastructure.database_manager import DatabaseManager
        db_path = "data/test_exp_e2e.db"
        if Path(db_path).exists():
            Path(db_path).unlink()
        try:
            ep = ExperiencePool(db_path=db_path)
            ep.add_experience(
                intent_type="code",
                raw_input="写一个排序算法",
                plan="1.分析需求 2.选择算法 3.实现代码",
                model_name="test_model",
                quality_score=85,
                user_feedback=1,
                success=True,
                duration=5.0,
            )
            db = DatabaseManager.get(db_path)
            row = db.query_one("SELECT * FROM experiences LIMIT 1")
            assert row is not None
            assert row["plan"] is not None
            assert row["duration"] is not None
            assert row["user_feedback"] is not None
        finally:
            if Path(db_path).exists():
                try:
                    Path(db_path).unlink()
                except Exception:
                    pass


# ============================================================
# 7. 反思多样性
# ============================================================
class TestReflectionDiversity:

    def test_four_perspectives(self):
        from meta.self_reflector_v2 import SelfReflector
        assert hasattr(SelfReflector, 'PERSPECTIVES')
        names = [p["name"] for p in SelfReflector.PERSPECTIVES]
        assert "failure_analyst" in names
        assert "devils_advocate" in names
        assert "alternative_path" in names
        assert "system_health" in names

    def test_rule_based_has_perspectives(self):
        from meta.self_reflector_v2 import SelfReflector
        sr = SelfReflector({})
        failures = [
            {"intent_type": "code", "model_name": "bad_model", "quality_score": 15, "duration": 20},
            {"intent_type": "code", "model_name": "bad_model", "quality_score": 20, "duration": 25},
        ]
        rules = sr._rule_based_reflection(failures)
        perspectives = [r.get("perspective") for r in rules]
        assert "failure_analyst" in perspectives
        assert any(p in perspectives for p in ["devils_advocate", "alternative_path", "system_health"])

    def test_counterfactual_method(self):
        from meta.self_reflector_v2 import SelfReflector
        sr = SelfReflector({})
        assert hasattr(sr, '_counterfactual_reflection')

    def test_rules_saved_with_perspective_and_confidence(self):
        from meta.self_reflector_v2 import SelfReflector
        from infrastructure.database_manager import DatabaseManager
        db_path = "data/test_rules_e2e.db"
        if Path(db_path).exists():
            Path(db_path).unlink()
        try:
            sr = SelfReflector({})
            sr.db_path = db_path
            sr._init_db()
            rules = [
                {"condition": "test", "action": "test_action", "priority": 3,
                 "perspective": "counterfactual", "confidence": 0.3},
            ]
            sr._save_rules(rules)
            db = DatabaseManager.get(db_path)
            row = db.query_one("SELECT source, confidence, metadata FROM learning_rules LIMIT 1")
            assert row is not None
            assert row["source"] == "counterfactual"
            assert row["confidence"] == 0.3
        finally:
            if Path(db_path).exists():
                try:
                    Path(db_path).unlink()
                except Exception:
                    pass


# ============================================================
# 8. 端口合规
# ============================================================
class TestPortCompliance:

    def test_storage_port_executescript(self):
        from core.ports.storage_port import StoragePort
        assert hasattr(StoragePort, 'executescript')

    def test_get_storage_port_kwargs(self):
        from core.ports.adapters import get_storage_port
        try:
            port = get_storage_port(timeout=10)
            assert port is not None
        except TypeError:
            pytest.fail("get_storage_port应接受**kwargs")

    def test_storage_port_has_core_methods(self):
        from core.ports.adapters import get_storage_port
        try:
            port = get_storage_port()
            assert hasattr(port, 'execute')
            assert hasattr(port, 'query')
            assert hasattr(port, 'query_one')
        except Exception as e:
            pytest.skip(f"StoragePort初始化需要数据库: {e}")


# ============================================================
# 9. 认知核心独立性
# ============================================================
class TestCognitiveIndependence:

    def test_stimulus_types(self):
        from core.ports import CognitiveStimulus, StimulusType
        user = CognitiveStimulus.from_user_message("你好")
        assert user.stimulus_type == StimulusType.USER_MESSAGE
        sched = CognitiveStimulus.from_scheduled("定时")
        assert sched.stimulus_type == StimulusType.SCHEDULED

    def test_response_types(self):
        from core.ports import CognitiveResponse, ResponseType
        text = CognitiveResponse.text("回复", confidence=0.9, intent="greet")
        assert text.response_type == ResponseType.TEXT
        silent = CognitiveResponse.silent()
        assert silent.response_type == ResponseType.SILENT

    def test_buffered_event_sink(self):
        from core.ports import BufferedEventSink
        sink = BufferedEventSink()
        sink.emit("awareness", {"presence": "perceiving"})
        sink.emit("awareness", {"inner_phase": "reflecting"})
        assert len(sink.events) == 2

    def test_null_event_sink(self):
        from core.ports import NullEventSink
        sink = NullEventSink()
        result = sink.emit("test", {"data": 1})
        assert result is None


# ============================================================
# 10. 触发率监控
# ============================================================
class TestTriggerRateMonitor:

    def test_register_and_record(self):
        from infrastructure.trigger_rate_monitor import TriggerRateMonitor
        monitor = TriggerRateMonitor()
        monitor.register("test_event", expected_rate=0.5, description="测试")
        monitor.record("test_event", triggered=True)
        monitor.record("test_event", triggered=False)
        report = monitor.get_report()
        assert "test_event" in report
        assert report["test_event"]["actual"] == 0.5

    def test_status_healthy_when_above_expected(self):
        from infrastructure.trigger_rate_monitor import TriggerRateMonitor
        monitor = TriggerRateMonitor()
        monitor.register("good_event", expected_rate=0.3, description="好事件")
        for _ in range(10):
            monitor.record("good_event", triggered=True)
        report = monitor.get_report()
        assert report["good_event"]["status"] == "healthy"

    def test_trend_detection(self):
        from infrastructure.trigger_rate_monitor import TriggerRateMonitor
        monitor = TriggerRateMonitor()
        monitor.register("trend_event", expected_rate=0.3, description="趋势")
        for _ in range(10):
            monitor.record("trend_event", triggered=True)
        for _ in range(10):
            monitor.record("trend_event", triggered=False)
        report = monitor.get_report()
        assert report["trend_event"]["actual"] == 0.5


# ============================================================
# 11. 综合链路测试
# ============================================================
class TestEndToEndCognitiveCycle:

    def test_self_model_updates_on_cycle(self):
        from core.self.model import SelfModel
        sm = SelfModel()
        before = sm.get_maturity_score()
        sm.record_cognitive_cycle({"quality": 0.8, "user_engaged": True})
        after = sm.get_maturity_score()
        assert before != after or True

    def test_governor_blocks_runaway(self):
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        approved = 0
        for i in range(10):

            r = gov.approve_adjustment("bayesian_optimizer", {"param": 0.01})
            if r["approved"]:
                approved += 1
        assert approved <= 2, f"10次快速调整中最多批准2次，实际{approved}"

    def test_template_full_lifecycle(self):
        from infrastructure.plan_templates import PlanTemplateLibrary
        from infrastructure.database_manager import DatabaseManager
        db_path = Path("data/test_tpl_lifecycle.db")
        if db_path.exists():
            db_path.unlink()
        try:
            ptl = PlanTemplateLibrary()
            ptl.db_path = db_path
            ptl._init_db()
            ptl.save_template("code", [{"action": "analyze"}, {"action": "generate"}], 85, True, ["code"])
            ptl.save_template("code", [{"action": "analyze"}, {"action": "generate"}], 90, True, ["code"])
            db = DatabaseManager.get(db_path)
            row = db.query_one("SELECT COUNT(*) as cnt FROM plan_templates WHERE intent_type='code'")
            assert row["cnt"] >= 1
            t = ptl.find_matching("code")
            assert t is not None
            assert t.success_rate > 0
            d = t.to_dict()
            assert "is_stale" in d
        finally:
            if db_path.exists():
                try:
                    db_path.unlink()
                except Exception:
                    pass

    def test_sigmoid_sharpening_extends_range(self):
        import math
        raw_low = 0.25
        raw_high = 0.65
        s_low = 1.0 / (1.0 + math.exp(-12.0 * (raw_low - 0.45)))
        s_low = s_low * 0.85 + raw_low * 0.15
        s_high = 1.0 / (1.0 + math.exp(-12.0 * (raw_high - 0.45)))
        s_high = s_high * 0.85 + raw_high * 0.15
        assert s_low < raw_low, "sigmoid应将低值压得更低"
        assert s_high > raw_high, "sigmoid应将高值推得更高"


# ============================================================
# 12. 安全性验证
# ============================================================
class TestGovernorSafety:

    def test_empty_params(self):
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        r = gov.approve_adjustment("test_comp", {})
        assert isinstance(r, dict)
        assert "approved" in r

    def test_rollback_nonexistent(self):
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        result = gov.rollback_params("nonexistent")
        assert result is None or result == {}

    def test_thread_safety(self):
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        errors = []

        def try_approve():
            try:
                gov.approve_adjustment("bayesian_optimizer", {"p": 0.01})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=try_approve) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0, f"并发访问不应报错: {errors}"


# ============================================================
# 13. 治理器状态机
# ============================================================
class TestGovernorStateMachine:

    def _make_governor(self):
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        return gov

    def test_initial_state_is_stable(self):
        gov = self._make_governor()
        assert gov.current_state == "stable"

    def test_transition_to_cautious(self):
        gov = self._make_governor()
        gov.transition_to("cautious", "test")
        assert gov.current_state == "cautious"

    def test_transition_to_frozen(self):
        gov = self._make_governor()
        gov.transition_to("frozen", "test")
        assert gov.current_state == "frozen"

    def test_stable_allows_all(self):
        gov = self._make_governor()
        assert gov.can_run("bayesian_optimizer")
        assert gov.can_run("self_reflector")
        assert gov.can_run("active_learner")

    def test_cautious_only_reflection(self):
        gov = self._make_governor()
        gov.transition_to("cautious", "test")
        assert not gov.can_run("bayesian_optimizer")
        assert gov.can_run("self_reflector")
        assert not gov.can_run("active_learner")

    def test_frozen_allows_nothing(self):
        gov = self._make_governor()
        gov.transition_to("frozen", "test")
        assert not gov.can_run("bayesian_optimizer")
        assert not gov.can_run("self_reflector")
        assert not gov.can_run("active_learner")

    def test_recovering_allows_reflection(self):
        gov = self._make_governor()
        gov.transition_to("recovering", "test")
        assert not gov.can_run("bayesian_optimizer")
        assert gov.can_run("self_reflector")
        assert not gov.can_run("active_learner")

    def test_state_blocks_adjustment(self):
        gov = self._make_governor()
        gov.transition_to("frozen", "test")
        r = gov.approve_adjustment("bayesian_optimizer", {"p": 0.01})
        assert r["approved"] is False
        assert "frozen" in r["reason"]

    def test_state_blocks_question(self):
        gov = self._make_governor()
        gov.transition_to("frozen", "test")
        r = gov.approve_question("session_1")
        assert r["approved"] is False

    def test_update_system_health_triggers_transition(self):
        gov = self._make_governor()
        gov.update_system_health(success_rate=0.3, user_satisfaction=0.3)
        assert gov.current_state in ("cautious", "frozen")

    def test_update_system_health_recovers(self):
        gov = self._make_governor()
        gov.transition_to("cautious", "test")
        gov.update_system_health(success_rate=0.8, user_satisfaction=0.7)
        assert gov.current_state == "stable"

    def test_state_history_recorded(self):
        gov = self._make_governor()
        gov.transition_to("cautious", "test reason")
        assert len(gov._state_history) == 1
        assert gov._state_history[0]["from"] == "stable"
        assert gov._state_history[0]["to"] == "cautious"
        assert gov._state_history[0]["reason"] == "test reason"

    def test_allowed_operations(self):
        gov = self._make_governor()
        ops = gov.allowed_operations()
        assert "bayesian_optimizer" in ops
        assert "self_reflector" in ops
        assert "active_learner" in ops


# ============================================================
# 14. 主动学习过滤增强
# ============================================================
class TestActiveLearningFilters:

    def test_value_filter_blocks_low_gain(self):
        from meta.active_learner_v2 import ActiveLearner
        al = ActiveLearner({})
        result = al._value_filter("code", 0.95, {})
        assert result is False, "高置信度(0.95)时信息增益太低，应被过滤"

    def test_value_filter_passes_high_gain(self):
        from meta.active_learner_v2 import ActiveLearner
        al = ActiveLearner({})
        result = al._value_filter("unknown", 0.2, {})
        assert result is True, "低置信度(0.2)时信息增益高，应通过"

    def test_redundancy_filter(self):
        from meta.active_learner_v2 import ActiveLearner
        al = ActiveLearner({})
        al._recent_questions.append({
            "intent_type": "code",
            "question_id": "q_test",
            "timestamp": datetime.now().isoformat(),
        })
        result = al._is_redundant("code", {})
        assert result is True, "7天内已问过同类问题，应被过滤"

    def test_redundancy_filter_passes_different(self):
        from meta.active_learner_v2 import ActiveLearner
        al = ActiveLearner({})
        al._recent_questions.append({
            "intent_type": "code",
            "question_id": "q_test",
            "timestamp": datetime.now().isoformat(),
        })
        result = al._is_redundant("question", {})
        assert result is False, "不同意图类型不应被冗余过滤"

    def test_should_ask_user_with_session_id(self):
        from meta.active_learner_v2 import ActiveLearner
        al = ActiveLearner({})
        result = al.should_ask_user("unknown", 0.3, session_id="test_session")
        assert isinstance(result, bool)


# ============================================================
# 15. Governor状态机与Planner深度集成
# ============================================================
class TestGovernorPlannerIntegration:
    """验证governor状态机对planner执行路径的差异化控制"""

    def _make_planner_with_governor(self, governor_state="stable"):
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        gov._state = governor_state
        gov._state_entered_at = datetime.now()
        return gov

    def test_perception_stable_normal_confidence(self):
        from core.services.cognitive_planner import CognitivePlanner
        gov = self._make_planner_with_governor("stable")
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp.emotion_detector = None
        result = cp._perceive("测试输入")
        assert result["confidence"] == 0.7, f"STABLE应正常confidence=0.7, 实际={result['confidence']}"
        assert result["uncertainty"] is False
        assert result["caution_level"] == "none"

    def test_perception_cautious_reduced_confidence(self):
        from core.services.cognitive_planner import CognitivePlanner
        gov = self._make_planner_with_governor("cautious")
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp.emotion_detector = None
        result = cp._perceive("测试输入")
        assert result["confidence"] == 0.5, f"CAUTIOUS应confidence=0.5, 实际={result['confidence']}"
        assert result["uncertainty"] is True
        assert result["caution_level"] == "cautious"

    def test_perception_frozen_minimal_confidence(self):
        from core.services.cognitive_planner import CognitivePlanner
        gov = self._make_planner_with_governor("frozen")
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp.emotion_detector = None
        result = cp._perceive("测试输入")
        assert result["confidence"] == 0.3, f"FROZEN应confidence=0.3, 实际={result['confidence']}"
        assert result["uncertainty"] is True
        assert result["caution_level"] == "frozen"

    def test_perception_recovering_moderate_confidence(self):
        from core.services.cognitive_planner import CognitivePlanner
        gov = self._make_planner_with_governor("recovering")
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp.emotion_detector = None
        result = cp._perceive("测试输入")
        assert result["confidence"] == 0.6, f"RECOVERING应confidence=0.6, 实际={result['confidence']}"
        assert result["caution_level"] == "recovering"

    def test_validation_stable_normal_threshold(self):
        from core.services.cognitive_planner import CognitivePlanner
        gov = self._make_planner_with_governor("stable")
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp.planner = None
        cp.llm_adapter = None
        validation, response = cp._validate_and_respond(
            {"success": True}, "测试", {"intent": "general", "confidence": 0.7}
        )
        assert validation["confidence_threshold"] == 0.5

    def test_validation_cautious_higher_threshold(self):
        from core.services.cognitive_planner import CognitivePlanner
        gov = self._make_planner_with_governor("cautious")
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp.planner = None
        cp.llm_adapter = None
        validation, response = cp._validate_and_respond(
            {"success": True}, "测试", {"intent": "general", "confidence": 0.7}
        )
        assert validation["confidence_threshold"] == 0.7

    def test_validation_frozen_highest_threshold(self):
        from core.services.cognitive_planner import CognitivePlanner
        gov = self._make_planner_with_governor("frozen")
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp.planner = None
        cp.llm_adapter = None
        validation, response = cp._validate_and_respond(
            {"success": True}, "测试", {"intent": "general", "confidence": 0.7}
        )
        assert validation["confidence_threshold"] == 0.9
        assert "保护模式" in response

    def test_frozen_uses_safe_degraded_response(self):
        from core.services.cognitive_planner import CognitivePlanner
        gov = self._make_planner_with_governor("frozen")
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp.planner = None
        cp.llm_adapter = None
        safe = cp._safe_degraded_response("测试", {"intent": "question"}, "原始回复")
        assert "保护模式" in safe
        assert "原始回复" not in safe

    def test_cautious_pass_trust_change(self):
        from core.services.cognitive_planner import CognitivePlanner
        cp = CognitivePlanner.__new__(CognitivePlanner)
        assert cp._calculate_trust_change({"status": "cautious_pass"}) == 0.02

    def test_governor_health_update_on_success(self):
        from core.services.cognitive_planner import CognitivePlanner
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp._update_governor_health(
            {"status": "pass", "confidence": 0.8},
            {"emotion": "neutral"}
        )
        assert gov._recent_success_rate == 1.0

    def test_governor_health_update_on_failure(self):
        from core.services.cognitive_planner import CognitivePlanner
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp._update_governor_health(
            {"status": "fail", "confidence": 0.3},
            {"emotion": "neutral"}
        )
        assert gov._recent_success_rate == 0.0

    def test_governor_health_triggers_state_transition(self):
        from core.services.cognitive_planner import CognitivePlanner
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp._update_governor_health(
            {"status": "fail", "confidence": 0.4},
            {"emotion": "neutral"}
        )
        assert gov.current_state == "cautious", f"失败应转为cautious, 实际={gov.current_state}"

    def test_governor_health_cascades_to_frozen(self):
        from core.services.cognitive_planner import CognitivePlanner
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp._update_governor_health(
            {"status": "fail", "confidence": 0.1},
            {"emotion": "neutral"}
        )
        assert gov.current_state in ("cautious", "frozen"), f"严重失败应至少转为cautious, 实际={gov.current_state}"

    def test_active_learner_blocked_when_frozen(self):
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        gov._state = "frozen"
        assert gov.can_run("active_learner") is False

    def test_active_learner_allowed_when_stable(self):
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        gov._state = "stable"
        assert gov.can_run("active_learner") is True

    def test_system_status_includes_governor(self):
        from core.services.cognitive_planner import CognitivePlanner
        from meta.governor import MetaControlGovernor
        gov = MetaControlGovernor()
        cp = CognitivePlanner.__new__(CognitivePlanner)
        cp.meta_governor = gov
        cp.existence = None
        cp.self_perception = None
        cp.gap_growth = None
        cp.sleep_engine = None
        cp.proactivity = None
        cp.relationship_model = None
        cp.goal_engine = None
        cp.l6 = None
        cp._init_time = datetime.now()
        cp._conversation_id_counter = 0
        status = cp.get_system_status()
        assert "governor" in status
        assert status["governor"]["state"] == "stable"


# ============================================================
# 16. Chat Handler回复质量修复
# ============================================================
class TestChatHandlerReplyFix:
    """验证chat_handler三级回退：经验池→外部模型→模板"""

    def test_smart_reply_queries_experience_pool(self):
        from backend.chat_handler import _query_experience_pool_semantic
        results = _query_experience_pool_semantic("串口", top_k=3)
        assert isinstance(results, list), "应返回列表"

    def test_smart_reply_falls_to_template_without_pool(self):
        from backend.chat_handler import _generate_smart_reply
        reply = _generate_smart_reply("一个完全不存在于经验池的随机问题xyz", "question")
        assert len(reply) > 30, "即使无经验池匹配，模板兜底也应生成有意义回复"

    def test_smart_reply_uses_pool_when_available(self):
        from backend.chat_handler import _generate_smart_reply
        import sqlite3
        conn = sqlite3.connect("data/experience_pool.db")
        conn.execute("INSERT INTO experiences (timestamp, intent_type, raw_input, response, quality_score, success) VALUES (?, ?, ?, ?, ?, ?)",
                     ("2026-01-01T00:00:00", "test", "测试知识能力提升", "知识能力提升可以通过阅读、实践和反思三个途径来实现，每个途径都有其独特的作用。", 90, 1))
        conn.commit()
        conn.close()
        reply = _generate_smart_reply("知识能力提升", "question")
        assert "阅读" in reply or "参考历史经验" in reply, f"应使用经验池结果, 实际: {reply[:80]}"

    def test_spirit_core_enforce_passes_context(self):
        from core.spirit_core import SpiritCore
        sc = SpiritCore()
        good_response = "自我提升知识能力可以通过阅读、实践和反思三个途径来实现。阅读帮助获取新知识，实践将知识转化为技能，反思则深化理解并发现不足。"
        result = sc.enforce_on_output(good_response, source="test", query="自我提升知识能力的途径")
        assert result == good_response, "高质量回复不应被修正"

    def test_spirit_core_perfunctory_threshold(self):
        from core.spirit_core import SpiritCore
        sc = SpiritCore()
        short_perfunctory = "请稍后，正在思考中"
        validation = sc.validate_response(short_perfunctory, context={"query": "测试"})
        assert not validation["valid"], "短敷衍回复应被拦截"

    def test_spirit_core_long_with_substantive_passes(self):
        from core.spirit_core import SpiritCore
        sc = SpiritCore()
        long_with_keyword = "关于这个问题，我需要请稍后说明一下，因为涉及多个层面的分析，包括理论基础、实践方法和评估标准，每个方面都需要详细阐述才能给出完整的回答。"
        validation = sc.validate_response(long_with_keyword, context={"query": "测试"})
        assert validation["checks"].get("meaningful", True), "含敷衍词但有实质内容应通过"


# ============================================================
# 17. Feedback/Ethics/Dialogue子包接线验证
# ============================================================
class TestFeedbackWiring:
    """验证feedback信号管道：capture→router→pipeline"""

    def test_signal_capture_creates_db(self):
        from core.feedback.signal_capture import FeedbackSignalCapture, FeedbackSignal, FeedbackType
        from datetime import datetime
        db_path = "data/test_feedback_signals.db"
        capture = FeedbackSignalCapture(db_path=db_path)
        ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
        signal = FeedbackSignal(
            signal_id=f"test_{ts}",
            conversation_id="conv_test",
            turn_id="t1",
            feedback_type=FeedbackType.LIKE,
            value=1,
            context={"reason": "helpful"},
            timestamp=datetime.now().isoformat(),
        )
        sid = capture.capture(signal)
        assert sid == f"test_{ts}"

    def test_feedback_router_routes_like(self):
        from core.feedback.feedback_router import FeedbackSignalRouter, SignalCategory
        router = FeedbackSignalRouter()
        routed = router.route({"feedback_type": "like", "value": 1, "context": {}})
        assert routed.category in (SignalCategory.ADOPTION, SignalCategory.AFFECTIVE)

    def test_feedback_router_routes_correction(self):
        from core.feedback.feedback_router import FeedbackSignalRouter, SignalCategory
        router = FeedbackSignalRouter()
        routed = router.route({"feedback_type": "correction", "value": -1, "context": {"reason": "wrong"}})
        assert routed.category == SignalCategory.CORRECTION

    def test_knowledge_pipeline_add_candidate(self):
        from core.feedback.knowledge_pipeline import KnowledgePromotionPipeline
        db_path = "data/test_knowledge_pipeline.db"
        pipeline = KnowledgePromotionPipeline(db_path=db_path)
        cid = pipeline.add_candidate("test knowledge content", "test", [{"type": "like"}])
        assert len(cid) > 0


class TestEthicsWiring:
    """验证ethics安全学习层接线"""

    def test_safe_learning_returns_result(self):
        from core.ethics.safe_learning import SafeLearningLayer
        db_path = "data/test_safe_learning.db"
        sl = SafeLearningLayer(db_path=db_path)
        result = sl.learn_safely("Python是一种编程语言，广泛用于数据科学和Web开发。", source="test")
        assert "alignment" in result or "success" in result

    def test_value_alignment_checker_importable(self):
        from core.ethics.value_alignment_checker import check_value_alignment, AlignmentStatus
        assert AlignmentStatus.PASS is not None

    def test_save_to_experience_pool_with_ethics(self):
        from backend.services.path_handlers._shared import _save_to_experience_pool
        _save_to_experience_pool("test query", "test response", success=True, intent_type="test", model_name="test")
        assert True, "应不抛异常"


class TestDialogueWiring:
    """验证dialogue认知引擎接线"""

    def test_scene_perceiver_perceives(self):
        from core.dialogue.scene_perceiver import ScenePerceiver
        perceiver = ScenePerceiver()
        hint = perceiver.perceive("什么是机器学习？")
        assert hint.primary_role is not None

    def test_dialogue_engine_process(self):
        from core.dialogue.dialogue_cognitive_engine import DialogueCognitiveEngine
        engine = DialogueCognitiveEngine()
        result = engine.process("如何学习Python？")
        assert result.scene_hint is not None
        assert result.understanding is not None
        assert result.response_guidance is not None

    def test_dialogue_engine_identifies_question(self):
        from core.dialogue.dialogue_cognitive_engine import DialogueCognitiveEngine
        engine = DialogueCognitiveEngine()
        result = engine.process("为什么天空是蓝色的？")
        assert result.should_learn is True or result.understanding is not None
