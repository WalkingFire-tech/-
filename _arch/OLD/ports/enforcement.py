"""
端口强制执行 — 运行时检测绕过端口直接使用基础设施

使用方式：
  from core.ports.enforcement import require_port, port_bypass_warning

  # 方式1: 装饰器 — 标记函数必须通过端口调用
  @require_port("storage")
  async def save_data(data):
      ...

  # 方式2: 上下文管理器 — 标记代码块绕过端口
  with port_bypass_warning("storage", reason="初始化阶段端口未就绪"):
      db = DatabaseManager()
"""
import os
import functools
from contextlib import contextmanager
from loguru import logger

_ENFORCEMENT_MODE = os.environ.get("PORT_ENFORCEMENT", "warn")


@contextmanager
def port_bypass_warning(port_name: str, reason: str = ""):
    """
    上下文管理器 — 标记代码块绕过端口

    在enforcement=strict模式下抛出异常，
    在enforcement=warn模式下记录警告，
    在enforcement=off模式下静默。
    """
    msg = f"端口绕过: {port_name}" + (f" — 原因: {reason}" if reason else "")
    if _ENFORCEMENT_MODE == "strict":
        from core.ports.errors import PortError
        raise PortError(f"严格模式禁止绕过端口: {msg}")
    elif _ENFORCEMENT_MODE == "warn":
        logger.warning(f"⚠️ {msg}")
    yield


def require_port(port_name: str):
    """
    装饰器 — 标记函数应通过端口调用

    在strict模式下，如果端口可用但函数内直接使用基础设施，抛出异常。
    在warn模式下，记录警告。
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            ports = kwargs.get("ports") or kwargs.get("_ports")
            if ports and port_name in ports:
                port = ports[port_name]
                if hasattr(port, "is_available") and port.is_available():
                    return await func(*args, **kwargs)
                else:
                    msg = f"@require_port('{port_name}'): 端口不可用，降级到基础设施"
                    if _ENFORCEMENT_MODE == "strict":
                        from core.ports.errors import PortUnavailableError
                        raise PortUnavailableError(port_name, msg)
                    elif _ENFORCEMENT_MODE == "warn":
                        logger.warning(f"⚠️ {msg}")
                    return await func(*args, **kwargs)
            else:
                msg = f"@require_port('{port_name}'): 未传入ports参数，无法验证端口合规"
                if _ENFORCEMENT_MODE == "warn":
                    logger.debug(msg)
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            ports = kwargs.get("ports") or kwargs.get("_ports")
            if ports and port_name in ports:
                port = ports[port_name]
                if hasattr(port, "is_available") and port.is_available():
                    return func(*args, **kwargs)
                else:
                    msg = f"@require_port('{port_name}'): 端口不可用，降级到基础设施"
                    if _ENFORCEMENT_MODE == "strict":
                        from core.ports.errors import PortUnavailableError
                        raise PortUnavailableError(port_name, msg)
                    elif _ENFORCEMENT_MODE == "warn":
                        logger.warning(f"⚠️ {msg}")
                    return func(*args, **kwargs)
            else:
                msg = f"@require_port('{port_name}'): 未传入ports参数，无法验证端口合规"
                if _ENFORCEMENT_MODE == "warn":
                    logger.debug(msg)
                return func(*args, **kwargs)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator