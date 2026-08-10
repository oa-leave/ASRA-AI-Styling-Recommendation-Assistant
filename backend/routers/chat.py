from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.agent.explain import generate_llm_explanation
from backend.agent.graph import build_agent_graph
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.explanation_filter import filter_text
from backend.services.conversation_service import (
    get_or_create_session,
    list_messages,
    parse_adjustments,
    save_message,
)
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from database.models import ConversationSession, User, UserProfile


router = APIRouter(prefix="/chat", tags=["多轮对话"])


@router.post("/", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    try:
        session = get_or_create_session(db, current_user.id, payload.session_id)
    except ValueError:
        raise HTTPException(status_code=403, detail="无权使用该会话")
    context = parse_adjustments(payload.message, session.context)

    profile_row = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if profile_row:
        existing_avoid_colors = set(profile_row.avoid_colors or [])
        existing_avoid_colors.update(context.get("avoid_colors") or [])
        existing_avoid_colors.difference_update(
            context.get("removed_avoid_colors") or []
        )
        profile_row.avoid_colors = list(existing_avoid_colors)

        existing_favorite_colors = set(profile_row.favorite_colors or [])
        existing_favorite_colors.difference_update(existing_avoid_colors)
        existing_favorite_colors.update(context.get("liked_colors") or [])
        profile_row.favorite_colors = list(existing_favorite_colors)
        db.commit()

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

    avoid_colors = (result.get("conversation_context") or {}).get("avoid_colors") or []
    knowledge_text = filter_text(result.get("knowledge_text"), avoid_colors)

    explanation = generate_llm_explanation(
        result.get("city"),
        result.get("weather"),
        result.get("occasion"),
        result.get("recommendation"),
        result.get("profile"),
        result.get("memory"),
        knowledge_text,
    )

    memory = result.get("memory") or {}
    reply_memory = {
        "profile": memory.get("profile"),
        "feedback_summary": memory.get("feedback_summary"),
        "preference_signals": memory.get("preference_signals"),
    }

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
        {
            "text": explanation,
            "recommendation": result.get("recommendation"),
            "history_id": result.get("history_id"),
        },
    )

    messages = list_messages(db, session.id, current_user.id)
    return {
        "session_id": session.id,
        "reply": {
            **result,
            "knowledge_text": knowledge_text,
            "memory": reply_memory,
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
