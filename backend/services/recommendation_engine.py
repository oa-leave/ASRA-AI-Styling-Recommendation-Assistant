"""
ASRA 推荐算法核心模块
功能：
1. 计算单件衣服推荐分数
2. 根据分类整理衣服
3. 自动组合最佳穿搭
当前版本：
ASRA V4.3 Recommendation Engine
未来升级：
接入：
- Weather Agent
- Scene Agent
- User Memory
- LangGraph Agent
"""
# ==================================
# 颜色匹配函数
# ==================================
def color_match(
        clothes_color,
        favorite_color
):
    """
    判断衣服颜色是否符合用户偏好
    """
    if not favorite_color:
        return False
    clothes_text = (clothes_color or "").lower()
    favorite_text = favorite_color.lower()
    color_groups = [
        ("黑", "black"),
        ("白", "white"),
        ("灰", "gray", "grey"),
        ("蓝", "blue"),
        ("红", "red"),
        ("绿", "green"),
        ("黄", "yellow"),
    ]
    for group in color_groups:
        if any(color in clothes_text for color in group) and any(
            color in favorite_text for color in group
        ):
            return True
    return False
# ==================================
# 计算衣服评分
# ==================================
def calculate_clothes_score(
        clothes,
        profile
):
    """
    单件衣服评分
    风格:
        +40
    季节:
        +30
    颜色:
        +30
    满分100
    """
    result = []
    # 获取用户画像
    if profile:
        user_style = profile.style
        user_season = profile.season
        favorite_color = profile.favorite_color
    else:
        user_style = None
        user_season = None
        favorite_color = None
    # 遍历衣柜
    for item in clothes:
        score = 0
        reasons = []
        # ==========================
        # 季节过滤
        # ==========================
        if (
            user_season
            and
            item.season != user_season
        ):
            continue
        # ==========================
        # 风格匹配
        # ==========================
        if (
            user_style
            and
            item.style == user_style
        ):
            score += 40
            reasons.append(
                "符合用户喜欢风格"
            )
        # ==========================
        # 季节匹配
        # ==========================
        if (
            user_season
            and
            item.season == user_season
        ):
            score += 30
            reasons.append(
                "适合当前季节"
            )
        # ==========================
        # 颜色匹配
        # ==========================
        if color_match(
            item.color,
            favorite_color
        ):
            score += 30
            reasons.append(
                "符合用户颜色偏好"
            )
        # 过滤低分
        if score <= 0:
            continue
        result.append({
            "id":
            item.id,
            "name":
            item.name,
            "category":
            item.category,
            "color":
            item.color,
            "style":
            item.style,
            "season":
            item.season,
            "score":
            score,
            "reason":
            reasons
        })
    return result
# ==================================
# 穿搭组合评分
# ==================================
def calculate_outfit_score(
        outfit
):
    """
    计算整体穿搭评分
    基础:
        单品分数相加
    加分:
        风格统一 +20
        黑白灰搭配 +20
    """
    score = 0
    reasons = []
    # ==========================
    # 单品基础分
    # ==========================
    for item in outfit.values():
        score += item["score"]
    styles = []
    colors = []
    for item in outfit.values():
        styles.append(
            item["style"]
        )
        colors.append(
            item["color"]
        )
    # ==========================
    # 风格统一
    # ==========================
    if len(outfit) >= 2 and len(set(styles)) == 1:
        score += 20
        reasons.append(
            "整体风格统一"
        )
    # ==========================
    # 黑白灰配色
    # ==========================
    neutral_colors = [
        "黑色",
        "白色",
        "灰色",
        "black",
        "white",
        "gray",
        "grey",
    ]
    count = 0
    for color in colors:
        if color in neutral_colors:
            count += 1
    if count >= 2:
        score += 20
        reasons.append(
            "颜色搭配协调"
        )
    return score, reasons
# ==================================
# 构建最佳穿搭
# ==================================
def build_best_outfit(
        clothes
):
    """
    根据评分结果组合最佳穿搭
    """
    categories = {
        "上衣": [],
        "裤子": [],
        "外套": [],
        "鞋子": []
    }
    # 分类
    for item in clothes:
        category = item["category"]
        if category in categories:
            categories[category].append(item)
    # 每类最高分排序
    for key in categories:
        categories[key].sort(
            key=lambda x:x["score"],
            reverse=True
        )
    outfit = {}
    reasons = []
    # 选择每类最高分
    for category, items in categories.items():
        if items:
            best = items[0]
            outfit[category] = best
            reasons.extend(
                best["reason"]
            )
    # ==========================
    # 计算整体穿搭评分
    # ==========================
    final_score, outfit_reasons = calculate_outfit_score(
        outfit
    )
    reasons.extend(
        outfit_reasons
    )
    # 去重
    reasons = list(set(reasons))
    return {
        "outfit":
        outfit,
        "score":
        final_score,
        "reason":
        reasons
    }
