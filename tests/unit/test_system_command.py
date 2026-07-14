"""
单元测试 — 系统命令安全执行器
"""
import pytest


class TestCommandValidation:
    @pytest.fixture(autouse=True)
    def _setup(self):
        import sys; from pathlib import Path
        root = str(Path(__file__).parent.parent.parent)
        if root not in sys.path: sys.path.insert(0, root)
        yield

    def test_allowed_python_version(self):
        from infrastructure.system_command import SystemCommandExecutor
        ok, reason = SystemCommandExecutor.validate_command("python --version")
        assert ok, f"python --version blocked: {reason}"

    def test_allowed_pytest(self):
        from infrastructure.system_command import SystemCommandExecutor
        ok, reason = SystemCommandExecutor.validate_command("python -m pytest tests/unit/ -q")
        assert ok, f"pytest blocked: {reason}"

    def test_allowed_dir(self):
        from infrastructure.system_command import SystemCommandExecutor
        ok, _ = SystemCommandExecutor.validate_command("dir")
        assert ok

    def test_allowed_pip_list(self):
        from infrastructure.system_command import SystemCommandExecutor
        ok, _ = SystemCommandExecutor.validate_command("pip list")
        assert ok

    def test_rejects_format(self):
        from infrastructure.system_command import SystemCommandExecutor
        ok, _ = SystemCommandExecutor.validate_command("format C:")
        assert not ok

    def test_rejects_unknown_command(self):
        from infrastructure.system_command import SystemCommandExecutor
        ok, _ = SystemCommandExecutor.validate_command("rm -rf /")
        assert not ok

    def test_allowed_git_status(self):
        from infrastructure.system_command import SystemCommandExecutor
        ok, _ = SystemCommandExecutor.validate_command("git status")
        assert ok

    def test_allowed_powershell_safe(self):
        from infrastructure.system_command import SystemCommandExecutor
        ok, _ = SystemCommandExecutor.validate_command("powershell Get-Process")
        assert ok


class TestCommandExecution:
    @pytest.fixture(autouse=True)
    def _setup(self):
        import sys; from pathlib import Path
        root = str(Path(__file__).parent.parent.parent)
        if root not in sys.path: sys.path.insert(0, root)
        yield

    def test_execute_echo(self):
        from infrastructure.system_command import SystemCommandExecutor
        result = SystemCommandExecutor.execute("echo hello_test_123")
        assert result.success is True
        assert "hello_test_123" in result.output

    def test_execute_python_version(self):
        from infrastructure.system_command import SystemCommandExecutor
        result = SystemCommandExecutor.execute("python --version", timeout=5)
        assert result.success is True
        assert "Python" in result.output

    def test_execute_blocked_command(self):
        from infrastructure.system_command import SystemCommandExecutor
        result = SystemCommandExecutor.execute("del C:\\Windows\\System32")
        assert result.success is False
        assert "blocked" in result.error.lower() or "不在" in result.error

    def test_execute_dir(self):
        from infrastructure.system_command import SystemCommandExecutor
        result = SystemCommandExecutor.execute("dir")
        assert result.success is True
        assert "tests" in result.output.lower() or "backend" in result.output.lower()


class TestVerificationIntegration:
    @pytest.fixture(autouse=True)
    def _setup(self):
        import sys; from pathlib import Path
        root = str(Path(__file__).parent.parent.parent)
        if root not in sys.path: sys.path.insert(0, root)
        yield

    def test_run_pytest(self):
        from infrastructure.system_command import SystemCommandExecutor
        result = SystemCommandExecutor.execute(
            "python -m pytest tests/unit/test_feature_flags.py -q", timeout=30
        )
        assert result.success is True
        assert "passed" in result.output

    def test_import_check(self):
        from infrastructure.system_command import SystemCommandExecutor
        result = SystemCommandExecutor.execute(
            'python -c "from core.self_modification.defect_diagnoser import defect_diagnoser; print(\'OK\')"',
            timeout=10
        )
        assert result.success is True
        assert "OK" in result.output

    def test_diagnostics(self):
        from infrastructure.system_command import SystemCommandExecutor
        diag = SystemCommandExecutor.run_diagnostics()
        assert isinstance(diag, dict)
        assert len(diag) > 0, f"diagnostics should not be empty"
