from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.services.evaluation_service import compute_metrics
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from database.models import User


router = APIRouter(prefix="/evaluation", tags=["评估"])


@router.get("/metrics")
def evaluation_metrics(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    return compute_metrics(db, current_user.id)
