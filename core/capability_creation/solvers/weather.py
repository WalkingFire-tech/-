import re
import urllib.parse
from typing import Dict

from loguru import logger

_ZH_CITY_MAP = {
    "北京": "Beijing", "上海": "Shanghai", "广州": "Guangzhou",
    "深圳": "Shenzhen", "杭州": "Hangzhou", "成都": "Chengdu",
    "武汉": "Wuhan", "南京": "Nanjing", "重庆": "Chongqing",
    "天津": "Tianjin", "西安": "Xian", "苏州": "Suzhou",
    "长沙": "Changsha", "郑州": "Zhengzhou", "青岛": "Qingdao",
    "大连": "Dalian", "厦门": "Xiamen", "昆明": "Kunming",
    "哈尔滨": "Harbin", "沈阳": "Shenyang", "济南": "Jinan",
    "福州": "Fuzhou", "合肥": "Hefei", "南昌": "Nanchang",
    "贵阳": "Guiyang", "太原": "Taiyuan", "石家庄": "Shijiazhuang",
    "兰州": "Lanzhou", "乌鲁木齐": "Urumqi", "呼和浩特": "Hohhot",
    "南宁": "Nanning", "海口": "Haikou", "银川": "Yinchuan",
    "西宁": "Xining", "拉萨": "Lhasa", "长春": "Changchun",
}

_WEATHER_ZH = {
    "Sunny": "晴天", "Clear": "晴朗", "Partly cloudy": "多云",
    "Cloudy": "阴天", "Overcast": "阴", "Mist": "薄雾",
    "Fog": "雾", "Light rain": "小雨", "Moderate rain": "中雨",
    "Heavy rain": "大雨", "Patchy rain nearby": "零星小雨",
    "Light drizzle": "毛毛雨", "Thunderstorm": "雷暴",
    "Light snow": "小雪", "Moderate snow": "中雪",
    "Heavy snow": "大雪", "Blizzard": "暴风雪",
    "Freezing fog": "冻雾", "Light freezing rain": "冻雨",
}


async def solve_weather_query(query: str) -> Dict:
    import httpx

    location = None
    loc_match = re.search(r'(?:在|去|到|的|附近|最近)\s*([^\s?？，,！!的]+?)(?:的|天气|$)', query)
    if not loc_match:
        loc_match = re.search(r'^([\u4e00-\u9fa5]{2,4}(?:市|区|县|省)?)(?:今天|明天|后天|本周|这周)', query)
    if not loc_match:
        loc_match = re.search(r'^([\u4e00-\u9fa5]{2,4}(?:市|区|县|省)?)天气', query)
    if not loc_match:
        loc_match = re.search(r'([\u4e00-\u9fa5]{2,4}(?:市|区|县|省)?)天气', query)
    if loc_match:
        location = loc_match.group(1).strip()
    _time_words = {'今天', '明天', '后天', '大后天', '昨天', '前天', '本周', '这周', '上周', '下周'}
    if location in _time_words:
        location = None

    api_location = location
    if location:
        for zh, en in _ZH_CITY_MAP.items():
            if zh in location:
                api_location = en
                break

    try:
        url = "https://wttr.in/"
        if api_location:
            url += f"{urllib.parse.quote(api_location)}?format=j1&lang=zh"
        else:
            url += "?format=j1&lang=zh"

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"User-Agent": "curl/7.68.0"})
            resp.raise_for_status()
            data = resp.json()

        current = data.get("current_condition", [{}])[0]
        area = data.get("nearest_area", [{}])[0]
        api_city = area.get("areaName", [{}])[0].get("value", location or "当前位置")
        country = area.get("country", [{}])[0].get("value", "")

        if location and api_location and api_location != api_city:
            region = area.get("region", [{}])[0].get("value", "")
            if region:
                api_city = f"{api_city}({region})"

        display_city = location if location else api_city
        if country and country not in ("China", "中国"):
            display_city = f"{display_city}（{country}）"

        temp_c = current.get("temp_C", "?")
        feels_like = current.get("FeelsLikeC", "?")
        humidity = current.get("humidity", "?")
        desc_raw = current.get("lang_zh", [{}])[0].get("value", "") or current.get("weatherDesc", [{}])[0].get("value", "")
        desc = _WEATHER_ZH.get(desc_raw, desc_raw)
        wind_speed = current.get("windspeedKmph", "?")
        wind_dir = current.get("winddir16Point", "")
        visibility = current.get("visibility", "?")
        pressure = current.get("pressure", "?")

        result_text = f"**{display_city}当前天气**\n\n"
        result_text += f"- 天气状况：{desc}\n"
        result_text += f"- 气温：{temp_c}°C（体感温度 {feels_like}°C）\n"
        result_text += f"- 湿度：{humidity}%\n"
        result_text += f"- 风速：{wind_speed} km/h {wind_dir}\n"
        result_text += f"- 能见度：{visibility} km\n"
        result_text += f"- 气压：{pressure} hPa\n"

        weather_list = data.get("weather", [])
        if len(weather_list) > 1:
            tomorrow = weather_list[1]
            t_max = tomorrow.get("maxtempC", "?")
            t_min = tomorrow.get("mintempC", "?")
            t_desc_raw = ""
            try:
                t_desc_raw = tomorrow.get("hourly", [{}])[4].get("lang_zh", [{}])[0].get("value", "") or tomorrow.get("hourly", [{}])[4].get("weatherDesc", [{}])[0].get("value", "")
            except (IndexError, TypeError):
                pass
            t_desc = _WEATHER_ZH.get(t_desc_raw, t_desc_raw)
            result_text += f"\n**明天预报**：{t_desc}，{t_min}°C ~ {t_max}°C\n"

        return {"success": True, "data": result_text}

    except Exception as e:
        return {"success": False, "data": f"天气查询失败：{str(e)[:100]}。建议查看天气应用获取实时天气信息。"}