from backend.services.recommend_service import (
    _apply_required_item_keywords,
    _apply_knowledge_rules,
    _apply_memory_adjustments,
    _apply_formal_fallback_adjustments,
    _apply_recent_liked_color_bonus,
    _apply_scene_scoring,
    _apply_weather_adjustments,
    _filter_excluded_keywords,
)


def test_memory_adjustments():
    scored = [
        {"name": "白色T恤", "score": 100},
        {"name": "黑色西服", "score": 80},
    ]
    memory = {
        "feedback_summary": {
            "recent": [
                {
                    "feedback_type": "like",
                    "outfit_snapshot": {"上衣": "白色T恤"},
                },
                {
                    "feedback_type": "dislike",
                    "outfit_snapshot": {"上衣": "黑色西服"},
                },
            ]
        }
    }

    adjusted = _apply_memory_adjustments(scored, memory)
    assert adjusted[0]["score"] == 105
    assert adjusted[1]["score"] == 50


def test_memory_adjustments_without_memory():
    scored = [{"name": "白色T恤", "score": 100}]
    adjusted = _apply_memory_adjustments(scored, None)
    assert adjusted[0]["score"] == 100


def test_memory_style_color_adjustments():
    scored = [
        {
            "name": "日系衬衫",
            "style": "日系",
            "color": "白色",
            "score": 100,
        }
    ]
    memory = {
        "preference_signals": {
            "favorite_styles": ["日系"],
            "favorite_colors": ["白色"],
        }
    }

    adjusted = _apply_memory_adjustments(scored, memory)
    assert adjusted[0]["score"] == 118


def test_recent_item_names_penalize_repeat():
    scored = [
        {"name": "白色T恤", "score": 100},
        {"name": "灰色裤子", "score": 90},
    ]
    memory = {
        "preference_signals": {
            "recent_item_names": ["白色T恤"],
        }
    }
    adjusted = _apply_memory_adjustments(scored, memory)
    assert adjusted[0]["score"] == 94
    assert adjusted[1]["score"] == 90


def test_filter_excluded_keywords():
    scored = [
        {"name": "白色短袖T恤", "category": "上衣", "score": 100},
        {"name": "白色衬衫", "category": "上衣", "score": 90},
    ]
    filtered = _filter_excluded_keywords(scored, ["短袖"])
    assert len(filtered) == 1
    assert filtered[0]["name"] == "白色衬衫"


def test_formal_fallback_boosts_formal_items():
    scored = [
        {"name": "白色T恤", "category": "上衣", "fit_tags": [], "score": 100},
        {"name": "白色衬衫", "category": "上衣", "fit_tags": [], "score": 80},
    ]
    adjusted = _apply_formal_fallback_adjustments(scored)
    assert adjusted[1]["score"] > adjusted[0]["score"]


def test_formal_fallback_does_not_penalize_preferred_tshirt():
    scored = [
        {"name": "白色T恤", "category": "上衣", "fit_tags": [], "score": 90},
        {"name": "白色衬衫", "category": "上衣", "fit_tags": [], "score": 80},
    ]
    adjusted = _apply_formal_fallback_adjustments(scored, ["T恤"])
    assert adjusted[0]["score"] == 90
    assert adjusted[1]["score"] == 100


def test_scene_scoring_date_prefers_formal_and_soft():
    scored = [
        {
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "fit_tags": ["宽松"],
            "score": 100,
        },
        {
            "name": "修身衬衫",
            "category": "上衣",
            "color": "白色",
            "fit_tags": ["修身"],
            "score": 90,
        },
        {
            "name": "灰色运动鞋",
            "category": "鞋子",
            "color": "灰色",
            "fit_tags": [],
            "score": 90,
        },
    ]
    adjusted = _apply_scene_scoring(scored, {"occasion_tags": ["约会"]})
    assert adjusted[1]["score"] > adjusted[0]["score"]
    assert adjusted[2]["score"] < 90


def test_recent_liked_color_bonus():
    scored = [
        {"name": "蓝色衬衫", "color": "蓝色", "score": 100},
        {"name": "白色T恤", "color": "白色", "score": 100},
    ]
    adjusted = _apply_recent_liked_color_bonus(
        scored,
        {"liked_colors": ["蓝色"]},
    )
    assert adjusted[0]["score"] == 110
    assert adjusted[1]["score"] == 100


def test_knowledge_rules_add_score_to_matching_items():
    scored = [
        {
            "name": "白色衬衫",
            "category": "上衣",
            "season": "夏季",
            "style": "商务",
            "color_tags": ["白色"],
            "style_tags": [],
            "occasion_tags": [],
            "score": 100,
        }
    ]
    rules = [{"tags": ["夏季", "透气"]}]
    adjusted = _apply_knowledge_rules(scored, rules)
    assert adjusted[0]["score"] == 105


def test_required_item_keywords_filter_top_and_force_slots():
    scored = [
        {"name": "白色T恤", "category": "上衣", "score": 100},
        {"name": "白色衬衫", "category": "上衣", "score": 90},
        {"name": "蓝色裤子", "category": "裤子", "score": 80},
    ]

    filtered, missing, forced_slots, required_slot_keywords = (
        _apply_required_item_keywords(
            scored,
            ["衬衫", "裤子"],
        )
    )
    names = [item["name"] for item in filtered]
    assert missing == []
    assert forced_slots == {"上衣", "裤子"}
    assert required_slot_keywords == {
        "上衣": ["衬衫"],
        "裤子": ["裤子"],
    }
    assert "白色衬衫" in names
    assert "蓝色裤子" in names
    assert "白色T恤" not in names


def test_required_item_keywords_missing_returns_reason():
    scored = [
        {"name": "白色T恤", "category": "上衣", "score": 100},
        {"name": "蓝色裤子", "category": "裤子", "score": 80},
    ]

    filtered, missing, forced_slots, required_slot_keywords = (
        _apply_required_item_keywords(
            scored,
            ["衬衫"],
        )
    )
    assert missing == ["衬衫"]
    assert filtered


def test_required_xiku_is_not_satisfied_by_jeans():
    scored = [
        {"name": "灰色衬衫", "category": "上衣", "score": 90},
        {"name": "蓝色牛仔裤", "category": "裤子", "score": 80},
    ]

    filtered, missing, forced_slots, required_slot_keywords = (
        _apply_required_item_keywords(
            scored,
            ["西裤", "衬衫"],
        )
    )
    assert missing == ["西裤"]
    assert forced_slots == {"上衣"}
    assert required_slot_keywords == {"上衣": ["衬衫"]}


def test_required_long_sleeve_maps_to_top():
    scored = [
        {
            "name": "白色长袖衬衣",
            "category": "上衣",
            "score": 90,
        }
    ]

    filtered, missing, forced_slots, required_slot_keywords = (
        _apply_required_item_keywords(
            scored,
            ["长袖"],
        )
    )
    assert missing == []
    assert forced_slots == {"上衣"}
    assert required_slot_keywords == {"上衣": ["长袖"]}


def test_weather_adjustments_prefer_long_sleeve_in_rain():
    scored = [
        {
            "name": "白色长袖衬衫",
            "category": "上衣",
            "fit_tags": [],
            "score": 100,
        },
        {
            "name": "白色短袖T恤",
            "category": "上衣",
            "fit_tags": [],
            "score": 100,
        },
    ]
    adjusted = _apply_weather_adjustments(
        scored,
        {"temperature": 27, "weather": "毛毛雨"},
    )
    assert adjusted[0]["score"] > adjusted[1]["score"]


def test_weather_adjustments_high_humidity_prefers_quick_dry():
    scored = [
        {
            "name": "速干T恤",
            "category": "上衣",
            "fit_tags": [],
            "score": 100,
        },
        {
            "name": "厚毛呢大衣",
            "category": "外套",
            "fit_tags": [],
            "score": 100,
        },
    ]
    adjusted = _apply_weather_adjustments(
        scored,
        {"temperature": 27, "humidity": 85, "weather": "多云"},
    )
    assert adjusted[0]["score"] > adjusted[1]["score"]
