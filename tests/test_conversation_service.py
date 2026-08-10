from backend.services.conversation_service import parse_adjustments


def test_parse_avoid_color():
    context = parse_adjustments("不要蓝色", {})
    assert "蓝色" in context["avoid_colors"]


def test_parse_slot_style():
    context = parse_adjustments("裤子换正式一点", {})
    assert context["slot_style"] == {"裤子": "商务"}


def test_parse_force_and_remove_slot():
    context = parse_adjustments("加一件外套", {})
    assert "外套" in context["force_slot"]

    context = parse_adjustments("去掉外套", context)
    assert "外套" in context["remove_slot"]


def test_parse_replace_slot():
    context = parse_adjustments("裤子换裙子", {})
    assert context["replace_slot"] == {"裤子": "裙子"}


def test_parse_remove_avoid_color():
    context = parse_adjustments("不要蓝色", {})
    context = parse_adjustments("要蓝色", context)
    assert "蓝色" not in context["avoid_colors"]
    assert "蓝色" in context["removed_avoid_colors"]


def test_parse_flexible_negative_color():
    assert "黑色" in parse_adjustments("不要推荐黑色", {})["avoid_colors"]
    assert "蓝色" in parse_adjustments("最近不喜欢蓝色", {})["avoid_colors"]
    assert "红色" in parse_adjustments("没相中红色", {})["avoid_colors"]


def test_parse_formal_style():
    context = parse_adjustments("今天想穿正式一点", {})
    assert context["style"] == "商务"


def test_parse_exclude_item_keyword():
    context = parse_adjustments("不要短袖", {})
    assert "短袖" in context["exclude_item_keywords"]
    assert "T恤" in context["exclude_item_keywords"]


def test_occasion_resets_previous_style():
    context = parse_adjustments(
        "\u7ed9\u6211\u63a8\u8350\u7ea6\u4f1a\u7a7f\u642d",
        {"style": "\u5546\u52a1"},
    )
    assert context["style"] == "\u4f11\u95f2"


def test_parse_liked_color():
    context = parse_adjustments("最近喜欢灰色", {})
    assert "灰色" in context["liked_colors"]
