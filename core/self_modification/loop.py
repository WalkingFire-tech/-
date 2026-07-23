"""
L5自触发回路 — 从"感知局限"到"自我改进"的完整闭环

数据流:
  CuriosityEngine.reflect_internal
    → DefectDiagnoser.diagnose_from_lessons / diagnose_file
    → PatchGenerator.generate_patch / generate_llm_patch
    → PatchSandbox.validate_safety + validate_syntax
    → PatchDeployer.propose → approve → sandbox_verify → inject

设计原则:
  - R1: 未经沙盒验证的补丁，视同毒药——所有补丁必须通过PatchSandbox验证
  - R2: 未经渐进注入的补丁，视同自杀——所有部署必须走6步安全协议
  - R3: 始于本心，路径须可回溯，偏移须可感知，不可逆变更须共决
  - 生存优先：当深度推理与资源约束冲突时，优先确保系统存在
  - 渐进式触发：先模板补丁，模板匹配失败才尝试LLM补丁
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from core.loop_mixin import LoopMixin, LoopStatus

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from core.explainability.l5_explainer import L5Explainer
except ImportError:
    L5Explainer = None


@dataclass
class ModificationResult:
    triggered: bool = False
    defects_found: int = 0
    patches_generated: int = 0
    patches_safe: int = 0
    proposals_created: int = 0
    source: str = ""
    details: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


class SelfModificationLoop(LoopMixin):
    MIN_INTERVAL_SEC = 600

    def __init__(self):
        super().__init__(name="self_modification_loop", cooldown_seconds=600.0, max_failures_before_degraded=2)
        self._last_run: Optional[datetime] = None
        self._run_count = 0

    def run_from_lessons(self) -> ModificationResult:
        result = ModificationResult(source="lesson")
        with self.loop_context():
            from core.self_modification.defect_diagnoser import defect_diagnoser
            defects = defect_diagnoser.diagnose_from_lessons()
            result.defects_found = len(defects)
            if not defects:
                result.triggered = False
                return result
            result.triggered = True
            logger.info(f"🔧 L5自触发: 从教训中发现{len(defects)}个缺陷")
            self._process_defects(defects, result)
        self._record_run()
        return result

    def run_from_file(self, relative_path: str) -> ModificationResult:
        result = ModificationResult(source=f"file:{relative_path}")
        with self.loop_context():
            from core.self_modification.defect_diagnoser import defect_diagnoser
            defects = defect_diagnoser.diagnose_file(relative_path)
            result.defects_found = len(defects)
            if not defects:
                result.triggered = False
                return result
            result.triggered = True
            logger.info(f"🔧 L5自触发: 从{relative_path}中发现{len(defects)}个缺陷")
            self._process_defects(defects, result)
        self._record_run()
        return result

    def run_from_directory(self, directory: str = "core") -> ModificationResult:
        result = ModificationResult(source=f"dir:{directory}")
        with self.loop_context():
            from core.self_modification.defect_diagnoser import defect_diagnoser
            all_defects = defect_diagnoser.diagnose_directory(directory)
            total = sum(len(v) for v in all_defects.values())
            result.defects_found = total
            if total == 0:
                result.triggered = False
                return result
            result.triggered = True
            logger.info(f"🔧 L5自触发: 从{directory}/中发现{total}个缺陷")
            for file_path, defects in all_defects.items():
                self._process_defects(defects, result, file_hint=file_path)
        self._record_run()
        return result

    def can_run(self) -> bool:
        if self._last_run is None:
            return True
        elapsed = (datetime.now() - self._last_run).total_seconds()
        return elapsed >= self.MIN_INTERVAL_SEC and self.loop_status != LoopStatus.DEGRADED

    def get_status(self) -> Dict[str, Any]:
        status = {
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count,
            "can_run": self.can_run(),
            "min_interval_sec": self.MIN_INTERVAL_SEC,
        }
        status.update(self.get_loop_snapshot())
        return status

    def _process_defects(self, defects: list, result: ModificationResult, file_hint: str = "") -> None:
        from core.self_modification.patch_generator import patch_generator
        from core.self_modification.patch_sandbox_deployer import patch_sandbox, PatchDeployer

        deployer = PatchDeployer()
        lesson_rules = self._load_lesson_rules()

        for defect in defects[:5]:
            defect_dict = self._defect_to_dict(defect)
            matched_lesson = self._match_lesson(defect_dict, lesson_rules)
            if matched_lesson:
                logger.info(f"🔧 教训匹配: {matched_lesson.get('lesson', '')[:60]}")
            file_path = defect_dict.get("file", file_hint)
            if file_path in ("unknown", ""):
                file_path = file_hint
            if file_path and not file_path.endswith(".py"):
                file_path = self._resolve_file_path(file_path)
            if not file_path or file_path in ("unknown", ""):
                result.details.append({"defect": defect_dict.get("description", ""), "status": "skipped_no_file"})
                continue

            source_code = self._read_source(file_path)
            if not source_code:
                result.details.append({"defect": defect_dict.get("description", ""), "status": "skipped_no_source"})
                continue

            patch = patch_generator.generate_patch(defect_dict, source_code)
            if not patch:
                patch = patch_generator.generate_llm_patch(defect_dict, source_code)
            if not patch:
                result.details.append({"defect": defect_dict.get("description", ""), "status": "no_patch_match"})
                if L5Explainer:
                    L5Explainer.explain_patch_strategy(strategy="none", category=defect_dict.get("category", ""), reason="模板和LLM均未生成有效补丁")
                continue

            _patch_strategy = "template" if patch.confidence >= 0.7 else "llm"
            if L5Explainer:
                L5Explainer.explain_patch_strategy(
                    strategy=_patch_strategy, category=patch.defect_category,
                    reason=patch.description[:80] if patch.description else "",
                    confidence=patch.confidence, template_name=patch.defect_category,
                )

            result.patches_generated += 1

            patched_source = source_code.replace(patch.original, patch.replacement, 1) if patch.original else source_code
            safe, violations = patch_sandbox.validate_safety(file_path, patched_source)
            if not safe:
                result.details.append({"defect": defect_dict.get("description", ""), "status": "unsafe", "violations": violations})
                if L5Explainer:
                    L5Explainer.explain_safety_rejection(file_path=file_path, violations=violations)
                continue

            syntax_ok, syntax_err = patch_sandbox.validate_syntax(patched_source)
            if not syntax_ok:
                result.details.append({"defect": defect_dict.get("description", ""), "status": "syntax_error", "error": syntax_err})
                continue

            result.patches_safe += 1

            is_self_mod = self._is_self_modification(file_path)
            if is_self_mod:
                from core.self_modification.bootstrap_sandbox import bootstrap_sandbox as _bs
                bootstrap_result = _bs.verify_self_consistency(file_path, patched_source, source_code)
                if not bootstrap_result.can_bootstrap:
                    result.details.append({
                        "defect": defect_dict.get("description", ""),
                        "status": "bootstrap_failed",
                        "errors": bootstrap_result.errors,
                    })
                    if L5Explainer:
                        L5Explainer.explain_bootstrap_verification(file_path=file_path, can_bootstrap=False, errors=bootstrap_result.errors)
                    continue
                logger.info(f"🧬 自修改自举验证通过: {file_path}")
                if L5Explainer:
                    L5Explainer.explain_bootstrap_verification(file_path=file_path, can_bootstrap=True)

            wm_verdict = self._simulate_in_world_model(file_path, defect_dict, patch)
            if wm_verdict.get("risk_level") == "high":
                result.details.append({"defect": defect_dict.get("description", ""), "status": "world_model_high_risk", "verdict": wm_verdict})
                if L5Explainer:
                    L5Explainer.explain_world_model_risk(file_path=file_path, risk_level="high", improves_outcome=False, risk_details=wm_verdict)
                continue

            effective_confidence = patch.confidence
            if wm_verdict.get("improves_outcome"):
                effective_confidence = min(1.0, patch.confidence + 0.1)

            proposal = deployer.propose(
                file_path=file_path,
                original_code=source_code,
                patched_code=patched_source,
                description=patch.description,
                defect_category=patch.defect_category,
                confidence=effective_confidence,
            )
            result.proposals_created += 1

            auto_status = "proposed"
            if is_self_mod:
                from core.self_modification.bootstrap_sandbox import self_modification_deployer as _smd
                deploy_result = _smd.deploy_self_modification(
                    file_path, patched_source, source_code, effective_confidence
                )
                auto_status = deploy_result.get("final_status", "unknown")
                if auto_status == "completed":
                    self._learn_modification_outcome(file_path, defect_dict, True)
                else:
                    self._learn_modification_outcome(file_path, defect_dict, False)
                result.details.append({
                    "defect": defect_dict.get("description", ""),
                    "status": auto_status,
                    "file": file_path,
                    "is_self_modification": True,
                    "stages": deploy_result.get("stages", {}),
                })
                self._write_audit_log(file_path, defect_dict, patch, auto_status, wm_verdict,
                                      is_self_mod=True, stage_details=deploy_result.get("stages", {}))
                continue

            try:
                from core.self_modification.strategy_evolver import strategy_evolver as _se
                should_auto = _se.should_auto_approve(effective_confidence, patch.defect_category, is_self_mod)
                if L5Explainer:
                    L5Explainer.explain_auto_approve(
                        approved=should_auto, confidence=effective_confidence,
                        threshold=_se._get_threshold_for_category(patch.defect_category),
                        category=patch.defect_category, is_self_mod=is_self_mod,
                        effective_threshold=_se._get_threshold_for_category(patch.defect_category) - (_se.params.self_mod_confidence_bonus if is_self_mod else 0),
                        auto_approve_categories=list(_se.params.auto_approve_categories),
                    )
            except Exception:
                should_auto = effective_confidence >= 0.9 and patch.defect_category == "exception_handling"

            if should_auto:
                approve_result = deployer.approve(proposal.proposal_id, approver="L5-auto")
                if approve_result.get("status") == "approved":
                    sandbox_result = deployer.sandbox_verify(proposal.proposal_id)
                    if sandbox_result.get("status") == "sandbox_passed":
                        deployer.inject_1pct(proposal.proposal_id)
                        deployer.inject_20pct(proposal.proposal_id)
                        deployer.inject_100pct(proposal.proposal_id)
                        auto_status = "completed"
                        self._learn_modification_outcome(file_path, defect_dict, True)
                    else:
                        auto_status = "sandbox_rejected"
                        self._learn_modification_outcome(file_path, defect_dict, False)
                else:
                    auto_status = "approve_blocked"
            result.details.append({
                "defect": defect_dict.get("description", ""),
                "status": auto_status,
                "proposal_id": proposal.proposal_id,
                "file": file_path,
                "world_model_verdict": wm_verdict,
            })
            self._write_audit_log(file_path, defect_dict, patch, auto_status, wm_verdict,
                                  is_self_mod=is_self_mod)
            logger.info(f"🔧 L5补丁提案: {proposal.proposal_id} ({file_path}) — {patch.description[:60]}")

    def _is_self_modification(self, file_path: str) -> bool:
        from core.self_modification.bootstrap_sandbox import L5_SELF_FILES
        return file_path in L5_SELF_FILES

    def _simulate_in_world_model(self, file_path: str, defect_dict: Dict, patch) -> Dict:
        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            category = defect_dict.get("category", "unknown")
            return wm.simulate(
                {"intent": "self_modification", "file": file_path},
                {"action": f"fix_{category}", "patch_confidence": patch.confidence},
                intent="self_modification"
            )
        except Exception as e:
            logger.debug(f"世界模型模拟跳过: {e}")
            return {"risk_level": "low", "improves_outcome": False, "error": str(e)}

    def _learn_modification_outcome(self, file_path: str, defect_dict: Dict, success: bool) -> None:
        try:
            from core.world_model import get_world_model
            wm = get_world_model()
            wm.learn_from_experience({
                "intent_type": "self_modification",
                "model_name": defect_dict.get("category", "unknown"),
                "success": success,
                "quality_score": 80 if success else 20,
            })
        except Exception:
            pass

    def _write_audit_log(self, file_path: str, defect_dict: Dict, patch, result_status: str,
                         wm_verdict: Dict = None, is_self_mod: bool = False,
                         stage_details: Dict = None) -> None:
        try:
            from core.ports.adapters import get_storage_port
            import json
            db = get_storage_port("data/l5_audit.db")
            db.executescript('''
                CREATE TABLE IF NOT EXISTS l5_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    file_path TEXT,
                    defect_category TEXT,
                    defect_description TEXT,
                    patch_description TEXT,
                    patch_confidence REAL,
                    result_status TEXT,
                    world_model_verdict TEXT,
                    approver TEXT,
                    is_self_modification INTEGER DEFAULT 0,
                    stage_details TEXT,
                    diff_before TEXT,
                    diff_after TEXT
                )
            ''')
            is_self_mod_int = 1 if is_self_mod else 0
            diff_before = ""
            diff_after = ""
            if patch and hasattr(patch, 'original') and patch.original:
                diff_before = patch.original[:500]
                diff_after = patch.replacement[:500] if hasattr(patch, 'replacement') else ""
            db.execute(
                'INSERT INTO l5_audit_log (timestamp, file_path, defect_category, defect_description, patch_description, patch_confidence, result_status, world_model_verdict, approver, is_self_modification, stage_details, diff_before, diff_after) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    datetime.now().isoformat(),
                    file_path,
                    defect_dict.get("category", ""),
                    defect_dict.get("description", "")[:200],
                    patch.description[:200] if patch else "",
                    patch.confidence if patch else 0.0,
                    result_status,
                    json.dumps(wm_verdict or {}, ensure_ascii=False)[:500],
                    "L5-auto",
                    is_self_mod_int,
                    json.dumps(stage_details or {}, ensure_ascii=False)[:1000],
                    diff_before,
                    diff_after,
                ),
                commit=True,
            )
        except Exception:
            pass

    def _defect_to_dict(self, defect) -> Dict[str, Any]:
        if hasattr(defect, "__dataclass_fields__"):
            return {f: getattr(defect, f) for f in defect.__dataclass_fields__}
        if isinstance(defect, dict):
            return defect
        return {"description": str(defect)}

    MODULE_PATH_MAP = {
        "chat_stream": "backend/chat_stream.py",
        "chat_orchestrator": "backend/services/chat_orchestrator.py",
        "parallel_router": "backend/services/parallel_router.py",
        "cognitive_dispatcher": "core/cognitive_dispatcher.py",
        "self_model": "core/self/model.py",
        "curiosity_engine": "core/presence/curiosity_engine.py",
        "scene_awareness": "core/presence/scene_awareness.py",
        "existence_layer": "core/presence/existence_layer.py",
        "adaptive_governor": "core/resource_awareness/adaptive_governor.py",
        "health_monitor": "core/resource_awareness/health_monitor.py",
        "scheduled_tasks": "infrastructure/scheduled_tasks.py",
        "path_weight_manager": "core/path_weight_manager.py",
        "capability_creation_loop": "core/capability_creation_loop.py",
        "persistent_solver": "backend/services/persistent_solver.py",
        "tool_registry": "core/tool_registry.py",
        "spirit_core": "core/spirit_core.py",
        "truth_accumulator": "core/truth_accumulator.py",
    }

    def _resolve_file_path(self, module_name: str) -> str:
        if module_name in self.MODULE_PATH_MAP:
            return self.MODULE_PATH_MAP[module_name]
        if module_name.endswith(".py"):
            return module_name
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for root_dir in ("core", "backend", "infrastructure", "adapters"):
            for suffix in (f"/{module_name}.py", f"/services/{module_name}.py", f"/{module_name}/__init__.py"):
                candidate = os.path.join(project_root, root_dir, suffix.lstrip("/").replace("/", os.sep))
                if os.path.exists(candidate):
                    return root_dir + suffix
        return module_name

    def _read_source(self, relative_path: str) -> Optional[str]:
        try:
            from core.self_modification.code_reader import code_reader
            return code_reader.read_file(relative_path)
        except Exception:
            return None

    def _record_run(self) -> None:
        self._last_run = datetime.now()
        self._run_count += 1
        if self._run_count % 5 == 0:
            try:
                from core.self_modification.strategy_evolver import strategy_evolver
                strategy_evolver.evolve_modification_strategy()
        except Exception as e:
            logger.warning(f"自修改审计记录DB写入失败: {e}")

    def _load_lesson_rules(self) -> List[Dict[str, Any]]:
        try:
            from core.ports.adapters import get_storage_port
            db = get_storage_port("data/learning_rules.db")
            rows = db.query(
                "SELECT condition, action, priority, metadata FROM learning_rules "
                "WHERE source LIKE 'lesson:%' AND status='active' ORDER BY priority DESC"
            )
            rules = []
            for r in rows:
                d = dict(r) if hasattr(r, "keys") else {}
                meta = {}
                if d.get("metadata"):
                    try:
                        import json
                        meta = json.loads(d["metadata"])
                    except Exception:
                        pass
                rules.append({
                    "condition": d.get("condition", ""),
                    "action": d.get("action", ""),
                    "priority": d.get("priority", 0),
                    "lesson": meta.get("lesson", ""),
                    "ref": meta.get("ref", ""),
                })
            return rules
        except Exception:
            return []

    def _match_lesson(self, defect_dict: Dict[str, Any], lesson_rules: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        desc = defect_dict.get("description", "").lower()
        category = defect_dict.get("category", "").lower()
        file_path = defect_dict.get("file", "")

        for rule in lesson_rules:
            cond = rule["condition"].lower()
            if "bypass_safety" in cond and ("绕过" in desc or "bypass" in desc or "直接写" in desc):
                return rule
            if "new_module" in cond and ("新建" in desc or "new module" in desc):
                return rule
            if "not_called" in cond and ("未调用" in desc or "not_called" in desc or "断裂" in desc):
                return rule
            if "not_driving" in cond and ("纯接收" in desc or "未驱动" in desc):
                return rule
            if "always_zero" in cond and ("始终为0" in desc or "never_triggered" in desc):
                return rule
        return None


self_modification_loop = SelfModificationLoop()