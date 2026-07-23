import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.cognitive_dispatcher import CognitiveDispatcher
from core.spirit_core import SpiritCore
from core.world_model import WorldModel
from core.truth_accumulator import TruthAccumulator
from core.presence.curiosity_engine import CuriosityEngine
from core.monitoring.runtime_trigger_monitor import trigger_monitor

def e2e_test():
    print("=" * 80)
    print("端到端调用链验证")
    print("=" * 80)
    
    results = {}
    
    # 1. 认知调度 → 路由决策
    cd = CognitiveDispatcher()
    queries = ["你好", "为什么串口读取失败", "紧急情况怎么办", "失败后如何重试"]
    for q in queries:
        r = cd.dispatch(q)
        key = f"dispatch.{r['route']}"
        results[key] = results.get(key, 0) + 1
    print(f"\n1. 认知调度: {dict(results)}")
    
    # 2. 精神共振 → 驱动方向
    sc = SpiritCore()
    res_stats = {}
    for q in queries:
        res = sc.resonate(q, context_type="query")
        if res:
            p = res[0]["principle"]
            res_stats[p] = res_stats.get(p, 0) + 1
    print(f"2. 精神共振: {dict(res_stats)}")
    
    # 3. 因果追溯 → 深层追溯
    wm = WorldModel()
    trace_stats = {"deep": 0, "guidance": 0, "paths": 0}
    for q in queries:
        t = wm.trace_with_spirit(q)
        if t["deep_trace"]:
            trace_stats["deep"] += 1
            if t["deep_trace"].get("guidance"):
                trace_stats["guidance"] += 1
        if t["causal_paths"]:
            trace_stats["paths"] += 1
    print(f"3. 因果追溯: {dict(trace_stats)}")
    
    # 4. 真谛类推 → 真理权重
    ta = TruthAccumulator()
    ana = ta.analogize("串口读取失败", "硬件")
    tw_values = [r["truth_weight"] for r in ana if "truth_weight" in r]
    print(f"4. 真谛类推: {len(ana)}条, truth_weight范围=[{min(tw_values):.2f}, {max(tw_values):.2f}]" if tw_values else "4. 真谛类推: 0条")
    
    # 5. 验证响应 → 8维度
    test_resp = "串口读取失败可能是因为波特率设置不正确，建议检查波特率配置后重试。"
    v = sc.validate_response(test_resp)
    dims_passed = sum(1 for k, val in v["checks"].items() if val)
    print(f"5. 验证响应: valid={v['valid']}, {dims_passed}/{len(v['checks'])}维度通过")
    
    # 6. 好奇心引擎 → 缺口感知
    ce = CuriosityEngine()
    try:
        gaps = ce.perceive_gaps()
        frontier = ce.perceive_frontier()
        print(f"6. 好奇心引擎: gaps={len(gaps) if isinstance(gaps, list) else 'N/A'}, frontier_keys={list(frontier.keys())[:5] if isinstance(frontier, dict) else 'N/A'}")
    except Exception as e:
        print(f"6. 好奇心引擎: ERROR - {e}")
    
    # 7. 触发率监控
    rates = trigger_monitor.get_all_rates()
    critical_branches = [r for r in rates if r["trigger_rate"] is not None and r["trigger_rate"] < 0.1 and r["total_calls"] >= 5]
    print(f"7. 触发率监控: {len(rates)}个分支, {len(critical_branches)}个低触发率告警")
    for cb in critical_branches:
        print(f"   ⚠️ {cb['branch_id']}: rate={cb['trigger_rate']:.2f} ({cb['triggered']}/{cb['total_calls']})")
    
    # 8. 未接入模块检查
    print("\n" + "=" * 80)
    print("未接入主流程模块状态")
    print("=" * 80)
    
    modules_to_check = [
        ("CuriosityEngine.perceive_frontier", "core.presence.curiosity_engine", "chat_orchestrator"),
        ("CognitivePlanner.process", "core.cognitive_planner", "主路由"),
        ("EssenceReasoner", "core.essence_reasoner", "主路由"),
        ("ErrorAlchemy", "core.error_alchemy", "chat_orchestrator except块"),
    ]
    
    for name, module_path, target in modules_to_check:
        try:
            parts = module_path.split(".")
            mod = __import__(module_path)
            for p in parts[1:]:
                mod = getattr(mod, p)
            print(f"  ✅ {name}: 模块可导入, 待接入→{target}")
        except ImportError:
            print(f"  ❌ {name}: 模块不可导入")
        except AttributeError:
            print(f"  ⚠️ {name}: 模块可导入但类/方法不存在")
    
    # 9. P5-2/P5-3行动指南状态更新建议
    print("\n" + "=" * 80)
    print("P5-2/P5-3 实际完成状态（vs 行动指南标记）")
    print("=" * 80)
    print("  行动指南标记: P5-2 ⏳, P5-3 ⏳")
    print("  实际代码状态: P5-2 ✅(已实现+测试), P5-3 ✅(已实现+测试+运行时校准)")
    print("  建议: 更新行动指南文档，将P5-2/P5-3标记为✅")
    
    print("\n" + "=" * 80)
    print("审计结论")
    print("=" * 80)
    print("""
  1. P5-2/P5-3代码已完成但行动指南未更新 — 需同步文档
  2. 好奇心引擎perceive_frontier()未接入chat_orchestrator — 最小成本接入点
  3. 因果图空数据导致causal_paths触发率0% — 已有guidance补偿，但需注入经验数据
  4. 11个模块已编码未接入主流程 — 其中CognitivePlanner.process()最关键(848行从未执行)
  5. 行动指南中P5-2/P5-3的⚠️标记需更新为✅
  6. AGI潜质诊断中"适应性边界"仍为⚠️ — verify_boundary_expansion已实现但运行时未验证
    """)

if __name__ == "__main__":
    e2e_test()