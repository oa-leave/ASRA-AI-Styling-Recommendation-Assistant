from types import SimpleNamespace

from backend.services.recommendation_engine import (
    build_best_outfit,
    build_top_outfits,
    calculate_clothes_score,
    calculate_outfit_score,
    color_match,
    generate_summary,
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
    assert color_match("蓝色薄外套", ["蓝"]) is True


def test_normalize_colors():
    assert normalize_colors("黑白") == ["黑色", "白色"]
    assert normalize_colors(["白色", "黑色"]) == ["白色", "黑色"]
    assert normalize_colors(["白", "black"]) == ["白色", "黑色"]
    assert normalize_colors(["黑白"]) == ["黑色", "白色"]
    assert normalize_colors("黑色白色") == ["黑色", "白色"]
    assert normalize_colors(None) == []


def test_normalize_tags():
    assert normalize_tags("日系, 极简") == ["日系", "极简"]
    assert normalize_tags('["白色", "蓝色"]') == ["白色", "蓝色"]
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


def test_summer_outerwear_is_filtered():
    profile = SimpleNamespace(season="夏季", style="休闲")
    clothes = [
        {
            "id": 1,
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "style": "休闲",
            "season": "夏季",
            "score": 100,
            "reason": ["风格"],
        },
        {
            "id": 2,
            "name": "黑色休闲裤",
            "category": "裤子",
            "color": "黑色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
        {
            "id": 3,
            "name": "灰色运动鞋",
            "category": "鞋子",
            "color": "灰色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
        {
            "id": 4,
            "name": "蓝色薄外套",
            "category": "外套",
            "color": "蓝色",
            "style": "休闲",
            "season": "夏季",
            "score": 80,
            "reason": ["风格"],
        },
    ]

    result = build_best_outfit(clothes, profile)
    assert "外套" not in result["outfit"]


def test_generate_summary():
    outfit = {
        "上衣": {"style": "休闲"},
        "裤子": {"style": "休闲"},
    }
    profile = SimpleNamespace(season="夏季", style="休闲")
    reasons = ["整体风格统一", "颜色搭配协调"]

    summary = generate_summary(outfit, reasons, profile)
    assert "休闲风格" in summary
    assert "适合夏季" in summary
    assert "配色协调" in summary


def test_generate_summary_marks_missing_shoes_instead_of_core_complete():
    outfit = {
        "上衣": {"style": "休闲"},
        "裤子": {"style": "休闲"},
    }
    reasons = ["核心穿搭完整（裤装搭配）"]

    summary = generate_summary(outfit, reasons)
    assert "核心穿搭完整" not in summary
    assert "缺少鞋子" in summary


def test_generate_summary_uses_shoe_suitability_for_completeness():
    outfit = {
        "上衣": {"style": "休闲"},
        "裤子": {"style": "休闲"},
        "鞋子": {"name": "白色运动鞋", "style": "运动"},
    }
    reasons = ["核心穿搭完整（裤装搭配）"]

    unsuitable_summary = generate_summary(
        outfit,
        reasons,
        shoe_feedback={"status": "unsuitable"},
    )
    assert "核心穿搭完整" not in unsuitable_summary
    assert "鞋子不满足当前场景要求" in unsuitable_summary

    suitable_summary = generate_summary(
        outfit,
        reasons,
        shoe_feedback={"status": "suitable"},
    )
    assert "核心穿搭完整" in suitable_summary


def test_build_top_outfits_returns_multiple():
    clothes = [
        {
            "id": 1,
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "style": "休闲",
            "season": "夏季",
            "score": 100,
            "reason": ["风格"],
        },
        {
            "id": 2,
            "name": "黑色休闲裤",
            "category": "裤子",
            "color": "黑色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
    ]

    results = build_top_outfits(clothes, top_n=3)
    assert len(results) >= 1
    assert results[0]["score"] >= results[-1]["score"]


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

    scored, filtered = calculate_clothes_score(
        [item],
        profile,
        collect_filtered=True,
    )
    assert scored == []
    assert filtered == ["用户不喜欢红色"]


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


def test_onepiece_category_maps_to_dress_slot():
    clothes = [
        {
            "id": 1,
            "name": "红色旗袍",
            "category": "旗袍",
            "color": "红色",
            "style": "中式",
            "season": "四季",
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
            "name": "黑色裤子",
            "category": "裤子",
            "color": "黑色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
    ]

    result = build_best_outfit(clothes)
    assert "连衣裙" in result["outfit"]
    assert "上衣" not in result["outfit"]
    assert "裤子" not in result["outfit"]


def test_slot_style_filter():
    clothes = [
        {
            "id": 1,
            "name": "黑色休闲裤",
            "category": "裤子",
            "color": "黑色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
        {
            "id": 2,
            "name": "黑色西裤",
            "category": "裤子",
            "color": "黑色",
            "style": "商务",
            "season": "夏季",
            "score": 80,
            "reason": ["风格"],
        },
    ]

    results = build_top_outfits(
        clothes,
        top_n=3,
        slot_style={"裤子": "商务"},
    )
    assert results[0]["outfit"]["裤子"]["style"] == "商务"


def test_force_slot_missing_returns_empty():
    clothes = [
        {
            "id": 1,
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        }
    ]

    results = build_top_outfits(
        clothes,
        top_n=3,
        force_slot=["外套"],
    )
    assert results[0]["outfit"] == {}
    assert results[0]["reason"] == ["缺少指定搭配"]


def test_remove_slot():
    clothes = [
        {
            "id": 1,
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
        {
            "id": 2,
            "name": "黑色休闲裤",
            "category": "裤子",
            "color": "黑色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
        {
            "id": 3,
            "name": "蓝色外套",
            "category": "外套",
            "color": "蓝色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
    ]

    results = build_top_outfits(
        clothes,
        top_n=3,
        remove_slot=["外套"],
    )
    assert "外套" not in results[0]["outfit"]


def test_replace_slot():
    clothes = [
        {
            "id": 1,
            "name": "黑色西裤",
            "category": "裤子",
            "color": "黑色",
            "style": "商务",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        }
    ]

    results = build_top_outfits(
        clothes,
        top_n=3,
        replace_slot={"裤子": "裙子"},
    )
    assert "裙子" in results[0]["outfit"]
    assert "裤子" not in results[0]["outfit"]


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
    assert any("核心穿搭完整" in reason for reason in reasons)


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


def test_build_top_outfits_required_slot_keywords_filter_and_force():
    clothes = [
        {
            "id": 1,
            "name": "白色衬衫",
            "category": "上衣",
            "color": "白色",
            "style": "商务",
            "season": "夏季",
            "score": 90,
            "reason": [],
        },
        {
            "id": 2,
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "style": "休闲",
            "season": "夏季",
            "score": 100,
            "reason": [],
        },
        {
            "id": 3,
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "style": "商务",
            "season": "夏季",
            "score": 90,
            "reason": [],
        },
    ]

    results = build_top_outfits(
        clothes,
        top_n=1,
        required_slot_keywords={
            "上衣": ["衬衫"],
            "裤子": ["裤子"],
        },
    )
    outfit = results[0]["outfit"]
    assert "上衣" in outfit
    assert "裤子" in outfit
    assert outfit["上衣"]["name"] == "白色衬衫"
    assert outfit["裤子"]["name"] == "蓝色裤子"


def test_build_best_outfit_missing_required_slot_returns_empty():
    clothes = [
        {
            "id": 1,
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "style": "休闲",
            "season": "夏季",
            "score": 100,
            "reason": [],
        },
        {
            "id": 2,
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": [],
        },
    ]

    result = build_best_outfit(
        clothes,
        required_slot_keywords={"上衣": ["衬衫"]},
    )
    assert result["outfit"] == {}
    assert result["reason"] == ["缺少指定搭配"]


def test_build_top_outfits_allowed_slots_limits_scope():
    clothes = [
        {
            "id": 1,
            "name": "灰色衬衫",
            "category": "上衣",
            "color": "灰色",
            "style": "商务",
            "season": "夏季",
            "score": 90,
            "reason": [],
        },
        {
            "id": 2,
            "name": "蓝色裤子",
            "category": "裤子",
            "color": "蓝色",
            "style": "商务",
            "season": "夏季",
            "score": 90,
            "reason": [],
        },
        {
            "id": 3,
            "name": "白色运动鞋",
            "category": "鞋子",
            "color": "白色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": [],
        },
    ]

    results = build_top_outfits(
        clothes,
        top_n=1,
        force_slot=["上衣"],
        allowed_slots=["上衣"],
    )
    assert set(results[0]["outfit"].keys()) == {"上衣"}


def test_generate_summary_skips_conflicting_memory_style():
    profile = SimpleNamespace(style="休闲", season="夏季")
    formal_summary = generate_summary(
        {},
        [],
        profile,
        current_style="商务",
    )
    assert not any(
        "用户喜欢休闲风格" in item
        for item in formal_summary
    )

    casual_summary = generate_summary(
        {},
        [],
        profile,
        current_style="休闲",
    )
    assert any(
        "用户喜欢休闲风格" in item
        for item in casual_summary
    )


def test_generate_summary_omits_item_style_when_conflicting():
    profile = SimpleNamespace(style="休闲", season="夏季")
    summary = generate_summary(
        {"上衣": {"style": "休闲", "score": 1}},
        [],
        profile,
        current_style="商务",
    )
    assert not any("休闲风格" in item for item in summary)
