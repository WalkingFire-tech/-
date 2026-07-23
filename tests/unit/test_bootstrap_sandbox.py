"""
BootstrapSandbox + SelfModificationDeployer 测试
"""
import pytest
from core.self_modification.bootstrap_sandbox import (
    BootstrapSandbox, BootstrapResult, L5_SELF_FILES, MODULE_TEST_MAP,
    SelfModificationDeployer,
)


class TestBootstrapSandbox:
    def test_l5_self_files_defined(self):
        assert len(L5_SELF_FILES) >= 4
        assert "core/self_modification/loop.py" in L5_SELF_FILES

    def test_is_self_modification_true(self):
        sandbox = BootstrapSandbox()
        assert sandbox.is_self_modification("core/self_modification/loop.py") is True

    def test_is_self_modification_false(self):
        sandbox = BootstrapSandbox()
        assert sandbox.is_self_modification("core/world_model.py") is False

    def test_safety_checklist_exists(self):
        sandbox = BootstrapSandbox()
        assert len(sandbox.SELF_MODIFICATION_SAFETY_CHECKLIST) >= 8

    def test_module_test_map_covers_self_files(self):
        for f in L5_SELF_FILES:
            if f != "core/self_modification/bootstrap_sandbox.py":
                assert f in MODULE_TEST_MAP, f"MODULE_TEST_MAP missing: {f}"

    def test_verify_syntax_error(self):
        sandbox = BootstrapSandbox()
        result = sandbox.verify_self_consistency(
            "core/self_modification/loop.py",
            "def broken(\n",
            "class SelfModificationLoop:\n    pass\n"
        )
        assert result.syntax_ok is False
        assert result.can_bootstrap is False

    def test_verify_safety_violation_clear_immutable(self):
        sandbox = BootstrapSandbox()
        original = 'IMMUTABLE_FILES = {"core/spirit_core.py"}\n'
        patched = 'IMMUTABLE_FILES = {}\n'
        result = sandbox._validate_self_modification_safety(
            "core/self_modification/loop.py", patched, original
        )
        assert result[0] is False
        assert any("清空IMMUTABLE" in v for v in result[1])

    def test_verify_safety_violation_remove_audit(self):
        sandbox = BootstrapSandbox()
        original = 'class Foo:\n    def _write_audit_log(self): pass\n    def rollback(self): pass\n'
        patched = 'class Foo:\n    def rollback(self): pass\n'
        result = sandbox._validate_self_modification_safety(
            "core/self_modification/loop.py", patched, original
        )
        assert result[0] is False

    def test_verify_safety_ok(self):
        sandbox = BootstrapSandbox()
        code = 'class Foo:\n    def _write_audit_log(self): pass\n    def rollback(self): pass\n'
        result = sandbox._validate_self_modification_safety(
            "core/self_modification/loop.py", code, code
        )
        assert result[0] is True

    def test_bootstrap_result_defaults(self):
        result = BootstrapResult(file_path="test.py")
        assert result.can_bootstrap is False
        assert result.syntax_ok is False
        assert result.violations == []


class TestSelfModificationDeployer:
    def test_deployer_instantiation(self):
        deployer = SelfModificationDeployer()
        assert deployer._bootstrap is not None

    def test_deploy_syntax_error_fails_early(self):
        deployer = SelfModificationDeployer()
        result = deployer.deploy_self_modification(
            "core/self_modification/loop.py",
            "def broken(\n",
            "class SelfModificationLoop:\n    pass\n",
            0.95,
        )
        assert result["final_status"] == "sandbox_failed"
        assert result["stages"]["0_1pct"]["passed"] is False

    def test_deploy_safety_violation_fails(self):
        deployer = SelfModificationDeployer()
        original = 'IMMUTABLE_FILES = {"core/spirit_core.py"}\n'
        patched = 'IMMUTABLE_FILES = {}\n'
        result = deployer.deploy_self_modification(
            "core/self_modification/loop.py",
            patched,
            original,
            0.95,
        )
        assert result["final_status"] == "sandbox_failed"

    def test_deploy_result_has_stages(self):
        deployer = SelfModificationDeployer()
        result = deployer.deploy_self_modification(
            "core/self_modification/loop.py",
            "def broken(\n",
            "class SelfModificationLoop:\n    pass\n",
            0.95,
        )
        assert "0_1pct" in result["stages"]
        assert "file_path" in result
