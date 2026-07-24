"""
响应后认知同步 — 主流程完成后的SelfModel/存在层/学习规则副作用
"""
import time
from loguru import logger


async def sync_post_response(
    user_input: str,
    final_response: str,
    intent_type: str,
    confidence: float,
    route: str,
    cp,
    cognitive_perception: dict = None,
    cognitive_learning: dict = None,
    cognitive_integration: dict = None,
    cognitive_validation: dict = None,
    methodology: dict = None,
    attempts: list = None,
) -> None:
    """响应后认知同步 + 学习规则晋升"""
    try:
        from backend.services.orchestrator_helpers import get_self_model_safe
        _sm = get_self_model_safe()
    except Exception:
        _sm = None

    if _sm:
        try:
            if cp:
                _sm.sync_from_cognitive_planner(cp)
            _sm.record_cognitive_cycle(
                perception=cognitive_perception,
                learning=cognitive_learning,
                integration=cognitive_integration,
                validation=cognitive_validation,
            )
            _sm.update("relationship", {
                "trust": min(0.5 + _sm._update_count * 0.01, 1.0),
                "phase": "established" if _sm._update_count > 10 else "initial",
            })
            if methodology and methodology.get("behavioral_directive"):
                _directive_consumed = {
                    "exploration_drive": methodology.get("exploration_drive", 0.5),
                    "consolidation_need": methodology.get("consolidation_need", 0.0),
                    "preferred_depth": methodology.get("preferred_depth", "moderate"),
                    "perspective_mode": methodology.get("perspective_mode", "companion"),
                    "interaction_confidence": confidence,
                    "interaction_success": confidence > 0.5 and bool(final_response and len(final_response) > 50),
                }
                _sm.record_cognitive_cycle(introspection=_directive_consumed)
                logger.debug(f"🪞 行为指令闭环: directive已反馈给SelfModel, success={_directive_consumed['interaction_success']}")
            if _sm._update_count % 20 == 0:
                _sm.persist_state()

            if attempts:
                try:
                    _path_results = {}
                    _paths_used = []
                    for _a in attempts:
                        if isinstance(_a, (list, tuple)) and len(_a) >= 2:
                            _pn = _a[0]
                            _ps = bool(_a[1])
                            _paths_used.append(_pn)
                            _path_results[_pn] = {
                                "success": _ps,
                                "quality": confidence if _ps else 0.1,
                                "error": _a[2] if len(_a) > 2 and not _ps else None,
                            }
                    if _path_results:
                        _sm.integrate_experience({
                            "intent": user_input[:100],
                            "paths_used": _paths_used,
                            "path_results": _path_results,
                            "final_response": final_response[:200] if final_response else "",
                        })
                except Exception as _ie:
                    logger.debug(f"integrate_experience跳过: {_ie}")
        except Exception as e:
            logger.debug(f"SelfModel同步跳过: {e}")

    try:
        from core.presence.existence_layer import get_existence_layer
        _el = get_existence_layer()
        _el.receive_signal({
            "signal": "interaction_completed",
            "intent_type": intent_type,
            "confidence": confidence,
            "route": route,
            "response_length": len(final_response) if final_response else 0,
        })
    except Exception:
        pass

    try:
        from core.presence.probability_field import get_probability_field
        pf = get_probability_field()
        quality_signal = confidence * (1.0 if final_response and len(final_response) > 50 else 0.5)
        pf.update(signal=quality_signal)
    except Exception:
        pass

    try:
        from core.ports.adapters import get_storage_port
        from infrastructure.rule_matcher import RuleMatcher
        _rule_ctx = {"intent_type": intent_type, "raw_input": user_input}
        _rule_db = get_storage_port("data/learning_rules.db")
        _rule_rows = _rule_db.query("SELECT id, condition, action, status FROM learning_rules WHERE status IN ('active','trial') ORDER BY priority ASC, confidence DESC LIMIT 20")
        _matcher = RuleMatcher()
        for _rr in _rule_rows:
            try:
                if _matcher.evaluate_condition(_rr["condition"], _rule_ctx):
                    _rule_db.execute("UPDATE learning_rules SET apply_count=apply_count+1, last_applied=? WHERE id=?", (time.time(), _rr["id"]), commit=True)
                    if _rr["status"] == "trial":
                        _success = confidence > 0.5 and final_response and len(final_response) > 50
                        _rule_db.execute("UPDATE learning_rules SET trial_count=trial_count+1, trial_success=trial_success+? WHERE id=?", (1 if _success else 0, _rr["id"]), commit=True)
                        _tc_row = _rule_db.query_one("SELECT trial_count, trial_success FROM learning_rules WHERE id=?", (_rr["id"],))
                        if _tc_row and _tc_row[0] >= 5:
                            _sr = _tc_row[1] / _tc_row[0]
                            if _sr >= 0.6:
                                _rule_db.execute("UPDATE learning_rules SET status='active' WHERE id=?", (_rr["id"],), commit=True)
                                logger.info(f"✅ 试用期规则 #{_rr['id']} 激活 (成功率: {_sr:.1%})")
            except Exception:
                pass
    except Exception:
        pass