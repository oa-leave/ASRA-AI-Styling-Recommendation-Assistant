COLOR_GROUPS = {
    "白色": ["白", "white"],
    "黑色": ["黑", "black"],
    "灰色": ["灰", "gray", "grey"],
    "蓝色": ["蓝", "blue"],
    "红色": ["红", "red"],
    "绿色": ["绿", "green"],
    "黄色": ["黄", "yellow"],
    "粉色": ["粉", "pink"],
    "紫色": ["紫", "purple"],
    "橙色": ["橙", "orange"],
    "棕色": ["棕", "brown"],
    "米色": ["米", "beige"],
}

CATEGORIES = ["内搭", "上衣", "裤子", "外套", "鞋子", "裙子", "配饰"]
STYLES = ["休闲", "商务", "运动", "日系", "街头", "极简"]
SEASONS = ["春季", "夏季", "秋季", "冬季", "春秋", "四季"]
OCCASIONS = ["通勤", "约会", "运动", "旅行", "日常"]
OUTFIT_SLOTS = ["内搭", "上衣", "裤子", "外套", "鞋子", "配饰"]

NEUTRAL_COLOR_GROUPS = ["黑色", "白色", "灰色"]

MAX_OUTFIT_CANDIDATES = 5

SCORE_RULES = {
    "style": 40,
    "season": 30,
    "color": 30,
    "fit": 20,
    "occasion": 30,
    "avoid_color": 30,
}

OUTFIT_BONUS = {
    "style_unified": 20,
    "neutral_colors": 20,
}

REQUIRED_OUTFIT_SLOTS = [
    {
        "name": "裤装搭配",
        "slots": ["上衣", "裤子"],
        "bonus": 20,
    },
    {
        "name": "裙装搭配",
        "slots": ["上衣", "裙子"],
        "bonus": 20,
    },
]

COMPATIBILITY_PENALTIES = {
    "style_mismatch": 10,
    "color_clash": 20,
    "season_clash": 30,
    "incomplete_outfit": 20,
}

MIN_OUTFIT_ITEMS = 2

COLOR_CLASH_PAIRS = [("红色", "绿色")]

SEASON_CLASH_RULES = [
    {
        "user_season": "夏季",
        "category": "外套",
        "item_seasons": ["冬季", "秋冬"],
        "penalty": 30,
    },
    {
        "user_season": "冬季",
        "category": "裤子",
        "item_seasons": ["夏季"],
        "penalty": 30,
    },
]
