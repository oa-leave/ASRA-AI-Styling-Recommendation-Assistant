from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.schemas.feedback import FeedbackCreate, FeedbackResponse
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from backend.utils.events import record_event
from database.models import RecommendationFeedback, User


router = APIRouter(prefix="/feedback", tags=["推荐反馈"])


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
