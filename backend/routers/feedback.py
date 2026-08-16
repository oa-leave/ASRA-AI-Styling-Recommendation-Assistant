import re
from typing import Any, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.schemas.feedback import FeedbackCreate, FeedbackResponse
from backend.services.recommendation_config import COLOR_GROUPS, STYLES
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from backend.utils.events import record_event
from database.models import RecommendationFeedback, User, UserProfile


router = APIRouter(prefix="/feedback", tags=["推荐反馈"])

DISLIKE_COLOR_MARKERS = (
    "不喜欢",
    "不要",
    "没相中",
    "讨厌",
    "别",
    "避免",
    "不考虑",
    "不用",
    "不接受",
    "不想",
)


def _collect_text_values(value: Any) -> List[str]:
    texts = []
    if isinstance(value, str):
        texts.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            texts.extend(_collect_text_values(item))
    elif isinstance(value, list):
        for item in value:
            texts.extend(_collect_text_values(item))
    return texts


def _update_profile_from_feedback(
    db: Session,
    user_id: int,
    payload: FeedbackCreate,
) -> None:
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )
    if profile is None:
        return

    texts = _collect_text_values(payload.reason)
    if payload.feedback_type == "dislike":
        avoid_colors = set(profile.avoid_colors or [])
        for text in texts:
            for color in COLOR_GROUPS:
                if re.search(
                    rf"(?:{'|'.join(DISLIKE_COLOR_MARKERS)}).{{0,8}}{re.escape(color)}",
                    text,
                ):
                    avoid_colors.add(color)
        profile.favorite_colors = [
            color
            for color in (profile.favorite_colors or [])
            if color not in avoid_colors
        ]
        profile.avoid_colors = list(avoid_colors)
    elif payload.feedback_type == "like":
        style_tags = set(profile.style_tags or [])
        for text in texts:
            for style in STYLES:
                if style in text:
                    style_tags.add(style)
        profile.style_tags = list(style_tags)


@router.post("/", response_model=FeedbackResponse, status_code=201)
def create_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    feedback = RecommendationFeedback(
        user_id=current_user.id,
        feedback_type=payload.feedback_type,
        outfit_score=payload.outfit_score,
        outfit_snapshot=payload.outfit_snapshot,
        reason=payload.reason,
    )
    db.add(feedback)
    _update_profile_from_feedback(db, current_user.id, payload)
    db.commit()
    db.refresh(feedback)
    record_event(
        db,
        current_user.id,
        f"feedback_{payload.feedback_type}",
        {"feedback_id": feedback.id, "outfit_score": payload.outfit_score},
    )
    return feedback


@router.get("/", response_model=List[FeedbackResponse])
def list_feedback(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(RecommendationFeedback)
        .filter(RecommendationFeedback.user_id == current_user.id)
        .order_by(RecommendationFeedback.id.desc())
        .all()
    )


@router.delete("/")
def clear_feedback(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    deleted = (
        db.query(RecommendationFeedback)
        .filter(RecommendationFeedback.user_id == current_user.id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {
        "message": "反馈已清空",
        "deleted_count": deleted,
    }
