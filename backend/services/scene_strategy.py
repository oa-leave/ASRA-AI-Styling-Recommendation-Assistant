"""场景约束与反馈。"""
from typing import Any, Dict, List, Optional

from backend.services.recommendation_config import CATEGORY_TO_SLOT


SCENE_OCCASION_BONUS = 20
SCENE_PREFERRED_BONUS = 10
SCENE_NON_FORMAL_PENALTY = 80
SCENE_HIGH_FORMALITY_OCCASION_BONUS = 60
SCENE_CASUAL_FORMAL_PENALTY = 50
SCENE_SPORT_OCCASION_BONUS = 40

SHOE_STATUS_SUITABLE = "suitable"
SHOE_STATUS_FALLBACK = "fallback"
SHOE_STATUS_UNSUITABLE = "unsuitable"
SHOE_STATUS_MISSING = "missing"

SHOE_REQUIREMENTS = {
    "徒步登山": {
        "required": ("登山鞋", "徒步鞋", "防滑鞋"),
        "suggested": "防滑登山鞋",
        "label": "防滑登山鞋",
    },
    "海边": {
        "required": ("凉鞋", "沙滩鞋", "防水鞋", "洞洞鞋"),
        "suggested": "凉鞋/沙滩鞋/防水鞋",
        "label": "海边鞋",
    },
}

BUSINESS_CASUAL_BAD_KEYWORDS = {
    "上衣": ("T恤", "卫衣", "背心", "吊带"),
    "裤子": ("牛仔裤", "运动裤", "短裤", "工装裤"),
    "鞋子": ("运动鞋", "帆布鞋", "凉鞋", "拖鞋"),
}

BUSINESS_CASUAL_GENERIC_KEYWORDS = {"上衣", "裤子", "鞋子", "外套"}


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
        "上衣": ["衬衫", "衬衣", "Polo"],
        "裤子": ["西裤", "直筒裤", "休闲裤", "烟管裤"],
        "外套": ["针织开衫", "风衣", "休闲西装"],
        "鞋子": ["乐福鞋", "皮鞋", "单鞋"],
    },
    "suggestions": ["白色衬衫或Polo", "直筒裤或休闲裤", "乐福鞋"],
}

CASUAL_RULES = {
    "name": "休闲",
    "occasion_tags": ["日常", "休闲"],
    "required_slots": ["上衣", "裤子", "鞋子"],
    "preferred_keywords": {
        "上衣": ["T恤", "卫衣", "Polo"],
        "裤子": ["休闲裤", "牛仔裤", "直筒裤"],
        "外套": ["针织开衫", "风衣", "牛仔外套"],
        "鞋子": ["运动鞋", "乐福鞋", "小白鞋"],
    },
    "suggestions": ["浅色T恤或Polo", "休闲裤或直筒裤", "运动鞋或乐福鞋"],
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

SUGGESTION_SLOT_HINTS = (
    ("上衣", ("衬衫", "衬衣", "上衣", "Polo")),
    ("裤子", ("裤",)),
    ("外套", ("外套", "风衣", "大衣")),
    ("鞋子", ("鞋",)),
)


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
    text += " " + " ".join(item.get("occasion_tags") or [])
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
    activity_level = scene.get("activity_level")
    if activity_level is not None and int(activity_level) >= 3:
        if scene.get("style") == "运动":
            return SPORT_RULES

    formality = scene.get("formality")
    if formality is not None:
        formality = int(formality)
        if formality >= 4:
            return FORMAL_RULES
        if formality == 3:
            return CLIENT_RULES
        rule = _find_rule(scene)
        if rule and rule is not FORMAL_RULES:
            return rule
        return CASUAL_RULES
    return _find_rule(scene)


def is_strict_formal_scene(scene: Dict[str, Any]) -> bool:
    if not scene:
        return False
    formality = int(scene.get("formality") or 0)
    if formality >= 4:
        return True
    return formality >= 3 and scene.get("scene_type") == "面试"


def _suggestion_slot(suggestion: str) -> Optional[str]:
    for slot, hints in SUGGESTION_SLOT_HINTS:
        if any(hint in suggestion for hint in hints):
            return slot
    return None


def _suggestion_keywords(suggestion: str) -> List[str]:
    parts = [
        part.strip()
        for part in suggestion.replace("或", "/").split("/")
        if part.strip()
    ]
    keywords = list(parts)
    if any("衬衫" in part or "衬衣" in part for part in parts):
        keywords.append("衬衣")
    if any("T恤" in part for part in parts):
        keywords.append("T恤")
    return keywords


def _has_preferred_item_for_slot(
    outfit: Dict[str, Any],
    wardrobe: Optional[List[Dict[str, Any]]],
    slot: str,
    keywords: List[str],
) -> bool:
    if outfit.get(slot) and _has_keyword(outfit[slot], keywords):
        return True
    return any(
        _slot_for_item(item) == slot and _has_keyword(item, keywords)
        for item in (wardrobe or [])
    )


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


def _matches_strict_formal_style(item: Dict[str, Any]) -> bool:
    return item.get("style") in {"商务", "正式"}


def _formal_tags_for_scene(scene: Optional[Dict[str, Any]]) -> set:
    scene_type = (scene or {}).get("scene_type") or ""
    if "客户" in scene_type or "商务" in scene_type or "会议" in scene_type:
        return {"商务会议", "工作", "商务", "会议", "客户", "正式"}
    if "面试" in scene_type:
        return {"工作", "面试", "商务", "正式"}
    return {"正式", "商务", "工作", "商务会议", "面试", "客户", "会议"}


def _matches_formal_request_style(
    item: Dict[str, Any],
    scene: Optional[Dict[str, Any]] = None,
) -> bool:
    if item.get("style") in {"商务", "正式"}:
        return True
    scene_type = (scene or {}).get("scene_type") or ""
    if _slot_for_item(item) == "上衣" and (
        not scene_type
        or scene_type in STRICT_FORMAL_SCENE_TYPES
        or scene_type not in MEDIUM_FORMAL_SCENE_TYPES
    ):
        return False
    formal_tags = _formal_tags_for_scene(scene)
    return bool(set(item.get("occasion_tags") or []) & formal_tags)


STRICT_FORMAL_SCENE_TYPES = {
    "婚礼",
    "宴会",
    "酒会",
    "正式活动",
    "毕业典礼",
    "商务宴会",
}

MEDIUM_FORMAL_SCENE_TYPES = {
    "客户拜访",
    "客户会议",
    "商务会谈",
    "面试",
    "会议",
    "普通通勤",
    "通勤",
    "汇报",
    "签约",
    "答辩",
    "入职",
}


def _is_high_formal_item(item: Dict[str, Any]) -> bool:
    if item.get("category") in {"西装", "西裤"}:
        return True
    text = _item_text(item)
    text += " " + " ".join(item.get("occasion_tags") or [])
    return any(
        keyword in text
        for keyword in ("西装", "西服", "礼服")
    )


def _is_business_casual_acceptable(item: Dict[str, Any], slot: str) -> bool:
    text = _item_text(item)
    return not any(
        keyword.lower() in text
        for keyword in BUSINESS_CASUAL_BAD_KEYWORDS.get(slot, ())
    )


def _matches_preferred_item(
    item: Dict[str, Any],
    preferred_keywords: Optional[List[str]],
) -> bool:
    if not preferred_keywords:
        return False
    text = (
        f"{item.get('name', '')} {item.get('category', '')}"
    ).lower()
    return any(
        keyword.lower() in text
        for keyword in preferred_keywords
    )


def _apply_business_casual_constraints(
    scored_items: List[Dict[str, Any]],
    preferred_keywords: Optional[List[str]] = None,
    allowed_slots: Optional[set] = None,
    strict_style: bool = False,
) -> List[Dict[str, Any]]:
    if not scored_items:
        return scored_items

    explicit_preferred = (
        [
            keyword
            for keyword in (preferred_keywords or [])
            if keyword not in BUSINESS_CASUAL_GENERIC_KEYWORDS
        ]
        if strict_style
        else preferred_keywords
    )
    for slot, bad_keywords in BUSINESS_CASUAL_BAD_KEYWORDS.items():
        slot_items = [
            item
            for item in scored_items
            if _slot_for_item(item) == slot
        ]
        has_acceptable = any(
            _is_business_casual_acceptable(item, slot)
            for item in slot_items
        )
        if has_acceptable and any(
            not _is_business_casual_acceptable(item, slot)
            for item in slot_items
        ):
            scored_items = [
                item
                for item in scored_items
                if _slot_for_item(item) != slot
                or _is_business_casual_acceptable(item, slot)
                or _matches_preferred_item(item, explicit_preferred)
            ]
        elif not has_acceptable and strict_style and slot_items:
            scored_items = [
                item
                for item in scored_items
                if _slot_for_item(item) != slot
                or _matches_preferred_item(item, explicit_preferred)
            ]

    required_slots = [
        slot
        for slot in ("上衣", "裤子")
        if not allowed_slots or slot in allowed_slots
    ]
    for slot in required_slots:
        if not any(
            _slot_for_item(item) == slot
            and (
                _is_business_casual_acceptable(item, slot)
                or _matches_preferred_item(item, explicit_preferred)
            )
            for item in scored_items
        ):
            return []

    return scored_items


SPORT_SCENE_TYPES = {
    "运动",
    "健身",
    "跑步",
    "篮球",
    "网球",
    "羽毛球",
    "瑜伽",
    "跳操",
}


def _apply_sport_style_constraints(
    scored_items: List[Dict[str, Any]],
    allowed_slots: Optional[set] = None,
    preferred_keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if not scored_items:
        return scored_items

    keywords_by_slot = SPORT_RULES["preferred_keywords"]
    slots_to_check = set(keywords_by_slot.keys())
    if allowed_slots:
        slots_to_check &= allowed_slots

    explicit_preferred = [
        keyword
        for keyword in (preferred_keywords or [])
        if keyword not in BUSINESS_CASUAL_GENERIC_KEYWORDS
    ]

    filtered = []
    for item in scored_items:
        slot = _slot_for_item(item)
        if slot not in slots_to_check:
            filtered.append(item)
            continue
        if any(
            keyword.lower() in _item_text(item)
            for keyword in keywords_by_slot.get(slot, [])
        ):
            filtered.append(item)
        elif _matches_preferred_item(item, explicit_preferred):
            filtered.append(item)

    required_slots = [
        slot
        for slot in ("上衣", "裤子", "鞋子")
        if not allowed_slots or slot in allowed_slots
    ]
    for slot in required_slots:
        if not any(_slot_for_item(item) == slot for item in filtered):
            return []

    return filtered


OUTDOOR_SCENE_TYPES = {
    "露营",
    "户外",
    "户外旅行",
    "登山",
    "徒步",
    "爬山",
}

OUTDOOR_STYLE_KEYWORDS = {
    "上衣": ("速干", "透气", "户外", "防晒", "冲锋衣", "运动"),
    "裤子": ("速干", "运动裤", "登山裤", "工装裤", "户外"),
    "鞋子": ("防滑", "登山鞋", "徒步鞋", "溯溪鞋", "运动鞋"),
}


def _apply_outdoor_style_constraints(
    scored_items: List[Dict[str, Any]],
    allowed_slots: Optional[set] = None,
    preferred_keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    if not scored_items:
        return scored_items

    slots_to_check = set(OUTDOOR_STYLE_KEYWORDS.keys())
    if allowed_slots:
        slots_to_check &= allowed_slots

    explicit_preferred = [
        keyword
        for keyword in (preferred_keywords or [])
        if keyword not in BUSINESS_CASUAL_GENERIC_KEYWORDS
    ]

    filtered = []
    for item in scored_items:
        slot = _slot_for_item(item)
        if slot not in slots_to_check:
            filtered.append(item)
            continue
        if any(
            keyword.lower() in _item_text(item)
            for keyword in OUTDOOR_STYLE_KEYWORDS.get(slot, [])
        ):
            filtered.append(item)
        elif _matches_preferred_item(item, explicit_preferred):
            filtered.append(item)

    required_slots = [
        slot
        for slot in ("上衣", "裤子", "鞋子")
        if not allowed_slots or slot in allowed_slots
    ]
    for slot in required_slots:
        if not any(_slot_for_item(item) == slot for item in filtered):
            return []

    return filtered


def apply_scene_constraints(
    scored_items: List[Dict[str, Any]],
    scene: Optional[Dict[str, Any]],
    preferred_keywords: Optional[List[str]] = None,
    allowed_slots: Optional[set] = None,
    strict_style: bool = False,
    formal_requested: bool = False,
    business_requested: bool = False,
) -> List[Dict[str, Any]]:
    if not scored_items or not scene:
        return scored_items

    if scene.get("scene_type") in OUTDOOR_SCENE_TYPES:
        return _apply_outdoor_style_constraints(
            scored_items,
            allowed_slots,
            preferred_keywords,
        )

    if scene.get("style") == "运动" and (
        strict_style
        or scene.get("scene_type") in SPORT_SCENE_TYPES
    ):
        return _apply_sport_style_constraints(
            scored_items,
            allowed_slots,
            preferred_keywords,
        )

    if business_requested and scene.get("style") == "商务":
        scored_items = [
            item
            for item in scored_items
            if item.get("style") in {"商务", "正式"}
        ]

    elif formal_requested and scene.get("style") == "商务":
        explicit_preferred = [
            keyword
            for keyword in (preferred_keywords or [])
            if keyword not in BUSINESS_CASUAL_GENERIC_KEYWORDS
        ]
        scored_items = [
            item
            for item in scored_items
            if (
                _matches_formal_request_style(item, scene)
                or _matches_preferred_item(item, explicit_preferred)
            )
        ]
    formality = int(scene.get("formality") or 0)
    if not is_strict_formal_scene(scene):
        if formality == 3:
            return _apply_business_casual_constraints(
                scored_items,
                preferred_keywords,
                allowed_slots,
                strict_style,
            )
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
            if (
                _slot_for_item(item) not in formal_slots
                or _is_formal_item(item)
                or _matches_preferred_item(item, preferred_keywords)
            )
        ]

    scored_items = [
        item
        for item in scored_items
        if (
            _slot_for_item(item) != "鞋子"
            or _is_formal_item(item)
            or _matches_preferred_item(item, preferred_keywords)
        )
    ]

    penalty = SCENE_NON_FORMAL_PENALTY
    if formality >= 4:
        penalty += 40

    for item in scored_items:
        if not _is_formal_item(item):
            item["score"] = item.get("score", 0) - penalty

    if (
        strict_style
        and formality >= 4
        and scene.get("scene_type") in STRICT_FORMAL_SCENE_TYPES
    ):
        scored_items = [
            item
            for item in scored_items
            if _matches_strict_formal_style(item)
        ]

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
    if rule is SPORT_RULES:
        occasion_bonus = SCENE_SPORT_OCCASION_BONUS
    elif formality >= 4:
        occasion_bonus = SCENE_HIGH_FORMALITY_OCCASION_BONUS
    else:
        occasion_bonus = SCENE_OCCASION_BONUS

    for item in scored_items:
        bonus = 0
        if _occasion_matches(item.get("occasion_tags"), scene_tags):
            bonus += occasion_bonus

        slot = CATEGORY_TO_SLOT.get(item.get("category"), item.get("category"))
        keywords = preferred_keywords.get(slot, [])
        if keywords and _has_keyword(item, keywords):
            bonus += SCENE_PREFERRED_BONUS

        if formality <= 2 and _is_high_formal_item(item):
            item["score"] = item.get("score", 0) - SCENE_CASUAL_FORMAL_PENALTY

        if bonus:
            item["score"] = item.get("score", 0) + bonus

    return scored_items


def build_scene_feedback(
    scene: Optional[Dict[str, Any]],
    outfit: Optional[Dict[str, Any]],
    wardrobe: Optional[List[Dict[str, Any]]] = None,
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
    suggestions = [
        suggestion
        for suggestion in rule["suggestions"]
        if not (
            (slot := _suggestion_slot(suggestion))
            and _has_preferred_item_for_slot(
                outfit,
                wardrobe,
                slot,
                _suggestion_keywords(suggestion),
            )
        )
    ]

    preferred_missing = []
    for slot, keywords in rule["preferred_keywords"].items():
        if outfit.get(slot) and not _has_keyword(outfit[slot], keywords):
            preferred_missing.append(slot)

    if missing_slots:
        if (
            "鞋子" in missing_slots
            and rule.get("name") in {"正式", "面试", "婚礼"}
            and wardrobe
            and any(_slot_for_item(item) == "鞋子" for item in wardrobe)
        ):
            warning = (
                "衣柜有运动鞋或休闲鞋，但缺少正式皮鞋；"
                "如果希望更正式，可以考虑补充皮鞋。"
            )
        else:
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

    shoe_feedback = build_shoe_feedback(scene, outfit)
    if (
        shoe_feedback
        and shoe_feedback.get("status") in {
            SHOE_STATUS_FALLBACK,
            SHOE_STATUS_UNSUITABLE,
        }
    ):
        shoe_warning = shoe_feedback.get("warning")
        if shoe_warning and shoe_warning not in (warning or ""):
            warning = "；".join(
                part for part in (warning, shoe_warning) if part
            )

    return {
        "warning": warning,
        "missing_slots": missing_slots,
        "suggestions": suggestions,
    }


def _shoe_requirement(scene: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not scene:
        return None
    scene_type = scene.get("scene_type") or ""
    if scene_type in SHOE_REQUIREMENTS:
        return SHOE_REQUIREMENTS[scene_type]
    if scene_type == "露营" and scene.get("requires_hiking_shoes"):
        return {
            "required": ("防滑鞋", "登山鞋", "徒步鞋"),
            "suggested": "防滑登山鞋",
            "label": "防滑登山鞋",
        }

    formality = int(scene.get("formality") or 0)
    strict_formal_types = {
        "面试",
        "婚礼",
        "宴会",
        "酒会",
        "签约仪式",
        "商务宴请",
        "正式活动",
        "毕业典礼",
    }
    if formality >= 4 or scene_type in strict_formal_types:
        return {
            "required": ("皮鞋", "乐福鞋", "单鞋", "低跟鞋"),
            "suggested": "皮鞋",
            "label": "正式皮鞋",
        }

    business_types = {
        "客户拜访",
        "商务洽谈",
        "客户会议",
        "会议",
        "演讲",
        "答辩",
        "汇报",
        "入职",
    }
    if formality == 3 or scene_type in business_types:
        return {
            "required": ("皮鞋", "乐福鞋", "单鞋", "低跟鞋"),
            "suggested": "乐福鞋",
            "label": "商务休闲鞋",
        }
    return None


def build_shoe_feedback(
    scene: Optional[Dict[str, Any]],
    outfit: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not scene or not outfit:
        return None

    shoe = outfit.get("鞋子")
    current_shoe = shoe.get("name") if shoe else None
    scene_type = scene.get("scene_type") or "日常"
    requirement = _shoe_requirement(scene)
    suggested = requirement["suggested"] if requirement else "运动鞋"
    label = requirement["label"] if requirement else "鞋子"

    base = {
        "scene_type": scene_type,
        "has_shoe": bool(shoe),
        "current_shoe": current_shoe,
        "suggested_shoe": suggested,
        "required_shoe": label if requirement else None,
        "status": None,
        "suitable": False,
        "reason": None,
        "warning": None,
    }

    if not shoe:
        reason = f"当前搭配缺少{label}，建议补充{suggested}。"
        return {
            **base,
            "status": SHOE_STATUS_MISSING,
            "reason": reason,
            "warning": reason,
        }

    if requirement and _has_keyword(shoe, requirement["required"]):
        reason = f"{current_shoe}适配{scene_type}场景。"
        return {
            **base,
            "status": SHOE_STATUS_SUITABLE,
            "suitable": True,
            "reason": reason,
            "warning": None,
        }

    if requirement:
        formality = int(scene.get("formality") or 0)
        if scene_type == "海边" or formality >= 4:
            status = SHOE_STATUS_UNSUITABLE
            reason = f"{current_shoe}不适合{scene_type}场景，建议更换{suggested}。"
        else:
            status = SHOE_STATUS_FALLBACK
            reason = (
                f"当前只有{current_shoe}，缺少{label}；"
                f"可临时使用，建议补充{suggested}。"
            )
        return {
            **base,
            "status": status,
            "reason": reason,
            "warning": reason,
        }

    reason = f"{current_shoe}适配{scene_type}场景。"
    return {
        **base,
        "status": SHOE_STATUS_SUITABLE,
        "suitable": True,
        "reason": reason,
        "warning": None,
    }
