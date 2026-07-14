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

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


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


class SelfModificationLoop:
    MIN_INTERVAL_SEC = 600

    def __init__(self):
        self._last_run: Optional[datetime] = None
        self._run_count = 0

    def run_from_lessons(self) -> ModificationResult:
        result = ModificationResult(source="lesson")
        try:
            from core.self_modification.defect_diagnoser import defect_diagnoser
            defects = defect_diagnoser.diagnose_from_lessons()
            result.defects_found = len(defects)
            if not defects:
                result.triggered = False
                return result
            result.triggered = True
            logger.info(f"🔧 L5自触发: 从教训中发现{len(defects)}个缺陷")
            self._process_defects(defects, result)
        except Exception as e:
            result.error = str(e)
            logger.warning(f"🔧 L5自触发(教训)失败: {e}")
        self._record_run()
        return result

    def run_from_file(self, relative_path: str) -> ModificationResult:
        result = ModificationResult(source=f"file:{relative_path}")
        try:
            from core.self_modification.defect_diagnoser import defect_diagnoser
            defects = defect_diagnoser.diagnose_file(relative_path)
            result.defects_found = len(defects)
            if not defects:
                result.triggered = False
                return result
            result.triggered = True
            logger.info(f"🔧 L5自触发: 从{relative_path}中发现{len(defects)}个缺陷")
            self._process_defects(defects, result)
        except Exception as e:
            result.error = str(e)
            logger.warning(f"🔧 L5自触发(文件)失败: {e}")
        self._record_run()
        return result

    def run_from_directory(self, directory: str = "core") -> ModificationResult:
        result = ModificationResult(source=f"dir:{directory}")
        try:
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
        except Exception as e:
            result.error = str(e)
            logger.warning(f"🔧 L5自触发(目录)失败: {e}")
        self._record_run()
        return result

    def can_run(self) -> bool:
        if self._last_run is None:
            return True
        elapsed = (datetime.now() - self._last_run).total_seconds()
        return elapsed >= self.MIN_INTERVAL_SEC

    def get_status(self) -> Dict[str, Any]:
        return {
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "run_count": self._run_count,
            "can_run": self.can_run(),
            "min_interval_sec": self.MIN_INTERVAL_SEC,
        }

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
                continue

            result.patches_generated += 1

            # Build full patched source for validation
            patched_source = source_code.replace(patch.original, patch.replacement, 1) if patch.original else source_code
            safe, violations = patch_sandbox.validate_safety(file_path, patched_source)
            if not safe:
                result.details.append({"defect": defect_dict.get("description", ""), "status": "unsafe", "violations": violations})
                continue

            syntax_ok, syntax_err = patch_sandbox.validate_syntax(patched_source)
            if not syntax_ok:
                result.details.append({"defect": defect_dict.get("description", ""), "status": "syntax_error", "error": syntax_err})
                continue

            result.patches_safe += 1

            proposal = deployer.propose(
                file_path=file_path,
                original_code=source_code,
                patched_code=patched_source,
                description=patch.description,
                defect_category=patch.defect_category,
                confidence=patch.confidence,
            )
            result.proposals_created += 1

            # Activate 6-step safety protocol for high-confidence template patches
            auto_status = "proposed"
            if patch.confidence >= 0.9 and patch.defect_category == "exception_handling":
                approve_result = deployer.approve(proposal.proposal_id, approver="L5-auto")
                if approve_result.get("status") == "approved":
                    sandbox_result = deployer.sandbox_verify(proposal.proposal_id)
                    if sandbox_result.get("status") == "sandbox_passed":
                        deployer.inject_1pct(proposal.proposal_id)
                        deployer.inject_20pct(proposal.proposal_id)
                        deployer.inject_100pct(proposal.proposal_id)
                        auto_status = "completed"
                    else:
                        auto_status = "sandbox_rejected"
                else:
                    auto_status = "approve_blocked"
            result.details.append({
                "defect": defect_dict.get("description", ""),
                "status": auto_status,
                "proposal_id": proposal.proposal_id,
                "file": file_path,
            })
            logger.info(f"🔧 L5补丁提案: {proposal.proposal_id} ({file_path}) — {patch.description[:60]}")

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

    def _load_lesson_rules(self) -> List[Dict[str, Any]]:
        try:
            from infrastructure.database_manager import DatabaseManager
            db = DatabaseManager.get("data/learning_rules.db")
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