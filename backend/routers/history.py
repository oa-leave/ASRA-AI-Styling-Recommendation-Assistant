from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.schemas.history import HistoryResponse
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from database.models import RecommendationHistory, User


router = APIRouter(prefix="/history", tags=["推荐历史"])


@router.get("/", response_model=List[HistoryResponse])
def list_history(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(RecommendationHistory)
        .filter(RecommendationHistory.user_id == current_user.id)
        .order_by(RecommendationHistory.id.desc())
        .all()
    )
