from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.agent.explain import generate_llm_explanation
from backend.agent.graph import build_agent_graph
from backend.schemas.agent import AgentRecommendRequest
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

    explanation = generate_llm_explanation(
        result.get("city"),
        result.get("weather"),
        result.get("occasion"),
        result.get("recommendation"),
        result.get("profile"),
        result.get("memory"),
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
        "explanation": explanation,
        "history_id": result.get("history_id"),
    }
