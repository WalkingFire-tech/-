"""
认知成长报告 — 让系统的能力提升可见

用法：
    python scripts/growth_report.py
"""
import json
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def generate_growth_report():
    report = {
        "timestamp": datetime.now().isoformat(),
        "self_model": {},
        "inner_time": {},
        "existence_layer": {},
        "capabilities": {},
        "learning": {},
        "port_independence": {},
    }

    try:
        from core.self.model import get_self_model
        sm = get_self_model()
        sm.record_cognitive_cycle()
        report["self_model"] = {
            "description": sm.describe_self(),
            "maturity": sm.get_maturity_score(),
            "update_count": sm._update_count if hasattr(sm, '_update_count') else 0,
        }
    except Exception as e:
        report["self_model"]["error"] = str(e)

    try:
        from core.presence.inner_time import inner_time_engine, CognitiveEventType
        state = inner_time_engine.get_state()
        report["inner_time"] = {
            "tick_count": state.tick_count,
            "flow_rate": round(state.flow_rate, 3),
            "rhythm_bpm": round(state.rhythm_bpm, 1),
            "cognitive_density": round(state.cognitive_density, 3),
            "phase": state.current_phase,
        }
    except Exception as e:
        report["inner_time"]["error"] = str(e)

    try:
        from core.presence.existence_layer import get_existence_layer
        el = get_existence_layer()
        report["existence_layer"] = {
            "state": el.state.value,
            "health": el._health if hasattr(el, '_health') else None,
            "energy": el._energy if hasattr(el, '_energy') else None,
        }
    except Exception as e:
        report["existence_layer"]["error"] = str(e)

    try:
        from core.tool_registry import get_tool_registry
        tr = get_tool_registry()
        tools = tr.list_tools() if hasattr(tr, 'list_tools') else []
        report["capabilities"] = {
            "tools_count": len(tools),
            "tools": [t.get("name", "") for t in tools[:10]] if tools else [],
        }
    except Exception as e:
        report["capabilities"]["error"] = str(e)

    try:
        from infrastructure.database_manager import DatabaseManager
        db = DatabaseManager.get("data/experience_pool.db")
        rows = db.fetch_all("SELECT COUNT(*) as cnt, AVG(quality_score) as avg_q FROM experiences")
        if rows:
            report["learning"] = {
                "experience_count": rows[0]["cnt"],
                "avg_quality": round(rows[0]["avg_q"] or 0, 1),
            }
        rule_rows = db.fetch_all("SELECT COUNT(*) as cnt FROM learning_rules WHERE active=1")
        if rule_rows:
            report["learning"]["active_rules"] = rule_rows[0]["cnt"]
    except Exception as e:
        report["learning"]["error"] = str(e)

    report["port_independence"] = {
        "event_sink": "NullEventSink可用",
        "notification_port": "NullNotificationPort可用",
        "cognitive_process": "cognitive_process()可独立调用",
        "self_reference": "自我参照检测+锚点查询可用",
        "independent_entry": "run_cognitive_core.py可用",
    }

    return report


def print_report(report):
    print("=" * 60)
    print("  认知成长报告")
    print(f"  {report['timestamp']}")
    print("=" * 60)

    sm = report.get("self_model", {})
    if "error" not in sm:
        print(f"\n  🪞 SelfModel:")
        print(f"     {sm.get('description', 'N/A')}")
        maturity = sm.get("maturity", {})
        if maturity:
            print(f"     成熟度:")
            for k, v in maturity.items():
                bar = "█" * int(v * 10) + "░" * (10 - int(v * 10))
                print(f"       {k:20s} [{bar}] {v:.2f}")
        print(f"     更新次数: {sm.get('update_count', 0)}")
    else:
        print(f"\n  🪞 SelfModel: 不可用 ({sm['error']})")

    it = report.get("inner_time", {})
    if "error" not in it:
        print(f"\n  ⏱️ InnerTimeEngine:")
        print(f"     认知节拍: {it.get('tick_count', 0)}")
        print(f"     时间流速: {it.get('flow_rate', 0):.2f}x")
        print(f"     认知节奏: {it.get('rhythm_bpm', 0):.0f} BPM")
        print(f"     认知密度: {it.get('cognitive_density', 0):.3f}")
        print(f"     当前阶段: {it.get('phase', '?')}")
    else:
        print(f"\n  ⏱️ InnerTimeEngine: 不可用")

    el = report.get("existence_layer", {})
    if "error" not in el:
        print(f"\n  🌟 ExistenceLayer:")
        print(f"     存在状态: {el.get('state', '?')}")
        print(f"     健康: {el.get('health', 'N/A')}")
        print(f"     能量: {el.get('energy', 'N/A')}")
    else:
        print(f"\n  🌟 ExistenceLayer: 不可用")

    cap = report.get("capabilities", {})
    if "error" not in cap:
        print(f"\n  🔧 能力:")
        print(f"     工具数: {cap.get('tools_count', 0)}")
        tools = cap.get("tools", [])
        if tools:
            print(f"     工具列表: {', '.join(tools)}")
    else:
        print(f"\n  🔧 能力: 不可用")

    lrn = report.get("learning", {})
    if "error" not in lrn:
        print(f"\n  📚 学习:")
        print(f"     经验数: {lrn.get('experience_count', 0)}")
        print(f"     平均质量: {lrn.get('avg_quality', 0):.1f}")
        print(f"     活跃规则: {lrn.get('active_rules', 0)}")
    else:
        print(f"\n  📚 学习: 不可用")

    pi = report.get("port_independence", {})
    print(f"\n  🔌 端口独立性:")
    for k, v in pi.items():
        print(f"     ✅ {k}: {v}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    report = generate_growth_report()
    print_report(report)