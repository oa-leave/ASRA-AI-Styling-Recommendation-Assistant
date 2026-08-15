from backend.agent.decision import (
    _extract_day_label,
    _extract_forecast_day,
    decide_agent_plan,
)
from backend.agent.explain import build_deterministic_explanation
from backend.agent.graph import build_agent_graph
from backend.agent.tools import analyze_scene, get_fallback_weather, get_weather
from backend.services.memory_service import build_memory_text
from database.connection import SessionLocal


def test_weather_tool():
    weather = get_weather("沈阳")
    assert weather["temperature"] == 25
    assert weather["season"] == "夏季"
    assert weather["source"] == "fallback"


def test_weather_fallback():
    weather = get_fallback_weather("未知城市")
    assert weather["source"] == "fallback"
    assert weather["temperature"] == 25


def test_scene_tool():
    scene = analyze_scene("通勤")
    assert scene["style"] == "商务"
    assert scene["occasion_tags"] == ["通勤"]


def test_customer_scene_maps_to_business():
    scene = analyze_scene("客户")
    assert scene["style"] == "商务"
    assert "客户" in scene["occasion_tags"]


def test_deterministic_decision_detects_customer_meeting():
    plan = decide_agent_plan(
        query="明天去见客户怎么穿",
        city=None,
        occasion=None,
        style=None,
    )
    assert plan["occasion"] == "通勤"
    assert plan["style"] == "商务"
    assert plan["scene_type"] == "客户拜访"
    assert plan["formality"] == 3
    assert plan["activity_level"] == 0


def test_casual_customer_query_sets_casual_style_and_low_formality():
    plan = decide_agent_plan(
        query="明天见客户，休闲一点，不要太正式",
        city=None,
        occasion=None,
        style=None,
    )
    assert plan["style"] == "休闲"
    assert plan["formality"] == 2


def test_formal_but_not_too_serious_query_stays_medium_formality():
    plan = decide_agent_plan(
        query="明天见客户，正式一点但不要太严肃",
        city=None,
        occasion=None,
        style=None,
    )
    assert plan["style"] == "商务"
    assert plan["formality"] == 3


def test_forecast_day_extraction():
    assert _extract_forecast_day("今天穿什么") == 0
    assert _extract_forecast_day("明天去见客户") == 1
    assert _extract_forecast_day("后天出差") == 2


def test_day_label_extraction():
    assert _extract_day_label("周末去爬山") == "周末"
    assert _extract_day_label("明天去见客户") == "明天"
    assert _extract_day_label("今天穿什么") is None


def test_deterministic_decision_includes_tomorrow():
    plan = decide_agent_plan(
        query="明天去见客户怎么穿",
        city=None,
        occasion=None,
        style=None,
    )
    assert plan["forecast_day"] == 1


def test_get_weather_tomorrow_uses_daily_forecast(monkeypatch):
    calls = []

    class FakeGeoResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{"latitude": 31.23, "longitude": 121.47}]}

    class FakeForecastResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "daily": {
                    "temperature_2m_max": [30, 28],
                    "temperature_2m_min": [22, 20],
                    "weather_code": [1, 3],
                }
            }

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if "geocoding" in url:
            return FakeGeoResponse()
        return FakeForecastResponse()

    monkeypatch.setattr("backend.agent.tools.requests.get", fake_get)
    weather = get_weather("上海", use_api=True, forecast_day=1)
    assert weather["source"] == "api"
    assert weather["day_offset"] == 1
    assert weather["temperature"] == 24
    assert "daily" in calls[1][1]["params"]


def test_get_weather_current_includes_humidity(monkeypatch):
    calls = []

    class FakeGeoResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [{"latitude": 31.23, "longitude": 121.47}]}

    class FakeForecastResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "current": {
                    "temperature_2m": 27,
                    "weather_code": 1,
                    "relative_humidity_2m": 82,
                }
            }

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        if "geocoding" in url:
            return FakeGeoResponse()
        return FakeForecastResponse()

    monkeypatch.setattr("backend.agent.tools.requests.get", fake_get)
    weather = get_weather("上海", use_api=True)
    assert weather["humidity"] == 82
    assert "relative_humidity_2m" in calls[1][1]["params"]["current"]


def test_deterministic_decision_from_query():
    plan = decide_agent_plan(
        query="明天上海约会穿什么？",
        city=None,
        occasion=None,
        style=None,
    )
    assert plan["city"] == "上海"
    assert plan["occasion"] == "约会"
    assert "weather" in plan["tool_plan"]


def test_agent_graph_compiles():
    graph = build_agent_graph(SessionLocal())
    assert graph is not None


def test_deterministic_explanation():
    explanation = build_deterministic_explanation(
        "沈阳",
        {"temperature": 25, "weather": "晴"},
        "通勤",
        {
            "items": [{"name": "白色T恤"}],
            "summary": ["休闲风格"],
        },
    )
    assert "白色T恤" in explanation
    assert "通勤" in explanation


def test_deterministic_explanation_uses_tomorrow_label():
    explanation = build_deterministic_explanation(
        "沈阳",
        {"temperature": 25, "weather": "晴"},
        "通勤",
        {
            "items": [{"name": "白色衬衫"}],
            "summary": ["商务休闲"],
        },
        forecast_day=1,
    )
    assert "明天沈阳" in explanation
    assert "今天" not in explanation.split("明天")[0]


def test_deterministic_explanation_uses_weekend_label():
    explanation = build_deterministic_explanation(
        "沈阳",
        {"temperature": 25, "weather": "晴"},
        "登山",
        {
            "items": [{"name": "运动鞋"}],
            "summary": ["适合周末"],
        },
        day_label="周末",
    )
    assert "周末沈阳" in explanation


def test_deterministic_explanation_includes_scene_warning():
    explanation = build_deterministic_explanation(
        "沈阳",
        {"temperature": 25, "weather": "晴"},
        "通勤",
        {
            "items": [{"name": "白色衬衫"}],
            "summary": ["核心穿搭完整"],
            "scene_feedback": {"warning": "当前衣柜缺少鞋子，建议补充皮鞋。"},
        },
        scene={"scene_type": "面试"},
    )
    assert "面试场景" in explanation
    assert "建议补充皮鞋" in explanation


def test_deterministic_explanation_reason_explains_items():
    explanation = build_deterministic_explanation(
        "沈阳",
        {"temperature": 27, "weather": "毛毛雨"},
        "客户拜访",
        {
            "items": [
                {"name": "白色长袖衬衣", "slot": "上衣"},
                {"name": "灰色裤子", "slot": "裤子"},
            ],
            "summary": ["白色/灰色配色协调"],
        },
        scene={"scene_type": "客户拜访"},
    )
    assert "比较得体" in explanation
    assert "搭配协调" in explanation
    assert "适合27℃毛毛雨天气" in explanation


def test_build_memory_text():
    text = build_memory_text({
        "profile": {
            "style": "休闲",
            "favorite_color": "白色",
            "favorite_colors": ["灰色", "白色", "黑色"],
        },
        "recent_history": [{"id": 1}],
        "feedback_summary": {"like_count": 2, "dislike_count": 1},
    })
    assert "休闲" in text
    assert "灰色" in text
    assert "最近有1次推荐记录" in text


def test_build_memory_text_excludes_avoid_colors():
    text = build_memory_text({
        "profile": {
            "style": "休闲",
            "favorite_color": "黑色",
            "favorite_colors": ["白色", "灰色", "黑色", "蓝色"],
            "avoid_colors": ["黑色"],
        },
        "recent_history": [],
        "feedback_summary": {},
    })
    assert "黑色" not in text
    assert "白色" in text
    assert "灰色" in text


def test_build_memory_text_uses_active_style_when_conflict():
    text = build_memory_text(
        {
            "profile": {
                "style": "休闲",
                "favorite_color": "白色",
                "favorite_colors": ["白色"],
                "avoid_colors": [],
            },
            "recent_history": [],
            "feedback_summary": {},
        },
        active_style="商务",
    )
    assert "本次要求：商务风格" in text
    assert "用户偏好：休闲风格" not in text


def test_deterministic_explanation_answers_can_wear_question():
    explanation = build_deterministic_explanation(
        "沈阳",
        {"temperature": 26, "weather": "雷暴"},
        "通勤",
        {
            "items": [{"name": "蓝色衬衫"}],
            "summary": ["商务风格"],
        },
        scene={"scene_type": "面试", "formality": 3},
        query="明天面试，我可以穿T恤吗？",
    )
    assert explanation.startswith("不太建议面试穿T恤")
    assert "推荐" in explanation


def test_deterministic_explanation_notes_missing_question_item():
    explanation = build_deterministic_explanation(
        "沈阳",
        {"temperature": 26, "weather": "阴"},
        "日常",
        {
            "items": [{"name": "灰色衬衫"}],
            "summary": ["休闲风格"],
        },
        scene={"formality": 1},
        query="可以穿T恤吗？",
    )
    assert "可以穿T恤" in explanation
    assert "当前衣柜没有T恤" in explanation
