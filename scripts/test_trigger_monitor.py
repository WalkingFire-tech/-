import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.world_model import WorldModel
from core.spirit_core import SpiritCore
from core.monitoring.runtime_trigger_monitor import trigger_monitor

wm = WorldModel()
sc = SpiritCore()

queries = ["为什么串口读取会失败", "失败后重试的方法", "你好", "不可能完成但可以尝试", "为什么会出现矛盾"]
for q in queries:
    wm.trace_with_spirit(q)
    sc.resonate(q, context_type="query")
    sc.validate_response(f"关于{q}的分析：建议从根本原因出发解决问题。")

rates = trigger_monitor.get_all_rates()
print("=== 触发率监控 ===")
for r in rates:
    if r["total_calls"] > 0:
        tr = r["trigger_rate"] if r["trigger_rate"] is not None else 0
        er = r["empty_rate"] if r["empty_rate"] is not None else 0
        print(f"  {r['branch_id']:45s} rate={tr:.2f} empty={er:.2f} total={r['total_calls']}")

alerts = trigger_monitor.check_alerts()
if alerts:
    print("\n=== 告警 ===")
    for a in alerts:
        print(f"  [{a['severity']}] {a['message']}")
else:
    print("\n无告警")