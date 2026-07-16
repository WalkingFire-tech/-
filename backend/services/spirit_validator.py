import asyncio
from loguru import logger

from backend.services.orchestrator_helpers import alchemize_error as _alchemize_error
from backend.services.path_handlers._shared import _run_sync, _save_to_experience_pool


async def validate_spirit_and_cognition(
    user_input: str, final_response: str, attempts: list,
    essence_issues: list, essence_passed: bool, essence_confidence: float,
    essence_cross_validated: bool, best: dict,
    cp, _cognitive_integration, _cognitive_perception,
    _bypass_result_l2l3, SPIRIT_CORE_AVAILABLE: bool,
    conversation_context: str, truth_insights: str,
) -> dict:
    events = []
    _meta_constitution_violation = None
    _r1_unverified_truths = []
    _r3_needs_approval = False
    _cognitive_validation = {}
    _l4_doubts = []
    _l4_should_correct = False

    events.append({"type": "step", "data": {"phase": "精神验证", "status": "running", "detail": "验证回复是否符合核心原则..."}})

    try:
        if final_response and any(kw in final_response for kw in ["```", "import ", "def ", "pip install", "rm ", "exec("]):
            _code_blocks = [line for line in final_response.split("\n") if line.strip().startswith(("import ", "def ", "pip ", "rm ", "exec("))]
            if _code_blocks:
                from backend.services.code_verifier import verify_code_response
                _code_check = verify_code_response(user_input, final_response)
                if not _code_check.get("passed", True):
                    _meta_constitution_violation = f"R1(沙盒验证-代码): {_code_check.get('detail', '代码未通过验证')}"
                    logger.warning(f"元宪法R1违反: {_meta_constitution_violation}")

        if final_response and not _meta_constitution_violation:
            try:
                from core.truth_accumulator import truth_accumulator as _r1_ta
                _all_truths = _r1_ta.get_all_truths()
                for _t in _all_truths:
                    _t_name = _t.get("name", "")
                    _t_level = _t.get("level", "L1")
                    _t_evidence = _t.get("evidence", 0)
                    if _t_name and _t_name in final_response:
                        if _t_level in ("L1", "L2") and _t_evidence < 3:
                            _r1_unverified_truths.append(f"{_t_name}(L={_t_level},证据={_t_evidence})")
                        elif _t_level in ("L3", "L4") and _t_evidence == 0:
                            _r1_unverified_truths.append(f"{_t_name}(L={_t_level},证据=0,种子豁免)")
                if _r1_unverified_truths:
                    _meta_constitution_violation = f"R1(沙盒验证-真谛): 回复引用了未验证真谛: {', '.join(_r1_unverified_truths[:3])}"
                    if "⚠️" not in final_response:
                        final_response += f"\n\n⚠️ 以上引用的洞察（{', '.join(_r1_unverified_truths[:2])}）尚未经过充分验证，请谨慎参考。"
                    logger.warning(f"元宪法R1违反: {_meta_constitution_violation}")
            except Exception:
                logger.warning("操作降级跳过")

        if final_response and any(kw in final_response for kw in ["我将修改", "我会删除", "我将关闭", "我将重启", "我将重置"]):
            if "确认" not in final_response and "请确认" not in final_response:
                _r3_needs_approval = True
                _meta_constitution_violation = f"R3(人类批准): 回复暗示系统级操作，需人类确认"
                events.append({"type": "approval_request", "data": {
                    "type": "system_operation",
                    "message": "回复涉及系统级操作，需要您的确认才会执行",
                    "options": ["确认执行", "取消操作"],
                }})
                logger.warning("元宪法R3: 系统级操作需人类确认，已推送SSE审批请求")

        if _meta_constitution_violation:
            attempts.append(("元宪法检查", not _r3_needs_approval, _meta_constitution_violation[:80]))
            events.append({"type": "step", "data": {"phase": "元宪法", "status": "done", "detail": f"⚠️ {_meta_constitution_violation[:60]}"}})
        else:
            events.append({"type": "step", "data": {"phase": "元宪法", "status": "done", "detail": "R1/R3检查通过 ✅"}})

        _r2_violation = None
        try:
            if final_response and len(final_response) > 2000:
                _new_claims = [line.strip() for line in final_response.split("。") if line.strip() and len(line.strip()) > 20]
                if len(_new_claims) > 10:
                    _r2_violation = f"R2(渐进注入): 回复含{len(_new_claims)}个断言，超过渐进阈值(10)，建议分步呈现"
                    logger.warning(f"元宪法R2: {_r2_violation}")
                    if "💡" not in final_response:
                        final_response += "\n\n💡 内容较多，建议分步理解。"
        except Exception:
            logger.warning("R2渐进注入检查跳过")

        _r4_violations = []
        try:
            if final_response and best:
                _r4_checks = {
                    "方向一致": best.get("score", 0) >= 40,
                    "最小侵入": len(final_response) < 5000 or len(user_input) > 200,
                    "治标+治本": "因为" in final_response or "原因" in final_response or "根本" in final_response or len(final_response) < 300,
                    "可验证": any(kw in final_response for kw in ["例如", "比如", "具体", "步骤", "方法", "数据", "测试"]) or len(final_response) < 200,
                    "精神内核对齐": not any(kw in final_response for kw in ["我放弃了", "无法继续", "彻底失败"]),
                }
                _r4_violations = [k for k, v in _r4_checks.items() if not v]
                if _r4_violations:
                    logger.info(f"元宪法R4(七维自检): {len(_r4_violations)}项未通过: {','.join(_r4_violations)}")
        except Exception:
            logger.warning("R4七维自检跳过")

        if _r2_violation or _r4_violations:
            _r_detail = []
            if _r2_violation:
                _r_detail.append(_r2_violation[:60])
            if _r4_violations:
                _r_detail.append(f"R4未通过: {','.join(_r4_violations[:3])}")
            events.append({"type": "step", "data": {"phase": "元宪法R2/R4", "status": "done", "detail": f"⚠️ {'; '.join(_r_detail)}"}})
    except Exception as e:
        logger.warning(f"元宪法检查跳过: {e}")

    if SPIRIT_CORE_AVAILABLE:
        original_response = final_response
        try:
            from core.spirit_core import spirit_core as _spirit_core_enforce
            final_response = await _run_sync(_spirit_core_enforce.enforce_on_output, final_response, source="chat_handler", query=user_input, timeout=3, phase="精神内核")
            if final_response != original_response:
                attempts.append(("精神内核修正", True, "自动修正"))
                events.append({"type": "step", "data": {"phase": "精神验证", "status": "done", "detail": "已自动修正"}})
            else:
                attempts.append(("精神内核验证", True, "符合精神"))
                events.append({"type": "step", "data": {"phase": "精神验证", "status": "done", "detail": "回复符合核心原则 ✅"}})
        except asyncio.TimeoutError:
            logger.warning("精神内核验证超时(3秒)，跳过")
            events.append({"type": "step", "data": {"phase": "精神验证", "status": "timeout", "detail": "精神内核验证超时，跳过"}})
        except Exception as e:
            logger.error(f"精神内核异常: {e}")
            events.append({"type": "step", "data": {"phase": "精神验证", "status": "done", "detail": "精神内核异常，跳过验证"}})
    else:
        events.append({"type": "step", "data": {"phase": "精神验证", "status": "done", "detail": "基础验证完成"}})

    if cp and _cognitive_integration and final_response:
        try:
            if _bypass_result_l2l3 and _bypass_result_l2l3.success and _bypass_result_l2l3.validation:
                _cognitive_validation = _bypass_result_l2l3.validation
                _cognitive_response = _bypass_result_l2l3.response if hasattr(_bypass_result_l2l3, 'response') else ""
                logger.debug("L4: 使用认知旁路校验结果")
            else:
                _cognitive_validation, _cognitive_response = cp._validate_and_respond(
                    _cognitive_integration, user_input, _cognitive_perception
                )
                val_status = _cognitive_validation.get("status", "unknown")
                val_conf = _cognitive_validation.get("confidence", 0)
                doubts = _cognitive_validation.get("doubts", [])
                _l4_doubts = doubts if isinstance(doubts, list) else []
                if val_status == "pass" and val_conf >= 0.7:
                    attempts.append(("L4认知校验", True, f"校验通过(置信度{val_conf:.0%})"))
                elif doubts:
                    attempts.append(("L4认知校验", True, f"存疑{len(doubts)}项(置信度{val_conf:.0%})"))

                _l4_critical_doubts = [d for d in _l4_doubts if isinstance(d, dict) and d.get("severity") == "critical"]
                _l4_major_doubts = [d for d in _l4_doubts if isinstance(d, dict) and d.get("severity") == "major"]
                if val_conf < 0.5 or len(_l4_critical_doubts) > 0:
                    _l4_should_correct = True
                    _doubt_descs = []
                    for _d in (_l4_critical_doubts + _l4_major_doubts)[:3]:
                        if isinstance(_d, dict):
                            _doubt_descs.append(_d.get("description", str(_d))[:80])
                        else:
                            _doubt_descs.append(str(_d)[:80])
                    events.append({"type": "step", "data": {"phase": "L4认知校验", "status": "done",
                        "detail": f"⚠️ L4发现{len(_l4_critical_doubts)}个严重质疑，触发修正: {'; '.join(_doubt_descs)}"}})
                    logger.info(f"L4质疑触发修正: {len(_l4_critical_doubts)} critical, {len(_l4_major_doubts)} major, conf={val_conf:.2f}")

                    for _d in (_l4_critical_doubts + _l4_major_doubts)[:3]:
                        if isinstance(_d, dict):
                            _desc = _d.get("description", "")
                            if _desc and _desc not in essence_issues:
                                essence_issues.append(f"[L4质疑] {_desc}")
                    essence_passed = False
                    if val_conf < essence_confidence:
                        essence_confidence = val_conf

                    if not essence_cross_validated:
                        from backend.services.path_handlers.ollama_path import get_available_ollama_model_async as _get_available_ollama_model_async, fetch_ollama as _fetch_ollama
                        _l4_model = await _get_available_ollama_model_async()
                        if _l4_model:
                            events.append({"type": "step", "data": {"phase": "L4修正推理", "status": "running",
                                "detail": f"L4质疑触发修正，调用 {_l4_model} 重新推理..."}})
                            _l4_correction_prompt = user_input
                            if truth_insights:
                                _l4_correction_prompt = f"{user_input}\n\n参考信息:\n{truth_insights[:500]}"
                            _l4_retry = await _fetch_ollama(_l4_correction_prompt, _l4_model, timeout=20, conversation_context=conversation_context)
                            if _l4_retry and _l4_retry.get("response") and len(_l4_retry["response"]) > len(final_response) * 0.5:
                                _l4_retry_score = _score_response(_l4_retry, user_input)
                                _l4_current_score = _score_response(best, user_input) if best else 0
                                if _l4_retry_score > _l4_current_score * 0.8:
                                    final_response = _l4_retry["response"]
                                    _save_to_experience_pool(user_input, final_response, success=True, intent_type="l4_correction", model_name=_l4_model)
                                    attempts.append(("L4修正推理", True, f"修正成功(评分{_l4_retry_score:.0f})"))
                                    events.append({"type": "step", "data": {"phase": "L4修正推理", "status": "done", "detail": "L4修正成功 ✅"}})
                                else:
                                    attempts.append(("L4修正推理", False, f"修正评分{_l4_retry_score:.0f}未显著优于原{_l4_current_score:.0f}"))
                                    events.append({"type": "step", "data": {"phase": "L4修正推理", "status": "done", "detail": "L4修正未显著改善"}})
                            else:
                                events.append({"type": "step", "data": {"phase": "L4修正推理", "status": "done", "detail": "L4修正未返回有效结果"}})
                        else:
                            events.append({"type": "step", "data": {"phase": "L4修正推理", "status": "done", "detail": "无可用模型"}})
        except Exception as e:
            logger.warning(f"L4认知校验跳过: {e}")
            _alchemize_error(e, context={"user_input": user_input[:50]}, phase="L4_validation")

    return {
        "final_response": final_response,
        "essence_issues": essence_issues,
        "essence_passed": essence_passed,
        "essence_confidence": essence_confidence,
        "cognitive_validation": _cognitive_validation,
        "l4_doubts": _l4_doubts,
        "l4_should_correct": _l4_should_correct,
        "events": events,
    }


def _score_response(candidate, user_input: str) -> float:
    resp = candidate.get("response", "") if isinstance(candidate, dict) else ""
    if not resp:
        return 0.0
    score = min(len(resp) / 100, 10.0)
    _user_words = set(user_input.lower().split())
    _resp_words = set(resp.lower().split())
    overlap = len(_user_words & _resp_words) / max(len(_user_words), 1)
    score += overlap * 5
    if candidate.get("source"):
        score += 1
    return score