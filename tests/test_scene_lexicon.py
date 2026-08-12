from backend.agent.scene_lexicon import resolve_scene


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
