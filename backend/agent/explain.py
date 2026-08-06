import os
from typing import Any, Dict, Optional

import requests


def build_deterministic_explanation(
    city: str,
    weather: Optional[Dict[str, Any]],
    occasion: str,
    recommendation: Optional[Dict[str, Any]],
) -> str:
    weather_text = "天气未知"
    if weather:
        weather_text = f"{weather.get('temperature')}℃{weather.get('weather')}"

    items = recommendation.get("items", []) if recommendation else []
    names = "、".join(item["name"] for item in items) or "暂无可推荐衣物"
    summary = "、".join(recommendation.get("summary", [])) if recommendation else ""
    reason = f"，理由：{summary}" if summary else ""
    return f"今天{city}{weather_text}，{occasion}场景，推荐：{names}{reason}。"


def generate_llm_explanation(
    city: str,
    weather: Optional[Dict[str, Any]],
    occasion: str,
    recommendation: Optional[Dict[str, Any]],
    profile: Optional[Dict[str, Any]] = None,
) -> str:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return build_deterministic_explanation(city, weather, occasion, recommendation)

    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是ASRA穿搭助手，用简洁中文解释推荐原因。",
                    },
                    {
                        "role": "user",
                        "content": (
                            f"城市:{city}，天气:{weather}，场景:{occasion}，"
                            f"推荐:{recommendation}，用户画像:{profile}"
                        ),
                    },
                ],
                "temperature": 0.3,
                "max_tokens": 300,
            },
            timeout=10,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        return content
    except Exception:
        return build_deterministic_explanation(city, weather, occasion, recommendation)
