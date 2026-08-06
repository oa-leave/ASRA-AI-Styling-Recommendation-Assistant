from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.services.memory_service import get_user_memory
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from database.models import User


router = APIRouter(prefix="/memory", tags=["用户记忆"])


@router.get("/")
def get_memory(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    return get_user_memory(db, current_user.id)
