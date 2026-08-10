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
