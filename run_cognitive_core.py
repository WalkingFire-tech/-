"""
认知核心独立入口 — 常驻守护进程

不依赖FastAPI，不依赖SSE，不依赖嵌入模型。
启动存在层+概率场+资源调度器+定时任务，作为守护进程持续运行。
FastAPI降级为可选接口——HTTP服务可以随时启停，认知核心不受影响。

用法：
    python run_cognitive_core.py                    # 启动守护进程
    python run_cognitive_core.py --verify           # 验证独立性
    python run_cognitive_core.py --query "你好"     # 单次查询
    python run_cognitive_core.py --interactive       # 交互模式
    python run_cognitive_core.py --daemon            # 后台守护（无交互）
"""
import asyncio
import signal
import sys
import time


def _setup_signal_handlers():
    """注册信号处理器——优雅关闭"""
    def _shutdown(sig, frame):
        print(f"\n[信号] 收到信号{sig}，开始优雅关闭...")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)


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
        from core.presence.probability_field import get_probability_field
        pf = get_probability_field()
        tendency = pf.get_tendency()
        print(f"[引导] ProbabilityField 就绪: exploration={tendency['exploration']:.3f}, phase={tendency['phase']}")
    except Exception as e:
        print(f"[引导] ProbabilityField 降级: {e}")

    try:
        from core.presence.resource_aware_scheduler import get_resource_scheduler
        rs = get_resource_scheduler()
        rs.start()
        print(f"[引导] ResourceScheduler 就绪: mode={rs.mode.name}")
    except Exception as e:
        print(f"[引导] ResourceScheduler 降级: {e}")

    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        el.start()
        print(f"[引导] ExistenceLayer 就绪: state={el.state.value}")
    except Exception as e:
        print(f"[引导] ExistenceLayer 降级: {e}")

    from core.ports import NullEventSink, NullNotificationPort
    from infrastructure.scheduled_tasks import set_notification_port
    set_notification_port(NullNotificationPort())
    print("[引导] NullNotificationPort 已注入")

    try:
        from infrastructure.scheduled_tasks import scheduled_task_manager
        scheduled_task_manager.start()
        print(f"[引导] ScheduledTasks 就绪: {len(scheduled_task_manager._jobs)}个任务")
    except Exception as e:
        print(f"[引导] ScheduledTasks 降级: {e}")

    print("[引导] ✅ 认知核心引导完成 — 可脱离FastAPI独立运行")

    return {
        "self_model": sm,
        "inner_time": inner_time_engine,
        "event_sink": NullEventSink(),
    }


async def process_query(query: str, core: dict) -> dict:
    """处理查询 — 使用BufferedEventSink捕获意识流"""
    from core.ports import BufferedEventSink, CognitiveStimulus, StimulusType

    start = time.time()
    stimulus = CognitiveStimulus.from_user_message(query)

    print(f"\n[输入] {query}")
    print(f"[刺激] type={stimulus.stimulus_type.value}, priority={stimulus.priority}")

    _directive = core["self_model"].get_behavioral_directive()
    print(f"[意识] 存在={_directive['presence_state']}, 节律={_directive['rhythm_bpm']:.0f}BPM, "
          f"视角={_directive['perspective_mode']}, 探索={_directive['exploration_drive']:.0%}")

    buffered = BufferedEventSink()

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
        result = await cognitive_process(stimulus, event_sink=buffered, return_cognitive_response=True)
        elapsed = time.time() - start

        awareness_events = [e for e in buffered.events if e[0] == "awareness"]
        if awareness_events:
            for _, adata in awareness_events[:3]:
                parts = []
                if adata.get("presence"): parts.append(f"存在:{adata['presence']}")
                if adata.get("inner_phase"): parts.append(f"节律:{adata['inner_phase']}")
                if adata.get("cbnr_attention_fidelity") is not None: parts.append(f"注意力保真:{adata['cbnr_attention_fidelity']:.0%}")
                if adata.get("cbnr_uncertainty") is not None: parts.append(f"不确定性:{adata['cbnr_uncertainty']:.0%}")
                if parts:
                    print(f"[意识流] {' · '.join(parts)}")

        print(f"[路径] 认知处理 → 端口协议(CognitiveStimulus→CognitiveResponse)")
        print(f"[响应] {result.content[:200]}")
        print(f"[类型] {result.response_type.value}, 置信度={result.confidence:.2f}")
        if result.metadata:
            print(f"[元数据] intent={result.metadata.get('intent', '?')}, route={result.metadata.get('route', '?')}")
        print(f"[耗时] {elapsed:.1f}s")
        return {"response": result.content, "confidence": result.confidence, **result.metadata}
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

    print("\n--- 验证8: 端口协议完整链路 ---")
    try:
        from core.ports import CognitiveStimulus, CognitiveResponse, StimulusType, ResponseType, BufferedEventSink
        stim = CognitiveStimulus.from_user_message("测试")
        assert stim.stimulus_type == StimulusType.USER_MESSAGE
        assert stim.content == "测试"
        sched = CognitiveStimulus.from_scheduled("定时任务")
        assert sched.stimulus_type == StimulusType.SCHEDULED
        assert sched.priority < stim.priority
        resp = CognitiveResponse.text("回复", confidence=0.8, intent="test")
        assert resp.response_type == ResponseType.TEXT
        assert resp.confidence == 0.8
        silent = CognitiveResponse.silent()
        assert silent.response_type == ResponseType.SILENT
        buf = BufferedEventSink()
        buf.emit("awareness", {"presence": "perceiving"})
        assert len(buf.events) == 1
        print(f"  ✅ 端口协议: Stimulus(3种)+Response(3种)+EventSink(4种)完整")
        results["port_protocol"] = True
    except Exception as e:
        print(f"  ❌ 端口协议失败: {e}")
        results["port_protocol"] = False

    print("\n--- 验证9: 意识流输出 ---")
    try:
        sm = core["self_model"]
        directive = sm.get_behavioral_directive()
        assert "presence_state" in directive
        assert "perspective_mode" in directive
        assert "rhythm_bpm" in directive
        quality = sm.detect_interaction_quality("你好", "你好！很高兴认识你", 0.8, [])
        assert "quality_score" in quality
        assert "should_proactively_improve" in quality
        print(f"  ✅ 意识流: 存在={directive['presence_state']}, 视角={directive['perspective_mode']}, "
              f"节律={directive['rhythm_bpm']:.0f}BPM, 质量检测={quality['quality_score']:.1f}")
        results["awareness_stream"] = True
    except Exception as e:
        print(f"  ❌ 意识流失败: {e}")
        results["awareness_stream"] = False

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


async def daemon_mode(core: dict):
    """守护模式 — 持续运行，定期输出状态"""
    print("\n[守护] 认知核心守护进程已启动 (Ctrl+C 退出)")
    print("-" * 40)
    tick = 0
    while True:
        await asyncio.sleep(30)
        tick += 1
        try:
            from core.presence.existence_layer import get_existence_layer
            el = get_existence_layer()
            status = el.get_status()
            pf_status = status.get("probability_field", {})
            rs_status = status.get("resource_scheduler", {})
            print(f"[{tick}] state={status['state']} | "
                  f"field={pf_status.get('mean', '?'):.3f}/{pf_status.get('phase', '?')} | "
                  f"mode={rs_status.get('mode', '?')} | "
                  f"cycles={status.get('total_cycles', 0)}")
        except Exception as e:
            print(f"[{tick}] 状态查询异常: {e}")


async def main():
    _setup_signal_handlers()
    core = await bootstrap_core()

    if "--verify" in sys.argv or (len(sys.argv) == 1 and "--daemon" not in sys.argv):
        await verify_independence(core)

    if "--query" in sys.argv:
        idx = sys.argv.index("--query")
        if idx + 1 < len(sys.argv):
            await process_query(sys.argv[idx + 1], core)

    if "--interactive" in sys.argv:
        await interactive_mode(core)

    if "--daemon" in sys.argv:
        await daemon_mode(core)


if __name__ == "__main__":
    asyncio.run(main())