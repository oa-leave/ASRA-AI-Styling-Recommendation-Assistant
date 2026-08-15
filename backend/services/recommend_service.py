from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.services.recommendation_engine import (
    _color_group_name,
    build_top_outfits,
    calculate_clothes_score,
    generate_summary,
    normalize_colors,
    normalize_tags,
)
from backend.services.recommendation_config import (
    CATEGORY_TO_SLOT,
    FORMAL_FALLBACK_BONUS,
    FORMAL_FALLBACK_PENALTY,
    MEMORY_BONUS,
    RECENT_LIKED_COLOR_BONUS,
    SCENE_SCORING,
)
from backend.services.scene_strategy import (
    apply_scene_constraints,
    apply_scene_preferences,
    build_scene_feedback,
    build_shoe_feedback,
    is_strict_formal_scene,
)
from backend.services.explanation_filter import filter_summary
from database.models import RecommendationHistory, User, UserProfile, Wardrobe


def _profile_to_dict(profile) -> Optional[Dict[str, Any]]:
    if profile is None:
        return None
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "style": profile.style,
        "favorite_color": profile.favorite_color,
        "favorite_colors": profile.favorite_colors or [],
        "style_tags": profile.style_tags or [],
        "fit_tags": profile.fit_tags or [],
        "avoid_colors": profile.avoid_colors or [],
        "occasion_preferences": profile.occasion_preferences or [],
        "body_type": profile.body_type,
        "season": profile.season,
    }


def _build_items(outfit: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "slot": slot,
            "name": item["name"],
            "score": item["score"],
            "style": item.get("style"),
            "color": item.get("color"),
            "reason": item.get("reason", []),
        }
        for slot, item in outfit.items()
    ]


def _append_avoid_reason(summary: List[str], avoid_colors: List[str]) -> List[str]:
    if avoid_colors:
        summary.append(f"本次避开{'、'.join(avoid_colors)}")
    return summary


def _filter_excluded_keywords(
    scored: List[Dict[str, Any]],
    keywords: Optional[List[str]],
) -> List[Dict[str, Any]]:
    if not keywords:
        return scored
    return [
        item
        for item in scored
        if not _matches_excluded_keywords(item, keywords)
    ]


def _matches_excluded_keywords(
    item: Dict[str, Any],
    keywords: List[str],
) -> bool:
    if not keywords:
        return False
    text = f"{item.get('name', '')} {item.get('category', '')}"
    return any(keyword in text for keyword in keywords)


def _matches_preferred_keywords(
    item: Dict[str, Any],
    keywords: Optional[List[str]],
) -> bool:
    if not keywords:
        return False
    text = f"{item.get('name', '')} {item.get('category', '')}"
    return any(keyword in text for keyword in keywords)


REQUIRED_ITEM_ALIASES = {
    "衬衫": ["衬衫", "衬衣"],
    "T恤": ["T恤", "短袖"],
    "西装": ["西装", "西服", "西装外套"],
    "裤子": ["裤子", "裤"],
    "裙子": ["裙子", "半身裙"],
    "鞋子": ["鞋子", "鞋"],
}

REQUIRED_ITEM_TO_SLOT = {
    "上衣": "上衣",
    "衬衫": "上衣",
    "T恤": "上衣",
    "短袖": "上衣",
    "卫衣": "上衣",
    "Polo": "上衣",
    "POLO": "上衣",
    "polo": "上衣",
    "毛衣": "上衣",
    "开衫": "外套",
    "西装": "外套",
    "西服": "外套",
    "西装外套": "外套",
    "外套": "外套",
    "风衣": "外套",
    "裤子": "裤子",
    "西裤": "裤子",
    "牛仔裤": "裤子",
    "休闲裤": "裤子",
    "运动裤": "裤子",
    "短裤": "裤子",
    "裙子": "裙子",
    "半身裙": "裙子",
    "连衣裙": "连衣裙",
    "鞋子": "鞋子",
    "运动鞋": "鞋子",
    "皮鞋": "鞋子",
    "乐福鞋": "鞋子",
    "帆布鞋": "鞋子",
    "帽子": "帽子",
    "包包": "包包",
}


def _matches_required_keyword(
    item: Dict[str, Any],
    keyword: str,
) -> bool:
    text = (
        f"{item.get('name', '')} {item.get('category', '')}"
    ).lower()
    aliases = REQUIRED_ITEM_ALIASES.get(keyword, [keyword])
    return any(alias.lower() in text for alias in aliases)


def _apply_required_item_keywords(
    scored: List[Dict[str, Any]],
    required_item_keywords: Optional[List[str]],
):
    if not required_item_keywords:
        return scored, [], set(), {}

    grouped: Dict[str, List[str]] = {}
    for keyword in required_item_keywords:
        slot = REQUIRED_ITEM_TO_SLOT.get(keyword, keyword)
        grouped.setdefault(slot, []).append(keyword)

    filtered = list(scored)
    missing = []
    forced_slots = set()
    required_slot_keywords = {}

    for slot, keywords in grouped.items():
        slot_items = [
            item
            for item in filtered
            if (
                CATEGORY_TO_SLOT.get(
                    item.get("category"),
                    item.get("category"),
                )
                == slot
            )
        ]
        matching = [
            item
            for item in slot_items
            if any(_matches_required_keyword(item, keyword) for keyword in keywords)
        ]
        for keyword in keywords:
            if not any(
                _matches_required_keyword(item, keyword)
                for item in slot_items
            ):
                missing.append(keyword)
        if not matching:
            continue

        forced_slots.add(slot)
        required_slot_keywords[slot] = keywords
        filtered = [
            item
            for item in filtered
            if (
                CATEGORY_TO_SLOT.get(
                    item.get("category"),
                    item.get("category"),
                )
                != slot
                or any(
                    _matches_required_keyword(item, keyword)
                    for keyword in keywords
                )
            )
        ]

    return filtered, missing, forced_slots, required_slot_keywords


def _question_item_allowed_by_scene(
    scene: Optional[Dict[str, Any]],
    question_item_keywords: Optional[List[str]],
) -> bool:
    if not scene or not question_item_keywords:
        return True
    casual_keywords = ("T恤", "短袖", "卫衣", "牛仔裤", "运动鞋", "帆布鞋")
    if not any(
        keyword in question_item
        for question_item in question_item_keywords
        for keyword in casual_keywords
    ):
        return True
    formal_markers = ("面试", "客户", "会议", "正式", "商务", "签约", "汇报")
    scene_type = scene.get("scene_type") or ""
    if is_strict_formal_scene(scene) or any(
        marker in scene_type
        for marker in formal_markers
    ):
        return False
    return True


def _apply_preferred_item_keywords(
    scored: List[Dict[str, Any]],
    keywords: Optional[List[str]],
) -> List[Dict[str, Any]]:
    if not keywords:
        return scored
    for item in scored:
        if _matches_preferred_keywords(item, keywords):
            item["score"] += PREFERRED_ITEM_BONUS
    return scored


FORMAL_ITEM_KEYWORDS = (
    "西装",
    "西裤",
    "衬衫",
    "衬衣",
    "皮鞋",
    "礼服",
    "乐福鞋",
    "单鞋",
)

KNOWLEDGE_BONUS = 5
PREFERRED_ITEM_BONUS = 30


def _is_formal_wardrobe_item(item) -> bool:
    if item.category in ("西装", "西裤"):
        return True
    text = (
        f"{item.name or ''} {item.category or ''} "
        f"{' '.join(item.occasion_tags or [])}"
    ).lower()
    return any(keyword in text for keyword in FORMAL_ITEM_KEYWORDS)


def _include_scene_candidates(
    scored: List[Dict[str, Any]],
    wardrobe,
    profile_data: Dict[str, Any],
    exclude_item_keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    existing_ids = {item.get("id") for item in scored}
    avoid_colors = set(normalize_colors(profile_data.get("avoid_colors") or []))
    candidates = []
    for item in wardrobe:
        if item.id in existing_ids:
            continue
        if _color_group_name(item.color) in avoid_colors:
            continue
        item_data = {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "color": item.color,
            "style": item.style,
            "season": item.season,
            "color_tags": normalize_tags(item.color_tags),
            "style_tags": normalize_tags(item.style_tags),
            "fit_tags": normalize_tags(item.fit_tags),
            "occasion_tags": normalize_tags(item.occasion_tags),
            "score": 0,
            "reason": ["场景候选"],
        }
        if _matches_excluded_keywords(item_data, exclude_item_keywords):
            continue
        candidates.append(item_data)
    return scored + candidates


def _apply_knowledge_rules(
    scored: List[Dict[str, Any]],
    knowledge_rules: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    if not scored or not knowledge_rules:
        return scored

    for item in scored:
        item_tags = set()
        item_tags.add(str(item.get("category") or ""))
        item_tags.add(str(item.get("season") or ""))
        item_tags.add(str(item.get("style") or ""))
        item_tags.update(item.get("color_tags") or [])
        item_tags.update(item.get("style_tags") or [])
        item_tags.update(item.get("occasion_tags") or [])
        item_tags.discard("")

        for rule in knowledge_rules:
            if item_tags & set(rule.get("tags") or []):
                item["score"] = item.get("score", 0) + KNOWLEDGE_BONUS

    return scored


def _apply_formal_fallback_adjustments(
    scored: List[Dict[str, Any]],
    preferred_keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    for item in scored:
        if _matches_preferred_keywords(item, preferred_keywords):
            continue
        text = (
            f"{item.get('name', '')} "
            f"{item.get('category', '')} "
            f"{' '.join(item.get('fit_tags', []))}"
        )
        for keyword, bonus in FORMAL_FALLBACK_BONUS.items():
            if keyword in text:
                item["score"] += bonus
        for keyword, penalty in FORMAL_FALLBACK_PENALTY.items():
            if keyword in text:
                item["score"] -= penalty
    return scored


def _apply_scene_scoring(
    scored: List[Dict[str, Any]],
    scene: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not scene:
        return scored

    rules = None
    for occasion in scene.get("occasion_tags") or []:
        if occasion in SCENE_SCORING:
            rules = SCENE_SCORING[occasion]
            break
    if not rules:
        return scored

    for item in scored:
        text = (
            f"{item.get('name', '')} "
            f"{item.get('category', '')} "
            f"{' '.join(item.get('fit_tags', []))}"
        )
        if any(keyword in text for keyword in rules["fit_keywords"]):
            item["score"] += rules["fit_bonus"]
        if item.get("color") in rules["soft_colors"]:
            item["score"] += rules["soft_color_bonus"]
        if any(keyword in text for keyword in rules["shoes_keywords"]):
            item["score"] += rules["shoes_bonus"]
        if any(keyword in text for keyword in rules["sporty_keywords"]):
            item["score"] -= rules["sporty_penalty"]
    return scored


def _apply_weather_adjustments(
    scored: List[Dict[str, Any]],
    weather: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not scored or not weather:
        return scored

    temperature = weather.get("temperature")
    humidity = weather.get("humidity")
    weather_text = weather.get("weather") or ""
    rainy = any(
        keyword in weather_text
        for keyword in ("雨", "毛毛雨", "阵雨", "雷")
    )

    for item in scored:
        text = (
            f"{item.get('name', '')} "
            f"{item.get('category', '')} "
            f"{' '.join(item.get('fit_tags') or [])}"
        )
        if temperature is not None:
            if temperature >= 28:
                if any(keyword in text for keyword in ("毛衣", "羽绒", "大衣", "厚")):
                    item["score"] -= 10
                if any(keyword in text for keyword in ("短袖", "T恤", "薄")):
                    item["score"] += 5
            elif temperature <= 18:
                if any(keyword in text for keyword in ("短袖", "T恤")):
                    item["score"] -= 10
                if any(
                    keyword in text
                    for keyword in ("长袖", "衬衫", "衬衣", "风衣", "外套", "西装")
                ):
                    item["score"] += 5

        if rainy:
            if any(keyword in text for keyword in ("短袖", "T恤")):
                item["score"] -= 8
            if any(keyword in text for keyword in ("长袖", "衬衫", "衬衣")):
                item["score"] += 8
            if any(keyword in text for keyword in ("帆布鞋", "棉鞋", "毛呢")):
                item["score"] -= 8
            if any(keyword in text for keyword in ("防水", "冲锋衣", "风衣")):
                item["score"] += 8

        if humidity is not None and humidity >= 80:
            if any(keyword in text for keyword in ("速干", "透气", "薄")):
                item["score"] += 6
            if any(keyword in text for keyword in ("厚", "毛呢", "羽绒", "大衣")):
                item["score"] -= 6

    return scored


def _apply_recent_liked_color_bonus(
    scored: List[Dict[str, Any]],
    conversation_context: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not conversation_context:
        return scored
    liked_groups = {
        _color_group_name(color)
        for color in (conversation_context.get("liked_colors") or [])
        if _color_group_name(color)
    }
    for item in scored:
        if _color_group_name(item.get("color")) in liked_groups:
            item["score"] += RECENT_LIKED_COLOR_BONUS
    return scored


def _collect_names(snapshot: Any) -> List[str]:
    names = []
    if isinstance(snapshot, dict):
        for value in snapshot.values():
            if isinstance(value, dict):
                if value.get("name"):
                    names.append(str(value["name"]))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        if item.get("name"):
                            names.append(str(item["name"]))
                    elif item:
                        names.append(str(item))
            elif value:
                names.append(str(value))
    return names


def _outfit_signature(outfit: Dict[str, Any]) -> frozenset:
    return frozenset(
        item.get("name", "")
        for item in outfit.values()
        if item.get("name")
    )


def _build_disliked_outfit_signatures(
    memory: Optional[Dict[str, Any]],
) -> set:
    signatures = set()
    feedback = (memory or {}).get("feedback_summary") or {}
    for item in feedback.get("recent", []):
        if item.get("feedback_type") != "dislike":
            continue
        names = _collect_names(item.get("outfit_snapshot"))
        if names:
            signatures.add(frozenset(names))
    return signatures


def _build_last_outfit_signature(
    memory: Optional[Dict[str, Any]],
) -> Optional[frozenset]:
    recent_history = (memory or {}).get("recent_history") or []
    if not recent_history:
        return None
    response = recent_history[0].get("response_snapshot") or {}
    names = [
        item.get("name")
        for item in (response.get("items") or [])
        if item.get("name")
    ]
    return frozenset(names) if names else None


def _apply_memory_adjustments(
    scored: List[Dict[str, Any]],
    memory: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not memory:
        return scored

    liked_names = set()
    disliked_names = set()
    feedback = memory.get("feedback_summary") or {}
    for item in feedback.get("recent", []):
        snapshot = item.get("outfit_snapshot")
        names = _collect_names(snapshot)
        if item.get("feedback_type") == "like":
            liked_names.update(names)
        elif item.get("feedback_type") == "dislike":
            disliked_names.update(names)

    preferences = memory.get("preference_signals") or {}
    favorite_styles = set(preferences.get("favorite_styles") or [])
    recent_item_names = set(preferences.get("recent_item_names") or [])
    favorite_color_groups = {
        group
        for color in (preferences.get("favorite_colors") or [])
        if (group := _color_group_name(color))
    }

    for item in scored:
        name = item.get("name")
        if name in liked_names:
            item["score"] += MEMORY_BONUS["liked_item"]
        if name in disliked_names:
            item["score"] += MEMORY_BONUS["disliked_item"]
        if name in recent_item_names:
            item["score"] += MEMORY_BONUS["recent_item_penalty"]
        if item.get("style") in favorite_styles:
            item["score"] += MEMORY_BONUS["favorite_style"]
        item_color_group = _color_group_name(item.get("color"))
        if item_color_group in favorite_color_groups:
            item["score"] += MEMORY_BONUS["favorite_color"]

    return scored


def generate_recommendation(
    user_id: int,
    db: Session,
    weather: Optional[Dict[str, Any]] = None,
    scene: Optional[Dict[str, Any]] = None,
    memory: Optional[Dict[str, Any]] = None,
    conversation_context: Optional[Dict[str, Any]] = None,
    knowledge_rules: Optional[List[Dict[str, Any]]] = None,
    top_n: int = 3,
    history_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == user_id)
        .first()
    )
    user = db.query(User).filter(User.id == user_id).first()
    wardrobe = (
        db.query(Wardrobe)
        .filter(Wardrobe.user_id == user_id)
        .all()
    )
    wardrobe_feedback_items = [
        {
            "name": item.name,
            "category": item.category,
            "occasion_tags": item.occasion_tags or [],
            "fit_tags": item.fit_tags or [],
            "style": item.style,
        }
        for item in wardrobe
    ]

    profile_data = _profile_to_dict(profile) or {}
    avoid_colors = set(profile_data.get("avoid_colors") or [])
    if conversation_context:
        avoid_colors.update(conversation_context.get("avoid_colors") or [])
        profile_data["avoid_colors"] = list(avoid_colors)

    exclude_item_keywords = (
        conversation_context.get("exclude_item_keywords")
        if conversation_context
        else []
    )
    required_item_keywords = (
        conversation_context.get("required_item_keywords")
        if conversation_context
        else []
    )
    allowed_item_keywords = (
        conversation_context.get("allowed_item_keywords")
        if conversation_context
        else []
    )
    allowed_colors = (
        conversation_context.get("allowed_colors")
        if conversation_context
        else []
    )
    required_colors = (
        conversation_context.get("required_colors")
        if conversation_context
        else []
    )
    color_conflicts = (
        conversation_context.get("color_conflicts")
        if conversation_context
        else []
    )
    item_conflicts = (
        conversation_context.get("item_conflicts")
        if conversation_context
        else []
    )
    style_conflicts = (
        conversation_context.get("style_conflicts")
        if conversation_context
        else []
    )
    question_item_keywords = (
        conversation_context.get("question_item_keywords")
        if conversation_context
        else []
    )
    style_requested = bool(
        conversation_context
        and conversation_context.get("style_requested")
    )
    formal_requested = bool(
        conversation_context
        and conversation_context.get("formal_requested")
    )

    favorite_colors = set(profile_data.get("favorite_colors") or [])
    liked_colors = (
        conversation_context.get("liked_colors")
        if conversation_context
        else []
    )
    favorite_colors.update(liked_colors)
    favorite_colors.difference_update(avoid_colors)
    profile_data["favorite_colors"] = list(favorite_colors)
    if profile_data.get("favorite_color") in avoid_colors:
        profile_data["favorite_color"] = None

    context_data = {}
    if scene and scene.get("style"):
        context_data["style"] = scene["style"]
    if weather and weather.get("season"):
        context_data["season"] = weather["season"]

    engine_profile_data = {**profile_data, **context_data}
    profile_obj = (
        SimpleNamespace(**engine_profile_data)
        if engine_profile_data
        else None
    )
    summary_profile_data = {**profile_data}
    if "season" in context_data:
        summary_profile_data["season"] = context_data["season"]
    summary_profile = (
        SimpleNamespace(**summary_profile_data)
        if summary_profile_data
        else None
    )
    scored, filtered_reasons = calculate_clothes_score(
        wardrobe,
        profile_obj,
        collect_filtered=True,
    )
    scored = _filter_excluded_keywords(scored, exclude_item_keywords)
    scored = _include_scene_candidates(
        scored,
        wardrobe,
        profile_data,
        exclude_item_keywords,
    )
    scored = _apply_memory_adjustments(scored, memory)
    scored = apply_scene_preferences(scored, scene)
    preferred_item_keywords = list(
        dict.fromkeys(
            [
                *(
                    conversation_context.get("preferred_item_keywords")
                    if conversation_context
                    else []
                ),
                *required_item_keywords,
                *(
                    question_item_keywords
                    if _question_item_allowed_by_scene(
                        scene,
                        question_item_keywords,
                    )
                    else []
                ),
            ]
        )
    )
    allowed_slots = set()
    allowed_slot_keywords = {}
    if allowed_item_keywords:
        for keyword in allowed_item_keywords:
            slot = REQUIRED_ITEM_TO_SLOT.get(keyword, keyword)
            allowed_slots.add(slot)
            allowed_slot_keywords.setdefault(slot, []).append(keyword)

    scored = apply_scene_constraints(
        scored,
        scene,
        preferred_item_keywords,
        allowed_slots or None,
        style_requested,
        formal_requested,
    )
    scored = _filter_excluded_keywords(
        scored,
        exclude_item_keywords,
    )
    scored, required_missing, required_force_slots, required_slot_keywords = (
        _apply_required_item_keywords(
            scored,
            required_item_keywords,
        )
    )
    if required_missing:
        scored = []

    if allowed_item_keywords:
        filtered_allowed = []
        for item in scored:
            item_slot = CATEGORY_TO_SLOT.get(
                item.get("category"),
                item.get("category"),
            )
            if item_slot not in allowed_slots:
                continue
            slot_keywords = allowed_slot_keywords.get(item_slot, [])
            if slot_keywords and not any(
                _matches_required_keyword(item, keyword)
                for keyword in slot_keywords
            ):
                continue
            filtered_allowed.append(item)
        scored = filtered_allowed

    if allowed_colors:
        allowed_color_groups = set(normalize_colors(allowed_colors))
        scored = [
            item
            for item in scored
            if _color_group_name(item.get("color")) in allowed_color_groups
        ]

    if required_colors:
        required_color_groups = set(normalize_colors(required_colors))
        scored = [
            item
            for item in scored
            if _color_group_name(item.get("color")) in required_color_groups
        ]

    if conversation_context:
        scored = _apply_preferred_item_keywords(
            scored,
            preferred_item_keywords,
        )
        scored = _apply_recent_liked_color_bonus(
            scored,
            conversation_context,
        )

    requested_style = context_data.get("style")
    style_missing = bool(requested_style) and not any(
        item.get("style") == requested_style
        for item in scored
    )
    if style_missing and requested_style == "商务":
        scored = _apply_formal_fallback_adjustments(
            scored,
            preferred_item_keywords,
        )
    if scene and scene.get("occasion_tags"):
        scored = _apply_scene_scoring(scored, scene)
    scored = _apply_knowledge_rules(scored, knowledge_rules)
    scored = _apply_weather_adjustments(scored, weather)
    request_avoid_colors = (
        list(conversation_context.get("request_avoid_colors") or [])
        if conversation_context
        else []
    )
    color_conflict_message = "、".join(
        f"要{color}和不要{color}"
        for color in color_conflicts
    )
    item_conflict_message = "、".join(
        f"只要{item}和不要{item}"
        for item in item_conflicts
    )
    style_conflict_message = "、".join(
        f"要{style}和不要{style}"
        for style in style_conflicts
    )
    no_matching_items = (
        not scored
        or bool(color_conflicts)
        or bool(item_conflicts)
        or bool(style_conflicts)
    )
    best_shoe_feedback = None

    if no_matching_items:
        missing_required_message = "、".join(required_missing)
        missing_item_message = (
            "、".join(allowed_item_keywords)
            or missing_required_message
        )
        missing_color_message = "、".join(required_colors)
        if style_conflict_message:
            message = (
                f"你的要求有冲突：{style_conflict_message}，"
                "请先确认。"
            )
        elif item_conflict_message:
            message = (
                f"你的要求有冲突：{item_conflict_message}，"
                "请先确认。"
            )
        elif color_conflict_message:
            message = (
                f"你的要求有冲突：{color_conflict_message}，"
                "请先确认。"
            )
        elif missing_color_message:
            if missing_item_message:
                message = (
                    f"当前衣柜缺少{missing_color_message}"
                    f"{missing_item_message}"
                )
            else:
                message = f"当前衣柜缺少{missing_color_message}衣物"
        elif missing_required_message:
            if requested_style:
                message = (
                    f"当前衣柜缺少{missing_required_message}"
                    f"（需要符合{requested_style}风格）"
                )
            else:
                message = f"当前衣柜缺少{missing_required_message}"
        elif requested_style:
            message = f"缺少{requested_style}风格衣物"
        else:
            message = "没有符合条件的衣物"
        outfit_results = []
        best = {
            "outfit": {},
            "score": 0,
            "reason": [message],
        }
        items = []
        summary = [message]
        summary = _append_avoid_reason(
            summary,
            request_avoid_colors,
        )
        top_outfits = []
    else:
        force_slot = set(conversation_context.get("force_slot") or []) if conversation_context else set()
        force_slot.update(required_force_slots)
        scene_requires_outerwear = bool(scene) and is_strict_formal_scene(scene)
        if scene_requires_outerwear and not allowed_item_keywords and any(
            item.get("category") in {"外套", "西装"}
            for item in scored
        ):
            force_slot.add("外套")

        outfit_results = build_top_outfits(
            scored,
            profile_obj,
            top_n=top_n,
            slot_style=conversation_context.get("slot_style")
            if conversation_context
            else None,
            force_slot=list(force_slot) or None,
            remove_slot=conversation_context.get("remove_slot")
            if conversation_context
            else None,
            replace_slot=conversation_context.get("replace_slot")
            if conversation_context
            else None,
            required_slot_keywords=required_slot_keywords,
            allowed_slots=list(allowed_slots) or None,
        )
        unique_outfits = []
        seen_outfits = set()
        for outfit_result in outfit_results:
            signature = tuple(
                sorted(
                    item.get("name", "")
                    for item in outfit_result.get("outfit", {}).values()
                )
            )
            if signature not in seen_outfits:
                seen_outfits.add(signature)
                unique_outfits.append(outfit_result)
        outfit_results = unique_outfits
        disliked_signatures = _build_disliked_outfit_signatures(memory)
        last_signature = _build_last_outfit_signature(memory)
        avoidable_outfits = []
        for outfit_result in outfit_results:
            signature = _outfit_signature(outfit_result.get("outfit", {}))
            if signature in disliked_signatures:
                continue
            if last_signature and signature == last_signature:
                continue
            avoidable_outfits.append(outfit_result)
        if avoidable_outfits:
            outfit_results = avoidable_outfits
        elif disliked_signatures:
            outfit_results = []
        best = outfit_results[0] if outfit_results else {
            "outfit": {},
            "score": 0,
            "reason": [],
        }
        best_shoe_feedback = build_shoe_feedback(scene, best["outfit"])

        items = _build_items(best["outfit"])
        summary = generate_summary(
            best["outfit"],
            best["reason"],
            summary_profile,
            best_shoe_feedback,
            current_style=context_data.get("style"),
        )
        if not best["outfit"]:
            summary = [
                "当前衣柜中没有未被点踩的替代搭配，"
                "建议补充新单品后再试"
            ]
        summary = filter_summary(summary, profile_data.get("avoid_colors"))
        summary = _append_avoid_reason(summary, request_avoid_colors)

        top_outfits = []
        for outfit_result in outfit_results:
            outfit_shoe_feedback = build_shoe_feedback(
                scene,
                outfit_result["outfit"],
            )
            outfit_summary = generate_summary(
                outfit_result["outfit"],
                outfit_result["reason"],
                summary_profile,
                outfit_shoe_feedback,
                current_style=context_data.get("style"),
            )
            outfit_summary = filter_summary(
                outfit_summary,
                profile_data.get("avoid_colors"),
            )
            outfit_summary = _append_avoid_reason(
                outfit_summary,
                request_avoid_colors,
            )
            top_outfits.append({
                "outfit_score": outfit_result["score"],
                "items": _build_items(outfit_result["outfit"]),
                "summary": outfit_summary,
                "shoe_feedback": outfit_shoe_feedback,
                "scene_feedback": build_scene_feedback(
                    scene,
                    outfit_result["outfit"],
                    wardrobe_feedback_items,
                ),
            })

    scene_feedback = build_scene_feedback(
        scene,
        best["outfit"],
        wardrobe_feedback_items,
    )
    shoe_feedback = best_shoe_feedback
    context = dict(history_context or {"source": "recommend"})
    if weather is not None:
        context["weather"] = weather
    if scene is not None:
        context["scene"] = scene

    history = RecommendationHistory(
        user_id=user_id,
        request_context=context,
        response_snapshot={
            "outfit_score": best["score"],
            "items": items,
            "summary": summary,
            "weather": weather,
            "scene": scene,
            "scene_feedback": scene_feedback,
            "shoe_feedback": shoe_feedback,
        },
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return {
        "user_id": user_id,
        "username": user.username if user else None,
        "profile": profile_data,
        "context_profile": engine_profile_data,
        "clothes_count": len(wardrobe),
        "recommendation": {
            "outfit_score": best["score"],
            "items": items,
            "summary": summary,
            "scene_feedback": scene_feedback,
            "shoe_feedback": shoe_feedback,
        },
        "recommendations": top_outfits,
        "scene_feedback": scene_feedback,
        "shoe_feedback": shoe_feedback,
        "outfit_score": best["score"],
        "outfit_reason": best["reason"],
        "filtered_reasons": filtered_reasons,
        "history_id": history.id,
    }
