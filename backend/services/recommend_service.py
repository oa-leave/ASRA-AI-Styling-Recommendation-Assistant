from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.services.recommendation_engine import (
    _color_group_name,
    build_top_outfits,
    calculate_clothes_score,
    generate_summary,
)
from backend.services.recommendation_config import MEMORY_BONUS
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
            "style": item.get("style"),
            "color": item.get("color"),
            "reason": item.get("reason", []),
        }
        for slot, item in outfit.items()
    ]


def _collect_names(snapshot: Any) -> List[str]:
    names = []
    if isinstance(snapshot, dict):
        for value in snapshot.values():
            if isinstance(value, dict):
                if value.get("name"):
                    names.append(str(value["name"]))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and item.get("name"):
                        names.append(str(item["name"]))
            elif value:
                names.append(str(value))
    return names


def _apply_memory_adjustments(
    scored: List[Dict[str, Any]],
    memory: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not memory:
        return scored

    liked_names = set()
    disliked_names = set()
    feedback = memory.get("feedback_summary") or {}
    for item in feedback.get("recent", []):
        snapshot = item.get("outfit_snapshot")
        names = _collect_names(snapshot)
        if item.get("feedback_type") == "like":
            liked_names.update(names)
        elif item.get("feedback_type") == "dislike":
            disliked_names.update(names)

    preferences = memory.get("preference_signals") or {}
    favorite_styles = set(preferences.get("favorite_styles") or [])
    favorite_color_groups = {
        group
        for color in (preferences.get("favorite_colors") or [])
        if (group := _color_group_name(color))
    }

    for item in scored:
        name = item.get("name")
        if name in liked_names:
            item["score"] += MEMORY_BONUS["liked_item"]
        if name in disliked_names:
            item["score"] += MEMORY_BONUS["disliked_item"]
        if item.get("style") in favorite_styles:
            item["score"] += MEMORY_BONUS["favorite_style"]
        item_color_group = _color_group_name(item.get("color"))
        if item_color_group in favorite_color_groups:
            item["score"] += MEMORY_BONUS["favorite_color"]

    return scored


def generate_recommendation(
    user_id: int,
    db: Session,
    weather: Optional[Dict[str, Any]] = None,
    scene: Optional[Dict[str, Any]] = None,
    memory: Optional[Dict[str, Any]] = None,
    conversation_context: Optional[Dict[str, Any]] = None,
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
    if conversation_context:
        avoid_colors = set(profile_data.get("avoid_colors") or [])
        avoid_colors.update(conversation_context.get("avoid_colors") or [])
        profile_data["avoid_colors"] = list(avoid_colors)

    context_data = {}
    if scene and scene.get("style"):
        context_data["style"] = scene["style"]
    if weather and weather.get("season"):
        context_data["season"] = weather["season"]

    engine_profile_data = {**profile_data, **context_data}
    profile_obj = (
        SimpleNamespace(**engine_profile_data)
        if engine_profile_data
        else None
    )
    summary_profile_data = {**profile_data}
    if "season" in context_data:
        summary_profile_data["season"] = context_data["season"]
    summary_profile = (
        SimpleNamespace(**summary_profile_data)
        if summary_profile_data
        else None
    )
    scored, filtered_reasons = calculate_clothes_score(
        wardrobe,
        profile_obj,
        collect_filtered=True,
    )
    scored = _apply_memory_adjustments(scored, memory)
    outfit_results = build_top_outfits(scored, profile_obj, top_n=top_n)
    best = outfit_results[0] if outfit_results else {
        "outfit": {},
        "score": 0,
        "reason": [],
    }

    items = _build_items(best["outfit"])
    summary = generate_summary(best["outfit"], best["reason"], summary_profile)

    top_outfits = []
    for outfit_result in outfit_results:
        top_outfits.append({
            "outfit_score": outfit_result["score"],
            "items": _build_items(outfit_result["outfit"]),
            "summary": generate_summary(
                outfit_result["outfit"],
                outfit_result["reason"],
                summary_profile,
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
        "context_profile": engine_profile_data,
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
