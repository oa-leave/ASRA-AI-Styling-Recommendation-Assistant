from types import SimpleNamespace

from backend.services.recommendation_engine import (
    build_best_outfit,
    calculate_clothes_score,
    calculate_outfit_score,
    color_match,
    normalize_colors,
    normalize_tags,
    tag_match,
    tag_overlap,
)


def test_color_match_only_matches_same_color():
    assert color_match("黑色", ["白色"]) is False
    assert color_match("白色", ["白色"]) is True
    assert color_match("blue", ["白色"]) is False
    assert color_match("white", ["白色"]) is True


def test_normalize_colors():
    assert normalize_colors("黑白") == ["黑色", "白色"]
    assert normalize_colors(["白色", "黑色"]) == ["白色", "黑色"]
    assert normalize_colors(["白", "black"]) == ["白色", "黑色"]
    assert normalize_colors(None) == []


def test_normalize_tags():
    assert normalize_tags("日系, 极简") == ["日系", "极简"]
    assert normalize_tags(["日系", "极简"]) == ["日系", "极简"]
    assert normalize_tags(None) == []


def test_tag_overlap():
    assert tag_overlap(["休闲"], ["休闲"]) == {"休闲"}
    assert tag_overlap(["休闲"], ["商务"]) == set()
    assert tag_overlap([], ["休闲"]) == set()


def test_tag_match_counts_overlap():
    assert tag_match(["日系简约", "宽松", "基础款"], ["日系简约", "极简", "基础款"]) == 2
    assert tag_match(["商务"], ["休闲"]) == 0
    assert tag_match(["日系", "日系"], ["日系"]) == 1


def test_calculate_clothes_score_uses_tags_and_weights():
    profile = SimpleNamespace(
        style="休闲",
        season="夏季",
        favorite_color="白色",
        favorite_colors=["白色"],
        style_tags=["休闲"],
    )
    items = [
        SimpleNamespace(
            id=1,
            name="白色T恤",
            category="上衣",
            color="白色",
            style="休闲",
            season="夏季",
            color_tags=["白色"],
            style_tags=["休闲"],
            fit_tags=["宽松"],
        ),
        SimpleNamespace(
            id=2,
            name="黑色休闲裤",
            category="裤子",
            color="黑色",
            style="休闲",
            season="夏季",
            color_tags=["黑色"],
            style_tags=["休闲"],
            fit_tags=["修身"],
        ),
    ]

    scored = calculate_clothes_score(items, profile)
    assert scored[0]["score"] == 120
    assert scored[1]["score"] == 80


def test_season_mismatch_does_not_remove_item():
    profile = SimpleNamespace(
        style="商务",
        season="春季",
        favorite_color="黑色",
        favorite_colors=["黑色"],
        style_tags=["商务"],
    )
    item = SimpleNamespace(
        id=3,
        name="黑色西服",
        category="上衣",
        color="黑色",
        style="商务",
        season="秋冬",
        color_tags=["黑色"],
        style_tags=["商务"],
        fit_tags=["修身"],
    )

    scored = calculate_clothes_score([item], profile)
    assert len(scored) == 1
    assert scored[0]["score"] == 90


def test_build_best_outfit_empty():
    result = build_best_outfit([])
    assert result["outfit"] == {}
    assert result["score"] == 0
    assert result["reason"] == ["没有找到合适穿搭"]


def test_fit_tags_add_score():
    profile = SimpleNamespace(
        style="休闲",
        season="夏季",
        favorite_color="白色",
        favorite_colors=["白色"],
        style_tags=["休闲"],
        fit_tags=["宽松"],
    )
    item = SimpleNamespace(
        id=1,
        name="白色T恤",
        category="上衣",
        color="白色",
        style="休闲",
        season="夏季",
        color_tags=["白色"],
        style_tags=["休闲"],
        fit_tags=["宽松"],
    )

    scored = calculate_clothes_score([item], profile)
    assert scored[0]["score"] == 140
    assert "符合身材版型偏好" in scored[0]["reason"]


def test_avoid_colors_penalty():
    profile = SimpleNamespace(
        style="休闲",
        season="夏季",
        favorite_color="白色",
        favorite_colors=["白色"],
        style_tags=["休闲"],
        fit_tags=[],
        avoid_colors=["红色"],
    )
    item = SimpleNamespace(
        id=1,
        name="红色T恤",
        category="上衣",
        color="红色",
        style="休闲",
        season="夏季",
        color_tags=["红色"],
        style_tags=["休闲"],
        fit_tags=[],
    )

    scored = calculate_clothes_score([item], profile)
    assert scored == []


def test_occasion_tags_add_score():
    profile = SimpleNamespace(
        style="休闲",
        season="夏季",
        favorite_color="白色",
        favorite_colors=["白色"],
        style_tags=["休闲"],
        fit_tags=[],
        avoid_colors=[],
        occasion_preferences="通勤",
    )
    item = SimpleNamespace(
        id=1,
        name="白色衬衫",
        category="上衣",
        color="白色",
        style="休闲",
        season="夏季",
        color_tags=["白色"],
        style_tags=["休闲"],
        fit_tags=[],
        occasion_tags=["通勤"],
    )

    scored = calculate_clothes_score([item], profile)
    assert scored[0]["score"] == 150
    assert "符合使用场景" in scored[0]["reason"]


def test_build_best_outfit_searches_combinations():
    clothes = [
        {
            "id": 1,
            "name": "黑色T恤",
            "category": "上衣",
            "color": "黑色",
            "style": "休闲",
            "season": "夏季",
            "score": 100,
            "reason": ["风格"],
        },
        {
            "id": 2,
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
        {
            "id": 3,
            "name": "白色休闲裤",
            "category": "裤子",
            "color": "白色",
            "style": "商务",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
        {
            "id": 4,
            "name": "黑色休闲裤",
            "category": "裤子",
            "color": "黑色",
            "style": "休闲",
            "season": "夏季",
            "score": 80,
            "reason": ["风格"],
        },
    ]

    result = build_best_outfit(clothes)
    assert result["outfit"]["上衣"]["name"] == "黑色T恤"
    assert result["outfit"]["裤子"]["name"] == "黑色休闲裤"


def test_core_outfit_bonus():
    outfit = {
        "上衣": {
            "score": 100,
            "style": "休闲",
            "color": "白色",
            "season": "夏季",
            "category": "上衣",
        },
        "裤子": {
            "score": 100,
            "style": "休闲",
            "color": "黑色",
            "season": "夏季",
            "category": "裤子",
        },
    }

    score, reasons = calculate_outfit_score(outfit)
    assert "核心穿搭完整" in reasons


def test_single_item_outfit_gets_incomplete_penalty():
    outfit = {
        "上衣": {
            "score": 100,
            "style": "休闲",
            "color": "白色",
            "season": "夏季",
            "category": "上衣",
        }
    }

    score, reasons = calculate_outfit_score(outfit)
    assert score < 100
    assert "穿搭信息不足" in reasons


def test_outfit_compatibility_penalties():
    profile = SimpleNamespace(season="夏季")
    outfit = {
        "外套": {
            "score": 100,
            "style": "商务",
            "color": "红色",
            "season": "冬季",
            "category": "外套",
        },
        "裤子": {
            "score": 100,
            "style": "休闲",
            "color": "绿色",
            "season": "夏季",
            "category": "裤子",
        },
    }

    score, reasons = calculate_outfit_score(outfit, profile)
    assert score < 200
    assert "整体风格不统一" in reasons
    assert "颜色搭配冲突" in reasons
    assert "季节搭配不合理" in reasons
