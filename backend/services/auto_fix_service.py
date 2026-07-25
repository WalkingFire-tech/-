import asyncio
from loguru import logger


def never_give_up_response(user_input: str, attempts: list) -> str:
    try:
        from core.cognition.failure_classifier import FailureClassifier, FailureCategory
        failed_methods = [a[0] for a in attempts if isinstance(a, tuple) and len(a) >= 2 and not a[1]]
        if failed_methods:
            FailureClassifier.classify_and_fix_sync(
                {"status": "knowledge_gap"}, user_input,
                {"failed_methods": failed_methods[:5], "total_attempts": len(attempts)})
    except Exception as e:
        logger.warning(f"操作降级跳过: {e}")
    try:
        from core.spirit_core import spirit_core
        attempt_dicts = []
        for a in attempts:
            if isinstance(a, tuple) and len(a) >= 2:
                attempt_dicts.append({"method": a[0], "success": a[1], "error": a[2] if len(a) > 2 else ""})
            elif isinstance(a, dict):
                attempt_dicts.append(a)
        return spirit_core.ensure_meaningful_response(user_input, attempt_dicts)
    except Exception:
        failed_names = [a[0] for a in attempts if isinstance(a, tuple) and len(a) >= 2 and not a[1]]
        if failed_names:
            return f"我尝试了{len(attempts)}种方法（{', '.join(failed_names[:4])}均未成功），但我不打算放弃。此问题已记入学习清单，我会持续思考。你可以换个方式提问或提供更多背景，我们一起解决。"
        return f"关于「{user_input[:30]}」，我暂时还没找到最佳答案，但我在持续思考。换个角度试试？"


async def run_persistent_solve(user_input, attempts, conversation_context,
                               truth_insights, intent_type, phase_label, emit_fn):
    from backend.services.persistent_solver import persistent_solve, review_solution
    ps_events = []

    def _ps_collect(event_type, data):
        ps_events.append((event_type, data))

    ps_response, ps_new_attempts, ps_solved = await persistent_solve(
        user_input, attempts,
        conversation_context=conversation_context,
        truth_insights=truth_insights,
        emit_fn=_ps_collect,
        intent_type=intent_type,
    )
    for et, ed in ps_events:
        await emit_fn(et, ed)
    attempts.extend(ps_new_attempts)
    if ps_solved and ps_response:
        final_response = ps_response
        attempts.append((phase_label, True, f"第{len(ps_new_attempts)}轮成功"))
        await review_solution(user_input, ps_response, attempts, True)
        return final_response, True
    else:
        final_response = ps_response or never_give_up_response(user_input, attempts)
        attempts.append((phase_label, False, f"{len(ps_new_attempts)}轮后未解决"))
        return final_response, False


async def auto_fix_checkpoint(attempts: list, methodology: dict, user_input: str,
                              intent_type: str, checkpoint_name: str = "") -> dict:
    recent_failures = [(src, ok, detail) for src, ok, detail in attempts if not ok]
    if not recent_failures:
        return {"fixes_applied": 0}

    fixes_applied = 0
    patches_applied = []

    for src, _, detail in recent_failures[-3:]:
        try:
            from core.cognition.failure_classifier import FailureClassifier
            reflection = {
                "status": "execution_failure",
                "reason": f"{src}: {detail}",
                "source": src,
            }
            fix_result = await FailureClassifier.classify_and_fix(
                reflection, user_input,
                context={"intent_type": intent_type, "checkpoint": checkpoint_name},
            )
            auto_fix = fix_result.get("auto_fix_result", {})
            if auto_fix.get("fix_applied") and auto_fix.get("methodology_patch"):
                methodology.update(auto_fix["methodology_patch"])
                patches_applied.append({
                    "source": src,
                    "category": fix_result.get("category", "").value if hasattr(fix_result.get("category", ""), "value") else str(fix_result.get("category", "")),
                    "patch_keys": list(auto_fix["methodology_patch"].keys()),
                })
                fixes_applied += 1
                logger.info(f"🔧 闭环2修复 [{checkpoint_name}]: {src} → {auto_fix.get('detail', '')[:60]}")
        except Exception as e:
            logger.warning(f"闭环2修复跳过 [{src}]: {e}")

    if fixes_applied > 0:
        logger.info(f"🔧 闭环2检查点 [{checkpoint_name}]: {fixes_applied}个修复已注入methodology")

    return {"fixes_applied": fixes_applied, "patches": patches_applied}
