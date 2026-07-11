import asyncio
import subprocess
import platform
from typing import Dict
from loguru import logger
from core.tool_registry import ToolInterface, ToolResult, run_tool_async

_DANGEROUS_COMMANDS = [
    "rm -rf", "del /s /q", "format", "fdisk", "mkfs",
    "shutdown", "reboot", "taskkill /f /pid 0",
    "reg delete", "reg add", "net user", "net localgroup",
    "cipher /w", "sfc", "dism", "bcdedit",
]


class BashTool(ToolInterface):
    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "系统命令执行：在本地Windows/Linux终端执行shell命令，获取输出结果。可访问硬件、文件系统、网络等系统资源。"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "要执行的shell命令", "required": True},
            "timeout": {"type": "integer", "description": "超时秒数", "default": 15},
            "workdir": {"type": "string", "description": "工作目录", "default": ""},
        }

    @property
    def timeout(self) -> float:
        return 20.0

    @property
    def category(self) -> str:
        return "system"

    @property
    def priority(self) -> int:
        return 55

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        system_indicators = [
            "运行", "执行", "命令", "cmd", "powershell", "bash", "shell",
            "串口", "com", "端口", "硬件", "设备", "usb", "gpu", "cpu",
            "磁盘", "内存", "网络", "ip", "ping", "进程", "服务",
            "安装", "卸载", "启动", "停止", "查询", "检测", "扫描",
            "run", "execute", "command", "serial", "port", "hardware",
            "device", "install", "check", "scan", "list",
        ]
        q_lower = query.lower()
        return any(ind in q_lower for ind in system_indicators)

    async def execute(self, **kwargs) -> ToolResult:
        command = kwargs.get("query", "")
        timeout = kwargs.get("timeout", 15)
        workdir = kwargs.get("workdir", "")

        if not command:
            return ToolResult(success=False, error="命令不能为空", source=self.name)

        for dangerous in _DANGEROUS_COMMANDS:
            if dangerous in command.lower():
                return ToolResult(
                    success=False,
                    error=f"危险命令被拦截: {dangerous}",
                    source=self.name,
                    quality=0,
                )

        try:
            def _run_command():
                is_windows = platform.system() == "Windows"
                if is_windows:
                    cmd_args = ["powershell", "-Command", command]
                else:
                    cmd_args = ["bash", "-c", command]

                result = subprocess.run(
                    cmd_args,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=workdir if workdir else None,
                    encoding="utf-8",
                    errors="replace",
                )

                output_parts = []
                if result.stdout:
                    output_parts.append(result.stdout.strip())
                if result.stderr:
                    output_parts.append(f"[stderr] {result.stderr.strip()}")

                output = "\n".join(output_parts) if output_parts else "(无输出)"
                return {
                    "exit_code": result.returncode,
                    "output": output,
                    "success": result.returncode == 0,
                }

            result = await run_tool_async(_run_command, timeout=timeout + 5)

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                error=f"命令执行超时({timeout}s)",
                source=self.name,
                quality=10,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"命令执行失败: {e}",
                source=self.name,
                quality=10,
            )

        if result and result.get("success"):
            return ToolResult(
                success=True,
                data=result["output"],
                source=f"bash(exit={result['exit_code']})",
                quality=75,
                metadata={"exit_code": result["exit_code"]},
            )
        else:
            output = (result or {}).get("output", "未知错误")
            return ToolResult(
                success=False,
                error=output,
                source=self.name,
                quality=20,
                metadata={"exit_code": (result or {}).get("exit_code", -1)},
            )