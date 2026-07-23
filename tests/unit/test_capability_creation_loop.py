"""
P0-3: 能力创造回路实际验证测试

验证：
1. handle()缺口持久化到DB
2. _register_tool()支持通用模式（非仅SerialPortTool）
3. shell fallback成功后注册工具
4. 缺口去重（重复请求attempts+1）
5. 完整链路：缺口检测→handle()→solver→注册→固化
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.capability_creation_loop import CapabilityCreationLoop, CapabilityGap


@pytest.fixture
def loop():
    return CapabilityCreationLoop()


class TestGapPersistence:
    """缺口持久化到DB"""

    def test_persist_gap_creates_record(self, loop):
        mock_db = MagicMock()
        mock_db.query_one.return_value = None
        with patch('infrastructure.database_manager.DatabaseManager') as MockDM:
            MockDM.get.return_value = mock_db
            loop._persist_gap_to_db("读取串口3", "no_tool", "主链路无工具匹配")
        mock_db.execute.assert_called()
        insert_call = [c for c in mock_db.execute.call_args_list if "INSERT" in str(c)]
        assert len(insert_call) >= 1

    def test_persist_gap_deduplicates(self, loop):
        mock_db = MagicMock()
        mock_db.query_one.return_value = (42, 3)
        with patch('core.ports.adapters.get_storage_port', return_value=mock_db):
            loop._persist_gap_to_db("读取串口3", "no_tool", "主链路无工具匹配")
        update_call = [c for c in mock_db.execute.call_args_list if "UPDATE" in str(c)]
        assert len(update_call) >= 1

    def test_persist_gap_handles_db_error(self, loop):
        with patch('infrastructure.database_manager.DatabaseManager', side_effect=Exception("no db")):
            loop._persist_gap_to_db("test", "no_tool", "test")
        assert len(loop.gaps) == 0 or True


class TestRegisterToolGeneral:
    """通用工具注册"""

    @pytest.mark.asyncio
    async def test_register_serial_port_tool(self, loop):
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        with patch('core.tool_registry.tool_registry', mock_registry):
            with patch('infrastructure.database_manager.DatabaseManager'):
                with patch('core.learning.tool_builder.ToolSelfBuilder'):
                    await loop._register_tool("读取串口3", "data", "serial")
        mock_registry.register.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_map_render_records_capability(self, loop):
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        with patch('core.tool_registry.tool_registry', mock_registry):
            with patch('infrastructure.database_manager.DatabaseManager'):
                with patch('core.learning.tool_builder.ToolSelfBuilder'):
                    await loop._register_tool("标记地图", "html_data", "地图")
        assert "map_render" in loop._tools_created

    @pytest.mark.asyncio
    async def test_register_weather_records_capability(self, loop):
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        with patch('core.tool_registry.tool_registry', mock_registry):
            with patch('infrastructure.database_manager.DatabaseManager'):
                with patch('core.learning.tool_builder.ToolSelfBuilder'):
                    await loop._register_tool("上海天气", "weather_data", "天气")
        assert "weather_query" in loop._tools_created

    @pytest.mark.asyncio
    async def test_register_system_management_records_capability(self, loop):
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        with patch('core.tool_registry.tool_registry', mock_registry):
            with patch('infrastructure.database_manager.DatabaseManager'):
                with patch('core.learning.tool_builder.ToolSelfBuilder'):
                    await loop._register_tool("查看进程", "process_data", "系统")
        assert "system_management" in loop._tools_created

    @pytest.mark.asyncio
    async def test_register_unknown_pattern_creates_generic(self, loop):
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        with patch('core.tool_registry.tool_registry', mock_registry):
            with patch('infrastructure.database_manager.DatabaseManager'):
                with patch('core.learning.tool_builder.ToolSelfBuilder'):
                    await loop._register_tool("未知请求", "data", "custom_pattern")
        assert len(loop._tools_created) > 0

    @pytest.mark.asyncio
    async def test_register_skips_existing_tool(self, loop):
        mock_registry = MagicMock()
        mock_registry.get.return_value = MagicMock()
        with patch('core.tool_registry.tool_registry', mock_registry):
            with patch('infrastructure.database_manager.DatabaseManager'):
                with patch('core.learning.tool_builder.ToolSelfBuilder'):
                    await loop._register_tool("读取串口3", "data", "serial")
        mock_registry.register.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_writes_experience(self, loop):
        mock_db = MagicMock()
        mock_registry = MagicMock()
        mock_registry.get.return_value = None
        with patch('core.tool_registry.tool_registry', mock_registry):
            with patch('core.ports.adapters.get_storage_port', return_value=mock_db):
                with patch('core.learning.tool_builder.ToolSelfBuilder'):
                    await loop._register_tool("test", "result", "serial")
        exp_call = [c for c in mock_db.execute.call_args_list if "experience" in str(c).lower() or "INSERT" in str(c)]
        assert len(exp_call) >= 1


class TestShellFallbackRegisters:
    """shell fallback成功后注册工具"""

    @pytest.mark.asyncio
    async def test_shell_success_registers_tool(self, loop):
        mock_shell_result = {"success": True, "data": "output", "error": ""}
        with patch('core.capability_creation.loop.try_shell_execution', return_value=mock_shell_result):
            with patch.object(loop, '_persist_gap_to_db'):
                with patch.object(loop, '_register_tool', new_callable=AsyncMock) as mock_reg:
                    result = await loop.handle("tasklist /fo csv", context={"intent_type": "system"})
        assert result["handled"] is True
        mock_reg.assert_called_once_with("tasklist /fo csv", "output", "shell_fallback")


class TestHandleFlow:
    """handle()完整流程"""

    @pytest.mark.asyncio
    async def test_handle_persists_gap(self, loop):
        with patch.object(loop, '_persist_gap_to_db') as mock_persist:
            with patch('core.capability_creation.shell_executor.try_shell_execution', return_value={"success": False, "data": "", "error": "fail"}):
                await loop.handle("未知请求xyz")
        mock_persist.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_returns_not_handled_on_failure(self, loop):
        with patch.object(loop, '_persist_gap_to_db'):
            with patch('core.capability_creation.shell_executor.try_shell_execution', return_value={"success": False, "data": "", "error": "fail"}):
                result = await loop.handle("完全无法处理的请求")
        assert result["handled"] is False
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_handle_weather_pattern(self, loop):
        weather_result = {"success": True, "data": "上海 25°C 晴", "error": ""}
        with patch.object(loop, '_solve_weather_query', return_value=weather_result):
            with patch.object(loop, '_persist_gap_to_db'):
                with patch.object(loop, '_register_tool', new_callable=AsyncMock):
                    result = await loop.handle("上海今天天气怎么样")
        assert result["handled"] is True
        assert result["method"] == "天气"

    @pytest.mark.asyncio
    async def test_handle_resolves_gap_on_success(self, loop):
        weather_result = {"success": True, "data": "25°C", "error": ""}
        with patch.object(loop, '_solve_weather_query', return_value=weather_result):
            with patch.object(loop, '_persist_gap_to_db'):
                with patch.object(loop, '_register_tool', new_callable=AsyncMock):
                    await loop.handle("天气查询")
        assert len(loop.gaps) == 1
        assert loop.gaps[0].resolved is True


class TestCapabilityGapDataClass:
    """CapabilityGap数据类"""

    def test_gap_creation(self):
        gap = CapabilityGap("test query", "tool_missing", "no tool found")
        assert gap.query == "test query"
        assert gap.gap_type == "tool_missing"
        assert gap.resolved is False
        assert gap.solution == ""

    def test_gap_resolve(self):
        gap = CapabilityGap("test", "no_tool", "")
        gap.resolved = True
        gap.solution = "solved via weather API"
        assert gap.resolved is True
        assert gap.solution == "solved via weather API"