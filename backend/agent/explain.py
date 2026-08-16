import os
import re
from typing import Any, Dict, Optional

import requests

from backend.services.memory_service import build_memory_text


def _item_reason(item: Dict[str, Any], scene_label: str) -> Optional[str]:
    name = str(item.get("name") or "")
    slot = str(item.get("slot") or "")
    if any(keyword in name for keyword in ("衬衣", "衬衫")):
        return f"{name}比较得体"
    if "西装" in name or "西服" in name:
        return f"{name}提升正式感"
    if "T恤" in name or "短袖" in name:
        return f"{name}保持休闲感"
    if "运动鞋" in name or "小白鞋" in name:
        return f"{name}舒适好走"
    if "裤" in name:
        return f"{name}搭配协调"
    if slot:
        return f"{name}符合{scene_label}场景"
    return None


def _question_answer(
    query: Optional[str],
    scene: Optional[Dict[str, Any]],
    scene_label: str,
    recommendation: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    if not query:
        return None
    match = re.search(r"(?:可以|能)穿(.{1,8}?)(?:吗|么|行不行|可以吗)", query)
    if not match:
        return None

    item_text = match.group(1).strip("的 ")
    formality = int((scene or {}).get("formality") or 0)
    scene_type = (scene or {}).get("scene_type") or scene_label or ""
    casual_keywords = ("T恤", "短袖", "卫衣", "牛仔裤", "运动鞋", "帆布鞋")
    is_casual_item = any(keyword in item_text for keyword in casual_keywords)
    formal_markers = ("面试", "客户", "会议", "正式", "商务", "签约", "汇报")

    answer = None
    if is_casual_item and (
        formality >= 3
        or any(marker in scene_type for marker in formal_markers)
    ):
        answer = (
            f"不太建议{scene_label}穿{item_text}，"
            "因为容易显得过于休闲。"
        )
    elif is_casual_item:
        answer = f"可以穿{item_text}，这个场景不会太正式。"
    elif formality >= 3 or any(marker in scene_type for marker in formal_markers):
        answer = f"可以穿{item_text}，符合{scene_label}的正式度要求。"
    else:
        answer = f"可以穿{item_text}。"

    if "不太建议" not in answer:
        item_names = [
            str(item.get("name") or "")
            for item in (recommendation or {}).get("items", [])
        ]
        if not any(item_text in name for name in item_names):
            answer += f"当前衣柜没有{item_text}，先用推荐方案替代。"
    return answer


def build_deterministic_explanation(
    city: str,
    weather: Optional[Dict[str, Any]],
    occasion: str,
    recommendation: Optional[Dict[str, Any]],
    memory: Optional[Dict[str, Any]] = None,
    knowledge_text: Optional[str] = None,
    forecast_day: int = 0,
    scene: Optional[Dict[str, Any]] = None,
    day_label: Optional[str] = None,
    query: Optional[str] = None,
    explicit_style: bool = False,
) -> str:
    weather_text = "天气未知"
    if weather:
        weather_text = f"{weather.get('temperature')}℃{weather.get('weather')}"
    day_label = day_label or ("后天" if forecast_day >= 2 else ("明天" if forecast_day == 1 else "今天"))
    scene_label = occasion
    if scene and scene.get("scene_type"):
        scene_label = {
            "普通通勤": "通勤",
            "办公室": "通勤",
        }.get(scene["scene_type"], scene["scene_type"])

    items = recommendation.get("items", []) if recommendation else []
    names = "、".join(item["name"] for item in items) or "暂无可推荐衣物"
    summary = "、".join(recommendation.get("summary", [])) if recommendation else ""
    reason_parts = []
    for item in items:
        item_reason = _item_reason(item, scene_label)
        if item_reason:
            reason_parts.append(item_reason)
    if summary:
        reason_parts.append(summary)
    if weather:
        temperature = weather.get("temperature")
        weather_description = weather.get("weather")
        if temperature is not None:
            reason_parts.append(
                f"适合{temperature}℃{weather_description or ''}天气"
            )
    reason_parts = list(dict.fromkeys(reason_parts))
    reason = f"，理由：{'；'.join(reason_parts)}" if reason_parts else ""
    memory_text = (
        build_memory_text(
            memory,
            active_style=(scene or {}).get("style"),
            explicit_style=explicit_style,
        )
        if memory
        else ""
    )
    memory_part = f" 记忆：{memory_text}" if memory_text else ""
    knowledge_part = f" 穿搭知识：{knowledge_text}" if knowledge_text else ""
    scene_feedback = (recommendation or {}).get("scene_feedback") or {}
    warning = scene_feedback.get("warning")
    warning_part = f" 提示：{warning}" if warning else ""
    text = (
        f"{day_label}{city}{weather_text}，{scene_label}场景，推荐：{names}{reason}。"
        f"{memory_part}{knowledge_part}{warning_part}"
    ).strip()
    answer = _question_answer(query, scene, scene_label, recommendation)
    if answer:
        return f"{answer} {text}".strip()
    return text


def generate_llm_explanation(
    city: str,
    weather: Optional[Dict[str, Any]],
    occasion: str,
    recommendation: Optional[Dict[str, Any]],
    profile: Optional[Dict[str, Any]] = None,
    memory: Optional[Dict[str, Any]] = None,
    knowledge_text: Optional[str] = None,
    forecast_day: int = 0,
    scene: Optional[Dict[str, Any]] = None,
    day_label: Optional[str] = None,
    query: Optional[str] = None,
    explicit_style: bool = False,
) -> str:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        return build_deterministic_explanation(
            city,
            weather,
            occasion,
            recommendation,
            memory,
            knowledge_text,
            forecast_day,
            scene,
            day_label,
            query,
            explicit_style,
        )

    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")

    try:
        memory_text = (
            build_memory_text(
                memory,
                active_style=(scene or {}).get("style"),
                explicit_style=explicit_style,
            )
            if memory
            else ""
        )
        knowledge = knowledge_text or ""
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
                            "你是ASRA穿搭助手，用简洁中文解释推荐原因。"
                            "如果用户问'可以穿某件衣服吗'，先直接回答是否建议，再解释推荐。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"城市:{city}，天气:{weather}，场景:{occasion}，"
                            f"日期:{day_label or forecast_day}，"
                            f"推荐:{recommendation}，用户画像:{profile}，"
                            f"记忆:{memory_text}，穿搭知识:{knowledge}，"
                            f"用户问题:{query}"
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
        return build_deterministic_explanation(
            city,
            weather,
            occasion,
            recommendation,
            memory,
            knowledge_text,
            forecast_day,
            scene,
            day_label,
            query,
            explicit_style,
        )
