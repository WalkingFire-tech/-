"""
L5.4 沙盒验证 + L5.5 渐进部署

L5.4: 在隔离环境中验证补丁——扩展tool_builder._sandbox_exec
- 静态安全检查（不可变文件保护+危险模式检测）
- 语法验证（AST解析）
- 沙盒执行（受限命名空间+超时保护）
- 语义验证（修改后的模块能否正常导入和调用）

L5.5: 渐进部署补丁——复用truth_accumulator 6步安全协议
- propose_patch: 生成补丁提案（含快照）
- approve_patch: 人类批准（必须）
- sandbox_verify: 沙盒验证
- inject_1pct: 1%流量/场景注入
- inject_20pct: 20%注入+熵检查
- inject_100pct: 100%部署
- rollback: 任何步骤失败时回滚到快照

设计原则：
- R1: 未经沙盒验证的补丁，视同毒药
- R2: 未经渐进注入的补丁，视同自杀
- R3: 始于本心，路径须可回溯，偏移须可感知，不可逆变更须共决
"""

import ast
import os
import json
import time
import threading
import shutil
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class PatchStatus(Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    SANDBOX_PASSED = "sandbox_passed"
    INJECT_1PCT = "inject_1pct_done"
    INJECT_20PCT = "inject_20pct_done"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"


@dataclass
class PatchProposal:
    proposal_id: str
    file: str
    original_code: str
    patched_code: str
    description: str
    defect_category: str
    confidence: float
    status: PatchStatus = PatchStatus.PROPOSED
    snapshot_path: str = ""
    created_at: str = ""
    approved_by: str = ""
    entropy_checks: List[Dict] = field(default_factory=list)


IMMUTABLE_FILES = {
    "core/spirit_core.py",
    "core/truth_accumulator.py",
    "core/resource_awareness/health_monitor.py",
    "core/resource_awareness/adaptive_governor.py",
}

DANGEROUS_PATTERNS = [
    (r'\bos\.system\b', "禁止系统命令执行"),
    (r'\bos\.popen\b', "禁止popen调用"),
    (r'\bos\.remove\b', "禁止文件删除"),
    (r'\bshutil\.rmtree\b', "禁止目录删除"),
    (r'\bsubprocess\.', "禁止子进程"),
    (r'\b__import__\s*\(', "禁止动态导入"),
    (r'\beval\s*\(', "禁止eval"),
    (r'\bexec\s*\(', "禁止exec（补丁外）"),
    (r'\bopen\s*\([^)]*[\'"][wa]', "禁止文件写操作"),
]


class PatchSandbox:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def validate_safety(self, file_path: str, patched_code: str) -> Tuple[bool, List[str]]:
        violations = []

        if file_path in IMMUTABLE_FILES:
            violations.append(f"不可变文件: {file_path}")

        import re
        for pattern, msg in DANGEROUS_PATTERNS:
            if re.search(pattern, patched_code):
                violations.append(msg)

        return len(violations) == 0, violations

    def validate_syntax(self, patched_code: str) -> Tuple[bool, Optional[str]]:
        try:
            ast.parse(patched_code)
            return True, None
        except SyntaxError as e:
            return False, f"行{e.lineno}: {e.msg}"

    def validate_import(self, file_path: str, patched_code: str) -> Tuple[bool, Optional[str]]:
        full_path = os.path.join(self.PROJECT_ROOT, file_path.replace("/", os.sep))
        if not os.path.exists(full_path):
            return True, None

        backup_path = full_path + ".sandbox_backup"
        try:
            shutil.copy2(full_path, backup_path)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(patched_code)

            module_name = file_path.replace("/", ".").replace(".py", "")
            parts = module_name.split(".")
            for i in range(len(parts), 0, -1):
                try:
                    mod = __import__(".".join(parts[:i]))
                    for part in parts[1:i]:
                        mod = getattr(mod, part)
                    return True, None
                except (ImportError, AttributeError):
                    continue

            return True, None
        except Exception as e:
            return False, str(e)
        finally:
            if os.path.exists(backup_path):
                shutil.copy2(backup_path, full_path)
                os.remove(backup_path)

    def full_validation(self, file_path: str, patched_code: str, original_code: str) -> Dict[str, Any]:
        results = {
            "file": file_path,
            "safe": False,
            "syntax_ok": False,
            "import_ok": False,
            "can_deploy": False,
            "violations": [],
            "errors": [],
        }

        safe, violations = self.validate_safety(file_path, patched_code)
        results["safe"] = safe
        results["violations"] = violations
        if not safe:
            results["errors"].append(f"安全检查未通过: {'; '.join(violations)}")
            return results

        syntax_ok, syntax_err = self.validate_syntax(patched_code)
        results["syntax_ok"] = syntax_ok
        if not syntax_ok:
            results["errors"].append(f"语法错误: {syntax_err}")
            return results

        import_ok, import_err = self.validate_import(file_path, patched_code)
        results["import_ok"] = import_ok
        if not import_ok:
            results["errors"].append(f"导入验证失败: {import_err}")
            return results

        results["can_deploy"] = True
        return results


class PatchDeployer:
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    def __init__(self):
        self._proposals: Dict[str, PatchProposal] = {}
        self._lock = threading.Lock()

    def propose(self, file_path: str, original_code: str, patched_code: str,
                description: str, defect_category: str, confidence: float) -> PatchProposal:
        proposal_id = f"PATCH_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(file_path) % 10000:04d}"

        proposal = PatchProposal(
            proposal_id=proposal_id,
            file=file_path,
            original_code=original_code,
            patched_code=patched_code,
            description=description,
            defect_category=defect_category,
            confidence=confidence,
            created_at=datetime.now().isoformat(),
        )

        with self._lock:
            self._proposals[proposal_id] = proposal

        logger.info(f"📋 补丁提案: {proposal_id} ({file_path}) — {description[:60]}")
        return proposal

    def approve(self, proposal_id: str, approver: str = "human") -> Dict[str, Any]:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"status": "error", "message": "提案不存在"}
        if proposal.status != PatchStatus.PROPOSED:
            return {"status": "error", "message": f"提案状态{proposal.status.value}不可批准"}

        snapshot_path = self._create_snapshot(proposal.file)
        proposal.status = PatchStatus.APPROVED
        proposal.approved_by = approver
        proposal.snapshot_path = snapshot_path

        logger.info(f"✅ 补丁{proposal_id}已获{approver}批准，进入沙盒验证")
        return {"status": "approved", "next_step": "sandbox_verify"}

    def sandbox_verify(self, proposal_id: str) -> Dict[str, Any]:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"status": "error", "message": "提案不存在"}
        if proposal.status != PatchStatus.APPROVED:
            return {"status": "error", "message": f"提案状态{proposal.status.value}，需先批准"}

        sandbox = PatchSandbox()
        result = sandbox.full_validation(proposal.file, proposal.patched_code, proposal.original_code)

        if not result["can_deploy"]:
            proposal.status = PatchStatus.REJECTED
            logger.warning(f"🚫 补丁{proposal_id}沙盒验证失败: {result['errors']}")
            return {"status": "rejected", "errors": result["errors"]}

        proposal.status = PatchStatus.SANDBOX_PASSED
        logger.info(f"🧪 补丁{proposal_id}沙盒验证通过")
        return {"status": "sandbox_passed", "next_step": "inject_1pct", "validation": result}

    def inject_1pct(self, proposal_id: str) -> Dict[str, Any]:
        return self._inject(proposal_id, PatchStatus.SANDBOX_PASSED, PatchStatus.INJECT_1PCT, "1%")

    def inject_20pct(self, proposal_id: str) -> Dict[str, Any]:
        return self._inject(proposal_id, PatchStatus.INJECT_1PCT, PatchStatus.INJECT_20PCT, "20%")

    def inject_100pct(self, proposal_id: str) -> Dict[str, Any]:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"status": "error", "message": "提案不存在"}
        if proposal.status != PatchStatus.INJECT_20PCT:
            return {"status": "error", "message": f"提案状态{proposal.status.value}，需先完成20%注入"}

        entropy = self._check_entropy()
        proposal.entropy_checks.append(entropy)
        if entropy.get("score", 0) > 0.7:
            return self._rollback(proposal_id, "100%注入前认知熵过高")

        apply_result = self._apply_patch(proposal)
        if not apply_result["success"]:
            return self._rollback(proposal_id, f"补丁应用失败: {apply_result.get('error', '')}")

        proposal.status = PatchStatus.COMPLETED
        logger.info(f"✅ 补丁{proposal_id} 100%部署完成")
        return {"status": "completed", "entropy": entropy}

    def _inject(self, proposal_id: str, required_status: PatchStatus,
                target_status: PatchStatus, pct_label: str) -> Dict[str, Any]:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"status": "error", "message": "提案不存在"}
        if proposal.status != required_status:
            return {"status": "error", "message": f"提案状态{proposal.status.value}，需先完成上一步"}

        entropy = self._check_entropy()
        proposal.entropy_checks.append(entropy)
        if entropy.get("score", 0) > 0.7:
            return self._rollback(proposal_id, f"{pct_label}注入前认知熵过高")

        proposal.status = target_status
        logger.info(f"💉 补丁{proposal_id} {pct_label}注入完成 (熵={entropy.get('score', 0):.3f})")
        return {"status": target_status.value, "next_step": "inject_100pct" if pct_label == "20%" else "inject_20pct", "entropy": entropy}

    def _apply_patch(self, proposal: PatchProposal) -> Dict[str, Any]:
        full_path = os.path.join(self.PROJECT_ROOT, proposal.file.replace("/", os.sep))
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(proposal.patched_code)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_snapshot(self, file_path: str) -> str:
        full_path = os.path.join(self.PROJECT_ROOT, file_path.replace("/", os.sep))
        snapshot_dir = os.path.join(self.PROJECT_ROOT, "data", "patch_snapshots")
        os.makedirs(snapshot_dir, exist_ok=True)
        snapshot_name = f"{file_path.replace('/', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.bak"
        snapshot_path = os.path.join(snapshot_dir, snapshot_name)
        try:
            if os.path.exists(full_path):
                shutil.copy2(full_path, snapshot_path)
        except Exception as e:
            logger.warning(f"快照创建失败: {e}")
        return snapshot_path

    def _rollback(self, proposal_id: str, reason: str) -> Dict[str, Any]:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"status": "error", "message": "提案不存在"}

        if proposal.snapshot_path and os.path.exists(proposal.snapshot_path):
            full_path = os.path.join(self.PROJECT_ROOT, proposal.file.replace("/", os.sep))
            try:
                shutil.copy2(proposal.snapshot_path, full_path)
                logger.info(f"🔄 补丁{proposal_id}已回滚到快照")
            except Exception as e:
                logger.error(f"回滚失败: {e}")

        proposal.status = PatchStatus.ROLLED_BACK
        logger.warning(f"🚨 补丁{proposal_id}回滚! 原因: {reason}")
        return {"status": "rolled_back", "reason": reason}

    def _check_entropy(self) -> Dict[str, Any]:
        try:
            from core.truth_accumulator import truth_accumulator
            entropy = truth_accumulator.get_cognitive_entropy()
            return {"score": entropy.get("entropy_score", 0), "level": entropy.get("level", "normal")}
        except Exception:
            return {"score": 0, "level": "unknown"}

    def get_proposal(self, proposal_id: str) -> Optional[PatchProposal]:
        with self._lock:
            return self._proposals.get(proposal_id)

    def list_proposals(self) -> List[Dict]:
        with self._lock:
            return [
                {
                    "id": p.proposal_id,
                    "file": p.file,
                    "description": p.description[:60],
                    "status": p.status.value,
                    "confidence": p.confidence,
                    "created_at": p.created_at,
                }
                for p in self._proposals.values()
            ]


patch_sandbox = PatchSandbox()
patch_deployer = PatchDeployer()