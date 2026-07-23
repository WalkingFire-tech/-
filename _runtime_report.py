import json

print("=== 1. Probability Field ===")
from core.presence.probability_field import get_probability_field
pf = get_probability_field()
status = pf.get_status()
print("mean:", status["mean"], "variance:", status["variance"], "entropy:", status["entropy"])
print("phase:", status["phase"], "signal_memory:", status["signal_memory"], "updates:", status["update_count"])
t = status["tendency"]
print("tendency: exploration={:.3f} stability={:.3f} tension={:.3f} activity={:.3f}".format(
    t["exploration"], t["stability"], t["tension"], t["activity"]))
if "auto_tuner" in status:
    at = status["auto_tuner"]
    print("auto_tuner: tunings={}, best_perf={:.3f}".format(at["tuning_count"], at["best_performance"]))
    cp = at["current_params"]
    print("  params: alpha={:.5f} beta={:.5f} gamma={:.5f} delta={:.5f}".format(
        cp["alpha"], cp["beta"], cp["gamma"], cp["delta"]))
    print("  trend:", json.dumps(at["evolution_trend"]))
    print("  next_tuning_in:", at["next_tuning_in"], "s")

print("\n=== 2. Existence Layer ===")
from core.presence.existence_layer import get_existence_layer
el = get_existence_layer()
es = el.get_status()
print("state:", es["state"], "running:", es["running"], "uptime:", es["uptime_seconds"], "s")
print("cycles: total={} awake={} growing={} resting={}".format(
    es["total_cycles"], es["awake_cycles"], es["growing_cycles"], es["resting_cycles"]))
print("signals: pending={} processed={}".format(es["signals_pending"], es["signals_processed"]))
print("silence:", es["silence_duration"], "s")

print("\n=== 3. Signal Accumulator ===")
sa = es.get("signal_accumulator", {})
print("total_checks:", sa.get("total_checks", 0))
print("self_modify_triggers:", sa.get("self_modify_triggers", 0))
print("self_reference_triggers:", sa.get("self_reference_triggers", 0))
print("modify_cooldown:", sa.get("self_modify_cooldown", 0))
print("reference_cooldown:", sa.get("self_reference_cooldown", 0))
print("pattern_ratio:", sa.get("pattern_ratio", 0))
print("need_ratio:", sa.get("need_ratio", 0))

print("\n=== 4. Decision Bridge ===")
from core.presence.probability_decision_bridge import get_probability_decision_bridge
bridge = get_probability_decision_bridge()
bs = bridge.get_status()
print("mapping_count:", bs["mapping_count"])
print("last_decision:", json.dumps(bs["last_decision"]))
print("last_style:", bs["last_style_hint"])

print("\n=== 5. L2 Learning ===")
from core.layers.l2_learning import get_l2_learning
l2 = get_l2_learning()
l2s = l2.get_learning_status()
st = l2s["stats"]
print("attempts:", st["total_learning_attempts"], "successful:", st["total_successful_learning"])
print("knowledge_gained:", st["total_knowledge_gained"], "real_searches:", st["total_real_searches"])
print("search_failures:", st["total_search_failures"], "avg_quality:", st["avg_knowledge_quality"])
l2f = l2.get_knowledge_for_l5()
print("L2->L5: total_knowledge={}, avg_quality={:.1f}, reuse_rate={:.3f}".format(
    l2f["total_knowledge"], l2f["avg_quality"], l2f["knowledge_reuse_rate"]))

print("\n=== 6. L5 Evolution ===")
from core.layers.l5_evolution import get_l5_evolution
l5 = get_l5_evolution()
l5s = l5.get_evolution_status()
print("stage:", l5s["stage"])
print("avg_fitness:", l5s["stats"]["avg_fitness"], "trend:", l5s["stats"]["fitness_trend"])
print("gene_evolutions:", l5s["stats"]["gene_evolutions"])
print("successful_mutations:", l5s["stats"]["successful_mutations"])
print("failed_mutations:", l5s["stats"]["failed_mutations"])
print("skills:", l5s["skills_count"])
print("fitness_history:", l5s["fitness"]["history_count"])

genes = l5s["genes"]
print("\nGene values:")
for gid, g in sorted(genes.items()):
    print("  {}: {} = {:.4f} (stage={}, history={})".format(
        gid, g["name"], g["value"], g["stage"], g["history_count"]))

print("\n=== 7. Resource Scheduler ===")
rs = es.get("resource_scheduler", {})
print("mode:", rs.get("mode"), "growth_strategy:", rs.get("growth_strategy", {}).get("description", ""))

print("\n=== 8. Active Perception ===")
try:
    from core.presence.active_perception import get_active_perception_engine
    ape = get_active_perception_engine()
    aps = ape.get_stats()
    print("total_detections:", aps.get("total_detections", 0))
    by_sig = aps.get("by_signal", {})
    for k, v in sorted(by_sig.items()):
        print("  {}: {}".format(k, v))
except Exception as e:
    print("Error:", e)