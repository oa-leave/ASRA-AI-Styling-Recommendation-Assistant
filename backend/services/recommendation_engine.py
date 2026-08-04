from backend.services.recommendation_config import (
    COLOR_GROUPS,
    NEUTRAL_COLORS,
    OUTFIT_BONUS,
    OUTFIT_SLOTS,
    SCORE_RULES,
)


def color_match(clothes_color, favorite_color):
    if not favorite_color:
        return False
    clothes_text = (clothes_color or "").lower()
    favorite_text = favorite_color.lower()
    for aliases in COLOR_GROUPS.values():
        if any(alias in clothes_text for alias in aliases) and any(
            alias in favorite_text for alias in aliases
        ):
            return True
    return False


def tag_overlap(item_tags, preference_tags):
    if not item_tags or not preference_tags:
        return set()
    return set(item_tags) & set(preference_tags)


def tag_match(item_tags, user_tags):
    if not item_tags or not user_tags:
        return 0
    return sum(1 for tag in item_tags if tag in user_tags)


def calculate_clothes_score(clothes, profile):
    if profile:
        user_style = getattr(profile, "style", None)
        user_season = getattr(profile, "season", None)
        favorite_color = getattr(profile, "favorite_color", None)
        favorite_colors = getattr(profile, "favorite_colors", None) or []
        user_style_tags = getattr(profile, "style_tags", None) or []
    else:
        user_style = None
        user_season = None
        favorite_color = None
        favorite_colors = []
        user_style_tags = []

    result = []
    for item in clothes:
        score = 0
        reasons = []
        item_style_tags = getattr(item, "style_tags", None) or []
        item_color_tags = getattr(item, "color_tags", None) or []

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

        if color_match(item.color, favorite_color):
            score += SCORE_RULES["color"]
            reasons.append("符合用户颜色偏好")

        color_score = tag_match(item_color_tags, favorite_colors)
        if color_score > 0:
            score += color_score * 10
            reasons.append("匹配用户颜色标签")

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
            "fit_tags": getattr(item, "fit_tags", None) or [],
            "score": score,
            "reason": reasons,
        })
    return result


def calculate_outfit_score(outfit):
    score = 0
    reasons = []

    for item in outfit.values():
        score += item["score"]

    styles = [item["style"] for item in outfit.values()]
    colors = [item["color"] for item in outfit.values()]

    if len(outfit) >= 2 and len(set(styles)) == 1:
        score += OUTFIT_BONUS["style_unified"]
        reasons.append("整体风格统一")

    neutral_count = sum(1 for color in colors if color in NEUTRAL_COLORS)
    if neutral_count >= 2:
        score += OUTFIT_BONUS["neutral_colors"]
        reasons.append("颜色搭配协调")

    return score, reasons


def build_best_outfit(clothes):
    categories = {slot: [] for slot in OUTFIT_SLOTS}

    for item in clothes:
        category = item["category"]
        if category in categories:
            categories[category].append(item)

    for key in categories:
        categories[key].sort(key=lambda x: x["score"], reverse=True)

    outfit = {}
    reasons = []
    for category, items in categories.items():
        if items:
            best = items[0]
            outfit[category] = best
            reasons.extend(best["reason"])

    final_score, outfit_reasons = calculate_outfit_score(outfit)
    reasons.extend(outfit_reasons)
    reasons = list(set(reasons))

    return {
        "outfit": outfit,
        "score": final_score,
        "reason": reasons,
    }
