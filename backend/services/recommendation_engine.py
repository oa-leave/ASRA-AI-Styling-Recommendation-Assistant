import json
from itertools import product

from backend.services.recommendation_config import (
    CATEGORY_TO_SLOT,
    COLOR_CLASH_PAIRS,
    COLOR_GROUPS,
    COMPATIBILITY_PENALTIES,
    MAX_OUTFIT_CANDIDATES,
    MIN_OUTFIT_ITEMS,
    NEUTRAL_COLOR_GROUPS,
    ONEPIECE_SLOT,
    OUTFIT_BONUS,
    OUTFIT_SLOTS,
    REQUIRED_OUTFIT_SLOTS,
    SCORE_RULES,
    SEASON_CATEGORY_RULES,
    SEASON_CLASH_RULES,
)


def normalize_colors(colors):
    if not colors:
        return []
    if isinstance(colors, list):
        colors = " ".join(str(color) for color in colors)

    text = str(colors).lower()
    matches = []
    for name, aliases in COLOR_GROUPS.items():
        for alias in aliases:
            index = text.find(alias)
            if index != -1:
                matches.append((index, name))
                break
    matches.sort(key=lambda item: item[0])
    return list(dict.fromkeys(name for _, name in matches))


def normalize_tags(tags):
    if not tags:
        return []
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]
    if isinstance(tags, str):
        try:
            value = json.loads(tags)
            if isinstance(value, list):
                return [str(tag).strip() for tag in value if str(tag).strip()]
        except (ValueError, TypeError):
            pass
        return [tag.strip() for tag in tags.split(",") if tag.strip()]
    return []


def color_match(clothes_color, favorite_colors):
    if not clothes_color or not favorite_colors:
        return False
    clothes_group = _color_group_name(clothes_color)
    favorite_groups = normalize_colors(favorite_colors)
    return clothes_group in favorite_groups


def _color_group_name(color):
    if not color:
        return None
    text = color.lower()
    for name, aliases in COLOR_GROUPS.items():
        if any(alias in text for alias in aliases):
            return name
    return None


def normalize_color_tags(tags):
    tags = normalize_tags(tags)
    result = []
    seen = set()
    for tag in tags:
        for color in normalize_colors(tag):
            if color not in seen:
                seen.add(color)
                result.append(color)
    return result


def tag_overlap(item_tags, preference_tags):
    if not item_tags or not preference_tags:
        return set()
    return set(item_tags) & set(preference_tags)


def tag_match(item_tags, user_tags):
    if not item_tags or not user_tags:
        return 0
    return len(set(item_tags) & set(user_tags))


def _item_matches_keywords(item, keywords):
    if not keywords:
        return True
    text = (
        f"{item.get('name', '')} {item.get('category', '')}"
    ).lower()
    return any(str(keyword).lower() in text for keyword in keywords)


def calculate_clothes_score(clothes, profile, collect_filtered=False):
    filtered_reasons = []

    if profile:
        user_style = getattr(profile, "style", None)
        user_season = getattr(profile, "season", None)
        favorite_colors = normalize_colors(
            getattr(profile, "favorite_colors", None)
            or getattr(profile, "favorite_color", None)
        )
        user_style_tags = normalize_tags(getattr(profile, "style_tags", None))
        user_fit_tags = normalize_tags(getattr(profile, "fit_tags", None))
        avoid_colors = normalize_colors(getattr(profile, "avoid_colors", None) or [])
        user_occasions = normalize_tags(getattr(profile, "occasion_preferences", None))
    else:
        user_style = None
        user_season = None
        favorite_colors = []
        user_style_tags = []
        user_fit_tags = []
        avoid_colors = []
        user_occasions = []

    result = []
    for item in clothes:
        score = 0
        reasons = []
        item_style_tags = normalize_tags(getattr(item, "style_tags", None))
        item_color_tags = normalize_color_tags(getattr(item, "color_tags", None))
        item_fit_tags = normalize_tags(getattr(item, "fit_tags", None))
        item_occasion_tags = normalize_tags(getattr(item, "occasion_tags", None))

        item_color_group = _color_group_name(item.color)
        if item_color_group in avoid_colors:
            filtered_reasons.append(f"用户不喜欢{item.color}")
            continue

        if user_style and item.style == user_style:
            score += SCORE_RULES["style"]
            reasons.append("符合用户喜欢风格")

        style_score = tag_match(item_style_tags, user_style_tags)
        if style_score > 0:
            score += style_score * 10
            reasons.append("匹配用户风格标签")

        if user_season and item.season == user_season:
            score += SCORE_RULES["season"]
            reasons.append("适合当前季节")

        if color_match(item.color, favorite_colors):
            score += SCORE_RULES["color"]
            reasons.append("符合用户颜色偏好")

        color_score = tag_match(item_color_tags, favorite_colors)
        if color_score > 0:
            score += color_score * 10
            reasons.append("匹配用户颜色标签")

        occasion_score = tag_match(item_occasion_tags, user_occasions)
        if occasion_score > 0:
            score += occasion_score * SCORE_RULES["occasion"]
            reasons.append("符合使用场景")

        fit_score = tag_match(item_fit_tags, user_fit_tags)
        if fit_score > 0:
            score += fit_score * SCORE_RULES["fit"]
            reasons.append("符合身材版型偏好")

        if score <= 0:
            continue

        result.append({
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "color": item.color,
            "style": item.style,
            "season": item.season,
            "color_tags": item_color_tags,
            "style_tags": item_style_tags,
            "fit_tags": item_fit_tags,
            "occasion_tags": item_occasion_tags,
            "score": score,
            "reason": reasons,
        })
    if collect_filtered:
        return result, filtered_reasons
    return result


def calculate_outfit_score(outfit, profile=None):
    score = 0
    reasons = []

    for item in outfit.values():
        score += item["score"]

    if 0 < len(outfit) < MIN_OUTFIT_ITEMS:
        score -= COMPATIBILITY_PENALTIES["incomplete_outfit"]
        reasons.append("穿搭信息不足")

    styles = [item["style"] for item in outfit.values() if item.get("style")]
    colors = [item["color"] for item in outfit.values() if item.get("color")]

    if len(outfit) >= 2 and len(set(styles)) == 1:
        score += OUTFIT_BONUS["style_unified"]
        reasons.append("整体风格统一")
    elif len(outfit) >= 2 and len(set(styles)) > 1:
        score -= COMPATIBILITY_PENALTIES["style_mismatch"]
        reasons.append("整体风格不统一")

    outfit_keys = set(outfit.keys())
    for rule in REQUIRED_OUTFIT_SLOTS:
        if set(rule["slots"]).issubset(outfit_keys):
            score += rule["bonus"]
            reasons.append(f"核心穿搭完整（{rule['name']}）")
            break

    neutral_count = sum(
        1 for color in colors if _color_group_name(color) in NEUTRAL_COLOR_GROUPS
    )
    if neutral_count >= 2:
        score += OUTFIT_BONUS["neutral_colors"]
        reasons.append("颜色搭配协调")

    color_groups = {_color_group_name(color) for color in colors}
    for first, second in COLOR_CLASH_PAIRS:
        if first in color_groups and second in color_groups:
            score -= COMPATIBILITY_PENALTIES["color_clash"]
            reasons.append("颜色搭配冲突")

    if profile:
        season = getattr(profile, "season", None)
        if season:
            for rule in SEASON_CLASH_RULES:
                if season != rule["user_season"]:
                    continue
                for item in outfit.values():
                    if (
                        item.get("category") == rule["category"]
                        and item.get("season") in rule["item_seasons"]
                    ):
                        score -= rule["penalty"]
                        reasons.append("季节搭配不合理")

    return score, reasons


def filter_available_slots(categories, profile, force_slot=None):
    season = None
    if profile:
        season = getattr(profile, "season", None)

    season_rules = SEASON_CATEGORY_RULES.get(season, {})
    avoid_categories = season_rules.get("avoid_categories", [])
    forced_slots = set(force_slot or [])

    slots = []
    for key in OUTFIT_SLOTS:
        if not categories[key]:
            continue
        if key in avoid_categories and key not in forced_slots:
            continue
        slots.append(key)

    if categories.get(ONEPIECE_SLOT):
        slots = [
            slot
            for slot in slots
            if slot not in {"内搭", "上衣", "裤子", "裙子"}
        ]
    return slots


def generate_summary(
    outfit,
    reasons,
    profile=None,
    shoe_feedback=None,
    current_style=None,
):
    summary = []
    styles = {
        item.get("style")
        for item in outfit.values()
        if item.get("style")
    }

    if len(styles) == 1:
        style_name = next(iter(styles))
        if not current_style or current_style == style_name:
            summary.append(f"{style_name}风格")
    if "整体风格统一" in reasons:
        summary.append("整体风格统一")
    if "颜色搭配协调" in reasons:
        colors = list(dict.fromkeys(
            item.get("color")
            for item in outfit.values()
            if item.get("color")
        ))
        if colors:
            summary.append(f"{'/'.join(colors)}配色协调")
        else:
            summary.append("配色协调")
    if profile and getattr(profile, "season", None):
        summary.append(f"适合{profile.season}")
    if (
        profile
        and getattr(profile, "style", None)
        and (not current_style or profile.style == current_style)
    ):
        summary.append(f"用户喜欢{profile.style}风格")
    if any("核心穿搭完整" in reason for reason in reasons):
        shoe_status = (shoe_feedback or {}).get("status")
        if shoe_status == "suitable":
            summary.append("核心穿搭完整")
        elif shoe_status in {"fallback", "unsuitable"}:
            summary.append("鞋子不满足当前场景要求")
        else:
            summary.append("缺少鞋子")

    return summary


def build_top_outfits(
    clothes,
    profile=None,
    top_n=3,
    slot_style=None,
    force_slot=None,
    remove_slot=None,
    replace_slot=None,
    required_slot_keywords=None,
    allowed_slots=None,
):
    categories = {slot: [] for slot in OUTFIT_SLOTS}
    remove_slots = set(remove_slot or [])
    replace_map = replace_slot or {}

    for item in clothes:
        category = CATEGORY_TO_SLOT.get(item["category"], item["category"])
        category = replace_map.get(category, category)
        if category in categories and category not in remove_slots:
            categories[category].append(item)

    for slot, style in (slot_style or {}).items():
        if slot in categories:
            categories[slot] = [
                item
                for item in categories[slot]
                if item.get("style") == style
            ]

    for slot, keywords in (required_slot_keywords or {}).items():
        if slot in categories:
            categories[slot] = [
                item
                for item in categories[slot]
                if _item_matches_keywords(item, keywords)
            ]

    for key in OUTFIT_SLOTS:
        if categories[key]:
            categories[key].sort(key=lambda x: x["score"], reverse=True)
            categories[key] = categories[key][:MAX_OUTFIT_CANDIDATES]

    available_slots = filter_available_slots(categories, profile, force_slot)
    if allowed_slots:
        allowed_set = set(allowed_slots)
        available_slots = [
            slot
            for slot in available_slots
            if slot in allowed_set
        ]
    required_slots = set(force_slot or [])
    required_slots.update((required_slot_keywords or {}).keys())
    if required_slots and not required_slots.issubset(set(available_slots)):
        return [{
            "outfit": {},
            "score": 0,
            "reason": ["缺少指定搭配"],
        }]
    if not available_slots:
        return [{
            "outfit": {},
            "score": 0,
            "reason": ["没有找到合适穿搭"],
        }]

    candidates = [categories[key] for key in available_slots]
    scored_outfits = []
    for combo in product(*candidates):
        outfit = dict(zip(available_slots, combo))
        score, reasons = calculate_outfit_score(outfit, profile)
        scored_outfits.append({
            "outfit": outfit,
            "score": score,
            "reason": reasons,
        })

    scored_outfits.sort(key=lambda x: x["score"], reverse=True)
    return scored_outfits[:top_n]


def build_best_outfit(clothes, profile=None, required_slot_keywords=None):
    categories = {slot: [] for slot in OUTFIT_SLOTS}

    for item in clothes:
        category = CATEGORY_TO_SLOT.get(item["category"], item["category"])
        if category in categories:
            categories[category].append(item)

    for slot, keywords in (required_slot_keywords or {}).items():
        if slot in categories:
            categories[slot] = [
                item
                for item in categories[slot]
                if _item_matches_keywords(item, keywords)
            ]

    for key in OUTFIT_SLOTS:
        if categories[key]:
            categories[key].sort(key=lambda x: x["score"], reverse=True)
            categories[key] = categories[key][:MAX_OUTFIT_CANDIDATES]

    required_slots = set((required_slot_keywords or {}).keys())
    available_slots = filter_available_slots(
        categories,
        profile,
        list(required_slots) or None,
    )
    if required_slots and not required_slots.issubset(set(available_slots)):
        return {
            "outfit": {},
            "score": 0,
            "reason": ["缺少指定搭配"],
        }

    if not available_slots:
        final_score, _ = calculate_outfit_score({}, profile)
        return {
            "outfit": {},
            "score": final_score,
            "reason": ["没有找到合适穿搭"],
        }

    candidates = [categories[key] for key in available_slots]
    best_outfit = None
    best_score = None
    best_outfit_reasons = []

    for combo in product(*candidates):
        outfit = dict(zip(available_slots, combo))
        score, outfit_reasons = calculate_outfit_score(outfit, profile)
        if best_score is None or score > best_score:
            best_score = score
            best_outfit = outfit
            best_outfit_reasons = outfit_reasons

    if not best_outfit:
        return {
            "outfit": {},
            "score": 0,
            "reason": ["没有找到合适穿搭"],
        }

    reasons = []
    for item in best_outfit.values():
        reasons.extend(item.get("reason", []))
    reasons.extend(best_outfit_reasons)
    reasons = list(set(reasons))

    return {
        "outfit": best_outfit,
        "score": best_score,
        "reason": reasons,
    }
