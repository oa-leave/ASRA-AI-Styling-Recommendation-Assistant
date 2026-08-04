from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.utils.database import get_database
from backend.utils.events import record_event
from backend.utils.jwt import create_access_token
from backend.utils.security import verify_password
from database.models import User


router = APIRouter(prefix="/auth", tags=["登录"])


@router.post("/login")
def login(
    user: OAuth2PasswordRequestForm = Depends(),
    database: Session = Depends(get_database),
):
    database_user = (
        database.query(User).filter(User.username == user.username).first()
    )
    if not database_user or not verify_password(
        user.password, database_user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"user_id": database_user.id})
    record_event(database, database_user.id, "user_login")
    return {"access_token": access_token, "token_type": "bearer"}
