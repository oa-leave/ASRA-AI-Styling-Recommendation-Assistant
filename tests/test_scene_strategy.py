import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.scene_strategy import (
    apply_scene_constraints,
    apply_scene_preferences,
    build_scene_feedback,
    build_shoe_feedback,
)


client = TestClient(app)


def _unique(name):
    return f"{name}_{uuid.uuid4().hex[:8]}"


def test_formal_scene_returns_missing_slots_and_suggestions():
    outfit = {
        "上衣": {"name": "灰色T恤", "category": "上衣"},
    }
    feedback = build_scene_feedback(
        {"style": "商务", "occasion_tags": ["通勤"]},
        outfit,
    )
    assert feedback["missing_slots"] == ["裤子", "鞋子"]
    assert "白色衬衫" in feedback["suggestions"]
    assert "当前衣柜缺少裤子、鞋子" in feedback["warning"]


def test_business_casual_constraints_respect_allowed_slots():
    scored = [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "score": 10,
        }
    ]
    scene = {
        "formality": 3,
        "scene_type": "日常",
        "occasion_tags": ["日常"],
    }

    result = apply_scene_constraints(
        scored,
        scene,
        allowed_slots={"上衣"},
    )
    assert result == scored


def test_strict_business_style_does_not_fallback_to_sneakers():
    scored = [
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "fit_tags": [],
            "style": "运动",
            "score": 10,
        }
    ]
    scene = {
        "formality": 3,
        "scene_type": "日常",
        "occasion_tags": ["日常"],
    }

    result = apply_scene_constraints(
        scored,
        scene,
        preferred_keywords=["鞋子"],
        allowed_slots={"鞋子"},
        strict_style=True,
    )
    assert result == []


def test_strict_sport_style_removes_non_sport_top():
    scored = [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "occasion_tags": ["运动"],
            "score": 10,
        }
    ]
    scene = {
        "style": "运动",
        "formality": 1,
        "scene_type": "日常",
        "occasion_tags": ["日常"],
    }

    result = apply_scene_constraints(
        scored,
        scene,
        preferred_keywords=["上衣"],
        allowed_slots={"上衣"},
        strict_style=True,
    )
    assert result == []


def test_strict_sport_style_keeps_sport_top():
    scored = [
        {
            "name": "速干T恤",
            "category": "上衣",
            "fit_tags": [],
            "style": "运动",
            "score": 10,
        }
    ]
    scene = {
        "style": "运动",
        "formality": 1,
        "scene_type": "日常",
        "occasion_tags": ["日常"],
    }

    result = apply_scene_constraints(
        scored,
        scene,
        preferred_keywords=["上衣"],
        allowed_slots={"上衣"},
        strict_style=True,
    )
    assert result == scored


def test_strict_sport_style_does_not_trust_style_tags():
    scored = [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "fit_tags": [],
            "style_tags": ["运动"],
            "style": "休闲",
            "score": 10,
        }
    ]
    scene = {
        "style": "运动",
        "formality": 1,
        "scene_type": "日常",
        "occasion_tags": ["日常"],
    }

    result = apply_scene_constraints(
        scored,
        scene,
        preferred_keywords=["上衣"],
        allowed_slots={"上衣"},
        strict_style=True,
    )
    assert result == []


def test_strict_high_formal_style_removes_casual_shirt():
    items = [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 10,
        },
        {
            "name": "白色衬衫",
            "category": "上衣",
            "fit_tags": [],
            "style": "商务",
            "occasion_tags": ["婚礼"],
            "score": 10,
        },
        {
            "name": "白色长袖衬衣",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "occasion_tags": ["婚礼"],
            "score": 10,
        },
    ]
    scene = {
        "style": "商务",
        "formality": 4,
        "scene_type": "婚礼",
        "occasion_tags": ["婚礼"],
    }

    result = apply_scene_constraints(
        items,
        scene,
        strict_style=True,
    )
    names = [item["name"] for item in result]
    assert names == ["白色衬衫"]


def test_medium_formal_allows_casual_shirt_with_business_tag():
    items = [
        {
            "name": "白色长袖衬衣",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "occasion_tags": ["商务会议", "工作"],
            "score": 10,
        }
    ]
    scene = {
        "style": "商务",
        "formality": 3,
        "scene_type": "客户拜访",
        "occasion_tags": ["客户", "通勤"],
    }

    result = apply_scene_constraints(
        items,
        scene,
        preferred_keywords=["上衣"],
        allowed_slots={"上衣"},
        formal_requested=True,
    )
    names = [item["name"] for item in result]
    assert names == ["白色长袖衬衣"]


def test_medium_formal_keeps_explicit_tshirt():
    items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 10,
        },
        {
            "name": "白色长袖衬衣",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "occasion_tags": ["商务会议"],
            "score": 10,
        },
    ]
    scene = {
        "style": "商务",
        "formality": 3,
        "scene_type": "客户拜访",
        "occasion_tags": ["客户", "通勤"],
    }

    result = apply_scene_constraints(
        items,
        scene,
        preferred_keywords=["T恤"],
        allowed_slots={"上衣"},
        formal_requested=True,
    )
    names = [item["name"] for item in result]
    assert "白色T恤" in names


def test_medium_formal_business_constraints_keep_explicit_tshirt():
    items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 10,
        },
        {
            "name": "白色长袖衬衣",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "occasion_tags": ["商务会议"],
            "score": 10,
        },
        {
            "name": "蓝色裤子",
            "category": "裤子",
            "fit_tags": [],
            "style": "修身",
            "occasion_tags": ["正式"],
            "score": 10,
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "fit_tags": [],
            "style": "商务",
            "occasion_tags": ["商务"],
            "score": 10,
        },
    ]
    scene = {
        "style": "商务",
        "formality": 3,
        "scene_type": "客户拜访",
        "occasion_tags": ["客户", "通勤"],
    }

    result = apply_scene_constraints(
        items,
        scene,
        preferred_keywords=["T恤"],
        formal_requested=True,
    )
    names = [item["name"] for item in result]
    assert "白色T恤" in names


def test_high_formal_does_not_allow_casual_shirt_with_business_tag():
    items = [
        {
            "name": "白色长袖衬衣",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "occasion_tags": ["商务会议", "婚礼"],
            "score": 10,
        }
    ]
    scene = {
        "style": "商务",
        "formality": 4,
        "scene_type": "婚礼",
        "occasion_tags": ["婚礼"],
    }

    result = apply_scene_constraints(
        items,
        scene,
        preferred_keywords=["上衣"],
        formal_requested=True,
    )
    assert result == []


def test_outdoor_style_removes_casual_top():
    items = [
        {
            "name": "蓝色衬衫",
            "category": "上衣",
            "fit_tags": [],
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 10,
        },
        {
            "name": "白色速干T恤",
            "category": "上衣",
            "fit_tags": ["速干"],
            "style": "运动",
            "occasion_tags": ["户外"],
            "score": 10,
        },
    ]
    scene = {
        "style": "运动",
        "formality": 1,
        "scene_type": "露营",
        "occasion_tags": ["露营"],
    }

    result = apply_scene_constraints(
        items,
        scene,
        preferred_keywords=["上衣"],
        allowed_slots={"上衣"},
    )
    names = [item["name"] for item in result]
    assert names == ["白色速干T恤"]


def test_complete_formal_outfit_has_no_warning():
    outfit = {
        "上衣": {"name": "白色衬衫", "category": "上衣"},
        "裤子": {"name": "深色直筒裤", "category": "裤子"},
        "鞋子": {"name": "黑色皮鞋", "category": "鞋子"},
    }
    feedback = build_scene_feedback(
        {"style": "商务", "occasion_tags": ["通勤"]},
        outfit,
    )
    assert feedback["missing_slots"] == []
    assert feedback["warning"] is None


def test_date_scene_uses_soft_and_formal_suggestions():
    outfit = {
        "上衣": {"name": "灰色T恤", "category": "上衣"},
        "裤子": {"name": "牛仔裤", "category": "裤子"},
        "鞋子": {"name": "运动鞋", "category": "鞋子"},
    }
    feedback = build_scene_feedback(
        {"style": "休闲", "occasion_tags": ["约会"]},
        outfit,
    )
    assert feedback["suggestions"] == ["柔和色上衣", "直筒裤", "乐福鞋"]
    assert feedback["warning"] is not None


def test_apply_scene_preferences_boosts_all_matching_slots():
    items = [
        {"name": "灰色T恤", "category": "上衣", "occasion_tags": ["日常"], "score": 100},
        {"name": "白色衬衫", "category": "上衣", "occasion_tags": ["商务会议"], "score": 100},
        {"name": "牛仔裤", "category": "裤子", "occasion_tags": ["日常"], "score": 100},
        {"name": "黑色西裤", "category": "裤子", "occasion_tags": ["通勤"], "score": 100},
        {"name": "白色运动鞋", "category": "鞋子", "occasion_tags": ["日常"], "score": 100},
        {"name": "黑色皮鞋", "category": "鞋子", "occasion_tags": ["商务"], "score": 100},
    ]
    adjusted = apply_scene_preferences(
        items,
        {"style": "商务", "occasion_tags": ["正式", "通勤"]},
    )
    scores = {item["name"]: item["score"] for item in adjusted}
    assert scores["白色衬衫"] > scores["灰色T恤"]
    assert scores["黑色西裤"] > scores["牛仔裤"]
    assert scores["黑色皮鞋"] > scores["白色运动鞋"]


def test_formal_constraints_prioritize_suit_over_tshirt():
    items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 100,
        },
        {
            "name": "黑色西装",
            "category": "西装",
            "style": "商务",
            "occasion_tags": ["正式", "商务"],
            "score": 70,
        },
    ]
    adjusted = apply_scene_constraints(
        items,
        {
            "style": "商务",
            "formality": 4,
            "scene_type": "客户拜访",
            "activity_level": 0,
        },
    )
    scores = {item["name"]: item["score"] for item in adjusted}
    assert scores["黑色西装"] > scores["白色T恤"]


def test_hard_constraint_removes_tshirt_when_formal_shirt_exists():
    items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 100,
        },
        {
            "name": "白色衬衫",
            "category": "上衣",
            "style": "商务",
            "occasion_tags": ["商务会议"],
            "score": 80,
        },
        {
            "name": "黑色西装",
            "category": "西装",
            "style": "商务",
            "occasion_tags": ["正式", "商务"],
            "score": 70,
        },
    ]
    adjusted = apply_scene_constraints(
        items,
        {
            "style": "商务",
            "formality": 4,
            "scene_type": "客户拜访",
            "activity_level": 0,
        },
    )
    names = [item["name"] for item in adjusted]
    assert "白色T恤" not in names
    assert "白色衬衫" in names
    assert "黑色西装" in names


def test_medium_formality_client_prefers_shirt_when_available():
    items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 100,
        },
        {
            "name": "白色衬衫",
            "category": "上衣",
            "style": "商务",
            "occasion_tags": ["商务会议"],
            "score": 80,
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "style": "商务",
            "occasion_tags": ["正式", "商务"],
            "score": 70,
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 90,
        },
    ]
    adjusted = apply_scene_constraints(
        items,
        {
            "style": "商务",
            "formality": 3,
            "scene_type": "客户拜访",
            "activity_level": 0,
        },
    )
    names = [item["name"] for item in adjusted]
    assert "白色T恤" not in names
    assert "白色衬衫" in names
    assert "灰色裤子" in names
    assert "蓝色西装" in names


def test_business_casual_rejects_only_casual_outfit():
    items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 100,
        },
        {
            "name": "蓝色牛仔裤",
            "category": "裤子",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 100,
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "style": "运动",
            "occasion_tags": ["日常"],
            "score": 100,
        },
    ]
    adjusted = apply_scene_constraints(
        items,
        {
            "style": "商务",
            "formality": 3,
            "scene_type": "客户拜访",
            "activity_level": 0,
        },
    )
    assert adjusted == []


def test_business_casual_preserves_explicit_preferred_tshirt():
    items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 100,
        },
        {
            "name": "白色衬衫",
            "category": "上衣",
            "style": "商务",
            "occasion_tags": ["商务会议"],
            "score": 80,
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 90,
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "style": "商务",
            "occasion_tags": ["正式", "商务"],
            "score": 70,
        },
    ]
    adjusted = apply_scene_constraints(
        items,
        {
            "style": "商务",
            "formality": 3,
            "scene_type": "客户拜访",
            "activity_level": 0,
        },
        preferred_keywords=["T恤"],
    )
    names = [item["name"] for item in adjusted]
    assert "白色T恤" in names
    assert "白色衬衫" in names
    assert "灰色裤子" in names
    assert "蓝色西装" in names


def test_business_casual_keeps_only_sneaker_when_no_better_shoe():
    items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 100,
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 90,
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "style": "运动",
            "occasion_tags": ["日常"],
            "score": 80,
        },
    ]
    adjusted = apply_scene_constraints(
        items,
        {
            "style": "商务",
            "formality": 3,
            "scene_type": "客户拜访",
            "activity_level": 0,
        },
        preferred_keywords=["T恤"],
    )
    names = [item["name"] for item in adjusted]
    assert "白色T恤" in names
    assert "灰色裤子" in names
    assert "白色运动鞋" in names


def test_sport_scene_prefers_sport_tagged_items():
    items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 100,
        },
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["日常", "运动"],
            "score": 70,
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "style": "运动",
            "occasion_tags": ["日常"],
            "score": 30,
        },
        {
            "name": "灰色运动鞋",
            "category": "鞋子",
            "style": "运动",
            "occasion_tags": ["运动", "Fitness"],
            "score": 30,
        },
    ]
    adjusted = apply_scene_preferences(
        items,
        {
            "style": "运动",
            "formality": 0,
            "activity_level": 3,
            "scene_type": "健身",
            "occasion_tags": ["运动"],
        },
    )
    scores = {item["name"]: item["score"] for item in adjusted}
    assert scores["灰色衬衫"] > scores["白色T恤"]
    assert scores["灰色运动鞋"] > scores["白色运动鞋"]


def test_sport_feedback_does_not_suggest_shoes_already_worn():
    outfit = {
        "上衣": {
            "name": "灰色衬衫",
            "category": "上衣",
            "occasion_tags": ["运动"],
        },
        "裤子": {"name": "灰色裤子", "category": "裤子"},
        "鞋子": {
            "name": "白色运动鞋",
            "category": "鞋子",
            "occasion_tags": ["运动"],
        },
    }
    feedback = build_scene_feedback(
        {
            "style": "运动",
            "formality": 0,
            "activity_level": 3,
            "scene_type": "健身",
            "occasion_tags": ["运动"],
        },
        outfit,
    )
    assert "运动鞋" not in "、".join(feedback["suggestions"])


def test_shoe_feedback_hiking_sneaker_is_fallback():
    feedback = build_shoe_feedback(
        {
            "style": "运动",
            "formality": 0,
            "activity_level": 3,
            "scene_type": "徒步登山",
            "occasion_tags": ["户外", "旅行"],
        },
        {"鞋子": {"name": "白色运动鞋", "category": "鞋子"}},
    )
    assert feedback["status"] == "fallback"
    assert feedback["suitable"] is False
    assert feedback["suggested_shoe"] == "防滑登山鞋"


def test_shoe_feedback_camping_sneaker_is_suitable():
    feedback = build_shoe_feedback(
        {
            "style": "休闲",
            "formality": 0,
            "activity_level": 2,
            "scene_type": "露营",
            "occasion_tags": ["户外", "旅行"],
        },
        {"鞋子": {"name": "白色运动鞋", "category": "鞋子"}},
    )
    assert feedback["status"] == "suitable"
    assert feedback["suitable"] is True


def test_shoe_feedback_rugged_camping_sneaker_is_fallback():
    feedback = build_shoe_feedback(
        {
            "style": "休闲",
            "formality": 0,
            "activity_level": 2,
            "scene_type": "露营",
            "occasion_tags": ["户外", "旅行"],
            "requires_hiking_shoes": True,
        },
        {"鞋子": {"name": "白色运动鞋", "category": "鞋子"}},
    )
    assert feedback["status"] == "fallback"
    assert feedback["suggested_shoe"] == "防滑登山鞋"


def test_shoe_feedback_beach_sneaker_is_unsuitable():
    feedback = build_shoe_feedback(
        {
            "style": "休闲",
            "formality": 0,
            "activity_level": 1,
            "scene_type": "海边",
            "occasion_tags": ["旅行", "海边"],
        },
        {"鞋子": {"name": "白色运动鞋", "category": "鞋子"}},
    )
    assert feedback["status"] == "unsuitable"
    assert feedback["suitable"] is False
    assert "凉鞋" in feedback["suggested_shoe"]


def test_shoe_feedback_interview_missing_formal_shoe():
    feedback = build_shoe_feedback(
        {
            "style": "商务",
            "formality": 3,
            "activity_level": 0,
            "scene_type": "面试",
            "occasion_tags": ["面试", "通勤"],
        },
        {"上衣": {"name": "白色衬衫", "category": "上衣"}},
    )
    assert feedback["status"] == "missing"
    assert feedback["has_shoe"] is False
    assert feedback["suggested_shoe"] == "皮鞋"


def test_shoe_feedback_fitness_sneaker_is_suitable():
    feedback = build_shoe_feedback(
        {
            "style": "运动",
            "formality": 0,
            "activity_level": 3,
            "scene_type": "健身",
            "occasion_tags": ["运动"],
        },
        {"鞋子": {"name": "灰色运动鞋", "category": "鞋子"}},
    )
    assert feedback["status"] == "suitable"
    assert feedback["suitable"] is True


def test_hiking_scene_feedback_warns_missing_hiking_shoes():
    feedback = build_scene_feedback(
        {
            "style": "运动",
            "formality": 0,
            "activity_level": 3,
            "scene_type": "徒步登山",
            "occasion_tags": ["户外", "旅行"],
        },
        {
            "上衣": {
                "name": "灰色衬衫",
                "category": "上衣",
                "occasion_tags": ["运动"],
            },
            "裤子": {"name": "灰色裤子", "category": "裤子"},
            "鞋子": {"name": "白色运动鞋", "category": "鞋子"},
        },
    )
    assert "防滑登山鞋" in feedback["warning"]


def test_casual_client_rules_do_not_prefer_suit():
    items = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 100,
        },
        {
            "name": "蓝色西装",
            "category": "西装",
            "style": "商务",
            "occasion_tags": ["正式", "商务"],
            "score": 100,
        },
    ]
    adjusted = apply_scene_preferences(
        items,
        {
            "style": "休闲",
            "formality": 2,
            "scene_type": "客户拜访",
            "occasion_tags": ["客户", "通勤"],
        },
    )
    scores = {item["name"]: item["score"] for item in adjusted}
    assert scores["白色T恤"] > scores["蓝色西装"]


def test_formal_scene_removes_non_formal_shoes():
    items = [
        {
            "name": "白色衬衫",
            "category": "上衣",
            "occasion_tags": ["商务会议"],
            "score": 100,
        },
        {
            "name": "蓝色西裤",
            "category": "裤子",
            "occasion_tags": ["通勤"],
            "score": 100,
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "occasion_tags": ["日常"],
            "score": 100,
        },
    ]
    adjusted = apply_scene_constraints(
        items,
        {
            "style": "商务",
            "formality": 3,
            "scene_type": "面试",
            "activity_level": 0,
        },
    )
    assert all(item["category"] != "鞋子" for item in adjusted)


def test_formal_feedback_uses_wardrobe_for_suggestions():
    outfit = {
        "上衣": {
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
        },
        "裤子": {"name": "灰色裤子", "category": "裤子"},
    }
    wardrobe = [
        {
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
            "occasion_tags": ["工作", "婚礼", "商务会议"],
        },
        {
            "name": "白色运动鞋",
            "category": "鞋子",
            "occasion_tags": ["日常"],
        },
    ]
    feedback = build_scene_feedback(
        {
            "style": "商务",
            "formality": 4,
            "scene_type": "客户拜访",
            "occasion_tags": ["通勤"],
        },
        outfit,
        wardrobe,
    )
    assert "白色衬衫" not in "、".join(feedback["suggestions"])
    assert "缺少正式皮鞋" in feedback["warning"]
    assert "缺少鞋子" not in feedback["warning"]


def test_wedding_scene_uses_wedding_suggestions():
    feedback = build_scene_feedback(
        {
            "style": "商务",
            "formality": 4,
            "scene_type": "婚礼",
            "occasion_tags": ["婚礼"],
        },
        {"上衣": {"name": "灰色T恤", "category": "上衣"}},
    )
    assert feedback["suggestions"] == ["白色礼服衬衫", "黑色西裤", "皮鞋"]


def test_high_formality_occassion_bonus_beats_user_preference():
    items = [
        {
            "name": "灰色衬衫",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["日常"],
            "score": 80,
        },
        {
            "name": "白色纯棉衬衣",
            "category": "上衣",
            "style": "休闲",
            "occasion_tags": ["商务会议"],
            "score": 40,
        },
    ]
    adjusted = apply_scene_preferences(
        items,
        {
            "style": "商务",
            "formality": 4,
            "occasion_tags": ["正式", "通勤"],
            "scene_type": "客户拜访",
        },
    )
    scores = {item["name"]: item["score"] for item in adjusted}
    assert scores["白色纯棉衬衣"] > scores["灰色衬衫"]


def test_agent_formal_response_includes_scene_feedback():
    username = _unique("formal_scene")
    client.post(
        "/user/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "password123",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色", "白色"],
            "avoid_colors": ["蓝色"],
        },
    )
    client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "商务",
            "fit_tags": ["标准"],
            "occasion_tags": ["商务会议"],
        },
    )

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={"city": "沈阳", "style": "商务", "query": "正式一点怎么穿"},
    )
    assert response.status_code == 200
    data = response.json()
    feedback = data["recommendation"]["scene_feedback"]
    assert feedback is not None
    assert "裤子" in feedback["missing_slots"]
    assert "鞋子" in feedback["missing_slots"]
    assert data["occasion"] == "正式"


def test_agent_formal_prefers_shirt_over_tshirt():
    username = _unique("formal_shirt")
    client.post(
        "/user/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "password123",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色", "白色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色T恤",
            "category": "上衣",
            "color": "灰色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["标准"],
            "occasion_tags": ["工作", "婚礼", "商务会议"],
        },
    ]:
        client.post("/wardrobe/add", headers=headers, json=item)

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={"city": "沈阳", "style": "商务", "query": "正式一点怎么穿"},
    )
    assert response.status_code == 200
    items = response.json()["recommendation"]["items"]
    assert any("衬衣" in item["name"] for item in items)


def test_formal_summer_includes_suit_despite_season():
    username = _unique("summer_suit")
    client.post(
        "/user/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "password123",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "黑色西装",
            "category": "西装",
            "color": "黑色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式", "商务"],
        },
    ]:
        client.post("/wardrobe/add", headers=headers, json=item)

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={"city": "沈阳", "style": "商务", "query": "正式一点怎么穿"},
    )
    assert response.status_code == 200
    items = response.json()["recommendation"]["items"]
    assert any("西装" in item["name"] for item in items)


def test_formal_scene_prefers_formal_pants_over_casual_pants():
    username = _unique("formal_pants")
    client.post(
        "/user/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "password123",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "灰色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "白色衬衫",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["商务会议"],
        },
        {
            "name": "灰色裤子",
            "category": "裤子",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["直筒"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "蓝色正式裤",
            "category": "裤子",
            "color": "蓝色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式"],
        },
        {
            "name": "黑色西装",
            "category": "西装",
            "color": "黑色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式", "商务"],
        },
    ]:
        client.post("/wardrobe/add", headers=headers, json=item)

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={"city": "沈阳", "style": "商务", "query": "正式一点怎么穿"},
    )
    assert response.status_code == 200
    items = response.json()["recommendation"]["items"]
    names = [item["name"] for item in items]
    assert "蓝色正式裤" in names
    assert "灰色裤子" not in names


def test_filtered_formal_items_explanation_mentions_avoid_colors():
    username = _unique("filtered_formal")
    client.post(
        "/user/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "password123",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "avoid_colors": ["黑色"],
        },
    )
    client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "黑色西装",
            "category": "西装",
            "color": "黑色",
            "season": "春季",
            "style": "商务",
            "fit_tags": ["修身"],
            "occasion_tags": ["正式", "商务"],
        },
    )

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={"city": "沈阳", "style": "商务"},
    )
    assert response.status_code == 200
    summary = response.json()["recommendation"]["summary"]
    assert not any("本次避开" in item for item in summary)
    assert not any("请取消" in item for item in summary)
    assert not any("缺少商务风格单品" in item for item in summary)
