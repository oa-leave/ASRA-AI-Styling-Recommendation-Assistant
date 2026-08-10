from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.agent.explain import generate_llm_explanation
from backend.agent.graph import build_agent_graph
from backend.schemas.agent import AgentRecommendRequest
from backend.services.explanation_filter import filter_text
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from database.models import User


router = APIRouter(prefix="/agent", tags=["穿搭Agent"])


@router.post("/recommend")
def agent_recommend(
    payload: AgentRecommendRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    graph = build_agent_graph(db)
    result = graph.invoke({
        "query": payload.query,
        "city": payload.city,
        "occasion": payload.occasion,
        "style": payload.style,
        "user_id": current_user.id,
    })

    avoid_colors = (result.get("conversation_context") or {}).get("avoid_colors") or []
    knowledge_text = filter_text(result.get("knowledge_text"), avoid_colors)

    explanation = generate_llm_explanation(
        result.get("city"),
        result.get("weather"),
        result.get("occasion"),
        result.get("recommendation"),
        result.get("profile"),
        result.get("memory"),
        knowledge_text,
    )

    return {
        "code": 200,
        "message": "Agent推荐成功",
        "user": current_user.username,
        "weather": result.get("weather"),
        "scene": result.get("scene"),
        "tool_plan": result.get("tool_plan"),
        "recommendation": result.get("recommendation"),
        "memory": result.get("memory"),
        "knowledge_rules": result.get("knowledge_rules"),
        "knowledge_text": knowledge_text,
        "explanation": explanation,
        "history_id": result.get("history_id"),
    }
