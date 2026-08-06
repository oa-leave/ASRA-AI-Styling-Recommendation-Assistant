from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database.models import RecommendationFeedback, RecommendationHistory, UserProfile


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


def get_user_memory(
    db: Session,
    user_id: int,
    history_limit: int = 10,
    feedback_limit: int = 20,
) -> Dict[str, Any]:
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )

    recent_history = (
        db.query(RecommendationHistory)
        .filter(RecommendationHistory.user_id == user_id)
        .order_by(RecommendationHistory.id.desc())
        .limit(history_limit)
        .all()
    )

    feedback_rows = (
        db.query(RecommendationFeedback)
        .filter(RecommendationFeedback.user_id == user_id)
        .order_by(RecommendationFeedback.id.desc())
        .limit(feedback_limit)
        .all()
    )

    feedback_summary = {
        "like_count": 0,
        "dislike_count": 0,
        "recent": [],
    }
    for feedback in feedback_rows:
        if feedback.feedback_type == "like":
            feedback_summary["like_count"] += 1
        else:
            feedback_summary["dislike_count"] += 1
        feedback_summary["recent"].append({
            "feedback_type": feedback.feedback_type,
            "outfit_score": feedback.outfit_score,
            "outfit_snapshot": feedback.outfit_snapshot,
            "reason": feedback.reason,
        })

    style_counter = {}
    color_counter = {}
    for history in recent_history:
        response = history.response_snapshot or {}
        items = response.get("items") or []
        for item in items:
            style = item.get("style")
            color = item.get("color")
            if style:
                style_counter[style] = style_counter.get(style, 0) + 1
            if color:
                color_counter[color] = color_counter.get(color, 0) + 1

    favorite_styles = sorted(
        style_counter,
        key=style_counter.get,
        reverse=True,
    )[:3]
    favorite_colors = sorted(
        color_counter,
        key=color_counter.get,
        reverse=True,
    )[:3]

    return {
        "profile": _profile_to_dict(profile),
        "recent_history": [
            {
                "id": history.id,
                "request_context": history.request_context,
                "response_snapshot": history.response_snapshot,
                "created_at": str(history.created_at),
            }
            for history in recent_history
        ],
        "feedback_summary": feedback_summary,
        "preference_signals": {
            "favorite_styles": favorite_styles,
            "favorite_colors": favorite_colors,
        },
    }


def build_memory_text(memory: Dict[str, Any]) -> str:
    parts = []

    profile = memory.get("profile")
    if profile:
        parts.append(
            f"用户偏好：{profile.get('style') or '未知'}风格，"
            f"喜欢颜色：{profile.get('favorite_color') or '未知'}"
        )

    recent_history = memory.get("recent_history") or []
    if recent_history:
        parts.append(f"最近有{len(recent_history)}次推荐记录")

    feedback = memory.get("feedback_summary") or {}
    like_count = feedback.get("like_count", 0)
    dislike_count = feedback.get("dislike_count", 0)
    if like_count or dislike_count:
        parts.append(f"用户点赞{like_count}次，点踩{dislike_count}次")

    return "；".join(parts) if parts else "暂无历史记忆"
