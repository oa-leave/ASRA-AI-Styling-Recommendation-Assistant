import os
from datetime import datetime
from typing import Any, Dict, Optional

import requests


CITY_WEATHER = {
    "沈阳": {"temperature": 25, "weather": "晴", "season": "夏季"},
    "上海": {"temperature": 28, "weather": "多云", "season": "夏季"},
    "北京": {"temperature": 26, "weather": "晴", "season": "夏季"},
    "广州": {"temperature": 31, "weather": "阵雨", "season": "夏季"},
    "哈尔滨": {"temperature": 22, "weather": "多云", "season": "夏季"},
}

SCENE_MAP = {
    "日常": {"style": "休闲", "occasion_tags": ["日常"]},
    "通勤": {"style": "商务", "occasion_tags": ["通勤"]},
    "客户": {"style": "商务", "occasion_tags": ["客户", "通勤"]},
    "面试": {"style": "商务", "occasion_tags": ["面试", "通勤"]},
    "会议": {"style": "商务", "occasion_tags": ["会议", "通勤"]},
    "商务": {"style": "商务", "occasion_tags": ["商务", "通勤"]},
    "出差": {"style": "商务", "occasion_tags": ["出差", "旅行"]},
    "约会": {"style": "休闲", "occasion_tags": ["约会"]},
    "婚礼": {"style": "商务", "occasion_tags": ["婚礼", "宴会"]},
    "宴会": {"style": "商务", "occasion_tags": ["宴会"]},
    "酒会": {"style": "商务", "occasion_tags": ["宴会"]},
    "运动": {"style": "运动", "occasion_tags": ["运动"]},
    "健身": {"style": "运动", "occasion_tags": ["运动"]},
    "跑步": {"style": "运动", "occasion_tags": ["运动"]},
    "旅行": {"style": "休闲", "occasion_tags": ["旅行"]},
    "户外": {"style": "运动", "occasion_tags": ["户外", "旅行"]},
    "爬山": {"style": "运动", "occasion_tags": ["户外", "运动"]},
    "露营": {"style": "休闲", "occasion_tags": ["户外", "旅行"]},
    "校园": {"style": "学院", "occasion_tags": ["校园"]},
    "上学": {"style": "学院", "occasion_tags": ["校园"]},
    "居家": {"style": "休闲", "occasion_tags": ["居家"]},
    "海边": {"style": "休闲", "occasion_tags": ["旅行", "海边"]},
    "拍照": {"style": "休闲", "occasion_tags": ["拍照"]},
    "直播": {"style": "休闲", "occasion_tags": ["直播"]},
}

WEATHER_CODE_MAP = {
    0: "晴",
    1: "晴间多云",
    2: "多云",
    3: "阴",
    45: "雾",
    48: "雾凇",
    51: "毛毛雨",
    53: "毛毛雨",
    55: "毛毛雨",
    56: "冻毛毛雨",
    57: "冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "阵雨",
    81: "阵雨",
    82: "强阵雨",
    85: "阵雪",
    86: "强阵雪",
    95: "雷暴",
    96: "雷暴伴冰雹",
    99: "雷暴伴冰雹",
}


def _current_season() -> str:
    month = datetime.now().month
    if month in (3, 4, 5):
        return "春季"
    if month in (6, 7, 8):
        return "夏季"
    if month in (9, 10, 11):
        return "秋季"
    return "冬季"


def _weather_description(code: int) -> str:
    return WEATHER_CODE_MAP.get(code, "未知")


def get_fallback_weather(city: str) -> Dict[str, Any]:
    fallback = CITY_WEATHER.get(
        city,
        {"temperature": 25, "weather": "未知", "season": "夏季"},
    )
    return {
        "city": city,
        "temperature": fallback["temperature"],
        "weather": fallback["weather"],
        "season": fallback["season"],
        "source": "fallback",
    }


def get_weather(city: str, use_api: Optional[bool] = None) -> Dict[str, Any]:
    if use_api is None:
        use_api = os.getenv("USE_WEATHER_API", "true").lower() == "true"

    if not use_api:
        return get_fallback_weather(city)

    try:
        geo_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "zh", "format": "json"},
            timeout=5,
        )
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        results = geo_data.get("results") or []
        if not results:
            return get_fallback_weather(city)

        latitude = results[0]["latitude"]
        longitude = results[0]["longitude"]

        forecast_response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "timezone": "Asia/Shanghai",
            },
            timeout=5,
        )
        forecast_response.raise_for_status()
        forecast = forecast_response.json()
        current = forecast.get("current") or forecast.get("current_weather") or {}

        temperature = current.get("temperature_2m")
        if temperature is None:
            temperature = current.get("temperature")

        weather_code = current.get("weather_code")
        if weather_code is None:
            weather_code = current.get("weathercode")

        return {
            "city": city,
            "temperature": round(float(temperature)) if temperature is not None else 25,
            "weather": _weather_description(int(weather_code))
            if weather_code is not None
            else "未知",
            "season": _current_season(),
            "source": "api",
        }
    except Exception:
        return get_fallback_weather(city)


def analyze_scene(occasion: str) -> Dict[str, Any]:
    scene = SCENE_MAP.get(
        occasion,
        {"style": "休闲", "occasion_tags": ["日常"]},
    )
    return dict(scene)


def profile_to_dict(profile) -> Optional[Dict[str, Any]]:
    if profile is None:
        return None
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "style": profile.style,
        "favorite_color": profile.favorite_color,
        "favorite_colors": profile.favorite_colors or [],
        "style_tags": profile.style_tags or [],
        "fit_tags": profile.fit_tags or [],
        "avoid_colors": profile.avoid_colors or [],
        "occasion_preferences": profile.occasion_preferences or [],
        "body_type": profile.body_type,
        "season": profile.season,
    }


def wardrobe_to_dict(item) -> Dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "category": item.category,
        "color": item.color,
        "season": item.season,
        "style": item.style,
        "color_tags": item.color_tags or [],
        "style_tags": item.style_tags or [],
        "fit_tags": item.fit_tags or [],
        "occasion_tags": item.occasion_tags or [],
        "user_id": item.user_id,
    }
