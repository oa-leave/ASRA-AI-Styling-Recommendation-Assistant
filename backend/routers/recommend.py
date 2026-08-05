from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.services.recommendation_engine import (
    calculate_clothes_score,
    build_top_outfits,
    generate_summary,
)
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from backend.utils.events import record_event
from database.models import RecommendationHistory, User, UserProfile, Wardrobe


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
    outfit_results = build_top_outfits(recommendations, profile, top_n=3)
    best_outfit_result = outfit_results[0] if outfit_results else {
        "outfit": {},
        "score": 0,
        "reason": [],
    }

    record_event(
        db,
        current_user.id,
        "recommend_view",
        {"outfit_score": best_outfit_result["score"]},
    )

    items = [
        {
            "slot": slot,
            "name": item["name"],
            "score": item["score"],
            "reason": item.get("reason", []),
        }
        for slot, item in best_outfit_result["outfit"].items()
    ]

    reasons = best_outfit_result["reason"]
    summary = generate_summary(best_outfit_result["outfit"], reasons, profile)

    top_outfits = []
    for outfit_result in outfit_results:
        outfit_items = [
            {
                "slot": slot,
                "name": item["name"],
                "score": item["score"],
                "reason": item.get("reason", []),
            }
            for slot, item in outfit_result["outfit"].items()
        ]
        top_outfits.append({
            "outfit_score": outfit_result["score"],
            "items": outfit_items,
            "summary": generate_summary(
                outfit_result["outfit"],
                outfit_result["reason"],
                profile,
            ),
        })

    history = RecommendationHistory(
        user_id=current_user.id,
        request_context={
            "city": None,
            "occasion": None,
            "season": profile.season if profile else None,
            "style": profile.style if profile else None,
        },
        response_snapshot={
            "outfit_score": best_outfit_result["score"],
            "items": items,
            "summary": summary,
        },
    )
    db.add(history)
    db.commit()
    db.refresh(history)

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
        "recommendation": {
            "outfit_score": best_outfit_result["score"],
            "items": items,
            "summary": summary,
        },
        "recommendations": top_outfits,
        "outfit_score": best_outfit_result["score"],
        "outfit_reason": reasons,
        "filtered_reasons": filtered_reasons,
        "history_id": history.id,
    }
