from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.services.recommendation_engine import (
    build_best_outfit,
    calculate_clothes_score,
)
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from backend.utils.events import record_event
from database.models import User, UserProfile, Wardrobe


router = APIRouter(prefix="/recommend", tags=["穿搭推荐"])


@router.get("/")
def recommend(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    clothes = (
        db.query(Wardrobe)
        .filter(Wardrobe.user_id == current_user.id)
        .all()
    )
    recommendations, filtered_reasons = calculate_clothes_score(
        clothes,
        profile,
        collect_filtered=True,
    )
    outfit_result = build_best_outfit(recommendations, profile)

    record_event(
        db,
        current_user.id,
        "recommend_view",
        {"outfit_score": outfit_result["score"]},
    )

    return {
        "code": 200,
        "message": "推荐成功",
        "user": current_user.username,
        "profile": {
            "style": profile.style if profile else "未知",
            "season": profile.season if profile else "未知",
            "favorite_color": profile.favorite_color if profile else "未知",
        },
        "clothes_count": len(clothes),
        "recommendation": outfit_result["outfit"],
        "outfit_score": outfit_result["score"],
        "outfit_reason": outfit_result["reason"],
        "filtered_reasons": filtered_reasons,
    }
