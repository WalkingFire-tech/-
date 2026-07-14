"""
L5自触发回路 — 从"感知局限"到"自我改进"的完整闭环

数据流:
  CuriosityEngine.reflect_internal
    → DefectDiagnoser.diagnose_from_lessons / diagnose_file
    → PatchGenerator.generate_patch / generate_llm_patch
    → PatchSandbox.validate_safety + validate_syntax
    → PatchDeployer.propose → approve → sandbox_verify → inject

设计原则:
  - 不替系统做决定，让系统自己做决定——补丁必须经过6步安全协议
  - 渐进式触发：先模板补丁，模板匹配失败才尝试LLM补丁
  - 安全红线：不可变文件不可修改，危险模式不可注入
  - 日志可追溯：每一步都有结构化日志
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

        for defect in defects[:5]:
            defect_dict = self._defect_to_dict(defect)
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

            patch = patch_generator.generate_patch(defect_dict, source="template")
            if not patch:
                patch = patch_generator.generate_llm_patch(defect_dict, source_code)
            if not patch:
                result.details.append({"defect": defect_dict.get("description", ""), "status": "no_patch_match"})
                continue

            result.patches_generated += 1

            safe, violations = patch_sandbox.validate_safety(file_path, patch.replacement)
            if not safe:
                result.details.append({"defect": defect_dict.get("description", ""), "status": "unsafe", "violations": violations})
                continue

            syntax_ok, syntax_err = patch_sandbox.validate_syntax(patch.replacement)
            if not syntax_ok:
                result.details.append({"defect": defect_dict.get("description", ""), "status": "syntax_error", "error": syntax_err})
                continue

            result.patches_safe += 1

            proposal = deployer.propose(
                file_path=file_path,
                original_code=patch.original,
                patched_code=patch.replacement,
                description=patch.description,
                defect_category=patch.defect_category,
                confidence=patch.confidence,
            )
            result.proposals_created += 1
            result.details.append({
                "defect": defect_dict.get("description", ""),
                "status": "proposed",
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


self_modification_loop = SelfModificationLoop()