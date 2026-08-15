from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.agent.scene_lexicon import resolve_scene
from backend.agent.tools import analyze_scene, get_weather
from backend.services.knowledge_service import retrieve_fashion_rules
from backend.services.memory_service import get_user_memory
from backend.services.recommend_service import generate_recommendation
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from database.models import ConversationSession, User, UserProfile


router = APIRouter(prefix="/recommend", tags=["穿搭推荐"])


def _latest_conversation_context(db: Session, user_id: int) -> dict:
    session = (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == user_id)
        .order_by(ConversationSession.updated_at.desc())
        .first()
    )
    return session.context if session else {}


@router.get("/")
def recommend(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    context = _latest_conversation_context(db, current_user.id) or {}
    city = context.get("city") or "沈阳"
    occasion = context.get("occasion") or "日常"
    style = context.get("style")
    weather = get_weather(city)
    scene = analyze_scene(occasion)
    resolved = resolve_scene("", occasion, style)
    scene.update({
        "scene_type": resolved.get("scene_type"),
        "formality": resolved.get("formality"),
        "activity_level": resolved.get("activity_level"),
        "style": resolved.get("style") or style,
    })
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    favorite_colors = profile.favorite_colors or [] if profile else []
    style_tags = profile.style_tags or [] if profile else []
    knowledge_rules = retrieve_fashion_rules(
        style=scene.get("style") or style,
        occasion=occasion,
        season=weather.get("season"),
        colors=favorite_colors,
        tags=style_tags,
    )
    conversation_context = {
        key: value
        for key, value in context.items()
        if key not in {"last_recommendation", "last_explanation"}
    }
    result = generate_recommendation(
        current_user.id,
        db,
        weather=weather,
        scene=scene,
        memory=get_user_memory(db, current_user.id),
        conversation_context=conversation_context,
        knowledge_rules=knowledge_rules,
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
