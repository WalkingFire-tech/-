import asyncio
import subprocess
import importlib
from loguru import logger
from infrastructure.database_manager import DatabaseManager


class CapabilityGapLearner:
    _instance = None

    CAPABILITY_MAP = {
        "hardware_access": {
            "needed_capability": "硬件访问",
            "tools": ["serial_port", "bash"],
            "dependencies": ["serial"],
            "install_commands": {"serial": "pip install pyserial --quiet"},
            "self_reason": (
                "我运行在本地Windows环境，可以直接访问硬件。"
                "串口数据：用pyserial库打开COM端口读取。"
                "硬件信息：用PowerShell命令查询。"
                "系统命令：用subprocess执行。"
                "缺少依赖：先pip install安装。"
            ),
        },
        "system_command": {
            "needed_capability": "系统命令执行",
            "tools": ["bash"],
            "dependencies": [],
            "install_commands": {},
            "self_reason": "我可以通过subprocess模块执行PowerShell/CMD命令，访问文件系统、进程、网络等系统资源。",
        },
        "code_generation": {
            "needed_capability": "代码生成与执行",
            "tools": ["code_executor", "bash"],
            "dependencies": [],
            "install_commands": {},
            "self_reason": "我可以通过code_executor工具执行Python代码，或通过bash工具运行脚本。",
        },
        "tool_missing": {
            "needed_capability": "工具构建",
            "tools": [],
            "dependencies": [],
            "install_commands": {},
            "self_reason": "我可以使用tool_builder构建新工具，或直接编写Python代码创建工具并注册到tool_registry。",
        },
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._init_db()

    def _init_db(self):
        try:
            db = DatabaseManager.get("data/capability_gaps.db")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS capability_gaps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    failed_paths TEXT,
                    gap_type TEXT,
                    resolution TEXT,
                    resolved INTEGER DEFAULT 0,
                    attempts INTEGER DEFAULT 1,
                    first_seen TEXT,
                    last_seen TEXT
                )
            """)
        except Exception as e:
            logger.debug(f"能力缺失库初始化: {e}")

    def assess_capability(self, query: str, intent_type: str, methodology: dict) -> dict:
        gap_type = self._classify_gap(query)
        if gap_type == "knowledge_shallow":
            return None

        cap_info = self.CAPABILITY_MAP.get(gap_type, {})
        needed_tools = cap_info.get("tools", [])
        needed_deps = cap_info.get("dependencies", [])

        missing_tools = self._check_missing_tools(needed_tools)
        missing_deps = self._check_missing_deps(needed_deps)

        if not missing_tools and not missing_deps:
            return None

        resolution_plan = self._build_resolution_plan(gap_type, missing_tools, missing_deps)

        return {
            "gap_detected": True,
            "gap_type": gap_type,
            "needed_capability": cap_info.get("needed_capability", gap_type),
            "missing_tools": missing_tools,
            "missing_deps": missing_deps,
            "resolution_plan": resolution_plan,
            "query": query[:200],
        }

    def _classify_gap(self, query: str) -> str:
        q = query.lower()

        hardware_kw = ["串口", "com", "serial", "波特率", "gps", "nmea", "硬件",
                        "设备", "usb", "传感器", "arduino", "stm32", "esp32",
                        "单片机", "引脚", "gpio", "i2c", "spi", "uart"]
        if any(kw in q for kw in hardware_kw):
            return "hardware_access"

        system_kw = ["运行", "执行", "命令", "cmd", "powershell", "bash", "shell",
                      "安装", "启动", "停止", "进程", "服务", "脚本"]
        if any(kw in q for kw in system_kw):
            return "system_command"

        code_kw = ["代码", "编程", "函数", "程序", "算法", "实现", "写一段", "开发"]
        if any(kw in q for kw in code_kw):
            return "code_generation"

        if "工具" in q or "tool" in q:
            return "tool_missing"

        return "knowledge_shallow"

    def _check_missing_tools(self, tool_names: list) -> list:
        missing = []
        try:
            from core.tool_registry import tool_registry
            for name in tool_names:
                if name not in tool_registry._tools:
                    missing.append(name)
        except Exception:
            missing = list(tool_names)
        return missing

    def _check_missing_deps(self, dep_names: list) -> list:
        missing = []
        for dep in dep_names:
            try:
                importlib.import_module(dep)
            except ImportError:
                missing.append(dep)
        return missing

    def _build_resolution_plan(self, gap_type: str, missing_tools: list, missing_deps: list) -> str:
        steps = []

        for dep in missing_deps:
            cap_info = self.CAPABILITY_MAP.get(gap_type, {})
            install_cmd = cap_info.get("install_commands", {}).get(dep, f"pip install {dep}")
            steps.append(f"安装依赖: {install_cmd}")

        for tool in missing_tools:
            steps.append(f"注册工具: {tool}")

        cap_info = self.CAPABILITY_MAP.get(gap_type, {})
        self_reason = cap_info.get("self_reason", "")
        if self_reason:
            steps.append(f"自我认知: {self_reason}")

        return " → ".join(steps)

    async def acquire_capability(self, assessment: dict) -> str:
        if not assessment:
            return ""

        gap_type = assessment.get("gap_type", "")
        missing_deps = assessment.get("missing_deps", [])
        missing_tools = assessment.get("missing_tools", [])
        results = []

        for dep in missing_deps:
            result = await self._install_dependency(dep, gap_type)
            if result:
                results.append(result)

        for tool in missing_tools:
            result = await self._ensure_tool_registered(tool)
            if result:
                results.append(result)

        if not results and not missing_deps and not missing_tools:
            cap_info = self.CAPABILITY_MAP.get(gap_type, {})
            self_reason = cap_info.get("self_reason", "")
            if self_reason:
                results.append(self_reason)

        if results:
            self._record_gap(assessment, resolved=1, resolution="; ".join(results))
            return "; ".join(results)

        return ""

    async def _install_dependency(self, dep_name: str, gap_type: str) -> str:
        cap_info = self.CAPABILITY_MAP.get(gap_type, {})
        install_cmd = cap_info.get("install_commands", {}).get(dep_name, f"pip install {dep_name}")
        try:
            result = subprocess.run(
                install_cmd.split(),
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0:
                logger.info(f"📦 依赖安装成功: {dep_name}")
                return f"已安装 {dep_name}"
            else:
                logger.warning(f"依赖安装失败: {dep_name} - {result.stderr[:100]}")
                return f"安装{dep_name}失败: {result.stderr[:100]}"
        except Exception as e:
            logger.debug(f"安装依赖异常: {e}")
            return ""

    async def _ensure_tool_registered(self, tool_name: str) -> str:
        try:
            from core.tool_registry import tool_registry
            if tool_name in tool_registry._tools:
                return f"工具{tool_name}已就绪"

            tool_map = {
                "serial_port": "core.tools.serial_port_tool:SerialPortTool",
                "bash": "core.tools.bash_tool:BashTool",
            }

            if tool_name in tool_map:
                module_path, class_name = tool_map[tool_name].rsplit(":", 1)
                import importlib
                module = importlib.import_module(module_path)
                tool_cls = getattr(module, class_name)
                tool_registry.register(tool_cls())
                logger.info(f"🔧 工具已注册: {tool_name}")
                return f"已注册工具 {tool_name}"
        except Exception as e:
            logger.debug(f"工具注册失败: {tool_name} - {e}")
        return ""

    def update_methodology(self, methodology: dict, assessment: dict) -> dict:
        gap_type = assessment.get("gap_type", "")
        cap_info = self.CAPABILITY_MAP.get(gap_type, {})

        if gap_type == "hardware_access":
            methodology["strategy"] = "硬件访问+串口通信+数据解析"
            if "工具调用(串口)" not in methodology.get("source_priority", []):
                methodology.setdefault("source_priority", []).insert(0, "工具调用(串口)")
            methodology["need_essence_reasoning"] = False
        elif gap_type == "system_command":
            methodology["strategy"] = "系统命令执行+结果解析"
            if "工具调用(bash)" not in methodology.get("source_priority", []):
                methodology.setdefault("source_priority", []).insert(0, "工具调用(bash)")
            methodology["need_essence_reasoning"] = False
        elif gap_type == "code_generation":
            if "工具调用(代码)" not in methodology.get("source_priority", []):
                methodology.setdefault("source_priority", []).insert(0, "工具调用(代码)")

        return methodology

    def detect_gap(self, query: str, attempts: list, final_response: str) -> dict:
        failed = [a for a in attempts if not a[1]]
        successful = [a for a in attempts if a[1]]

        if successful and final_response and len(final_response) > 50:
            return None

        failed_names = [a[0] for a in failed]
        gap_type = self._classify_gap(query)

        gap = {
            "query": query[:200],
            "failed_paths": ", ".join(failed_names),
            "gap_type": gap_type,
            "resolution": "",
            "resolved": 0,
        }

        self._record_gap(gap)
        return gap

    def _record_gap(self, gap: dict, resolved: int = 0, resolution: str = ""):
        try:
            from datetime import datetime
            db = DatabaseManager.get("data/capability_gaps.db")
            now = datetime.now().isoformat()
            row = db.query_one(
                "SELECT id, attempts FROM capability_gaps WHERE query LIKE ? AND gap_type=?",
                (f"%{gap.get('query', '')[:30]}%", gap.get("gap_type", "")),
            )
            if row:
                db.execute(
                    "UPDATE capability_gaps SET attempts=?, last_seen=?, failed_paths=?, resolution=?, resolved=? WHERE id=?",
                    (row[1] + 1, now, gap.get("failed_paths", ""), resolution, resolved, row[0]),
                    commit=True,
                )
            else:
                db.execute(
                    "INSERT INTO capability_gaps (query, failed_paths, gap_type, resolution, resolved, attempts, first_seen, last_seen) VALUES (?,?,?,?,?,?,?,?)",
                    (gap.get("query", ""), gap.get("failed_paths", ""), gap.get("gap_type", ""),
                     resolution, resolved, 1, now, now),
                    commit=True,
                )
        except Exception as e:
            logger.debug(f"能力缺失记录失败: {e}")


capability_gap_learner = CapabilityGapLearner()
