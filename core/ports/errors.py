"""
端口异常类型 — 统一端口层的错误处理规范

所有端口实现应使用这些异常类型，而非抛出底层异常。
调用方可以统一捕获 PortError 或其子类。
"""


class PortError(Exception):
    """端口基础异常"""
    pass


class PortUnavailableError(PortError):
    """端口不可用（is_available()=False 或初始化失败）"""

    def __init__(self, port_name: str, reason: str = ""):
        self.port_name = port_name
        self.reason = reason
        super().__init__(f"Port '{port_name}' unavailable: {reason}" if reason else f"Port '{port_name}' unavailable")


class PortTimeoutError(PortError):
    """端口操作超时"""

    def __init__(self, port_name: str, operation: str = "", timeout: float = 0):
        self.port_name = port_name
        self.operation = operation
        self.timeout = timeout
        msg = f"Port '{port_name}' timeout"
        if operation:
            msg += f" on {operation}"
        if timeout:
            msg += f" ({timeout:.1f}s)"
        super().__init__(msg)


class PortMethodNotFoundError(PortError):
    """端口方法不存在（适配器探测失败）"""

    def __init__(self, port_name: str, method: str):
        self.port_name = port_name
        self.method = method
        super().__init__(f"Port '{port_name}' method '{method}' not found")