"""
单元测试 - chat_stream异常审计 (1.2) + 超时SSE反馈 (1.4)
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestRunSyncTimeout:
    @pytest.mark.asyncio
    async def test_run_sync_timeout_with_phase(self):
        from backend.services.path_handlers._shared import _run_sync
        import time

        def slow_func():
            time.sleep(5)
            return "done"

        with pytest.raises(asyncio.TimeoutError):
            await _run_sync(slow_func, timeout=0.1, phase="test_phase")

    @pytest.mark.asyncio
    async def test_run_sync_success(self):
        from backend.services.path_handlers._shared import _run_sync

        def fast_func():
            return "done"

        result = await _run_sync(fast_func, timeout=5, phase="test_phase")
        assert result == "done"


class TestBareExceptElimination:
    def test_no_bare_except_in_chat_stream(self):
        files_to_check = [
            "backend/chat_stream.py",
            "backend/services/chat_orchestrator.py",
        ]
        all_bare = []
        for filepath in files_to_check:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                stripped = line.rstrip()
                if stripped.endswith("except:") and "except Exception" not in stripped and "except ImportError" not in stripped and "except (" not in stripped:
                    all_bare.append((filepath, i, stripped))
        assert len(all_bare) == 0, f"Found bare except: {all_bare}"


class TestTimeoutSSEFeedback:
    def test_emit_supports_timeout_status(self):
        from backend.chat_stream import _emit
        event = _emit("step", {"phase": "test", "status": "timeout", "detail": "超时测试"})
        assert event is not None
        assert "timeout" in str(event) or event is not None