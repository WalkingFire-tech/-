import asyncio
import subprocess
from typing import Dict

from loguru import logger

from core.capability_creation.constants import _PS_ERROR_PATTERNS


async def try_shell_execution(query: str, ps_direct_fn=None) -> Dict:
    solutions = []
    if ps_direct_fn:
        solutions.append(ps_direct_fn(query))
    else:
        solutions.append(powershell_direct(query))

    for sol in solutions:
        try:
            result = await sol
            if result.get("success"):
                return result
        except Exception:
            continue

    return {"success": False, "data": "", "error": "所有shell方案均失败"}


async def powershell_direct(query: str) -> Dict:
    def _run():
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", query],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        combined = out + (" | " + err if err else "")
        if not combined or len(combined) <= 5:
            return {"success": False, "data": "", "error": "无输出"}
        for pat in _PS_ERROR_PATTERNS:
            if pat in combined:
                return {"success": False, "data": "", "error": f"PowerShell错误: {pat}"}
        if r.returncode != 0 and not out:
            return {"success": False, "data": "", "error": f"退出码{r.returncode}"}
        return {"success": True, "data": combined[:2000]}

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run)


async def solve_serial_read(query: str) -> Dict:
    import re
    port_match = re.search(r'COM\d+', query, re.IGNORECASE)
    cn_port_match = re.search(r'串口\s*(\d+)', query)
    baud_match = re.search(r'波特率\s*(\d{4,6})', query) or re.search(r'(\d{4,6})', query)

    if port_match:
        port = port_match.group(0).upper()
    elif cn_port_match:
        port = f"COM{cn_port_match.group(1)}"
    else:
        port = "COM1"
    baud = baud_match.group(1) if baud_match else "9600"

    ps_code = f"""
$port = New-Object System.IO.Ports.SerialPort '{port}',{baud},None,8,1
$port.ReadTimeout = 3000
try {{
    $port.Open()
    $data = @()
    $count = 0
    while ($count -lt 20) {{
        if ($port.BytesToRead -gt 0) {{
            $line = $port.ReadLine()
            $data += $line
            $count++
        }}
        Start-Sleep -Milliseconds 100
        if ($count -eq 0 -and (Measure-Command {{ $elapsed = 1 }}).TotalSeconds -gt 2) {{ break }}
    }}
    $port.Close()
    if ($data.Count -eq 0) {{
        "端口已打开但未收到数据，请确认设备已连接"
    }} else {{
        $data | ForEach-Object {{ $_ }}
    }}
}} catch {{
    "错误: $_"
}}
"""
    def _run():
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_code],
            capture_output=True, text=True, timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out = (r.stdout or "").strip()
        clean_lines = []
        for line in out.split("\n"):
            if line.strip() and not line.startswith("#<") and not line.startswith("<Objs"):
                clean_lines.append(line.rstrip('\r'))
        result = "\n".join(clean_lines)

        if "错误:" in result:
            return {"success": False, "data": result, "error": result}
        elif result and len(result) > 10:
            return {"success": True, "data": f"从 {port} (波特率{baud}) 读取到数据:\n{result}"}
        else:
            return {"success": False, "data": result, "error": "无有效数据"}

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run)