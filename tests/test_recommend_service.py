from backend.services.recommend_service import _apply_memory_adjustments


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
