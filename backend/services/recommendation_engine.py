from itertools import product

from backend.services.recommendation_config import (
    COLOR_CLASH_PAIRS,
    COLOR_GROUPS,
    COMPATIBILITY_PENALTIES,
    MAX_OUTFIT_CANDIDATES,
    MIN_OUTFIT_ITEMS,
    NEUTRAL_COLOR_GROUPS,
    OUTFIT_BONUS,
    OUTFIT_SLOTS,
    SCORE_RULES,
    SEASON_CLASH_RULES,
)


def normalize_colors(colors):
    if not colors:
        return []
    if isinstance(colors, list):
        return normalize_color_tags(colors)

    text = str(colors).lower()
    matches = []
    for name, aliases in COLOR_GROUPS.items():
        for alias in aliases:
            index = text.find(alias)
            if index != -1:
                matches.append((index, name))
                break
    matches.sort(key=lambda item: item[0])
    return [name for _, name in matches]


def color_match(clothes_color, favorite_colors):
    if not clothes_color or not favorite_colors:
        return False
    clothes_group = _color_group_name(clothes_color)
    return clothes_group in favorite_colors


def _color_group_name(color):
    if not color:
        return None
    text = color.lower()
    for name, aliases in COLOR_GROUPS.items():
        if any(alias in text for alias in aliases):
            return name
    return None


def normalize_color_tags(tags):
    if not tags:
        return []

    result = []
    for tag in tags:
        group = _color_group_name(tag)
        if group:
            result.append(group)
    return result


def tag_overlap(item_tags, preference_tags):
    if not item_tags or not preference_tags:
        return set()
    return set(item_tags) & set(preference_tags)


def tag_match(item_tags, user_tags):
    if not item_tags or not user_tags:
        return 0
    return len(set(item_tags) & set(user_tags))


def calculate_clothes_score(clothes, profile):
    if profile:
        user_style = getattr(profile, "style", None)
        user_season = getattr(profile, "season", None)
        favorite_colors = normalize_colors(
            getattr(profile, "favorite_colors", None)
            or getattr(profile, "favorite_color", None)
        )
        user_style_tags = getattr(profile, "style_tags", None) or []
        user_fit_tags = getattr(profile, "fit_tags", None) or []
        avoid_colors = normalize_colors(getattr(profile, "avoid_colors", None) or [])
        user_occasions = getattr(profile, "occasion_preferences", None) or []
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
        item_style_tags = getattr(item, "style_tags", None) or []
        item_color_tags = normalize_color_tags(
            getattr(item, "color_tags", None) or []
        )
        item_fit_tags = getattr(item, "fit_tags", None) or []
        item_occasion_tags = getattr(item, "occasion_tags", None) or []

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

        item_color_group = _color_group_name(item.color)
        if item_color_group in avoid_colors:
            continue

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


def build_best_outfit(clothes, profile=None):
    categories = {slot: [] for slot in OUTFIT_SLOTS}

    for item in clothes:
        category = item["category"]
        if category in categories:
            categories[category].append(item)

    available_slots = []
    for key in OUTFIT_SLOTS:
        if categories[key]:
            categories[key].sort(key=lambda x: x["score"], reverse=True)
            categories[key] = categories[key][:MAX_OUTFIT_CANDIDATES]
            available_slots.append(key)

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
