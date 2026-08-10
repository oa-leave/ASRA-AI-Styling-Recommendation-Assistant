from backend.services.recommend_service import (
    _apply_memory_adjustments,
    _apply_formal_fallback_adjustments,
    _apply_recent_liked_color_bonus,
    _apply_scene_scoring,
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
    assert adjusted[1]["score"] == 70


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
