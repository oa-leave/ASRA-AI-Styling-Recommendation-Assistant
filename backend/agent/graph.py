from typing import Any, Dict

from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from backend.agent.state import AgentState
from backend.agent.tools import analyze_scene, get_weather
from backend.services.memory_service import get_user_memory
from backend.services.recommend_service import generate_recommendation


def build_agent_graph(db: Session):
    def fetch_weather_node(state: AgentState) -> Dict[str, Any]:
        return {"weather": get_weather(state["city"])}

    def analyze_scene_node(state: AgentState) -> Dict[str, Any]:
        scene = analyze_scene(state["occasion"])
        if state.get("style"):
            scene["style"] = state["style"]
        return {"scene": scene}

    def load_memory_node(state: AgentState) -> Dict[str, Any]:
        return {"memory": get_user_memory(db, state["user_id"])}

    def recommend_node(state: AgentState) -> Dict[str, Any]:
        result = generate_recommendation(
            state["user_id"],
            db,
            weather=state.get("weather"),
            scene=state.get("scene"),
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
            "history_id": result["history_id"],
        }

    workflow = StateGraph(AgentState)
    workflow.add_node("fetch_weather", fetch_weather_node)
    workflow.add_node("analyze_scene", analyze_scene_node)
    workflow.add_node("load_memory", load_memory_node)
    workflow.add_node("recommend", recommend_node)

    workflow.add_edge(START, "fetch_weather")
    workflow.add_edge("fetch_weather", "analyze_scene")
    workflow.add_edge("analyze_scene", "load_memory")
    workflow.add_edge("load_memory", "recommend")
    workflow.add_edge("recommend", END)

    return workflow.compile()
