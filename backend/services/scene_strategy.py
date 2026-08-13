"""Scene-aware fallback advice without changing the core scoring engine."""
from typing import Any, Dict, List, Optional

from backend.services.recommendation_config import CATEGORY_TO_SLOT


SCENE_OCCASION_BONUS = 20
SCENE_PREFERRED_BONUS = 10
SCENE_NON_FORMAL_PENALTY = 80
SCENE_HIGH_FORMALITY_OCCASION_BONUS = 60


FORMAL_RULES = {
    "name": "正式",
    "occasion_tags": ["正式", "商务", "通勤"],
    "required_slots": ["上衣", "裤子", "鞋子"],
    "preferred_keywords": {
        "上衣": ["衬衫", "西装", "polo"],
        "裤子": ["西裤", "直筒裤", "休闲裤", "烟管裤"],
        "外套": ["西装", "西装外套", "礼服", "风衣", "大衣"],
        "鞋子": ["皮鞋", "乐福鞋", "单鞋"],
    },
    "suggestions": ["白色衬衫", "深色直筒裤", "皮鞋"],
}

INTERVIEW_RULES = {
    "name": "面试",
    "occasion_tags": ["面试", "通勤"],
    "required_slots": ["上衣", "裤子", "鞋子"],
    "preferred_keywords": {
        "上衣": ["衬衫", "衬衣", "西装"],
        "裤子": ["西裤", "直筒裤"],
        "外套": ["西装", "西装外套"],
        "鞋子": ["皮鞋", "乐福鞋"],
    },
    "suggestions": ["白色衬衫", "深色西裤", "皮鞋"],
}

CLIENT_RULES = {
    "name": "客户拜访",
    "occasion_tags": ["客户", "商务", "通勤"],
    "required_slots": ["上衣", "裤子", "鞋子"],
    "preferred_keywords": {
        "上衣": ["衬衫", "衬衣", "西装"],
        "裤子": ["西裤", "直筒裤"],
        "外套": ["西装", "西装外套"],
        "鞋子": ["皮鞋", "乐福鞋"],
    },
    "suggestions": ["白色衬衫", "深色西裤", "皮鞋"],
}

WEDDING_RULES = {
    "name": "婚礼",
    "occasion_tags": ["婚礼", "婚宴", "宴会"],
    "required_slots": ["上衣", "裤子", "鞋子"],
    "preferred_keywords": {
        "上衣": ["礼服", "衬衫", "衬衣"],
        "裤子": ["西裤", "礼服裤"],
        "外套": ["西装", "礼服"],
        "鞋子": ["皮鞋", "乐福鞋"],
    },
    "suggestions": ["白色礼服衬衫", "黑色西裤", "皮鞋"],
}

DATE_RULES = {
    "name": "约会",
    "occasion_tags": ["约会"],
    "required_slots": ["上衣", "裤子", "鞋子"],
    "preferred_keywords": {
        "上衣": ["衬衫", "柔和色", "修身"],
        "裤子": ["直筒裤", "牛仔裤"],
        "外套": ["风衣", "针织开衫"],
        "鞋子": ["皮鞋", "乐福鞋", "单鞋"],
    },
    "suggestions": ["柔和色上衣", "直筒裤", "乐福鞋"],
}

SPORT_RULES = {
    "name": "运动",
    "occasion_tags": ["运动"],
    "required_slots": ["上衣", "裤子", "鞋子"],
    "preferred_keywords": {
        "上衣": ["运动", "速干", "卫衣"],
        "裤子": ["运动裤", "短裤"],
        "外套": ["运动外套"],
        "鞋子": ["运动鞋"],
    },
    "suggestions": ["速干上衣", "运动裤", "运动鞋"],
}

TRAVEL_RULES = {
    "name": "旅行",
    "occasion_tags": ["旅行"],
    "required_slots": ["上衣", "裤子", "鞋子"],
    "preferred_keywords": {
        "上衣": ["宽松", "防晒", "速干"],
        "裤子": ["休闲裤", "工装裤"],
        "外套": ["防晒衣", "冲锋衣"],
        "鞋子": ["运动鞋", "舒适鞋"],
    },
    "suggestions": ["宽松上衣", "休闲裤", "运动鞋"],
}

CAMPUS_RULES = {
    "name": "校园",
    "occasion_tags": ["校园"],
    "required_slots": ["上衣", "裤子", "鞋子"],
    "preferred_keywords": {
        "上衣": ["卫衣", "衬衫"],
        "裤子": ["休闲裤", "牛仔裤"],
        "鞋子": ["运动鞋"],
    },
    "suggestions": ["卫衣", "休闲裤", "运动鞋"],
}

SCENE_RULES = {
    "商务": FORMAL_RULES,
    "通勤": FORMAL_RULES,
    "正式": FORMAL_RULES,
    "客户": FORMAL_RULES,
    "面试": FORMAL_RULES,
    "会议": FORMAL_RULES,
    "婚礼": FORMAL_RULES,
    "宴会": FORMAL_RULES,
    "酒会": FORMAL_RULES,
    "约会": DATE_RULES,
    "运动": SPORT_RULES,
    "健身": SPORT_RULES,
    "跑步": SPORT_RULES,
    "爬山": SPORT_RULES,
    "旅行": TRAVEL_RULES,
    "出差": TRAVEL_RULES,
    "户外": TRAVEL_RULES,
    "露营": TRAVEL_RULES,
    "海边": TRAVEL_RULES,
    "校园": CAMPUS_RULES,
    "上学": CAMPUS_RULES,
}


def _slot_for_item(item: Dict[str, Any]) -> str:
    return CATEGORY_TO_SLOT.get(item.get("category"), item.get("category"))


def _item_text(item: Optional[Dict[str, Any]]) -> str:
    if not item:
        return ""
    return " ".join([
        str(item.get("name") or ""),
        str(item.get("category") or ""),
        " ".join(item.get("fit_tags") or []),
        str(item.get("style") or ""),
    ]).lower()


def _has_keyword(item: Optional[Dict[str, Any]], keywords: List[str]) -> bool:
    text = _item_text(item)
    return any(keyword.lower() in text for keyword in keywords)


def _find_rule(scene: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    candidates = list(scene.get("occasion_tags") or [])
    if scene.get("style"):
        candidates.append(scene["style"])
    for key in candidates:
        rule = SCENE_RULES.get(key)
        if rule:
            return rule
    return None


def _select_rule(scene: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    scene_type = scene.get("scene_type")
    if scene_type in {"婚礼", "婚宴"}:
        return WEDDING_RULES
    if scene_type == "面试":
        return INTERVIEW_RULES
    if scene_type in {"客户拜访", "商务洽谈"}:
        return CLIENT_RULES
    formality = scene.get("formality")
    if formality is not None and int(formality) >= 3:
        return FORMAL_RULES
    activity_level = scene.get("activity_level")
    if activity_level is not None and int(activity_level) >= 3:
        if scene.get("style") == "运动":
            return SPORT_RULES
    return _find_rule(scene)


def _occasion_matches(item_tags, scene_tags) -> bool:
    item_tags = {str(tag) for tag in (item_tags or [])}
    scene_tags = {str(tag) for tag in (scene_tags or [])}
    for item_tag in item_tags:
        for scene_tag in scene_tags:
            if item_tag in scene_tag or scene_tag in item_tag:
                return True
    return False


def _is_formal_item(item: Dict[str, Any]) -> bool:
    if item.get("category") in {"西装", "西裤"}:
        return True
    text = _item_text(item)
    text += " " + " ".join(item.get("occasion_tags") or [])
    formal_keywords = (
        "西装",
        "西服",
        "西裤",
        "衬衫",
        "衬衣",
        "礼服",
        "皮鞋",
        "乐福鞋",
        "单鞋",
    )
    if any(keyword in text for keyword in formal_keywords):
        return True
    formal_occasions = [
        "正式",
        "商务",
        "通勤",
        "工作",
        "婚礼",
        "宴会",
        "客户",
        "会议",
        "面试",
        "商务会议",
    ]
    return _occasion_matches(item.get("occasion_tags"), formal_occasions)


def apply_scene_constraints(
    scored_items: List[Dict[str, Any]],
    scene: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not scored_items or not scene:
        return scored_items

    formality = int(scene.get("formality") or 0)
    if formality < 3:
        return scored_items

    formal_slots = {
        _slot_for_item(item)
        for item in scored_items
        if _is_formal_item(item)
    }
    if formal_slots:
        scored_items = [
            item
            for item in scored_items
            if _slot_for_item(item) not in formal_slots or _is_formal_item(item)
        ]

    penalty = SCENE_NON_FORMAL_PENALTY
    if formality >= 4:
        penalty += 40

    for item in scored_items:
        if not _is_formal_item(item):
            item["score"] = item.get("score", 0) - penalty

    return scored_items


def apply_scene_preferences(
    scored_items: List[Dict[str, Any]],
    scene: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    if not scored_items or not scene:
        return scored_items

    rule = _select_rule(scene)
    if not rule:
        return scored_items

    scene_tags = list(scene.get("occasion_tags") or [])
    scene_tags.extend(rule.get("occasion_tags") or [])
    preferred_keywords = rule.get("preferred_keywords") or {}
    formality = int(scene.get("formality") or 0)
    occasion_bonus = (
        SCENE_HIGH_FORMALITY_OCCASION_BONUS
        if formality >= 3
        else SCENE_OCCASION_BONUS
    )

    for item in scored_items:
        bonus = 0
        if _occasion_matches(item.get("occasion_tags"), scene_tags):
            bonus += occasion_bonus

        slot = CATEGORY_TO_SLOT.get(item.get("category"), item.get("category"))
        keywords = preferred_keywords.get(slot, [])
        if keywords and _has_keyword(item, keywords):
            bonus += SCENE_PREFERRED_BONUS

        if bonus:
            item["score"] = item.get("score", 0) + bonus

    return scored_items


def build_scene_feedback(
    scene: Optional[Dict[str, Any]],
    outfit: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not scene or not outfit:
        return None

    rule = _select_rule(scene)
    if not rule:
        return None

    missing_slots = [
        slot
        for slot in rule["required_slots"]
        if not outfit.get(slot)
    ]
    suggestions = list(rule["suggestions"])

    preferred_missing = []
    for slot, keywords in rule["preferred_keywords"].items():
        if outfit.get(slot) and not _has_keyword(outfit[slot], keywords):
            preferred_missing.append(slot)

    if missing_slots:
        warning = (
            f"当前衣柜缺少{'、'.join(missing_slots)}，"
            f"我先用现有衣物生成方案。建议补充{'、'.join(suggestions)}。"
        )
    elif preferred_missing:
        warning = (
            f"当前搭配缺少更适合{rule['name']}场景的单品，"
            f"建议优先选择{'、'.join(suggestions)}。"
        )
    else:
        warning = None

    return {
        "warning": warning,
        "missing_slots": missing_slots,
        "suggestions": suggestions,
    }
