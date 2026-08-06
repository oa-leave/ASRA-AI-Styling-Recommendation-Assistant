from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.services.recommend_service import generate_recommendation
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from database.models import User


router = APIRouter(prefix="/recommend", tags=["穿搭推荐"])


@router.get("/")
def recommend(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    result = generate_recommendation(
        current_user.id,
        db,
        history_context={"source": "recommend"},
    )
    profile = result.get("profile") or {}

    return {
        "code": 200,
        "message": "推荐成功",
        "user": current_user.username,
        "profile": {
            "style": profile.get("style") or "未知",
            "season": profile.get("season") or "未知",
            "favorite_color": profile.get("favorite_color") or "未知",
        },
        "clothes_count": result["clothes_count"],
        "recommendation": result["recommendation"],
        "recommendations": result["recommendations"],
        "outfit_score": result["outfit_score"],
        "outfit_reason": result["outfit_reason"],
        "filtered_reasons": result["filtered_reasons"],
        "history_id": result["history_id"],
    }
