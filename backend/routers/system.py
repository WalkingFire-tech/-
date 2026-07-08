"""
系统管理路由 — stats/introspection/alignment/module/self-assessment/coverage/defense/events/scheduled-tasks/models
"""
import asyncio
import json
from pathlib import Path
from fastapi import APIRouter
from loguru import logger
from infrastructure.database_manager import DatabaseManager

router = APIRouter()

ROOT_DIR = Path(__file__).parent.parent.parent


@router.get("/stats")
async def get_stats():
    stats = {}
    try:
        db = DatabaseManager.get("data/experience_pool.db")

        conn = db._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM experiences")
        stats["experiences"] = cursor.fetchone()[0]

    except Exception:
        stats["experiences"] = 0
    try:
        db = DatabaseManager.get("data/learning_rules.db")

        conn = db._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE status='active'")
        stats["active_rules"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM learning_rules WHERE status='pending'")
        stats["pending_rules"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM learning_rules")
        stats["rules"] = cursor.fetchone()[0]

    except Exception:
        stats["active_rules"] = 0
        stats["pending_rules"] = 0
        stats["rules"] = 0
    try:
        from core.task_queue import task_queue
        stats["task_queue"] = task_queue.get_stats()
    except Exception:
        stats["task_queue"] = {}
    return stats


@router.get("/background-tasks")
async def background_tasks_status():
    try:
        from core.resource_awareness.background_controller import get_background_controller
        return get_background_controller().get_status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/introspection/report")
async def introspection_report():
    try:
        from core.introspector import get_introspector
        report = get_introspector().run_check()
        return report.to_dict()
    except Exception as e:
        return {"error": str(e), "overall_health": 0}


@router.get("/introspection/status")
async def introspection_status():
    try:
        from core.introspector import get_introspector
        return get_introspector().get_status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/introspection/anomalies")
async def introspection_anomalies(limit: int = 20):
    try:
        from core.introspector import get_introspector
        return {"anomalies": get_introspector().get_recent_anomalies(limit)}
    except Exception as e:
        return {"error": str(e), "anomalies": []}


@router.get("/alignment/stats")
async def alignment_stats():
    try:
        from core.alignment_guard import get_alignment_guard
        return get_alignment_guard().get_stats()
    except Exception as e:
        return {"error": str(e), "total": 0, "open": 0}


@router.get("/alignment/deviations")
async def alignment_deviations(limit: int = 20):
    try:
        from core.alignment_guard import get_alignment_guard
        devs = get_alignment_guard().get_open_deviations(limit)
        return {"deviations": [d.to_dict() for d in devs]}
    except Exception as e:
        return {"error": str(e), "deviations": []}


@router.post("/alignment/correct/{dev_id}")
async def alignment_correct(dev_id: int, request: dict = None):
    try:
        from core.alignment_guard import get_alignment_guard
        correction = (request or {}).get("correction", "已修正")
        get_alignment_guard().correct_deviation(dev_id, correction)
        return {"status": "corrected", "dev_id": dev_id}
    except Exception as e:
        return {"error": str(e)}


@router.get("/input-processor/demo")
async def input_processor_demo(text: str = "", memory: float = 0.5, mode: str = "normal"):
    try:
        from core.input_processor import get_input_processor
        if not text:
            return {"error": "请提供text参数"}
        processor = get_input_processor()
        result = processor.process(text, memory_usage=memory, mode=mode)
        return result.to_dict()
    except Exception as e:
        return {"error": str(e)}


@router.get("/module/health")
async def get_module_health():
    try:
        from core.module_health import module_health
        return module_health.get_health_report()
    except Exception:
        return {"healthy": [], "degraded": [], "isolated": [], "unknown": []}


@router.post("/module/clear")
async def clear_module_anomaly(request: dict):
    module_name = request.get("module_name", "")
    if not module_name:
        return {"status": "error", "message": "缺少module_name"}
    try:
        from core.module_health import module_health
        module_health.clear_anomalies(module_name)
        return {"status": "ok", "message": f"模块{module_name}异常已清除"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/system/audit")
async def run_system_audit():
    try:
        from core.system_auditor import system_auditor
        return system_auditor.audit()
    except Exception as e:
        logger.error(f"系统审核失败: {e}")
        return {"error": str(e), "summary": {"total_gaps": 0}}


@router.get("/self-assessment")
async def get_self_assessment():
    try:
        from core.self_assessment import self_assessment
        latest = self_assessment.get_latest()
        if latest:
            return latest
        return self_assessment.assess()
    except Exception as e:
        logger.error(f"自我评估失败: {e}")
        return {"error": str(e), "overall": {"score": 0, "level": "error"}}


@router.get("/self-assessment/history")
async def get_assessment_history():
    try:
        from core.self_assessment import self_assessment
        return {"history": self_assessment.get_history(10), "trends": {
            "overall": self_assessment.get_trend("overall"),
            "loop_integrity": self_assessment.get_trend("loop_integrity"),
            "knowledge_vitality": self_assessment.get_trend("knowledge_vitality"),
            "learning_efficiency": self_assessment.get_trend("learning_efficiency"),
            "frontend_coverage": self_assessment.get_trend("frontend_coverage"),
        }}
    except Exception as e:
        return {"error": str(e), "history": []}


@router.get("/coverage/report")
async def get_coverage_report():
    try:
        from core.coverage_auditor import CoverageAuditor
        auditor = CoverageAuditor(str(ROOT_DIR))
        return auditor.generate_report()
    except Exception as e:
        logger.error(f"覆盖率报告生成失败: {e}")
        return {"error": str(e), "total_endpoints": 0, "coverage_rate": 0}


@router.get("/coverage/gaps")
async def get_coverage_gaps():
    try:
        from core.coverage_auditor import CoverageAuditor
        auditor = CoverageAuditor(str(ROOT_DIR))
        report = auditor.generate_report()
        return {"summary": auditor.get_gaps_summary(), "report": report}
    except Exception as e:
        return {"error": str(e), "summary": "无法生成"}


@router.get("/coverage/suggestions")
async def get_coverage_suggestions():
    try:
        from core.coverage_auditor import CoverageAuditor
        auditor = CoverageAuditor(str(ROOT_DIR))
        auditor.generate_report()
        suggestions = auditor.generate_suggestions()
        return {"suggestions": suggestions, "total": len(suggestions)}
    except Exception as e:
        return {"error": str(e), "suggestions": [], "total": 0}


@router.post("/coverage/auto-generate")
async def auto_generate_coverage(max_endpoints: int = 10):
    try:
        from core.coverage_auditor import CoverageAuditor
        auditor = CoverageAuditor(str(ROOT_DIR))
        auditor.generate_report()
        result = auditor.auto_generate(max_endpoints)
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/self-model")
async def get_self_model():
    """获取系统自我模型的完整快照"""
    try:
        from core.self.model import get_self_model
        model = get_self_model()
        return model.snapshot()
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}


@router.get("/self-model/status")
async def get_self_model_status():
    """获取系统自我模型的简短状态摘要"""
    try:
        from core.self.model import get_self_model
        model = get_self_model()
        return model.get_status_summary()
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}


@router.get("/defense/health/metrics")
async def get_health_metrics():
    try:
        from core.defense.health_metrics import health_metrics
        return {
            "snapshot": health_metrics.get_snapshot(),
            "alerts": health_metrics.get_alerts(10),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/events/stats")
async def get_event_stats():
    try:
        from infrastructure.event_bus import bus, EventTypes
        return {
            "stats": bus.get_stats(),
            "event_types": {
                "UserMessage": bus.get_subscriber_count(EventTypes.UserMessage),
                "ToolResult": bus.get_subscriber_count(EventTypes.ToolResult),
                "KnowledgeUpdate": bus.get_subscriber_count(EventTypes.KnowledgeUpdate),
                "ModelStatusChange": bus.get_subscriber_count(EventTypes.ModelStatusChange),
                "IdlePeriod": bus.get_subscriber_count(EventTypes.IdlePeriod),
                "ScheduledTask": bus.get_subscriber_count(EventTypes.ScheduledTask),
            },
            "recent_events": bus.get_history(limit=15),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/events/history/{event_type}")
async def get_event_history(event_type: str, limit: int = 20):
    try:
        from infrastructure.event_bus import bus
        return {"events": bus.get_history(event_type=event_type, limit=limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/scheduled-tasks/status")
async def get_scheduled_tasks_status():
    try:
        from infrastructure.scheduled_tasks import scheduled_task_manager
        return scheduled_task_manager.get_status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/models")
async def get_models():
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return {"models": [{"name": m['name'], "type": "Ollama"} for m in models], "count": len(models)}
    except Exception:
        pass
    return {"models": [], "count": 0}


@router.post("/models/reload")
async def models_reload():
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            return {"success": True, "added": [m['name'] for m in models], "total": len(models)}
    except Exception:
        pass
    return {"success": False, "added": [], "total": 0}


@router.post("/models/test")
async def test_model_connection():
    results = {}
    loop = asyncio.get_running_loop()

    try:
        import requests
        tags = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: requests.get("http://localhost:11434/api/tags", timeout=3)),
            timeout=5
        )
        if tags.status_code == 200:
            models = [m["name"] for m in tags.json().get("models", [])]
            if models:
                results["Ollama"] = {"success": True, "message": f"可用模型: {', '.join(models[:3])}"}
            else:
                results["Ollama"] = {"success": False, "message": "无可用模型"}
        else:
            results["Ollama"] = {"success": False, "message": f"HTTP {tags.status_code}"}
    except asyncio.TimeoutError:
        results["Ollama"] = {"success": False, "message": "连接超时(5秒)"}
    except Exception as e:
        results["Ollama"] = {"success": False, "message": f"连接失败: {str(e)[:50]}"}

    config_file = ROOT_DIR / "config" / "external_api.json"
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            openai_key = config.get("openai_api_key", "")
            deepseek_key = config.get("deepseek_api_key", "")

            if openai_key and not openai_key.startswith("●"):
                try:
                    import requests as req
                    r = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: req.get(
                            "https://api.openai.com/v1/models",
                            headers={"Authorization": f"Bearer {openai_key}"},
                            timeout=5
                        )),
                        timeout=8
                    )
                    if r.status_code == 200:
                        results["OpenAI"] = {"success": True, "message": "API Key有效"}
                    else:
                        results["OpenAI"] = {"success": False, "message": f"认证失败: HTTP {r.status_code}"}
                except asyncio.TimeoutError:
                    results["OpenAI"] = {"success": False, "message": "连接超时(8秒)"}
                except Exception as e:
                    results["OpenAI"] = {"success": False, "message": f"连接失败: {str(e)[:50]}"}

            if deepseek_key and not deepseek_key.startswith("●"):
                try:
                    import requests as req
                    r = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda: req.get(
                            "https://api.deepseek.com/v1/models",
                            headers={"Authorization": f"Bearer {deepseek_key}"},
                            timeout=5
                        )),
                        timeout=8
                    )
                    if r.status_code == 200:
                        results["DeepSeek"] = {"success": True, "message": "API Key有效"}
                    else:
                        results["DeepSeek"] = {"success": False, "message": f"认证失败: HTTP {r.status_code}"}
                except asyncio.TimeoutError:
                    results["DeepSeek"] = {"success": False, "message": "连接超时(8秒)"}
                except Exception as e:
                    results["DeepSeek"] = {"success": False, "message": f"连接失败: {str(e)[:50]}"}

            if not openai_key and not deepseek_key:
                results["外部API"] = {"success": False, "message": "未配置API Key"}
        except Exception as e:
            results["外部API"] = {"success": False, "message": f"读取配置失败: {str(e)[:50]}"}
    else:
        results["外部API"] = {"success": False, "message": "未配置外部API"}

    all_success = all(r.get("success", False) for r in results.values())
    return {"success": all_success, "results": results}


@router.get("/config/external")
async def get_external_config():
    config_file = ROOT_DIR / "config" / "external_api.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        data["success"] = True
        return data
    return {"success": False, "openai_api_key": "", "deepseek_api_key": "", "message": "未配置外置API"}


@router.post("/config/external")
async def save_external_config(config: dict):
    config_dir = ROOT_DIR / "config"
    config_dir.mkdir(exist_ok=True)
    config_file = config_dir / "external_api.json"

    existing = {}
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            existing = json.load(f)

    existing.update(config)

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return {"success": True, "message": "配置已保存"}


@router.get("/reflection/stats")
async def get_reflection_stats():
    try:
        from infrastructure.reflection_pipeline import get_reflection_pipeline
        pipeline = get_reflection_pipeline()
        if pipeline:
            return pipeline.get_stats()
    except Exception:
        pass
    return {"total_reflections": 0, "status": "unavailable"}


@router.get("/trajectory/stats")
async def get_trajectory_stats():
    try:
        from core.trajectory_evolution import trajectory_store
        return trajectory_store.get_evolution_stats()
    except Exception:
        return {"total_trajectories": 0, "avg_fitness": 0, "status": "unavailable"}


@router.get("/trajectory/search")
async def search_trajectories(q: str = "", intent: str = "", limit: int = 5):
    try:
        from core.trajectory_evolution import trajectory_store
        if q:
            results = trajectory_store.find_similar_trajectories(q, intent_type=intent or None, limit=limit)
            return {"trajectories": [{"id": r["id"], "query": r["query"][:50], "fitness": r["fitness_score"], "steps_count": len(json.loads(r["steps_json"]))} for r in results]}
        return {"trajectories": []}
    except Exception:
        return {"trajectories": []}


@router.get("/ratchet/stats")
async def ratchet_stats():
    try:
        from infrastructure.ratchet_gate import ratchet_gate
        return ratchet_gate.get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.get("/world-model/stats")
async def world_model_stats():
    try:
        from core.world_model import get_world_model
        return get_world_model().get_stats()
    except Exception as e:
        return {"error": str(e)}


@router.post("/world-model/predict")
async def world_model_predict(request: dict):
    try:
        from core.world_model import get_world_model
        wm = get_world_model()
        state = request.get("state", {})
        intent = request.get("intent", "")
        pred = wm.predict(state, intent)
        return {
            "predicted_state": pred.predicted_state,
            "probability": pred.probability,
            "confidence": pred.confidence,
            "causal_path": pred.causal_path,
            "alternatives": pred.alternatives,
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/world-model/pre-enact")
async def world_model_pre_enact(request: dict):
    try:
        from core.world_model import get_world_model
        wm = get_world_model()
        state = request.get("state", {})
        actions = request.get("actions", [])
        intent = request.get("intent", "")
        result = wm.pre_enact(state, actions, intent)
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/delta-stats")
async def get_delta_stats(topic: str = "", limit: int = 20):
    try:
        from core.delta_knowledge_updater import delta_knowledge_updater
        return {"delta_stats": delta_knowledge_updater.get_delta_stats(topic, limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/weights")
async def get_path_weights():
    try:
        from core.path_weight_manager import path_weight_manager
        from core.contrib_attributor import contrib_attributor
        result = {
            "weights": path_weight_manager.get_stats(),
            "confidence_distribution": path_weight_manager.get_confidence_distribution(),
            "source_reliability": contrib_attributor.get_source_reliability(),
        }
        try:
            from core.dynamic_probability_field import dynamic_probability_field
            dist = dynamic_probability_field.get_distribution()
            if dist.get("candidates"):
                result["confidence_distribution"] = {
                    v["source"]: v["probability"] for v in dist["candidates"].values()
                }
                result["prob_mode"] = "dynamic_field"
                result["query_entropy"] = dist.get("entropy", 0)
        except Exception:
            pass
        try:
            from infrastructure.vector_retriever import _ST_AVAILABLE
            result["prob_mode"] = "semantic" if _ST_AVAILABLE else "tfidf"
        except Exception:
            result["prob_mode"] = "unknown"
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/attributions")
async def get_attributions(limit: int = 20):
    try:
        from core.contrib_attributor import contrib_attributor
        return {"attributions": contrib_attributor.get_recent_attributions(limit)}
    except Exception as e:
        return {"error": str(e)}


@router.get("/probability-field")
async def get_probability_field():
    try:
        from core.dynamic_probability_field import dynamic_probability_field
        from core.react_enhancer import react_enhancer
        result = {
            "distribution": dynamic_probability_field.get_distribution(),
            "should_explore": dynamic_probability_field.should_explore(),
            "gap_stats": react_enhancer.get_gap_stats(),
            "recent_snapshots": dynamic_probability_field.get_recent_snapshots(5),
            "uncertainty_action": dynamic_probability_field.get_uncertainty_action(),
            "calibration_summary": dynamic_probability_field.get_calibration_summary(),
        }
        try:
            from infrastructure.vector_retriever import vector_retriever
            result["calibration_stats"] = vector_retriever._calibrator.get_calibration_stats()
        except Exception:
            pass
        return result
    except Exception as e:
        return {"error": str(e)}
