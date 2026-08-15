"""Structured scene lexicon for the rule-based Scene Agent."""
from typing import Any, Dict, Optional


CORE_SCENES = ["日常", "通勤", "约会", "运动", "旅行"]

SCENE_DEFAULTS = {
    "日常": {
        "occasion": "日常",
        "scene_type": "日常",
        "formality": 1,
        "activity_level": 1,
        "style": "休闲",
    },
    "通勤": {
        "occasion": "通勤",
        "scene_type": "普通通勤",
        "formality": 2,
        "activity_level": 1,
        "style": "商务",
    },
    "约会": {
        "occasion": "约会",
        "scene_type": "约会",
        "formality": 2,
        "activity_level": 1,
        "style": "休闲",
    },
    "运动": {
        "occasion": "运动",
        "scene_type": "运动",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "旅行": {
        "occasion": "旅行",
        "scene_type": "旅行",
        "formality": 1,
        "activity_level": 2,
        "style": "休闲",
    },
}

SCENE_ALIASES = {
    "明天见客户": {
        "occasion": "通勤",
        "scene_type": "客户拜访",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "见客户": {
        "occasion": "通勤",
        "scene_type": "客户拜访",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "客户": {
        "occasion": "通勤",
        "scene_type": "客户拜访",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "面试": {
        "occasion": "通勤",
        "scene_type": "面试",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "会议": {
        "occasion": "通勤",
        "scene_type": "会议",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "开会": {
        "occasion": "通勤",
        "scene_type": "会议",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "谈合作": {
        "occasion": "通勤",
        "scene_type": "商务洽谈",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "上班": {
        "occasion": "通勤",
        "scene_type": "普通通勤",
        "formality": 2,
        "activity_level": 1,
        "style": "商务",
    },
    "工作": {
        "occasion": "通勤",
        "scene_type": "普通通勤",
        "formality": 2,
        "activity_level": 1,
        "style": "商务",
    },
    "公司": {
        "occasion": "通勤",
        "scene_type": "办公室",
        "formality": 2,
        "activity_level": 1,
        "style": "商务",
    },
    "办公室": {
        "occasion": "通勤",
        "scene_type": "办公室",
        "formality": 2,
        "activity_level": 1,
        "style": "商务",
    },
    "通勤": {
        "occasion": "通勤",
        "scene_type": "普通通勤",
        "formality": 2,
        "activity_level": 1,
        "style": "商务",
    },
    "第一次约会": {
        "occasion": "约会",
        "scene_type": "第一次约会",
        "formality": 2,
        "activity_level": 1,
        "style": "休闲",
    },
    "见对象": {
        "occasion": "约会",
        "scene_type": "情侣约会",
        "formality": 2,
        "activity_level": 1,
        "style": "休闲",
    },
    "喜欢的人": {
        "occasion": "约会",
        "scene_type": "约会",
        "formality": 2,
        "activity_level": 1,
        "style": "休闲",
    },
    "约会": {
        "occasion": "约会",
        "scene_type": "约会",
        "formality": 2,
        "activity_level": 1,
        "style": "休闲",
    },
    "健身": {
        "occasion": "运动",
        "scene_type": "健身",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "跑步": {
        "occasion": "运动",
        "scene_type": "跑步",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "篮球": {
        "occasion": "运动",
        "scene_type": "球类",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "足球": {
        "occasion": "运动",
        "scene_type": "球类",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "羽毛球": {
        "occasion": "运动",
        "scene_type": "球类",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "瑜伽": {
        "occasion": "运动",
        "scene_type": "瑜伽",
        "formality": 0,
        "activity_level": 2,
        "style": "运动",
    },
    "运动": {
        "occasion": "运动",
        "scene_type": "运动",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "爬山": {
        "occasion": "旅行",
        "scene_type": "徒步登山",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "徒步": {
        "occasion": "旅行",
        "scene_type": "徒步",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "露营": {
        "occasion": "旅行",
        "scene_type": "露营",
        "formality": 0,
        "activity_level": 2,
        "style": "休闲",
    },
    "户外": {
        "occasion": "旅行",
        "scene_type": "户外旅行",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "出差": {
        "occasion": "旅行",
        "scene_type": "商务旅行",
        "formality": 2,
        "activity_level": 2,
        "style": "商务",
    },
    "旅游": {
        "occasion": "旅行",
        "scene_type": "旅行",
        "formality": 1,
        "activity_level": 2,
        "style": "休闲",
    },
    "旅行": {
        "occasion": "旅行",
        "scene_type": "旅行",
        "formality": 1,
        "activity_level": 2,
        "style": "休闲",
    },
    "婚礼": {
        "occasion": "日常",
        "scene_type": "婚礼",
        "formality": 4,
        "activity_level": 1,
        "style": "商务",
    },
    "宴会": {
        "occasion": "日常",
        "scene_type": "宴会",
        "formality": 4,
        "activity_level": 1,
        "style": "商务",
    },
    "酒会": {
        "occasion": "日常",
        "scene_type": "酒会",
        "formality": 4,
        "activity_level": 1,
        "style": "商务",
    },
    "逛街": {
        "occasion": "日常",
        "scene_type": "逛街",
        "formality": 0,
        "activity_level": 1,
        "style": "休闲",
    },
    "超市": {
        "occasion": "日常",
        "scene_type": "购物",
        "formality": 0,
        "activity_level": 1,
        "style": "休闲",
    },
    "买菜": {
        "occasion": "日常",
        "scene_type": "日常采购",
        "formality": 0,
        "activity_level": 1,
        "style": "休闲",
    },
    "商场": {
        "occasion": "日常",
        "scene_type": "逛街",
        "formality": 0,
        "activity_level": 1,
        "style": "休闲",
    },
    "咖啡": {
        "occasion": "日常",
        "scene_type": "咖啡",
        "formality": 1,
        "activity_level": 0,
        "style": "休闲",
    },
    "电影": {
        "occasion": "日常",
        "scene_type": "看电影",
        "formality": 1,
        "activity_level": 0,
        "style": "休闲",
    },
    "吃饭": {
        "occasion": "日常",
        "scene_type": "朋友聚餐",
        "formality": 1,
        "activity_level": 0,
        "style": "休闲",
    },
    "聚会": {
        "occasion": "日常",
        "scene_type": "社交聚会",
        "formality": 1,
        "activity_level": 1,
        "style": "休闲",
    },
    "在家": {
        "occasion": "日常",
        "scene_type": "居家",
        "formality": 0,
        "activity_level": 0,
        "style": "休闲",
    },
    "宅家": {
        "occasion": "日常",
        "scene_type": "居家",
        "formality": 0,
        "activity_level": 0,
        "style": "休闲",
    },
    "周末": {
        "occasion": "日常",
        "scene_type": "周末休闲",
        "formality": 1,
        "activity_level": 1,
        "style": "休闲",
    },
    "校园": {
        "occasion": "日常",
        "scene_type": "校园",
        "formality": 1,
        "activity_level": 2,
        "style": "学院",
    },
    "上学": {
        "occasion": "日常",
        "scene_type": "校园",
        "formality": 1,
        "activity_level": 2,
        "style": "学院",
    },
    "聚餐": {
        "occasion": "日常",
        "scene_type": "朋友聚餐",
        "formality": 1,
        "activity_level": 0,
        "style": "休闲",
    },
    "看电影": {
        "occasion": "日常",
        "scene_type": "看电影",
        "formality": 1,
        "activity_level": 0,
        "style": "休闲",
    },
    "葬礼": {
        "occasion": "日常",
        "scene_type": "葬礼",
        "formality": 4,
        "activity_level": 0,
        "style": "商务",
    },
    "商务宴请": {
        "occasion": "日常",
        "scene_type": "商务宴请",
        "formality": 4,
        "activity_level": 1,
        "style": "商务",
    },
    "客户会议": {
        "occasion": "通勤",
        "scene_type": "客户会议",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "签约": {
        "occasion": "通勤",
        "scene_type": "签约仪式",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "演讲": {
        "occasion": "通勤",
        "scene_type": "演讲",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "答辩": {
        "occasion": "通勤",
        "scene_type": "答辩",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "汇报": {
        "occasion": "通勤",
        "scene_type": "汇报",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "培训": {
        "occasion": "通勤",
        "scene_type": "培训",
        "formality": 2,
        "activity_level": 1,
        "style": "商务",
    },
    "朋友聚会": {
        "occasion": "日常",
        "scene_type": "朋友聚会",
        "formality": 1,
        "activity_level": 1,
        "style": "休闲",
    },
    "家庭聚会": {
        "occasion": "日常",
        "scene_type": "家庭聚会",
        "formality": 1,
        "activity_level": 1,
        "style": "休闲",
    },
    "购物": {
        "occasion": "日常",
        "scene_type": "购物",
        "formality": 0,
        "activity_level": 1,
        "style": "休闲",
    },
    "散步": {
        "occasion": "日常",
        "scene_type": "散步",
        "formality": 0,
        "activity_level": 2,
        "style": "休闲",
    },
    "打球": {
        "occasion": "运动",
        "scene_type": "球类",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "周末打球": {
        "occasion": "运动",
        "scene_type": "球类",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "周末去打球": {
        "occasion": "运动",
        "scene_type": "球类",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "户外活动": {
        "occasion": "旅行",
        "scene_type": "户外活动",
        "formality": 0,
        "activity_level": 3,
        "style": "运动",
    },
    "入职": {
        "occasion": "通勤",
        "scene_type": "入职",
        "formality": 3,
        "activity_level": 0,
        "style": "商务",
    },
    "毕业典礼": {
        "occasion": "日常",
        "scene_type": "毕业典礼",
        "formality": 3,
        "activity_level": 1,
        "style": "商务",
    },
    "正式活动": {
        "occasion": "日常",
        "scene_type": "正式活动",
        "formality": 4,
        "activity_level": 1,
        "style": "商务",
    },
}

FORMALITY_WORDS = {
    3: ["正式", "商务", "职业", "专业", "客户", "面试", "会议", "谈判", "合同"],
    4: ["庄重", "高正式", "婚礼", "婚宴", "宴会", "酒会"],
}

ACTIVITY_WORDS = {
    2: ["旅行", "出差", "逛街", "户外", "露营", "徒步", "爬山", "周末"],
    3: ["运动", "健身", "跑步", "球", "瑜伽", "爬山", "徒步"],
}


def resolve_scene(
    text: str = "",
    occasion: Optional[str] = None,
    style: Optional[str] = None,
) -> Dict[str, Any]:
    """Return structured scene fields from natural language or defaults."""
    text = text or ""
    matched = None
    for alias in sorted(SCENE_ALIASES, key=len, reverse=True):
        if alias in text:
            if alias == "运动" and any(
                marker in text
                for marker in ("运动风", "运动风格", "运动款", "运动穿搭", "运动装")
            ):
                continue
            matched = SCENE_ALIASES[alias]
            break

    if matched and occasion not in CORE_SCENES:
        scene = dict(matched)
    else:
        base = occasion if occasion in CORE_SCENES else "日常"
        scene = dict(SCENE_DEFAULTS[base])

    if style:
        scene["style"] = style
    negative_casual_markers = (
        "不要休闲",
        "不想穿休闲",
        "别休闲",
        "不穿休闲",
        "不要休闲风",
        "不想穿休闲风",
    )
    if any(
        marker in text
        for marker in negative_casual_markers
    ) and any(
        marker in text
        for marker in ("正式", "商务", "职场")
    ):
        scene["style"] = "商务"
    if scene.get("style") == "商务" and any(
        marker in text
        for marker in ("休闲", "舒服", "轻松", "不要太正式", "别太正式")
    ) and not any(
        marker in text
        for marker in negative_casual_markers
    ):
        scene["style"] = "休闲"

    formality = int(scene.get("formality", 1))
    for level, words in FORMALITY_WORDS.items():
        if any(word in text for word in words):
            formality = max(formality, level)
    if style == "商务":
        formal_context = f"{text} {occasion or ''}"
        if any(word in formal_context for word in FORMALITY_WORDS[3]):
            formality = max(formality, 3)
        formality = max(formality, 2)
    if any(word in text for word in ("正式一点", "正式些", "正式一些", "严肃一点")):
        formality += 1
    if any(
        word in text
        for word in (
            "不要太严肃",
            "不要太正式",
            "休闲一点",
            "别太正式",
            "别太严肃",
            "轻松一点",
            "休闲些",
        )
    ):
        formality = max(1, formality - 1)
    if any(word in text for word in ("不要太正式", "别太正式")):
        formality = min(formality, 2)
    if "T恤" in text and "正式" in text:
        formality = min(formality, 3)
    scene["formality"] = formality

    activity_level = int(scene.get("activity_level", 1))
    for level, words in ACTIVITY_WORDS.items():
        if any(word in text for word in words):
            activity_level = max(activity_level, level)
    scene["activity_level"] = activity_level

    if scene.get("scene_type") == "露营" and any(
        word in text
        for word in ("徒步", "崎岖", "爬山", "远足", "雨天", "长距离")
    ):
        scene["requires_hiking_shoes"] = True

    return scene
