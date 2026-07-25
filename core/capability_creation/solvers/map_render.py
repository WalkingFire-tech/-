import os
import re
import tempfile
from typing import Dict

from loguru import logger


async def solve_map_render(query: str, serial_solve_fn=None) -> Dict:
    try:
        import folium
    except ImportError:
        from core.capability_creation.execution_engine import auto_install
        auto_install("folium")
        try:
            import folium
        except ImportError:
            return {"success": False, "data": "", "error": "folium安装失败"}

    lat, lon = 31.2304, 121.4737
    _coords_from_serial = False

    if any(kw in query for kw in ["串口", "serial", "COM", "com"]):
        if serial_solve_fn:
            serial_result = await serial_solve_fn(query)
            if serial_result.get("success"):
                serial_data = serial_result.get("data", "")
                gga_match = re.search(r'\$GNGGA,\d+\.\d+,(\d{2})(\d{2}\.\d+),[NS],(\d{3})(\d{2}\.\d+),[EW]', serial_data)
                if gga_match:
                    lat = float(gga_match.group(1)) + float(gga_match.group(2)) / 60
                    lon = float(gga_match.group(3)) + float(gga_match.group(4)) / 60
                    _coords_from_serial = True
                    logger.info(f"🗺️ 从串口数据解析GPS: {lat:.6f}°N, {lon:.6f}°E")

    lat_patterns = [
        r'[纬纬度:：]*\s*(\d+\.?\d*)\s*[°度]\s*[NS北南]',
        r'[纬纬度:：]*\s*(\d+\.?\d*)\s*[NS北南]',
    ]
    lon_patterns = [
        r'[经经度:：]*\s*(\d+\.?\d*)\s*[°度]\s*[EW东西]',
        r'[经经度:：]*\s*(\d+\.?\d*)\s*[EW东西]',
    ]
    for pat in lat_patterns:
        lat_match = re.search(pat, query)
        if lat_match:
            lat = float(lat_match.group(1))
            _coords_from_serial = False
            break
    for pat in lon_patterns:
        lon_match = re.search(pat, query)
        if lon_match:
            lon = float(lon_match.group(1))
            _coords_from_serial = False
            break

    m = folium.Map(
        location=[lat, lon], zoom_start=13,
        tiles="https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
        attr="高德地图",
    )
    folium.Marker([lat, lon], popup=f"标记位置 ({lat:.4f}°N, {lon:.4f}°E)").add_to(m)
    filepath = os.path.join(tempfile.gettempdir(), "gps_map.html")
    m.save(filepath)

    try:
        import webbrowser
        webbrowser.open(filepath)
    except Exception as e:
        logger.warning(f"操作降级跳过: {e}")

    return {
        "success": True,
        "data": f"地图已生成: {filepath}\n坐标: {lat:.4f}°N, {lon:.4f}°E\n已在浏览器中打开",
    }