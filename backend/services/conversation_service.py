"""多轮对话服务：会话创建、消息保存、简单调整意图解析。"""
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.services.recommendation_config import COLOR_GROUPS
from database.models import ConversationMessage, ConversationSession


def get_or_create_session(
    db: Session,
    user_id: int,
    session_id: Optional[str] = None,
) -> ConversationSession:
    if session_id:
        session = (
            db.query(ConversationSession)
            .filter(ConversationSession.id == session_id)
            .first()
        )
        if session and session.user_id == user_id:
            return session

    session = ConversationSession(
        id=uuid.uuid4().hex,
        user_id=user_id,
        context={},
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def save_message(
    db: Session,
    session: ConversationSession,
    role: str,
    content: Dict[str, Any],
) -> ConversationMessage:
    message = ConversationMessage(
        session_id=session.id,
        role=role,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def list_messages(
    db: Session,
    session_id: str,
    user_id: int,
) -> List[ConversationMessage]:
    session = (
        db.query(ConversationSession)
        .filter(ConversationSession.id == session_id)
        .first()
    )
    if session is None or session.user_id != user_id:
        return []
    return (
        db.query(ConversationMessage)
        .filter(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.id.asc())
        .all()
    )


def parse_adjustments(message: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """从用户消息中解析简单调整意图，例如“不要蓝色”。"""
    context = dict(context or {})
    avoid_colors = set(context.get("avoid_colors") or [])

    for color in COLOR_GROUPS:
        for phrase in (f"不要{color}", f"不喜欢{color}", f"避免{color}"):
            if phrase in message:
                avoid_colors.add(color)

    context["avoid_colors"] = list(avoid_colors)
    return context
