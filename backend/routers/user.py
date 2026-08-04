from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.schemas.user import UserCreate
from backend.utils.database import get_database
from backend.utils.events import record_event
from backend.utils.security import hash_password
from database.models import User


router = APIRouter(prefix="/user", tags=["用户管理"])


@router.post("/register", status_code=201)
def register(
    user: UserCreate,
    database: Session = Depends(get_database),
):
    if database.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=409, detail="用户名已经存在")
    if database.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=409, detail="邮箱已经存在")

    new_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hash_password(user.password),
    )
    database.add(new_user)
    database.commit()
    database.refresh(new_user)
    record_event(database, new_user.id, "user_register")
    return {
        "message": "注册成功",
        "username": new_user.username,
        "email": new_user.email,
    }
