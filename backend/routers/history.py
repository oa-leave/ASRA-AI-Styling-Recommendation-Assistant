from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.schemas.history import HistoryResponse
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from database.models import RecommendationHistory, User


router = APIRouter(prefix="/history", tags=["推荐历史"])


@router.get("/", response_model=List[HistoryResponse])
def list_history(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(RecommendationHistory)
        .filter(RecommendationHistory.user_id == current_user.id)
        .order_by(RecommendationHistory.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
