from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.agent.explain import generate_llm_explanation
from backend.agent.graph import build_agent_graph
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.conversation_service import (
    get_or_create_session,
    list_messages,
    parse_adjustments,
    save_message,
)
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from database.models import ConversationSession, User


router = APIRouter(prefix="/chat", tags=["多轮对话"])


@router.post("/", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    session = get_or_create_session(db, current_user.id, payload.session_id)
    context = parse_adjustments(payload.message, session.context)

    save_message(db, session, "user", {"text": payload.message})

    graph = build_agent_graph(db)
    result = graph.invoke({
        "query": payload.message,
        "city": context.get("city"),
        "occasion": context.get("occasion"),
        "style": context.get("style"),
        "conversation_context": context,
        "user_id": current_user.id,
    })

    explanation = generate_llm_explanation(
        result.get("city"),
        result.get("weather"),
        result.get("occasion"),
        result.get("recommendation"),
        result.get("profile"),
        result.get("memory"),
        result.get("knowledge_text"),
    )

    context["city"] = result.get("city")
    context["occasion"] = result.get("occasion")
    context["last_recommendation"] = result.get("recommendation")
    context["last_explanation"] = explanation
    session.context = context
    db.commit()

    save_message(
        db,
        session,
        "assistant",
        {"text": explanation, "result": result},
    )

    messages = list_messages(db, session.id, current_user.id)
    return {
        "session_id": session.id,
        "reply": {
            **result,
            "explanation": explanation,
        },
        "messages": [
            {"role": message.role, "content": message.content}
            for message in messages
        ],
    }


@router.get("/conversations")
def list_conversations(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == current_user.id)
        .order_by(ConversationSession.updated_at.desc())
        .all()
    )


@router.get("/conversations/{session_id}")
def get_conversation(
    session_id: str,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ConversationSession)
        .filter(ConversationSession.id == session_id)
        .first()
    )
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = list_messages(db, session_id, current_user.id)
    return {
        "session_id": session.id,
        "context": session.context,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in messages
        ],
    }
