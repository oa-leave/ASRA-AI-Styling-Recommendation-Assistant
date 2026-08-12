"""Agent 决策模块：决定这次请求需要调用哪些工具。"""
import json
import os
from typing import Any, Dict, List, Optional

import requests

from backend.agent.tools import CITY_WEATHER, SCENE_MAP
from backend.agent.scene_lexicon import resolve_scene
from backend.services.recommendation_config import STYLES


def _extract_city(query: str, fallback: Optional[str]) -> Optional[str]:
    """从自然语言里提取城市，例如“明天上海约会” -> 上海。"""
    for city in CITY_WEATHER:
        if city in query:
            return city
    return fallback


def _extract_occasion(query: str, fallback: Optional[str]) -> Optional[str]:
    """从自然语言里提取场景，例如“约会”“通勤”“运动”。"""
    for occasion in SCENE_MAP:
        if occasion in query:
            return occasion
    return fallback


def _extract_style(query: str, fallback: Optional[str]) -> Optional[str]:
    """从自然语言里提取风格偏好。"""
    if "正式" in query:
        return "商务"
    for style in STYLES:
        if style in query:
            return style
    return fallback


def deterministic_decision(
    query: Optional[str],
    city: Optional[str],
    occasion: Optional[str],
    style: Optional[str],
) -> Dict[str, Any]:
    """没有 LLM Key 时的规则解析，保证 Agent 始终可用。"""
    text = query or ""
    city = _extract_city(text, city) or "沈阳"
    raw_occasion = _extract_occasion(text, occasion)
    detected_style = _extract_style(text, style)
    resolved = resolve_scene(text, raw_occasion, detected_style)
    occasion = resolved["occasion"]
    style = resolved.get("style")

    return {
        "city": city,
        "occasion": occasion,
        "style": style,
        "scene_type": resolved.get("scene_type"),
        "formality": resolved.get("formality"),
        "activity_level": resolved.get("activity_level"),
        "tool_plan": ["weather", "scene", "memory", "knowledge", "recommend"],
        "source": "deterministic",
    }


def decide_agent_plan(
    query: Optional[str] = None,
    city: Optional[str] = None,
    occasion: Optional[str] = None,
    style: Optional[str] = None,
) -> Dict[str, Any]:
    """LLM 决策入口；没有 Key 或调用失败时回退到规则解析。"""
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return deterministic_decision(query, city, occasion, style)

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
                        "content": (
                            "你是ASRA穿搭Agent的决策器。"
                            "根据用户输入输出JSON，字段："
                            "city、occasion、style、tool_plan。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps({
                            "query": query,
                            "city": city,
                            "occasion": occasion,
                            "style": style,
                        }, ensure_ascii=False),
                    },
                ],
                "temperature": 0,
                "max_tokens": 200,
                "response_format": {"type": "json_object"},
            },
            timeout=10,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        parsed_occasion = data.get("occasion")
        parsed_style = data.get("style")
        known_occasions = set(SCENE_MAP) | {"正式", "商务"}
        if not (parsed_occasion or parsed_style):
            return deterministic_decision(query, city, occasion, style)
        if parsed_occasion not in known_occasions and parsed_style not in STYLES:
            return deterministic_decision(query, city, occasion, style)
        resolved = resolve_scene(
            query or "",
            parsed_occasion or occasion,
            parsed_style or style,
        )
        return {
            "city": data.get("city") or city or "沈阳",
            "occasion": resolved["occasion"],
            "style": resolved.get("style") or style,
            "scene_type": resolved.get("scene_type"),
            "formality": resolved.get("formality"),
            "activity_level": resolved.get("activity_level"),
            "tool_plan": data.get("tool_plan") or [
                "weather",
                "scene",
                "memory",
                "knowledge",
                "recommend",
            ],
            "source": "llm",
        }
    except Exception:
        return deterministic_decision(query, city, occasion, style)
