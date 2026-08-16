"""Agent 工具注册表。"""
from typing import Any, Callable, Dict

from sqlalchemy.orm import Session

from backend.agent.tools import analyze_scene, get_weather
from backend.agent.scene_lexicon import resolve_scene
from backend.services.knowledge_service import (
    build_knowledge_text,
    retrieve_fashion_rules,
)
from backend.services.memory_service import get_user_memory
from backend.services.recommend_service import generate_recommendation


DEFAULT_TOOL_PLAN = ["weather", "scene", "memory", "knowledge", "recommend"]


def weather_tool(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """天气工具：根据城市获取天气和季节。"""
    return {
        "weather": get_weather(
            state["city"],
            forecast_day=state.get("forecast_day", 0),
        )
    }


def scene_tool(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """场景工具：根据场景分析推荐风格。"""
    scene = analyze_scene(state["occasion"])
    resolved = resolve_scene(
        state.get("query") or "",
        state.get("occasion"),
        state.get("style"),
    )
    scene["scene_type"] = state.get("scene_type") or resolved.get("scene_type")
    scene["formality"] = (
        state.get("formality")
        if state.get("formality") is not None
        else resolved.get("formality")
    )
    scene["activity_level"] = (
        state.get("activity_level")
        if state.get("activity_level") is not None
        else resolved.get("activity_level")
    )
    if state.get("style"):
        scene["style"] = state["style"]
        if state["style"] == "商务" and scene.get("occasion_tags") == ["日常"]:
            scene["occasion_tags"] = ["正式", "通勤"]
    return {"scene": scene}


def memory_tool(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """记忆工具：读取用户画像和反馈。"""
    memory = get_user_memory(db, state["user_id"])
    profile = memory.get("profile")
    if profile:
        avoid_colors = set(profile.get("avoid_colors") or [])
        profile["avoid_colors"] = sorted(avoid_colors)
        profile["favorite_colors"] = [
            color
            for color in (profile.get("favorite_colors") or [])
            if color not in avoid_colors
        ]
        if profile.get("favorite_color") in avoid_colors:
            profile["favorite_color"] = None
        preference_signals = memory.get("preference_signals") or {}
        preference_signals["favorite_colors"] = [
            color
            for color in (preference_signals.get("favorite_colors") or [])
            if color not in avoid_colors
        ]
    return {
        "memory": memory,
        "profile": profile,
    }


def knowledge_tool(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """穿搭知识工具：根据当前上下文检索穿搭规则。"""
    profile = state.get("profile") or {}
    scene = state.get("scene") or {}
    weather = state.get("weather") or {}

    rules = retrieve_fashion_rules(
        style=scene.get("style") or profile.get("style"),
        occasion=state.get("occasion"),
        season=weather.get("season"),
        colors=profile.get("favorite_colors") or [],
        tags=profile.get("style_tags") or [],
    )
    avoid_colors = set(profile.get("avoid_colors") or [])
    avoid_colors.update(
        (state.get("conversation_context") or {}).get("avoid_colors") or []
    )
    if avoid_colors:
        rules = [
            rule
            for rule in rules
            if not (avoid_colors & set(rule.get("tags", [])))
        ]
    return {
        "knowledge_rules": rules,
        "knowledge_text": build_knowledge_text(rules),
    }


def recommend_tool(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """推荐工具：调用统一推荐服务并保存历史。"""
    result = generate_recommendation(
        state["user_id"],
        db,
        weather=state.get("weather"),
        scene=state.get("scene"),
        memory=state.get("memory"),
        conversation_context=state.get("conversation_context"),
        knowledge_rules=state.get("knowledge_rules"),
        history_context={
            "source": "agent",
            "city": state.get("city"),
            "occasion": state.get("occasion"),
            "style": state.get("style"),
        },
    )
    scene = state.get("scene") or {}
    occasion = state.get("occasion")
    scene_tags = scene.get("occasion_tags") or []
    if scene_tags:
        occasion = scene_tags[0]

    return {
        "recommendation": result["recommendation"],
        "profile": result["profile"],
        "context_profile": result["context_profile"],
        "history_id": result["history_id"],
        "tool_plan": state.get("tool_plan"),
        "city": state.get("city"),
        "occasion": occasion,
        "forecast_day": state.get("forecast_day", 0),
    }


TOOL_REGISTRY: Dict[str, Callable[[Dict[str, Any], Session], Dict[str, Any]]] = {
    "weather": weather_tool,
    "scene": scene_tool,
    "memory": memory_tool,
    "knowledge": knowledge_tool,
    "recommend": recommend_tool,
}
