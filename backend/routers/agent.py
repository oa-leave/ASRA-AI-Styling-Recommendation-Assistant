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
        "city": payload.city,
        "occasion": payload.occasion,
        "style": payload.style,
        "user_id": current_user.id,
    })

    explanation = generate_llm_explanation(
        payload.city,
        result.get("weather"),
        payload.occasion,
        result.get("recommendation"),
        result.get("profile"),
    )

    return {
        "code": 200,
        "message": "Agent推荐成功",
        "user": current_user.username,
        "weather": result.get("weather"),
        "scene": result.get("scene"),
        "recommendation": result.get("recommendation"),
        "explanation": explanation,
        "history_id": result.get("history_id"),
    }
