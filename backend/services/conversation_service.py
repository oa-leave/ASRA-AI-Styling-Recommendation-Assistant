"""多轮对话服务：会话创建、消息保存、简单调整意图解析。"""
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.agent.tools import SCENE_MAP
from backend.services.recommendation_config import COLOR_GROUPS
from database.models import ConversationMessage, ConversationSession


ITEM_EXCLUDE_KEYWORDS = [
    "短袖",
    "长袖",
    "T恤",
    "卫衣",
    "牛仔裤",
    "西装",
    "衬衫",
    "风衣",
    "运动鞋",
    "皮鞋",
    "裙子",
    "外套",
    "开衫",
    "吊带",
]

ITEM_EXCLUDE_ALIASES = {
    "短袖": ["短袖", "T恤"],
    "长袖": ["长袖", "衬衫", "卫衣"],
    "T恤": ["T恤", "短袖"],
    "卫衣": ["卫衣", "长袖"],
}


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
        if session:
            if session.user_id == user_id:
                return session
            raise ValueError("session not owned")
        new_session_id = session_id
    else:
        new_session_id = uuid.uuid4().hex

    session = ConversationSession(
        id=new_session_id,
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
    """从用户消息中解析调整意图：回避颜色、槽位风格、强制槽位、移除槽位。"""
    context = dict(context or {})
    avoid_colors = set(context.get("avoid_colors") or [])
    slot_style = dict(context.get("slot_style") or {})
    force_slot = set(context.get("force_slot") or [])
    remove_slot = set(context.get("remove_slot") or [])
    replace_slot = dict(context.get("replace_slot") or {})
    removed_avoid_colors = set(context.get("removed_avoid_colors") or [])
    exclude_item_keywords = set(context.get("exclude_item_keywords") or [])
    liked_colors = set(context.get("liked_colors") or [])

    negative_markers = [
        "不要",
        "不喜欢",
        "没相中",
        "不推荐",
        "别",
        "避免",
        "讨厌",
        "接受不了",
        "不考虑",
        "不用",
    ]
    positive_markers = ["要", "可以", "喜欢", "不回避", "现在要"]
    for color in COLOR_GROUPS:
        neg_regex = re.compile(
            rf"(?:{'|'.join(negative_markers)}).{{0,8}}{re.escape(color)}"
        )
        pos_regex = re.compile(
            rf"(?:{'|'.join(positive_markers)}).{{0,8}}{re.escape(color)}"
        )

        if neg_regex.search(message):
            avoid_colors.add(color)
            liked_colors.discard(color)

        if pos_regex.search(message) and not neg_regex.search(message):
            avoid_colors.discard(color)
            removed_avoid_colors.add(color)
            liked_colors.add(color)

    for keyword in ITEM_EXCLUDE_KEYWORDS:
        keyword_regex = re.compile(
            rf"(?:{'|'.join(negative_markers)}).{{0,8}}{re.escape(keyword)}"
        )
        if keyword_regex.search(message):
            exclude_item_keywords.add(keyword)
            exclude_item_keywords.update(ITEM_EXCLUDE_ALIASES.get(keyword, []))

    explicit_style = any(
        word in message for word in ("正式", "职场", "商务")
    )
    if any(word in message for word in ("休闲", "舒服", "日常")):
        explicit_style = True
    if "运动" in message or "日系" in message:
        explicit_style = True

    if any(word in message for word in ("正式", "职场", "商务")):
        context["style"] = "商务"
    elif any(word in message for word in ("休闲", "舒服", "日常")):
        context["style"] = "休闲"
    elif "运动" in message:
        context["style"] = "运动"
    elif "日系" in message:
        context["style"] = "日系"
    elif not explicit_style:
        for occasion in SCENE_MAP:
            if occasion in message:
                context["style"] = SCENE_MAP[occasion].get("style", "休闲")
                break

    if "裤子" in message and ("正式" in message or "商务" in message):
        slot_style["裤子"] = "商务"
    if "上衣" in message and ("正式" in message or "商务" in message):
        slot_style["上衣"] = "商务"

    if "加" in message and "外套" in message:
        force_slot.add("外套")

    if ("去掉" in message or "不要" in message) and "外套" in message:
        remove_slot.add("外套")
    if ("去掉" in message or "不要" in message) and "裤子" in message:
        remove_slot.add("裤子")

    if "裤子" in message and "裙子" in message and (
        "换" in message or "改成" in message
    ):
        replace_slot["裤子"] = "裙子"

    context["avoid_colors"] = list(avoid_colors)
    context["slot_style"] = slot_style
    context["force_slot"] = list(force_slot)
    context["remove_slot"] = list(remove_slot)
    context["replace_slot"] = replace_slot
    context["removed_avoid_colors"] = list(removed_avoid_colors)
    context["exclude_item_keywords"] = list(exclude_item_keywords)
    context["liked_colors"] = list(liked_colors)
    return context
