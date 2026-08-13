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


def _filter_excluded_keywords(
    scored: List[Dict[str, Any]],
    keywords: Optional[List[str]],
) -> List[Dict[str, Any]]:
    if not keywords:
        return scored
    return [
        item
        for item in scored
        if not any(
            keyword in item.get("name", "") or keyword in item.get("category", "")
            for keyword in keywords
        )
    ]


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
) -> List[Dict[str, Any]]:
    existing_ids = {item.get("id") for item in scored}
    avoid_colors = set(normalize_colors(profile_data.get("avoid_colors") or []))
    candidates = []
    for item in wardrobe:
        if item.id in existing_ids:
            continue
        if _color_group_name(item.color) in avoid_colors:
            continue
        candidates.append({
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
        })
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
) -> List[Dict[str, Any]]:
    for item in scored:
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
                    if isinstance(item, dict) and item.get("name"):
                        names.append(str(item["name"]))
            elif value:
                names.append(str(value))
    return names


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

    profile_data = _profile_to_dict(profile) or {}
    avoid_colors = set(profile_data.get("avoid_colors") or [])
    if conversation_context:
        avoid_colors.update(conversation_context.get("avoid_colors") or [])
        profile_data["avoid_colors"] = list(avoid_colors)

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
    scored = _include_scene_candidates(scored, wardrobe, profile_data)
    scored = _apply_memory_adjustments(scored, memory)
    scored = apply_scene_preferences(scored, scene)
    scored = apply_scene_constraints(scored, scene)
    scored = _filter_excluded_keywords(
        scored,
        conversation_context.get("exclude_item_keywords")
        if conversation_context
        else None,
    )
    if conversation_context:
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
        scored = _apply_formal_fallback_adjustments(scored)
    if scene and scene.get("occasion_tags"):
        scored = _apply_scene_scoring(scored, scene)
    scored = _apply_knowledge_rules(scored, knowledge_rules)
    no_matching_items = not scored
    formal_in_wardrobe = any(_is_formal_wardrobe_item(item) for item in wardrobe)
    formal_filtered_message = None
    if formal_in_wardrobe and filtered_reasons:
        formal_filtered_message = (
            "衣柜中有正式单品，但部分被当前回避色过滤；"
            "请取消相关回避色或补充其他正式单品"
        )

    if no_matching_items:
        message = (
            formal_filtered_message
            or (
                f"缺少{requested_style}风格衣物"
                if requested_style
                else "没有符合条件的衣物"
            )
        )
        outfit_results = []
        best = {
            "outfit": {},
            "score": 0,
            "reason": [message],
        }
        items = []
        summary = [message]
        top_outfits = []
    else:
        force_slot = set(conversation_context.get("force_slot") or []) if conversation_context else set()
        scene_requires_outerwear = bool(scene) and (
            int(scene.get("formality") or 0) >= 3
            or scene.get("scene_type") in {
                "婚礼",
                "宴会",
                "酒会",
                "客户拜访",
                "面试",
                "会议",
            }
            or scene.get("style") == "商务"
        )
        if scene_requires_outerwear and any(
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
        )
        best = outfit_results[0] if outfit_results else {
            "outfit": {},
            "score": 0,
            "reason": [],
        }

        items = _build_items(best["outfit"])
        summary = generate_summary(best["outfit"], best["reason"], summary_profile)
        if style_missing:
            missing_summary = (
                formal_filtered_message
                or (
                    f"当前衣柜缺少{requested_style}风格单品，"
                    "使用简洁配色打造偏正式休闲风"
                )
            )
            summary.insert(
                0,
                missing_summary,
            )
        summary = filter_summary(summary, profile_data.get("avoid_colors"))

        top_outfits = []
        for outfit_result in outfit_results:
            outfit_summary = generate_summary(
                    outfit_result["outfit"],
                    outfit_result["reason"],
                    summary_profile,
                )
            if style_missing:
                missing_summary = (
                    formal_filtered_message
                    or (
                        f"当前衣柜缺少{requested_style}风格单品，"
                        "使用简洁配色打造偏正式休闲风"
                    )
                )
                outfit_summary.insert(
                    0,
                    missing_summary,
                )
            top_outfits.append({
                "outfit_score": outfit_result["score"],
                "items": _build_items(outfit_result["outfit"]),
                "summary": filter_summary(
                    outfit_summary,
                    profile_data.get("avoid_colors"),
                ),
                "scene_feedback": build_scene_feedback(
                    scene,
                    outfit_result["outfit"],
                ),
            })

    scene_feedback = build_scene_feedback(scene, best["outfit"])
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
        },
        "recommendations": top_outfits,
        "scene_feedback": scene_feedback,
        "outfit_score": best["score"],
        "outfit_reason": best["reason"],
        "filtered_reasons": filtered_reasons,
        "history_id": history.id,
    }
