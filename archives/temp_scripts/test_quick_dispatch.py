from core.cognitive_dispatcher import CognitiveDispatcher
d = CognitiveDispatcher()
r = d.dispatch("如何实现排序算法")
print(f"route={r['route']}, intent={r['intent_type']}")
h = d.get_dispatch_history(3)
print(f"history={len(h)}条")
if h:
    print(f"最新: query={h[0]['query']}, route={h[0]['route']}")