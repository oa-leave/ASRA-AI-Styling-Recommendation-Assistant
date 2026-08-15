from backend.agent.scene_lexicon import resolve_scene
from backend.agent.decision import deterministic_decision


def test_customer_meeting_resolves_to_business_scene():
    scene = resolve_scene("明天去见客户怎么穿")
    assert scene["occasion"] == "通勤"
    assert scene["scene_type"] == "客户拜访"
    assert scene["formality"] == 3
    assert scene["activity_level"] == 0
    assert scene["style"] == "商务"


def test_casual_outfit_resolves_to_low_formality():
    scene = resolve_scene("今天随便穿，舒服一点")
    assert scene["occasion"] == "日常"
    assert scene["formality"] == 1
    assert scene["style"] == "休闲"


def test_running_resolves_to_high_activity():
    scene = resolve_scene("去跑步")
    assert scene["occasion"] == "运动"
    assert scene["scene_type"] == "跑步"
    assert scene["activity_level"] == 3


def test_wedding_resolves_to_high_formality():
    scene = resolve_scene("参加婚礼")
    assert scene["occasion"] == "日常"
    assert scene["scene_type"] == "婚礼"
    assert scene["formality"] == 4


def test_business_style_boosts_formality():
    scene = resolve_scene("今天怎么穿？", occasion="正式", style="商务")
    assert scene["formality"] >= 3


def test_commute_with_business_style_keeps_commute_formality():
    scene = resolve_scene("今天怎么穿？", occasion="通勤", style="商务")
    assert scene["formality"] == 2


def test_expanded_scene_aliases():
    assert resolve_scene("参加答辩")["scene_type"] == "答辩"
    assert resolve_scene("周末家庭聚会")["scene_type"] == "家庭聚会"
    assert resolve_scene("参加葬礼")["formality"] == 4
    assert resolve_scene("入职第一天")["scene_type"] == "入职"
    assert resolve_scene("毕业典礼")["scene_type"] == "毕业典礼"
    assert resolve_scene("商务宴请")["scene_type"] == "商务宴请"
    assert resolve_scene("周末去打球")["scene_type"] == "球类"


def test_casual_client_meeting_lowers_formality():
    scene = resolve_scene("明天见客户，休闲一点，不要太正式", style="休闲")
    assert scene["formality"] == 2


def test_formal_but_not_too_serious_keeps_medium_formality():
    scene = resolve_scene("明天见客户，正式一点但不要太严肃", style="商务")
    assert scene["formality"] == 3


def test_explicit_tshirt_caps_medium_formality():
    scene = resolve_scene("明天见客户，我想穿T恤，但要正式一点")
    assert scene["formality"] == 3
    assert scene["style"] == "商务"


def test_camping_sneaker_friendly_unless_rugged():
    scene = resolve_scene("周末去露营")
    assert scene.get("requires_hiking_shoes") is not True

    rugged = resolve_scene("周末去露营，要走崎岖山路")
    assert rugged.get("requires_hiking_shoes") is True


def test_daily_with_sport_style_keeps_daily_scene():
    scene = resolve_scene(
        "今天日常穿，要运动风",
        occasion="日常",
        style="运动",
    )
    assert scene["scene_type"] == "日常"
    assert scene["style"] == "运动"


def test_deterministic_decision_daily_sport_style():
    plan = deterministic_decision(
        "今天日常穿，要运动风",
        None,
        None,
        None,
    )
    assert plan["occasion"] == "日常"
    assert plan["style"] == "运动"


def test_sport_style_without_occasion_is_not_sport_scene():
    plan = deterministic_decision(
        "我只要上衣，要运动风",
        None,
        None,
        None,
    )
    assert plan["occasion"] == "日常"
    assert plan["style"] == "运动"


def test_no_casual_with_formal_uses_business_style():
    scene = resolve_scene(
        "今天日常穿，我不想穿休闲风，要正式一点",
        occasion="日常",
        style="商务",
    )
    assert scene["style"] == "商务"
