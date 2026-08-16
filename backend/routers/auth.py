from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.schemas.auth import LogoutRequest, RefreshRequest, TokenResponse
from backend.utils.auth_tokens import (
    clear_login_attempts,
    consume_refresh_token,
    create_refresh_token,
    is_login_locked,
    record_login_attempt,
    revoke_refresh_token,
    utcnow,
)
from backend.utils.database import get_database
from backend.utils.events import record_event
from backend.utils.jwt import create_access_token
from backend.utils.security import verify_password
from database.models import User


router = APIRouter(prefix="/auth", tags=["登录"])


@router.post("/login", response_model=TokenResponse)
def login(
    user: OAuth2PasswordRequestForm = Depends(),
    database: Session = Depends(get_database),
):
    if is_login_locked(database, user.username):
        raise HTTPException(
            status_code=429,
            detail="登录失败次数过多，请稍后再试",
        )

    database_user = (
        database.query(User).filter(User.username == user.username).first()
    )
    if not database_user or not verify_password(
        user.password, database_user.hashed_password
    ):
        record_login_attempt(database, user.username, False)
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clear_login_attempts(database, user.username)
    access_token = create_access_token({"user_id": database_user.id})
    refresh_token = create_refresh_token(database, database_user.id)
    record_event(database, database_user.id, "user_login")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    payload: RefreshRequest,
    database: Session = Depends(get_database),
):
    token_row = consume_refresh_token(database, payload.refresh_token)
    if token_row is None:
        raise HTTPException(status_code=401, detail="刷新令牌无效或已过期")

    access_token = create_access_token({"user_id": token_row.user_id})
    refresh_token = create_refresh_token(database, token_row.user_id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    database: Session = Depends(get_database),
):
    revoke_refresh_token(database, payload.refresh_token)
    return {"message": "登出成功"}
