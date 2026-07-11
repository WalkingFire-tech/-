import asyncio
import re
from typing import Dict
from loguru import logger
from core.tool_registry import ToolInterface, ToolResult, run_tool_async


class SerialPortTool(ToolInterface):
    @property
    def name(self) -> str:
        return "serial_port"

    @property
    def description(self) -> str:
        return "串口通信：扫描可用串口、打开串口连接、读取串口数据（支持GPS/NMEA等协议）。运行在本地Windows环境，可直接访问物理硬件。"

    @property
    def parameters(self) -> Dict:
        return {
            "query": {"type": "string", "description": "操作描述或串口参数", "required": True},
            "action": {"type": "string", "description": "操作类型: scan/open/read", "default": "auto"},
            "port": {"type": "string", "description": "串口名(如COM8)", "default": ""},
            "baudrate": {"type": "integer", "description": "波特率", "default": 9600},
            "bytesize": {"type": "integer", "description": "数据位(5-8)", "default": 8},
            "parity": {"type": "string", "description": "校验位(N/E/O)", "default": "N"},
            "stopbits": {"type": "integer", "description": "停止位(1/2)", "default": 1},
            "timeout": {"type": "integer", "description": "读取超时秒数", "default": 5},
            "duration": {"type": "integer", "description": "持续读取秒数", "default": 5},
        }

    @property
    def timeout(self) -> float:
        return 30.0

    @property
    def category(self) -> str:
        return "hardware"

    @property
    def priority(self) -> int:
        return 60

    def can_handle(self, query: str, intent_type: str = "") -> bool:
        serial_indicators = [
            "串口", "com口", "com", "serial", "uart", "波特率", "baudrate",
            "gps数据", "gps", "nmea", "gnss", "gpgga", "gprmc",
            "ch340", "cp210", "ft232", "pl2303",
            "arduino", "stm32", "esp32", "单片机数据",
        ]
        q_lower = query.lower()
        return any(ind in q_lower for ind in serial_indicators)

    def _parse_port_params(self, query: str) -> dict:
        params = {}

        port_match = re.search(r'COM\d+|/dev/tty\w+', query, re.IGNORECASE)
        if port_match:
            params["port"] = port_match.group().upper()

        baud_match = re.search(r'(\d{3,6})\s*(?:波特率|baud|bps)', query, re.IGNORECASE)
        if baud_match:
            params["baudrate"] = int(baud_match.group(1))
        elif re.search(r'9600|19200|38400|57600|115200', query):
            for rate in ["9600", "19200", "38400", "57600", "115200"]:
                if rate in query:
                    params["baudrate"] = int(rate)
                    break

        if "8" in query and ("数据位" in query or "databits" in query.lower()):
            params["bytesize"] = 8

        parity_map = {"none": "N", "even": "E", "odd": "O", "无校验": "N", "偶校验": "E", "奇校验": "O"}
        for k, v in parity_map.items():
            if k in query.lower():
                params["parity"] = v
                break

        return params

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        action = kwargs.get("action", "auto")
        port = kwargs.get("port", "")
        baudrate = kwargs.get("baudrate", 9600)
        bytesize = kwargs.get("bytesize", 8)
        parity = kwargs.get("parity", "N")
        stopbits = kwargs.get("stopbits", 1)
        read_timeout = kwargs.get("timeout", 5)
        duration = kwargs.get("duration", 5)

        parsed = self._parse_port_params(query)
        port = port or parsed.get("port", "")
        baudrate = parsed.get("baudrate", baudrate)

        if action == "auto":
            if not port:
                action = "scan"
            else:
                action = "read"

        if action == "scan":
            return await self._scan_ports()
        elif action in ("open", "read"):
            if not port:
                scan_result = await self._scan_ports()
                if scan_result.success and scan_result.data:
                    first_port = re.search(r'COM\d+', scan_result.data)
                    if first_port:
                        port = first_port.group()
                    else:
                        return scan_result
                else:
                    return scan_result
            return await self._read_port(port, baudrate, bytesize, parity, stopbits, read_timeout, duration)
        else:
            return ToolResult(success=False, error=f"未知操作: {action}", source=self.name)

    async def _scan_ports(self) -> ToolResult:
        try:
            def _scan():
                import serial.tools.list_ports
                ports = serial.tools.list_ports.comports()
                if not ports:
                    return "未检测到任何串口设备"
                lines = [f"检测到 {len(ports)} 个串口:"]
                for p in sorted(ports, key=lambda x: x.device):
                    lines.append(f"  {p.device} | {p.description} | {p.hwid}")
                return "\n".join(lines)

            result = await run_tool_async(_scan, timeout=10)
            if result:
                return ToolResult(success=True, data=result, source="serial_scan", quality=80)
            else:
                return ToolResult(success=False, error="串口扫描失败", source=self.name)

        except ImportError:
            return ToolResult(
                success=False,
                error="pyserial未安装，请运行: pip install pyserial",
                source=self.name,
                quality=10,
            )
        except Exception as e:
            return ToolResult(success=False, error=f"串口扫描异常: {e}", source=self.name)

    async def _read_port(self, port: str, baudrate: int, bytesize: int,
                         parity: str, stopbits: int, read_timeout: int,
                         duration: int) -> ToolResult:
        try:
            def _read():
                import serial
                import time

                parity_map = {"N": serial.PARITY_NONE, "E": serial.PARITY_EVEN, "O": serial.PARITY_ODD}
                bytesize_map = {5: serial.FIVEBITS, 6: serial.SIXBITS, 7: serial.SEVENBITS, 8: serial.EIGHTBITS}
                stopbits_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}

                ser = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    bytesize=bytesize_map.get(bytesize, serial.EIGHTBITS),
                    parity=parity_map.get(parity.upper(), serial.PARITY_NONE),
                    stopbits=stopbits_map.get(stopbits, serial.STOPBITS_ONE),
                    timeout=read_timeout,
                )

                lines = []
                start = time.time()
                while time.time() - start < duration:
                    if ser.in_waiting > 0:
                        raw = ser.readline()
                        try:
                            decoded = raw.decode("ascii", errors="ignore").strip()
                        except Exception:
                            decoded = raw.hex()
                        if decoded:
                            lines.append(decoded)
                    time.sleep(0.05)

                ser.close()

                if not lines:
                    return f"端口 {port} 已打开(波特率{baudrate})，但{duration}秒内未收到数据。请确认设备已连接并正在发送数据。"

                output_parts = [
                    f"✅ 从 {port} (波特率{baudrate}, {bytesize}{parity}{stopbits}) 读取到 {len(lines)} 行数据:",
                    "",
                ]

                for line in lines[:50]:
                    output_parts.append(line)

                if len(lines) > 50:
                    output_parts.append(f"... (共{len(lines)}行，仅显示前50行)")

                gps_parsed = self._parse_nmea(lines)
                if gps_parsed:
                    output_parts.append("")
                    output_parts.append("--- GPS数据解析 ---")
                    for k, v in gps_parsed.items():
                        output_parts.append(f"  {k}: {v}")

                return "\n".join(output_parts)

            result = await run_tool_async(_read, timeout=duration + 10)
            if result:
                return ToolResult(success=True, data=result, source=f"serial:{port}", quality=85)
            else:
                return ToolResult(success=False, error=f"读取{port}失败", source=self.name)

        except ImportError:
            return ToolResult(
                success=False,
                error="pyserial未安装，请运行: pip install pyserial",
                source=self.name,
                quality=10,
            )
        except Exception as e:
            error_msg = str(e)
            if "Permission" in error_msg or "拒绝" in error_msg:
                error_msg += " — 端口可能被其他程序占用，请关闭串口助手后重试"
            elif "not found" in error_msg or "找不到" in error_msg:
                error_msg += " — 端口不存在，请确认设备已连接"
            return ToolResult(success=False, error=f"串口读取失败: {error_msg}", source=self.name)

    @staticmethod
    def _parse_nmea(lines: list) -> dict:
        result = {}
        for line in lines:
            if line.startswith("$GNGGA") or line.startswith("$GPGGA"):
                parts = line.split(",")
                if len(parts) >= 10:
                    try:
                        time_utc = parts[1][:2] + ":" + parts[1][2:4] + ":" + parts[1][4:6]
                        lat_raw = float(parts[2])
                        lat = int(lat_raw / 100) + (lat_raw % 100) / 60
                        lat_dir = parts[3]
                        lon_raw = float(parts[4])
                        lon = int(lon_raw / 100) + (lon_raw % 100) / 60
                        lon_dir = parts[5]
                        fix = int(parts[6])
                        sats = int(parts[7])

                        result["UTC时间"] = time_utc
                        result["纬度"] = f"{lat:.6f}° {lat_dir}"
                        result["经度"] = f"{lon:.6f}° {lon_dir}"
                        result["定位状态"] = "有效" if fix > 0 else "无效"
                        result["卫星数"] = sats
                        if len(parts) > 9:
                            result["海拔(m)"] = parts[9]
                    except (ValueError, IndexError):
                        pass
                break
        return result