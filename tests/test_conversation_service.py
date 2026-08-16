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


def test_removed_avoid_colors_not_carried_to_next_turn():
    context = parse_adjustments("不要黑色", {})
    context = parse_adjustments("要黑色", context)
    context = parse_adjustments("不要黑色", context)
    assert "黑色" in context["avoid_colors"]
    assert "黑色" not in context["removed_avoid_colors"]


def test_parse_allow_color_with_allow_marker():
    context = parse_adjustments("不要蓝色", {})
    context = parse_adjustments("允许蓝色，黑色", context)
    assert "蓝色" not in context["avoid_colors"]
    assert "黑色" not in context["avoid_colors"]
    assert "蓝色" in context["liked_colors"]
    assert "黑色" in context["liked_colors"]


def test_parse_disallow_color_with_disallow_marker():
    context = parse_adjustments("不允许蓝色", {})
    assert "蓝色" in context["avoid_colors"]
    assert "蓝色" not in context["liked_colors"]


def test_parse_flexible_negative_color():
    assert "黑色" in parse_adjustments("不要推荐黑色", {})["avoid_colors"]
    assert "蓝色" in parse_adjustments("最近不喜欢蓝色", {})["avoid_colors"]
    assert "红色" in parse_adjustments("没相中红色", {})["avoid_colors"]


def test_parse_formal_style():
    context = parse_adjustments("今天想穿正式一点", {})
    assert context["style"] == "商务"


def test_parse_not_too_formal_style_is_casual():
    context = parse_adjustments("休闲一点，不要太正式", {})
    assert context["style"] == "休闲"


def test_parse_exclude_item_keyword():
    context = parse_adjustments("不要短袖", {})
    assert "短袖" in context["exclude_item_keywords"]
    assert "T恤" in context["exclude_item_keywords"]


def test_parse_exclude_item_with_do_not_want_to_wear():
    context = parse_adjustments("不想穿西装", {})
    assert "西装" in context["exclude_item_keywords"]


def test_parse_exclude_shirt_alias():
    context = parse_adjustments("不要衬衫和西装", {})
    assert "衬衫" in context["exclude_item_keywords"]
    assert "衬衣" in context["exclude_item_keywords"]


def test_parse_positive_item_preference():
    context = parse_adjustments("想穿T恤", {})
    assert "T恤" in context["preferred_item_keywords"]


def test_occasion_resets_previous_style():
    context = parse_adjustments(
        "\u7ed9\u6211\u63a8\u8350\u7ea6\u4f1a\u7a7f\u642d",
        {"style": "\u5546\u52a1"},
    )
    assert context["style"] == "\u4f11\u95f2"


def test_parse_liked_color():
    context = parse_adjustments("最近喜欢灰色", {})
    assert "灰色" in context["liked_colors"]


def test_parse_plain_wear_marks_shirt_and_pants_as_required():
    context = parse_adjustments("今天日常穿衬衫和裤子，怎么搭？", {})
    assert "衬衫" in context["required_item_keywords"]
    assert "裤子" in context["required_item_keywords"]


def test_parse_only_recommend_marks_required_and_does_not_remove_pants():
    context = parse_adjustments(
        "明天面试，只推荐衬衫和裤子，不要西装",
        {},
    )
    assert "衬衫" in context["required_item_keywords"]
    assert "裤子" in context["required_item_keywords"]
    assert "西装" in context["exclude_item_keywords"]
    assert "裤子" not in context["remove_slot"]


def test_parse_do_not_want_suit_with_shirt_and_pants():
    context = parse_adjustments(
        "我明天面试，不想穿西装，只想穿衬衫和裤子，可以吗？",
        {},
    )
    assert "衬衫" in context["required_item_keywords"]
    assert "裤子" in context["required_item_keywords"]
    assert "西装" in context["exclude_item_keywords"]


def test_parse_can_wear_question_is_not_hard_required():
    context = parse_adjustments(
        "明天面试，我就想穿得特别休闲，可以穿T恤吗？",
        {},
    )
    assert "T恤" in context["question_item_keywords"]
    assert "T恤" not in context["required_item_keywords"]


def test_parse_only_recommend_sets_allowed_scope():
    context = parse_adjustments("只推荐衬衫和裤子", {})
    assert set(context["required_item_keywords"]) == {"衬衫", "裤子"}
    assert set(context["allowed_item_keywords"]) == {"衬衫", "裤子"}


def test_parse_plain_wear_has_no_allowed_scope():
    context = parse_adjustments("今天日常穿衬衫和裤子", {})
    assert set(context["required_item_keywords"]) == {"衬衫", "裤子"}
    assert context["allowed_item_keywords"] == []


def test_parse_only_recommend_with_excluded_pants():
    context = parse_adjustments(
        "不要裤子，只推荐衬衫和鞋子",
        {},
    )
    assert "裤子" in context["exclude_item_keywords"]
    assert set(context["required_item_keywords"]) == {"衬衫", "鞋子"}
    assert set(context["allowed_item_keywords"]) == {"衬衫", "鞋子"}


def test_parse_only_color_sets_allowed_colors():
    context = parse_adjustments("只推荐白色", {})
    assert context["allowed_colors"] == ["白色"]
    assert context["allowed_item_keywords"] == []


def test_negative_color_does_not_cross_only_recommend_clause():
    context = parse_adjustments("不要蓝色，只推荐白色", {})
    assert context["avoid_colors"] == ["蓝色"]
    assert "白色" in context["allowed_colors"]


def test_parse_only_top_sets_allowed_top():
    context = parse_adjustments("只推荐上衣", {})
    assert "上衣" in context["required_item_keywords"]
    assert "上衣" in context["allowed_item_keywords"]


def test_parse_only_sport_style_top_sets_allowed_top():
    context = parse_adjustments("只推荐运动风上衣", {})
    assert "上衣" in context["allowed_item_keywords"]
    assert context["style"] == "运动"


def test_parse_only_long_sleeve_shirt_keeps_both_constraints():
    context = parse_adjustments("只推荐长袖衬衫", {})
    assert "长袖" in context["required_item_keywords"]
    assert "衬衫" in context["required_item_keywords"]


def test_parse_requested_season():
    context = parse_adjustments("冬天只推荐短袖", {})
    assert context["requested_season"] == "冬季"


def test_parse_no_shoes_only_top():
    context = parse_adjustments("不要鞋子，只推荐上衣", {})
    assert "鞋子" in context["exclude_item_keywords"]
    assert "上衣" in context["allowed_item_keywords"]


def test_parse_no_long_sleeve_does_not_exclude_all_shirts():
    context = parse_adjustments("不要长袖", {})
    assert "长袖" in context["exclude_item_keywords"]
    assert "衬衫" not in context["exclude_item_keywords"]
    assert "衬衣" not in context["exclude_item_keywords"]


def test_business_style_only_top_does_not_set_slot_style():
    context = parse_adjustments(
        "今天日常穿，要商务风，只推荐上衣",
        {},
    )
    assert context["slot_style"] == {}
    assert context["style_requested"] is True


def test_parse_business_style_sets_business_requested():
    context = parse_adjustments("要商务风", {})
    assert context["business_requested"] is True


def test_parse_customer_tshirt_formal_keeps_tshirt_requirement():
    context = parse_adjustments(
        "明天见客户，我想穿T恤，但要正式一点",
        {},
    )
    assert "T恤" in context["required_item_keywords"]
    assert "T恤" in context["preferred_item_keywords"]
    assert context["formal_requested"] is True


def test_scene_style_from_occasion_is_not_explicit_request():
    context = parse_adjustments("明天见客户，我想穿T恤", {})
    assert context["style"] == "商务"
    assert context["style_requested"] is False


def test_require_color_is_hard_but_like_color_is_soft():
    context = parse_adjustments(
        "我只要上衣，不要黑色，要蓝色，休闲风",
        {},
    )
    assert "黑色" in context["avoid_colors"]
    assert "蓝色" in context["required_colors"]
    assert "上衣" in context["allowed_item_keywords"]

    liked = parse_adjustments("我喜欢蓝色", {})
    assert liked["required_colors"] == []
    assert "蓝色" in liked["liked_colors"]


def test_parse_contradictory_color_detects_conflict():
    context = parse_adjustments(
        "我只要上衣，要蓝色，不要蓝色",
        {},
    )
    assert "蓝色" in context["color_conflicts"]


def test_parse_contradictory_item_detects_conflict():
    context = parse_adjustments(
        "我只要上衣，不要上衣",
        {},
    )
    assert "上衣" in context["item_conflicts"]


def test_parse_contradictory_style_detects_conflict():
    context = parse_adjustments(
        "我只要上衣，要休闲风，不要休闲风",
        {},
    )
    assert "休闲风" in context["style_conflicts"]


def test_parse_contradictory_sport_style_detects_conflict():
    context = parse_adjustments(
        "只推荐运动风上衣，不要运动风",
        {},
    )
    assert "运动风" in context["style_conflicts"]


def test_parse_no_sport_style_does_not_create_conflict():
    context = parse_adjustments(
        "只推荐上衣，不要运动风",
        {},
    )
    assert context["style_conflicts"] == []
    assert context.get("style") != "运动"


def test_parse_contradictory_style_detects_all_styles():
    context = parse_adjustments(
        "要日系风，不要日系风",
        {},
    )
    assert "日系风" in context["style_conflicts"]
