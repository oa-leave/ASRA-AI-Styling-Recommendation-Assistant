"""工具注册表：Agent 根据 tool_plan 按顺序动态调用工具。"""
from typing import Any, Callable, Dict

from sqlalchemy.orm import Session

from backend.agent.tools import analyze_scene, get_weather
from backend.services.memory_service import get_user_memory
from backend.services.recommend_service import generate_recommendation


DEFAULT_TOOL_PLAN = ["weather", "scene", "memory", "recommend"]


def weather_tool(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """天气工具：根据城市获取天气和季节。"""
    return {"weather": get_weather(state["city"])}


def scene_tool(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """场景工具：根据场景分析推荐风格。"""
    scene = analyze_scene(state["occasion"])
    if state.get("style"):
        scene["style"] = state["style"]
    return {"scene": scene}


def memory_tool(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """记忆工具：读取用户画像、历史和反馈。"""
    return {"memory": get_user_memory(db, state["user_id"])}


def recommend_tool(state: Dict[str, Any], db: Session) -> Dict[str, Any]:
    """推荐工具：调用统一推荐服务并保存历史。"""
    result = generate_recommendation(
        state["user_id"],
        db,
        weather=state.get("weather"),
        scene=state.get("scene"),
        memory=state.get("memory"),
        history_context={
            "source": "agent",
            "city": state.get("city"),
            "occasion": state.get("occasion"),
            "style": state.get("style"),
        },
    )
    return {
        "recommendation": result["recommendation"],
        "profile": result["profile"],
        "context_profile": result["context_profile"],
        "history_id": result["history_id"],
        "tool_plan": state.get("tool_plan"),
        "city": state.get("city"),
        "occasion": state.get("occasion"),
    }


TOOL_REGISTRY: Dict[str, Callable[[Dict[str, Any], Session], Dict[str, Any]]] = {
    "weather": weather_tool,
    "scene": scene_tool,
    "memory": memory_tool,
    "recommend": recommend_tool,
}
