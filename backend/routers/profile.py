from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.schemas.profile import UserProfileCreate, UserProfileResponse
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from backend.utils.events import record_event
from database.models import User, UserProfile


router = APIRouter(prefix="/profile", tags=["用户画像"])


@router.post("/create", response_model=UserProfileResponse, status_code=201)
def create_profile(
    profile: UserProfileCreate,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    if (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    ):
        raise HTTPException(status_code=409, detail="用户画像已经存在")

    new_profile = UserProfile(
        user_id=current_user.id,
        style=profile.style,
        favorite_color=profile.favorite_color,
        body_type=profile.body_type,
        season=profile.season,
    )
    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)
    record_event(db, current_user.id, "profile_create")
    return new_profile


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="用户画像不存在")
    return profile


@router.get("/{user_id}", response_model=UserProfileResponse)
def get_profile(
    user_id: int,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看该用户画像")
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="用户画像不存在")
    return profile
