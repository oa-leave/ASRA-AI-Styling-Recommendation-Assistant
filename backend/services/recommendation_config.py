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

CATEGORIES = [
    "内搭",
    "上衣",
    "裤子",
    "西裤",
    "裙子",
    "半身裙",
    "连衣裙",
    "旗袍",
    "汉服",
    "外套",
    "西装",
    "鞋子",
    "配饰",
    "帽子",
    "包包",
]
STYLES = [
    "休闲",
    "商务",
    "运动",
    "日系",
    "极简",
    "复古",
    "学院",
    "简约",
    "中式",
    "新中式",
]
SEASONS = ["春季", "夏季", "秋季", "冬季", "春秋", "四季"]
OCCASIONS = ["日常", "通勤", "约会", "运动", "旅行", "面试", "婚礼", "宴会", "会议"]
OUTFIT_SLOTS = [
    "内搭",
    "上衣",
    "裤子",
    "裙子",
    "连衣裙",
    "外套",
    "鞋子",
    "配饰",
    "帽子",
    "包包",
]

CATEGORY_TO_SLOT = {
    "半身裙": "裙子",
    "连衣裙": "连衣裙",
    "旗袍": "连衣裙",
    "汉服": "连衣裙",
    "西装": "外套",
    "西裤": "裤子",
}

ONEPIECE_SLOT = "连衣裙"

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
    {
        "name": "连衣裙/旗袍搭配",
        "slots": ["连衣裙"],
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

SEASON_CATEGORY_RULES = {
    "夏季": {
        "avoid_categories": ["外套"],
    },
    "冬季": {
        "required_categories": ["外套"],
    },
}

MEMORY_BONUS = {
    "liked_item": 5,
    "disliked_item": -30,
    "recent_item_penalty": -6,
    "favorite_style": 10,
    "favorite_color": 8,
}

RECENT_LIKED_COLOR_BONUS = 10

SCENE_SCORING = {
    "约会": {
        "fit_bonus": 20,
        "fit_keywords": ["合身", "修身"],
        "soft_color_bonus": 15,
        "soft_colors": ["粉色", "白色", "米色", "紫色", "浅蓝"],
        "shoes_bonus": 10,
        "shoes_keywords": ["皮鞋", "乐福鞋", "单鞋", "低跟鞋"],
        "sporty_penalty": 10,
        "sporty_keywords": ["运动鞋", "卫衣", "牛仔裤"],
    }
}

FORMAL_FALLBACK_BONUS = {
    "衬衫": 20,
    "Polo": 20,
    "POLO": 20,
    "polo": 20,
    "直筒裤": 15,
    "西裤": 20,
    "皮鞋": 15,
    "乐福鞋": 15,
}

FORMAL_FALLBACK_PENALTY = {
    "T恤": 10,
    "运动鞋": 15,
    "牛仔裤": 10,
}
