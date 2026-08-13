from backend.agent.decision import _extract_forecast_day, decide_agent_plan
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


def test_forecast_day_extraction():
    assert _extract_forecast_day("今天穿什么") == 0
    assert _extract_forecast_day("明天去见客户") == 1
    assert _extract_forecast_day("后天出差") == 2


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
