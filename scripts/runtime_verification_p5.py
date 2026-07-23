"""运行时验证脚本 — P5-2/P5-3运行时校准"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from core.world_model import WorldModel
from core.truth_accumulator import TruthAccumulator
from core.spirit_core import SpiritCore
from core.cognitive_dispatcher import CognitiveDispatcher

QUERIES = [
    "为什么串口读取会失败",
    "如何优化GPS数据解析",
    "紧急情况下系统崩溃怎么办",
    "分析一下硬件连接超时的原因",
    "失败后重试的方法是什么",
    "你好",
    "不可能完成这个任务但可以尝试其他方法",
    "所有问题都必须立即解决",
    "为什么会出现矛盾的结果",
    "困惑时应该怎么处理",
]

def test_trace_with_spirit():
    print("=" * 80)
    print("1. trace_with_spirit 运行时验证")
    print("=" * 80)
    wm = WorldModel()
    deep_count = 0
    path_count = 0
    for q in QUERIES:
        r = wm.trace_with_spirit(q)
        res_count = len(r["resonances"])
        top = r["resonances"][0]["principle"] if r["resonances"] else "none"
        top_str = r["resonances"][0]["strength"] if r["resonances"] else 0
        paths = len(r["causal_paths"])
        deep = bool(r["deep_trace"])
        fb = r["truth_feedback"]["action"]
        if deep:
            deep_count += 1
        path_count += paths
        print(f"  Q: {q[:25]:25s} | res={res_count} top={top:25s} str={top_str:.2f} | paths={paths} deep={deep} fb={fb}")
    print(f"\n  汇总: deep_trace触发率={deep_count}/{len(QUERIES)} ({deep_count/len(QUERIES)*100:.0f}%), 平均因果路径={path_count/len(QUERIES):.1f}")

def test_truth_weight_distribution():
    print("\n" + "=" * 80)
    print("2. 真理权重分布校准")
    print("=" * 80)
    ta = TruthAccumulator()
    try:
        from infrastructure.database_manager import DatabaseManager
        db = DatabaseManager.get(ta.db_path)
        rows = db.query("SELECT name, level FROM truths WHERE is_active=1")
    except Exception:
        rows = []
    
    weights = []
    level_groups = {"L4": [], "L3": [], "L2": [], "L1": []}
    for row in rows:
        name = row["name"] if isinstance(row, dict) else row[0]
        level = row["level"] if isinstance(row, dict) else row[1]
        tw = ta.compute_truth_weight(name)
        weights.append(tw)
        level_groups.setdefault(level, []).append(tw)
    
    if not weights:
        print("  无真谛数据")
        return
    
    avg = sum(weights) / len(weights)
    min_w = min(weights)
    max_w = max(weights)
    spread = max_w - min_w
    print(f"  真谛总数: {len(weights)}")
    print(f"  权重范围: [{min_w:.2f}, {max_w:.2f}]")
    print(f"  平均权重: {avg:.2f}")
    print(f"  权重分散度: {spread:.2f}")
    
    bins = {"<0.3": 0, "0.3-0.4": 0, "0.4-0.5": 0, "0.5-0.6": 0, "0.6-0.7": 0, ">=0.7": 0}
    for w in weights:
        if w < 0.3: bins["<0.3"] += 1
        elif w < 0.4: bins["0.3-0.4"] += 1
        elif w < 0.5: bins["0.4-0.5"] += 1
        elif w < 0.6: bins["0.5-0.6"] += 1
        elif w < 0.7: bins["0.6-0.7"] += 1
        else: bins[">=0.7"] += 1
    print(f"  分布: {json.dumps(bins)}")
    
    for level, ws in level_groups.items():
        if ws:
            print(f"  {level}: 平均={sum(ws)/len(ws):.2f}, 数量={len(ws)}")
    
    if spread < 0.15:
        print("  ⚠️ 权重分散度不足，四因素公式可能需要调参")
    else:
        print("  ✅ 权重分散度合理")

def test_call_chain():
    print("\n" + "=" * 80)
    print("3. 闭环调用链完整性核查")
    print("=" * 80)
    
    chain_results = {}
    
    # Step 1: dispatch
    try:
        cd = CognitiveDispatcher()
        dispatch_result = cd.dispatch("为什么串口读取会失败")
        chain_results["dispatch"] = {"ok": True, "route": dispatch_result["route"]}
        print(f"  dispatch: OK, route={dispatch_result['route']}")
    except Exception as e:
        chain_results["dispatch"] = {"ok": False, "error": str(e)}
        print(f"  dispatch: FAIL, error={e}")
    
    # Step 2: resonate
    try:
        sc = SpiritCore()
        resonances = sc.resonate("为什么串口读取会失败", context_type="query")
        chain_results["resonate"] = {"ok": True, "count": len(resonances)}
        print(f"  resonate: OK, count={len(resonances)}")
    except Exception as e:
        chain_results["resonate"] = {"ok": False, "error": str(e)}
        print(f"  resonate: FAIL, error={e}")
    
    # Step 3: trace_with_spirit
    try:
        wm = WorldModel()
        trace_result = wm.trace_with_spirit("为什么串口读取会失败")
        chain_results["trace"] = {"ok": True, "deep": bool(trace_result["deep_trace"])}
        print(f"  trace_with_spirit: OK, deep_trace={bool(trace_result['deep_trace'])}")
    except Exception as e:
        chain_results["trace"] = {"ok": False, "error": str(e)}
        print(f"  trace_with_spirit: FAIL, error={e}")
    
    # Step 4: truth_feedback
    try:
        fb = trace_result.get("truth_feedback", {})
        chain_results["feedback"] = {"ok": True, "action": fb.get("action", "none")}
        print(f"  truth_feedback: OK, action={fb.get('action', 'none')}")
    except Exception as e:
        chain_results["feedback"] = {"ok": False, "error": str(e)}
        print(f"  truth_feedback: FAIL, error={e}")
    
    # Step 5: analogize with truth_weight
    try:
        ta = TruthAccumulator()
        analogize_result = ta.analogize("串口读取失败", "硬件")
        has_tw = all("truth_weight" in r for r in analogize_result) if analogize_result else True
        chain_results["analogize"] = {"ok": True, "count": len(analogize_result), "has_truth_weight": has_tw}
        print(f"  analogize: OK, count={len(analogize_result)}, has_truth_weight={has_tw}")
    except Exception as e:
        chain_results["analogize"] = {"ok": False, "error": str(e)}
        print(f"  analogize: FAIL, error={e}")
    
    # Step 6: validate_response (enhanced logical check)
    try:
        test_response = "串口读取失败可能是因为波特率设置不正确，建议检查波特率配置后重试。"
        validation = sc.validate_response(test_response)
        chain_results["validate"] = {"ok": True, "valid": validation["valid"], "logical": validation["checks"].get("logical", None)}
        print(f"  validate_response: OK, valid={validation['valid']}, logical={validation['checks'].get('logical', None)}")
    except Exception as e:
        chain_results["validate"] = {"ok": False, "error": str(e)}
        print(f"  validate_response: FAIL, error={e}")
    
    # Step 7: causal_explainer
    try:
        from core.explainability.causal_explainer import CausalExplainer
        explanation = CausalExplainer.explain_trace(trace_result)
        chain_results["explainer"] = {"ok": True, "has_output": explanation is not None}
        print(f"  causal_explainer: OK, has_output={explanation is not None}")
    except Exception as e:
        chain_results["explainer"] = {"ok": False, "error": str(e)}
        print(f"  causal_explainer: FAIL, error={e}")
    
    # Summary
    all_ok = all(v["ok"] for v in chain_results.values())
    broken = [k for k, v in chain_results.items() if not v["ok"]]
    print(f"\n  调用链完整性: {'✅ 全部贯通' if all_ok else '❌ 断点: ' + ', '.join(broken)}")

if __name__ == "__main__":
    test_trace_with_spirit()
    test_truth_weight_distribution()
    test_call_chain()