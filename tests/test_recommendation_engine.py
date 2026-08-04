from types import SimpleNamespace

from backend.services.recommendation_engine import (
    build_best_outfit,
    calculate_clothes_score,
    color_match,
    tag_match,
    tag_overlap,
)


def test_color_match_only_matches_same_color():
    assert color_match("黑色", "白色") is False
    assert color_match("白色", "白色") is True
    assert color_match("blue", "白色") is False


def test_tag_overlap():
    assert tag_overlap(["休闲"], ["休闲"]) == {"休闲"}
    assert tag_overlap(["休闲"], ["商务"]) == set()
    assert tag_overlap([], ["休闲"]) == set()


def test_tag_match_counts_overlap():
    assert tag_match(["日系简约", "宽松", "基础款"], ["日系简约", "极简", "基础款"]) == 2
    assert tag_match(["商务"], ["休闲"]) == 0


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
