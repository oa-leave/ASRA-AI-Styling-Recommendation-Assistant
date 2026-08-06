from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.services.recommendation_engine import (
    build_top_outfits,
    calculate_clothes_score,
    generate_summary,
)
from database.models import RecommendationHistory, User, UserProfile, Wardrobe


def _profile_to_dict(profile) -> Optional[Dict[str, Any]]:
    if profile is None:
        return None
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "style": profile.style,
        "favorite_color": profile.favorite_color,
        "favorite_colors": profile.favorite_colors or [],
        "style_tags": profile.style_tags or [],
        "fit_tags": profile.fit_tags or [],
        "avoid_colors": profile.avoid_colors or [],
        "occasion_preferences": profile.occasion_preferences or [],
        "body_type": profile.body_type,
        "season": profile.season,
    }


def _build_items(outfit: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "slot": slot,
            "name": item["name"],
            "score": item["score"],
            "reason": item.get("reason", []),
        }
        for slot, item in outfit.items()
    ]


def generate_recommendation(
    user_id: int,
    db: Session,
    weather: Optional[Dict[str, Any]] = None,
    scene: Optional[Dict[str, Any]] = None,
    top_n: int = 3,
    history_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )
    user = db.query(User).filter(User.id == user_id).first()
    wardrobe = (
        db.query(Wardrobe)
        .filter(Wardrobe.user_id == user_id)
        .all()
    )

    profile_data = _profile_to_dict(profile) or {}
    if scene and scene.get("style"):
        profile_data = {**profile_data, "style": scene["style"]}
    if weather and weather.get("season"):
        profile_data = {**profile_data, "season": weather["season"]}

    profile_obj = SimpleNamespace(**profile_data) if profile_data else None
    scored, filtered_reasons = calculate_clothes_score(
        wardrobe,
        profile_obj,
        collect_filtered=True,
    )
    outfit_results = build_top_outfits(scored, profile_obj, top_n=top_n)
    best = outfit_results[0] if outfit_results else {
        "outfit": {},
        "score": 0,
        "reason": [],
    }

    items = _build_items(best["outfit"])
    summary = generate_summary(best["outfit"], best["reason"], profile_obj)

    top_outfits = []
    for outfit_result in outfit_results:
        top_outfits.append({
            "outfit_score": outfit_result["score"],
            "items": _build_items(outfit_result["outfit"]),
            "summary": generate_summary(
                outfit_result["outfit"],
                outfit_result["reason"],
                profile_obj,
            ),
        })

    context = dict(history_context or {"source": "recommend"})
    if weather is not None:
        context["weather"] = weather
    if scene is not None:
        context["scene"] = scene

    history = RecommendationHistory(
        user_id=user_id,
        request_context=context,
        response_snapshot={
            "outfit_score": best["score"],
            "items": items,
            "summary": summary,
            "weather": weather,
            "scene": scene,
        },
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return {
        "user_id": user_id,
        "username": user.username if user else None,
        "profile": profile_data,
        "clothes_count": len(wardrobe),
        "recommendation": {
            "outfit_score": best["score"],
            "items": items,
            "summary": summary,
        },
        "recommendations": top_outfits,
        "outfit_score": best["score"],
        "outfit_reason": best["reason"],
        "filtered_reasons": filtered_reasons,
        "history_id": history.id,
    }
