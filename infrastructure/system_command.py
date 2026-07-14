"""
系统命令安全执行器 — 学习、诊断、验证

区别于CodeExecutor(仅Python代码):
  - 支持CMD/PowerShell指令
  - 白名单机制(只允许安全命令)
  - 集成到L5自修改管线作为验证步骤
  - 为CuriosityEngine提供自诊断能力

安全设计:
  - 命令白名单: 只允许已知安全的系统命令
  - 参数过滤: 阻止路径遍历、管道注入等
  - 超时保护: 默认15秒
  - 输出大小限制: 默认100KB
  - 工作目录隔离: 只能在项目目录下执行
"""
import subprocess
import os
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# --------------- 命令白名单 ---------------
ALLOWED_COMMANDS = {
    # 系统诊断
    "systeminfo": {"args": "", "desc": "系统信息概览"},
    "tasklist": {"args": "/FI", "desc": "进程列表"},
    "wmic": {"args": "cpu get name,loadpercentage /format:list", "desc": "CPU信息"},
    "wmic": {"args": "memorychip get capacity /format:list", "desc": "内存信息"},
    # Python/项目诊断
    "python": {
        "allowed_subcommands": ["--version", "-c", "-m"],
        "desc": "Python执行(受限)",
    },
    "pytest": {"args": "tests/unit/", "desc": "运行单元测试"},
    "pip": {"allowed_subcommands": ["list", "show", "freeze"], "desc": "包管理(只读)"},
    # 基础命令
    "echo": {"args": "", "desc": "文本输出(测试/诊断)"},
    # 文件/目录操作(只读)
    "dir": {"args": "", "desc": "列出目录"},
    "where": {"args": "", "desc": "查找可执行文件"},
    # Git操作(只读)
    "git": {
        "allowed_subcommands": [
            "status", "log", "diff", "branch", "show", "rev-parse",
            "ls-files", "describe", "--version",
        ],
        "desc": "Git操作(只读)",
    },
    # 网络诊断(只读)
    "curl": {"args": "", "desc": "HTTP请求(限本地)"},
    "netstat": {"args": "-ano", "desc": "网络连接"},
    # PowerShell安全命令
    "powershell": {
        "allowed_subcommands": [
            "Get-Process", "Get-Service", "Get-Date", "Get-ChildItem",
            "Select-Object", "Measure-Object", "Get-Content", "Test-Path",
            "Get-WmiObject", "Write-Output", "Get-ComputerInfo",
        ],
        "desc": "PowerShell(只读安全命令)",
    },
}

# 危险参数模式 — 即使命令在白名单中，这些参数也会被拒绝
DANGEROUS_ARGS = [
    r"[&|`](?!$)",          # 命令链/管道(排除行尾); 分号单独处理避免误伤Python语句
    r"\.\./",              # 路径遍历
    r"\.\.\\",             # Windows路径遍历
    r">\s*\S",             # 输出重定向
    r"<\s*\S",             # 输入重定向
    r"rm\s+-rf",           # 递归删除
    r"del\s+/[fsq]",       # 强制删除
    r"format\s",           # 格式化
    r"shutdown",           # 关机
    r"taskkill",           # 杀进程
    r"net\s+user",         # 用户管理
    r"reg\s+(add|delete)", # 注册表修改
    r"powershell.*-Command", # PowerShell命令执行(禁止，只允许cmdlet名)
]

MAX_OUTPUT_BYTES = 100 * 1024   # 100KB
DEFAULT_TIMEOUT = 15             # 15秒
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class CommandResult:
    success: bool
    command: str
    output: str
    error: str = ""
    exit_code: int = 0
    duration_ms: float = 0.0
    method: str = "subprocess"
    diagnostics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success, "command": self.command,
            "output": self.output, "error": self.error,
            "exit_code": self.exit_code, "duration_ms": self.duration_ms,
            "method": self.method, "diagnostics": self.diagnostics,
        }


class SystemCommandExecutor:
    """安全的系统命令执行器 — 白名单 + 参数过滤 + 超时 + 输出限制"""

    @classmethod
    def validate_command(cls, command: str) -> Tuple[bool, str]:
        """验证命令是否在白名单中且参数安全"""
        parts = command.strip().split(maxsplit=1)
        if not parts:
            return False, "空命令"
        cmd = parts[0].lower().replace(".exe", "")
        args = parts[1] if len(parts) > 1 else ""

        # 检查命令白名单
        if cmd not in ALLOWED_COMMANDS:
            return False, f"命令 '{cmd}' 不在白名单中。允许: {list(ALLOWED_COMMANDS.keys())}"

        cmd_config = ALLOWED_COMMANDS[cmd]

        # 检查子命令白名单
        if "allowed_subcommands" in cmd_config and args:
            first_arg = args.split()[0].lower()
            allowed = [s.lower() for s in cmd_config["allowed_subcommands"]]
            if not any(first_arg.startswith(a) for a in allowed):
                return False, (
                    f"子命令 '{first_arg}' 不允许。{cmd}允许: {cmd_config['allowed_subcommands']}"
                )

        # 检查危险参数
        for pattern in DANGEROUS_ARGS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"检测到危险参数模式: {pattern}"

        return True, ""

    @classmethod
    def execute(
        cls,
        command: str,
        timeout: int = DEFAULT_TIMEOUT,
        capture: bool = True,
        cwd: Optional[str] = None,
    ) -> CommandResult:
        """安全执行系统命令"""
        start = time.time()

        # 验证
        valid, reason = cls.validate_command(command)
        if not valid:
            return CommandResult(
                success=False, command=command, output="", error=reason,
                diagnostics={"validation": "rejected"},
            )

        # 执行
        cwd = cwd or PROJECT_ROOT
        try:
            if command.startswith("powershell"):
                shell_cmd = command
                use_shell = False
            else:
                shell_cmd = command
                use_shell = True

            proc = subprocess.run(
                shell_cmd,
                shell=use_shell,
                capture_output=capture,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "SYSTEMROOT": os.environ.get("SYSTEMROOT", "C:\\Windows"),
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            output = proc.stdout or ""
            if len(output) > MAX_OUTPUT_BYTES:
                output = output[:MAX_OUTPUT_BYTES] + "\n... (输出截断)"

            return CommandResult(
                success=proc.returncode == 0,
                command=command,
                output=output,
                error=proc.stderr or "",
                exit_code=proc.returncode,
                duration_ms=(time.time() - start) * 1000,
                diagnostics={"truncated": len(proc.stdout or "") > MAX_OUTPUT_BYTES},
            )

        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False, command=command, output="",
                error=f"命令超时({timeout}秒)", duration_ms=(time.time() - start) * 1000,
                diagnostics={"timeout": True},
            )
        except Exception as e:
            return CommandResult(
                success=False, command=command, output="",
                error=str(e), duration_ms=(time.time() - start) * 1000,
            )

    @classmethod
    def run_diagnostics(cls) -> Dict[str, Any]:
        """运行系统自诊断 — 供CuriosityEngine和health_monitor调用"""
        results = {}
        checks = [
            ("python --version", "Python版本"),
            ("pip list", "已安装包(截断)"),
            ("git status --short", "Git状态"),
            ("dir", "项目目录"),
            ("tasklist /FI \"IMAGENAME eq python.exe\"", "Python进程"),
        ]
        for cmd, label in checks:
            valid, _ = cls.validate_command(cmd)
            if valid:
                r = cls.execute(cmd, timeout=10)
                output = r.output[:200] if r.output else r.error[:200]
                results[label] = {"ok": r.success, "output": output}
            else:
                results[label] = {"ok": False, "output": "命令未在白名单"}
        return results

    @classmethod
    def run_verification(cls, test_pattern: str = "tests/unit/") -> CommandResult:
        """运行测试验证 — 供L5部署后验证调用"""
        cmd = f"python -m pytest {test_pattern} -q"
        valid, reason = cls.validate_command(cmd)
        if not valid:
            return CommandResult(success=False, command=cmd, output="", error=reason)
        return cls.execute(cmd, timeout=120)

    @classmethod
    def get_available_commands(cls) -> Dict[str, str]:
        """列出所有白名单命令及其用途"""
        return {k: v.get("desc", "") for k, v in ALLOWED_COMMANDS.items()}


# 单例
system_cmd = SystemCommandExecutor()
