import re
import asyncio
from typing import Optional
from loguru import logger
from backend.services.path_handlers._shared import _fast_executor


async def fetch_tool_results(query: str, intent_type: str = "", methodology: dict = None, tool_intent: bool = False) -> Optional[list]:
    """路径I：工具调用框架（P0-4）— 使用独立线程池，不阻塞共享_executor"""
    try:
        from core.tool_registry import tool_executor, tool_registry
        logger.debug(f"[TOOL_DIAG] fetch_tool_results入口: query='{query[:50]}', tool_intent={tool_intent}, registry_id={id(tool_registry)}, tool_count={tool_registry.tool_count}")
        if tool_registry.tool_count == 0:
            try:
                from core.tool_registry import register_builtin_tools
                register_builtin_tools()
                logger.debug(f"[TOOL_DIAG] 自动注册后: tool_count={tool_registry.tool_count}, registry_id={id(tool_registry)}")
            except Exception as reg_e:
                logger.warning(f"[TOOL_DIAG] 自动注册失败: {reg_e}")
        tool_names = tool_registry.plan_tools(query, intent_type, methodology=methodology)
        logger.debug(f"[TOOL_DIAG] plan_tools返回: {tool_names}, tool_count={tool_registry.tool_count}")
        if not tool_names:
            logger.warning(f"[TOOL_DIAG] plan_tools返回空! query='{query[:50]}', tool_count={tool_registry.tool_count}")
            return None
        tool_names = tool_names[:8]
        params = extract_tool_params(query, intent_type, methodology=methodology)
        if tool_intent:
            code_tools = [n for n in tool_names if n in ("file_reader", "project_scanner", "code_indexer", "dependency_analyzer")]
            other_tools = [n for n in tool_names if n not in ("file_reader", "project_scanner", "code_indexer", "dependency_analyzer")]
            hint_tool = params.get("_tool_hint", "")
            if hint_tool and hint_tool not in other_tools[:3] and hint_tool in other_tools:
                other_tools.remove(hint_tool)
                other_tools.insert(0, hint_tool)
            tool_names = code_tools + other_tools[:3]
        logger.debug(f"[TOOL_DIAG] 执行工具: {tool_names}, params={params}")
        results = await tool_executor.execute_parallel(tool_names, params, total_timeout=20.0)
        logger.debug(f"[TOOL_DIAG] execute_parallel返回: {len(results)}个结果")
        candidates = []
        for r in results:
            logger.debug(f"[TOOL_DIAG] 工具结果: source={r.source}, success={r.success}, quality={r.quality}, data_len={len(str(r.data)) if r.data else 0}, error={r.error[:80] if r.error else ''}")
            c = r.to_candidate()
            if c:
                candidates.append(c)
                logger.debug(f"[TOOL_DIAG] to_candidate成功: source={c['source']}, quality={c['quality']}, resp_len={len(c['response'])}")
            else:
                logger.warning(f"[TOOL_DIAG] to_candidate返回None: source={r.source}, success={r.success}, has_data={r.data is not None}")
            try:
                from core.memory.layered_memory import layered_memory
                layered_memory.record_tool_usage(
                    r.source, query, r.success, r.quality, r.duration_ms
                )
            except Exception:
                pass
        logger.debug(f"[TOOL_DIAG] 最终candidates: {len(candidates)}个, sources={[c['source'] for c in candidates]}")
        return candidates if candidates else None
    except Exception as e:
        logger.error(f"[TOOL_DIAG] 工具调用异常: {e}", exc_info=True)
        return None


def query_needs_tools(query: str) -> bool:
    """判断用户查询是否需要工具调用（代码/文件/项目分析/硬件/系统命令相关）"""
    ql = query.lower()
    tool_triggers = [
        "读取", "打开", "查看文件", "文件内容", "看看文件", "读一下",
        "项目结构", "目录树", "技术栈", "项目概览", "有哪些文件",
        "在哪定义", "函数在哪", "类在哪", "代码索引", "代码结构",
        "依赖", "调用链", "影响范围", "模块关系",
        "readme", "read file", "open file", "show file",
        "project structure", "scan project", "dependency",
        "where defined", "code index",
        "串口", "com口", "serial", "波特率", "baudrate",
        "gps数据", "nmea", "gnss", "gpgga", "gprmc",
        "硬件", "设备", "端口", "com8", "com3", "com5",
        "运行命令", "执行命令", "cmd", "powershell", "bash", "shell",
        "检测硬件", "扫描设备", "获取数据", "读取数据",
        "ch340", "cp210", "ft232", "arduino", "stm32", "esp32",
        "单片机", "传感器", "usb设备",
    ]
    if any(t in ql for t in tool_triggers):
        return True
    if re.search(r'COM\d+', query, re.IGNORECASE):
        return True
    if re.search(r'[\w/\\]+\.\w{1,6}', query):
        return True
    return False


def extract_tool_params(query: str, intent_type: str = "", methodology: dict = None) -> dict:
    """从用户消息中智能提取工具参数，methodology提供认知层理解指导"""
    params = {"query": query}

    if methodology:
        domain = methodology.get("domain", "")
        essence = methodology.get("essence_unit", "")
        strategy = methodology.get("strategy", "")
        if domain == "硬件" or "串口" in essence or "serial" in essence.lower():
            params.setdefault("_tool_hint", "serial_port")
            num_match = re.search(r'(\d+)', query)
            if num_match and "port" not in params:
                params["port"] = f"COM{num_match.group(1)}"
            serial_match = re.search(r'(COM\d+)', query, re.IGNORECASE)
            if serial_match:
                params["port"] = serial_match.group().upper()
            baud_match = re.search(r'(\d{3,6})\s*(?:波特率|baud|bps)?', query)
            if baud_match and int(baud_match.group(1)) >= 300:
                params["baudrate"] = int(baud_match.group(1))
            return params

    serial_match = re.search(r'(COM\d+)', query, re.IGNORECASE)
    if serial_match or any(kw in query.lower() for kw in ["串口", "serial", "gps数据", "nmea"]):
        params.setdefault("_tool_hint", "serial_port")
        if serial_match:
            params["port"] = serial_match.group().upper()
        baud_match = re.search(r'(\d{3,6})\s*(?:波特率|baud|bps)?', query)
        if baud_match and int(baud_match.group(1)) >= 300:
            params["baudrate"] = int(baud_match.group(1))
        return params

    if any(kw in query.lower() for kw in ["运行命令", "执行命令", "cmd", "powershell", "bash", "运行", "执行"]):
        if not re.search(r'[\w/\\]+\.\w{1,6}', query):
            params.setdefault("_tool_hint", "bash")
            return params

    path_pattern = r'(?:读取|打开|查看|看看|读一下|read|open|show|cat)\s*[`"\']?([\w/\\.-]+\.\w{1,6})[`"\']?'
    path_match = re.search(path_pattern, query, re.IGNORECASE)
    if path_match:
        params["query"] = path_match.group(1).strip()
    else:
        file_pattern = r'([\w/\\]+\.\w{1,6})'
        file_match = re.search(file_pattern, query)
        if file_match:
            params["query"] = file_match.group(1).strip()

    if "项目结构" in query or "目录树" in query or "project structure" in query.lower():
        params.setdefault("_tool_hint", "project_scanner")
    if "依赖" in query or "dependency" in query.lower():
        params.setdefault("_tool_hint", "dependency_analyzer")

    return params