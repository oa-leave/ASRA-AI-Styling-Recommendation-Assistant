from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.agent.explain import generate_llm_explanation
from backend.agent.graph import build_agent_graph
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services.explanation_filter import filter_text
from backend.services.conversation_service import (
    get_or_create_session,
    is_request_message,
    list_messages,
    parse_adjustments,
    save_message,
)
from backend.utils.database import get_database
from backend.utils.dependencies import get_current_user
from database.models import ConversationMessage, ConversationSession, User, UserProfile


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
    request_scoped = is_request_message(payload.message)
    item_constraint_request = bool(
        context.get("required_item_keywords")
        or context.get("allowed_item_keywords")
        or context.get("exclude_item_keywords")
        or context.get("question_item_keywords")
        or context.get("allowed_colors")
        or context.get("required_colors")
        or context.get("style_requested")
    )
    persistent_preference_request = bool(
        context.get("required_item_keywords")
        or context.get("allowed_item_keywords")
        or context.get("exclude_item_keywords")
        or context.get("question_item_keywords")
        or context.get("allowed_colors")
        or context.get("style_requested")
    )
    previous_context = dict(session.context or {})
    if request_scoped:
        previous_avoid_colors = set(previous_context.get("avoid_colors") or [])
        request_avoid_colors = (
            set(context.get("avoid_colors") or []) - previous_avoid_colors
        )
        context["request_avoid_colors"] = sorted(request_avoid_colors)

    profile_row = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == current_user.id)
        .first()
    )
    if profile_row and not request_scoped and not persistent_preference_request:
        existing_avoid_colors = set(profile_row.avoid_colors or [])
        existing_avoid_colors.update(context.get("avoid_colors") or [])
        removed_avoid_colors = set(context.get("removed_avoid_colors") or [])
        removed_avoid_colors.difference_update(context.get("avoid_colors") or [])
        existing_avoid_colors.difference_update(removed_avoid_colors)
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
        forecast_day=result.get("forecast_day", 0),
        scene=result.get("scene"),
        day_label=result.get("day_label"),
        query=result.get("query"),
        explicit_style=bool(
            (result.get("conversation_context") or {}).get(
                "style_requested"
            )
        ),
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
    if request_scoped:
        for key in (
            "avoid_colors",
            "liked_colors",
            "removed_avoid_colors",
            "request_avoid_colors",
            "exclude_item_keywords",
            "preferred_item_keywords",
            "required_item_keywords",
            "question_item_keywords",
            "allowed_item_keywords",
            "allowed_colors",
            "style_requested",
            "formal_requested",
            "business_requested",
            "required_colors",
            "color_conflicts",
            "item_conflicts",
            "style_conflicts",
            "force_slot",
            "remove_slot",
            "replace_slot",
            "slot_style",
        ):
            context[key] = previous_context.get(
                key,
                {} if key in {"replace_slot", "slot_style"} else [],
            )
        context["style"] = previous_context.get("style")
        context["requested_season"] = previous_context.get("requested_season")
    elif item_constraint_request:
        previous_avoid = set(previous_context.get("avoid_colors") or [])
        removed_now = set(context.get("removed_avoid_colors") or [])
        context["avoid_colors"] = sorted(previous_avoid - removed_now)
        context["style"] = previous_context.get("style")
        context["requested_season"] = previous_context.get("requested_season")
        for key in (
            "liked_colors",
            "removed_avoid_colors",
            "request_avoid_colors",
        ):
            context[key] = previous_context.get(key, [])
        for key in (
            "exclude_item_keywords",
            "preferred_item_keywords",
            "required_item_keywords",
            "question_item_keywords",
            "allowed_item_keywords",
            "allowed_colors",
            "style_requested",
            "formal_requested",
            "business_requested",
            "required_colors",
            "color_conflicts",
            "item_conflicts",
            "style_conflicts",
            "force_slot",
            "remove_slot",
            "replace_slot",
            "slot_style",
        ):
            context[key] = (
                {}
                if key in {"replace_slot", "slot_style"}
                else []
            )
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


@router.delete("/conversations")
def clear_conversations(
    db: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    sessions = (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == current_user.id)
        .all()
    )
    session_ids = [session.id for session in sessions]
    if session_ids:
        db.query(ConversationMessage).filter(
            ConversationMessage.session_id.in_(session_ids)
        ).delete(synchronize_session=False)
    deleted = (
        db.query(ConversationSession)
        .filter(ConversationSession.user_id == current_user.id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {
        "message": "会话已清空",
        "deleted_count": deleted,
    }
