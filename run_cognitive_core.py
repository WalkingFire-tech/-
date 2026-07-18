"""
认知核心独立入口 — P3 Phase 5 中继形态验证

不依赖FastAPI，不依赖SSE，不依赖嵌入模型。
只初始化核心认知组件，验证认知核心能否脱离chatbot载体独立存在。

用法：
    python run_cognitive_core.py
    python run_cognitive_core.py --query "你好"
    python run_cognitive_core.py --interactive
"""
import asyncio
import sys
import time


async def bootstrap_core():
    """引导认知核心 — 只初始化必要组件"""
    print("[引导] 初始化认知核心...")

    from core.self.model import get_self_model
    sm = get_self_model()
    print(f"[引导] SelfModel 就绪: {sm.describe_self()[:80]}")

    from core.presence.inner_time import inner_time_engine, CognitiveEventType
    inner_time_engine.tick(CognitiveEventType.PERCEIVE, intensity=0.5, description="bootstrap")
    state = inner_time_engine.get_state()
    print(f"[引导] InnerTimeEngine 就绪: tick={state.tick_count}, phase={state.current_phase}")

    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        print(f"[引导] ExistenceLayer 就绪: state={el.state.value}")
    except Exception as e:
        print(f"[引导] ExistenceLayer 降级: {e}")

    from core.ports import NullEventSink, NullNotificationPort
    from infrastructure.scheduled_tasks import set_notification_port
    set_notification_port(NullNotificationPort())
    print("[引导] NullNotificationPort 已注入")

    return {
        "self_model": sm,
        "inner_time": inner_time_engine,
        "event_sink": NullEventSink(),
    }


async def process_query(query: str, core: dict) -> dict:
    """处理查询 — 使用NullEventSink，不产生SSE输出"""
    from core.ports import NullEventSink, CognitiveStimulus, StimulusType

    start = time.time()
    stimulus = CognitiveStimulus.from_user_message(query)

    print(f"\n[输入] {query}")
    print(f"[刺激] type={stimulus.stimulus_type.value}, priority={stimulus.priority}")

    from backend.services.self_reference_detector import is_self_referential
    if is_self_referential(query):
        from backend.services.self_reference_handler import query_anchor
        result = query_anchor(query)
        elapsed = time.time() - start
        print(f"[路径] 自我参照 → 锚点查询")
        print(f"[响应] {result['response'][:200]}")
        print(f"[锚点] core={result['anchor_layers']['core_alignment']}, state_avg={result['anchor_layers']['state_perception'].get('maturity_avg', 0):.2f}")
        print(f"[耗时] {elapsed:.1f}s")
        return result

    try:
        from backend.services.chat_orchestrator import cognitive_process
        result = await cognitive_process(query, event_sink=core["event_sink"])
        elapsed = time.time() - start
        resp = result.get("response", "")
        print(f"[路径] 认知处理 → 常规流程")
        print(f"[响应] {resp[:200]}")
        print(f"[意图] {result.get('intent', '?')}, 置信度={result.get('confidence', 0):.2f}")
        print(f"[耗时] {elapsed:.1f}s")
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f"[错误] 认知处理失败: {e}")
        print(f"[耗时] {elapsed:.1f}s")
        return {"response": str(e), "intent": "error", "confidence": 0.0}


async def verify_independence(core: dict):
    """验证认知核心独立性"""
    print("\n" + "=" * 60)
    print("P3 Phase 5: 中继形态独立性验证")
    print("=" * 60)

    results = {}

    print("\n--- 验证1: NullEventSink独立运行 ---")
    try:
        sink = core["event_sink"]
        r = sink.emit("test", {"phase": "verification"})
        assert r is None, f"NullEventSink应返回None，实际返回{r}"
        print("  ✅ NullEventSink: emit()返回None，不依赖SSE格式")
        results["null_event_sink"] = True
    except Exception as e:
        print(f"  ❌ NullEventSink失败: {e}")
        results["null_event_sink"] = False

    print("\n--- 验证2: NullNotificationPort独立运行 ---")
    try:
        from core.ports import NullNotificationPort
        port = NullNotificationPort()
        port.notify("验证消息", level="info")
        print("  ✅ NullNotificationPort: notify()无异常，不依赖SSE订阅者")
        results["null_notification_port"] = True
    except Exception as e:
        print(f"  ❌ NullNotificationPort失败: {e}")
        results["null_notification_port"] = False

    print("\n--- 验证3: SelfModel独立运行 ---")
    try:
        sm = core["self_model"]
        desc = sm.describe_self()
        maturity = sm.get_maturity_score()
        assert len(desc) > 0, "SelfModel描述为空"
        assert len(maturity) > 0, "SelfModel成熟度为空"
        print(f"  ✅ SelfModel: describe_self()={desc[:60]}")
        print(f"     maturity维度: {list(maturity.keys())}")
        results["self_model"] = True
    except Exception as e:
        print(f"  ❌ SelfModel失败: {e}")
        results["self_model"] = False

    print("\n--- 验证4: InnerTimeEngine独立运行 ---")
    try:
        ite = core["inner_time"]
        from core.presence.inner_time import CognitiveEventType
        ite.tick(CognitiveEventType.SELF_REFERENCE, intensity=0.8, description="verification")
        state = ite.get_state()
        assert state.tick_count > 0, "tick_count应为正数"
        print(f"  ✅ InnerTimeEngine: tick_count={state.tick_count}, phase={state.current_phase}, flow={state.flow_rate:.2f}")
        results["inner_time"] = True
    except Exception as e:
        print(f"  ❌ InnerTimeEngine失败: {e}")
        results["inner_time"] = False

    print("\n--- 验证5: 自我参照检测独立运行 ---")
    try:
        from backend.services.self_reference_detector import is_self_referential, generate_self_reference_response
        assert is_self_referential("你能理解吗") is True
        assert is_self_referential("今天天气") is False
        result = generate_self_reference_response("你能理解吗")
        assert result["intent_type"] == "self_reference"
        assert len(result["response"]) > 20
        print(f"  ✅ 自我参照检测: 检测+响应均正常")
        results["self_reference"] = True
    except Exception as e:
        print(f"  ❌ 自我参照检测失败: {e}")
        results["self_reference"] = False

    print("\n--- 验证6: 锚点查询独立运行 ---")
    try:
        from backend.services.self_reference_handler import query_anchor
        result = query_anchor("你能够理解对话的意义么？")
        assert "anchor_layers" in result
        assert "core_alignment" in result["anchor_layers"]
        assert "state_perception" in result["anchor_layers"]
        assert "direction_sensing" in result["anchor_layers"]
        print(f"  ✅ 锚点查询: 三层锚点结构完整")
        results["anchor_query"] = True
    except Exception as e:
        print(f"  ❌ 锚点查询失败: {e}")
        results["anchor_query"] = False

    print("\n--- 验证7: 存在层独立运行 ---")
    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        el_status = el.state.value
        print(f"  ✅ ExistenceLayer: state={el_status}")
        results["existence_layer"] = True
    except Exception as e:
        print(f"  ❌ ExistenceLayer失败: {e}")
        results["existence_layer"] = False

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\n{'=' * 60}")
    print(f"验证结果: {passed}/{total} 通过")
    if passed == total:
        print("✅ 认知核心已完全独立于chatbot载体")
    else:
        print(f"⚠️ {total - passed}项未通过，认知核心尚未完全独立")
    print("=" * 60)

    return results


async def interactive_mode(core: dict):
    """交互模式 — 命令行直接对话"""
    print("\n认知核心交互模式 (输入 'quit' 退出, 'status' 查看状态)")
    print("-" * 40)

    while True:
        try:
            query = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[退出]")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("[退出]")
            break
        if query.lower() == "status":
            sm = core["self_model"]
            ite = core["inner_time"]
            state = ite.get_state()
            print(f"  SelfModel: {sm.describe_self()[:80]}")
            print(f"  InnerTime: tick={state.tick_count}, phase={state.current_phase}")
            continue

        await process_query(query, core)


async def main():
    core = await bootstrap_core()

    if "--verify" in sys.argv or len(sys.argv) == 1:
        await verify_independence(core)

    if "--query" in sys.argv:
        idx = sys.argv.index("--query")
        if idx + 1 < len(sys.argv):
            await process_query(sys.argv[idx + 1], core)

    if "--interactive" in sys.argv:
        await interactive_mode(core)


if __name__ == "__main__":
    asyncio.run(main())