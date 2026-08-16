"""多轮对话服务：会话创建、消息保存、简单调整意图解析。"""
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.agent.tools import SCENE_MAP
from backend.services.recommendation_config import COLOR_GROUPS, STYLES
from database.models import ConversationMessage, ConversationSession


ITEM_EXCLUDE_KEYWORDS = [
    "短袖",
    "长袖",
    "T恤",
    "卫衣",
    "牛仔裤",
    "西装",
    "衬衫",
    "衬衣",
    "风衣",
    "上衣",
    "鞋子",
    "运动鞋",
    "皮鞋",
    "裙子",
    "外套",
    "开衫",
    "吊带",
]

ITEM_EXCLUDE_ALIASES = {
    "短袖": ["短袖", "T恤"],
    "长袖": ["长袖"],
    "T恤": ["T恤", "短袖"],
    "卫衣": ["卫衣", "长袖"],
    "衬衫": ["衬衫", "衬衣"],
    "西装": ["西装", "西服", "西装外套"],
}

ITEM_REQUIRED_ALIASES = {
    "衬衣": "衬衫",
    "短袖": "T恤",
    "西服": "西装",
    "西装外套": "西装",
}

ITEM_REQUIRED_KEYWORDS = list(
    dict.fromkeys(
        ITEM_EXCLUDE_KEYWORDS
        + [
            "衬衣",
            "西服",
            "西装外套",
            "西裤",
            "裤子",
            "牛仔裤",
            "休闲裤",
            "运动裤",
            "短裤",
            "半身裙",
            "连衣裙",
            "风衣",
            "毛衣",
            "开衫",
            "鞋子",
            "运动鞋",
            "皮鞋",
            "乐福鞋",
            "帆布鞋",
            "帽子",
            "包包",
        ]
    )
)

REQUEST_MARKERS = [
    "怎么穿",
    "穿什么",
    "穿什么好",
    "推荐一套",
    "给我推荐",
    "明天",
    "今天",
    "周末",
    "后天",
    "去",
    "参加",
    "见",
    "开会",
    "上班",
    "出差",
    "面试",
    "婚礼",
    "宴会",
    "约会",
    "爬山",
    "通勤",
    "聚会",
    "健身",
    "运动",
    "旅行",
    "电影",
    "逛街",
    "购物",
]


def is_request_message(message: str) -> bool:
    return any(marker in message for marker in REQUEST_MARKERS)


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
    removed_avoid_colors = set()
    exclude_item_keywords = set(context.get("exclude_item_keywords") or [])
    preferred_item_keywords = set(context.get("preferred_item_keywords") or [])
    required_item_keywords = set(context.get("required_item_keywords") or [])
    question_item_keywords = set(context.get("question_item_keywords") or [])
    allowed_item_keywords = set(context.get("allowed_item_keywords") or [])
    allowed_colors = set(context.get("allowed_colors") or [])
    required_colors = set(context.get("required_colors") or [])
    liked_colors = set(context.get("liked_colors") or [])
    color_conflicts = set(context.get("color_conflicts") or [])
    item_conflicts = set(context.get("item_conflicts") or [])
    style_conflicts = set(context.get("style_conflicts") or [])

    negative_markers = [
        "不要",
        "不喜欢",
        "没相中",
        "不推荐",
        "不想穿",
        "不想",
        "别",
        "避免",
        "讨厌",
        "接受不了",
        "不考虑",
        "不用",
        "不允许",
    ]
    positive_markers = ["要", "可以", "喜欢", "不回避", "现在要", "允许"]
    positive_item_markers = [
        "只推荐",
        "推荐",
        "只要",
        "只需",
        "就穿",
        "想穿",
        "要穿",
        "喜欢穿",
        "穿",
    ]
    for color in COLOR_GROUPS:
        neg_regex = re.compile(
            rf"(?:{'|'.join(negative_markers)}).{{0,3}}{re.escape(color)}"
        )
        pos_regex = re.compile(
            rf"(?:{'|'.join(positive_markers)}).{{0,8}}{re.escape(color)}"
        )
        required_color_regex = re.compile(
            rf"(?:要|现在要|只要|只推荐|只需|不回避|允许).{{0,4}}{re.escape(color)}"
        )
        liked_color_regex = re.compile(
            rf"喜欢.{{0,4}}{re.escape(color)}"
        )
        positive_color_regex = re.compile(
            rf"(?<!不)(?<!别)"
            rf"(?:要|现在要|只要|只推荐|只需|喜欢|允许|不回避)"
            rf".{{0,4}}{re.escape(color)}"
        )

        if neg_regex.search(message):
            avoid_colors.add(color)
            required_colors.discard(color)
            liked_colors.discard(color)

        if required_color_regex.search(message) and not neg_regex.search(message):
            required_colors.add(color)
            liked_colors.add(color)
            avoid_colors.discard(color)
            removed_avoid_colors.add(color)
        elif liked_color_regex.search(message) and not neg_regex.search(message):
            liked_colors.add(color)
        elif pos_regex.search(message) and not neg_regex.search(message):
            avoid_colors.discard(color)
            removed_avoid_colors.add(color)
            liked_colors.add(color)

        has_negative = bool(neg_regex.search(message))
        has_positive = bool(positive_color_regex.search(message))
        if has_negative and has_positive:
            color_conflicts.add(color)

    question_pattern = re.compile(r"(?:可以|能)穿(.{1,8}?)(?:吗|么|行不行|可以吗)")
    question_item_matches = set()
    for match in question_pattern.finditer(message):
        for keyword in ITEM_REQUIRED_KEYWORDS:
            if keyword in match.group(1):
                question_item_matches.add(keyword)

    def _inside_question(match) -> bool:
        for question_match in question_pattern.finditer(message):
            if question_match.start() <= match.start() < question_match.end():
                return True
        return False

    strict_item_markers = [
        "只推荐",
        "推荐",
        "只要",
        "只需",
        "就穿",
        "想穿",
        "要穿",
        "喜欢穿",
        "穿",
    ]
    for keyword in ITEM_REQUIRED_KEYWORDS:
        keyword_regex = re.compile(
            rf"(?:{'|'.join(negative_markers)}).{{0,2}}{re.escape(keyword)}"
        )
        strict_item_regex = re.compile(
            rf"(?:{'|'.join(strict_item_markers)}).{{0,4}}{re.escape(keyword)}"
        )
        strict_matches = list(strict_item_regex.finditer(message))
        outside_question = [
            match
            for match in strict_matches
            if not _inside_question(match)
        ]
        if keyword_regex.search(message):
            exclude_item_keywords.add(keyword)
            exclude_item_keywords.update(ITEM_EXCLUDE_ALIASES.get(keyword, []))
            if outside_question:
                item_conflicts.add(
                    ITEM_REQUIRED_ALIASES.get(keyword, keyword)
                )
            continue
        if outside_question:
            canonical = ITEM_REQUIRED_ALIASES.get(keyword, keyword)
            required_item_keywords.add(canonical)
            preferred_item_keywords.add(canonical)
        elif keyword in question_item_matches:
            question_item_keywords.add(
                ITEM_REQUIRED_ALIASES.get(keyword, keyword)
            )

    for keyword in ITEM_REQUIRED_KEYWORDS:
        canonical = ITEM_REQUIRED_ALIASES.get(keyword, keyword)
        if (
            canonical in required_item_keywords
            or keyword in exclude_item_keywords
        ):
            continue
        if any(
            re.search(
                rf"{re.escape(required_word)}(?:和|与|、|及)\s*{re.escape(keyword)}",
                message,
            )
            for required_word in required_item_keywords
        ):
            required_item_keywords.add(canonical)
            preferred_item_keywords.add(canonical)

    only_markers = ("只推荐", "只要", "只需", "只穿", "只想穿")
    if any(marker in message for marker in only_markers):
        allowed_item_keywords.update(required_item_keywords)
        for color in COLOR_GROUPS:
            only_color_regex = re.compile(
                rf"(?:{'|'.join(only_markers)}).{{0,2}}{re.escape(color)}"
            )
            if only_color_regex.search(message):
                allowed_colors.add(color)

    casual_markers = ("休闲", "舒服", "日常", "轻松", "不要太正式", "别太正式")
    formal_markers = ("正式", "职场", "商务")
    explicit_style = any(word in message for word in casual_markers)
    explicit_style = explicit_style or any(
        word in message for word in formal_markers
    )
    if "运动" in message or "日系" in message:
        explicit_style = True

    def _style_is_negated(style: str) -> bool:
        return any(
            marker in message
            for marker in (
                f"不要{style}",
                f"不想穿{style}",
                f"别{style}",
                f"不穿{style}",
                f"不要{style}风",
                f"不想穿{style}风",
            )
        )

    if any(word in message for word in casual_markers) and not _style_is_negated("休闲"):
        context["style"] = "休闲"
    elif any(word in message for word in formal_markers) and not _style_is_negated("商务"):
        context["style"] = "商务"
    elif "运动" in message and not _style_is_negated("运动"):
        context["style"] = "运动"
    elif "日系" in message and not _style_is_negated("日系"):
        context["style"] = "日系"
    elif not explicit_style:
        for occasion in SCENE_MAP:
            if occasion in message:
                context["style"] = SCENE_MAP[occasion].get("style", "休闲")
                break
    context["style_requested"] = explicit_style
    formal_requested = any(
        marker in message
        for marker in ("正式", "职场")
    ) and not any(
        marker in message
        for marker in ("不要太正式", "别太正式", "不太正式")
    )
    context["formal_requested"] = formal_requested
    business_requested = any(
        marker in message
        for marker in ("商务风", "商务风格", "要商务")
    ) and not any(
        marker in message
        for marker in ("不要商务", "不想穿商务", "别商务", "不穿商务")
    )
    context["business_requested"] = business_requested

    season_markers = {
        "春天": "春季",
        "夏天": "夏季",
        "秋天": "秋季",
        "冬天": "冬季",
        "春秋": "春秋",
    }
    requested_season = next(
        (
            value
            for key, value in season_markers.items()
            if key in message
        ),
        None,
    )
    context["requested_season"] = requested_season

    conflict_styles = list(STYLES) + ["正式"]
    for style in conflict_styles:
        positive_markers = (
            f"{style}风",
            f"{style}风格",
            f"要{style}",
            f"穿{style}",
            f"只推荐{style}",
        )
        negative_markers = (
            f"不要{style}",
            f"不想穿{style}",
            f"别{style}",
            f"不穿{style}",
            f"不要{style}风",
            f"不想穿{style}风",
            f"不要{style}风格",
        )
        positive_text = message
        for negative_marker in negative_markers:
            positive_text = positive_text.replace(negative_marker, "")
        if any(
            marker in positive_text
            for marker in positive_markers
        ) and any(
            marker in message
            for marker in negative_markers
        ):
            style_conflicts.add(f"{style}风")

    if (
        "裤子" in message
        and ("正式" in message or "商务" in message)
        and ("换" in message or "改" in message)
    ):
        slot_style["裤子"] = "商务"
    if (
        "上衣" in message
        and ("正式" in message or "商务" in message)
        and ("换" in message or "改" in message)
    ):
        slot_style["上衣"] = "商务"

    if "加" in message and "外套" in message:
        force_slot.add("外套")

    remove_slot_pattern = re.compile(
        r"(?:去掉|不要穿|不想穿|别穿|不穿|不要)\s*(外套|裤子)"
    )
    for match in remove_slot_pattern.finditer(message):
        remove_slot.add(match.group(1))

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
    context["preferred_item_keywords"] = list(preferred_item_keywords)
    context["required_item_keywords"] = list(required_item_keywords)
    context["question_item_keywords"] = list(question_item_keywords)
    context["allowed_item_keywords"] = list(allowed_item_keywords)
    context["allowed_colors"] = list(allowed_colors)
    context["required_colors"] = list(required_colors)
    context["color_conflicts"] = list(color_conflicts)
    context["item_conflicts"] = list(item_conflicts)
    context["style_conflicts"] = list(style_conflicts)
    context["liked_colors"] = list(liked_colors)
    return context
