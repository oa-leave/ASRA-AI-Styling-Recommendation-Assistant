from backend.agent.decision import decide_agent_plan
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


def test_build_memory_text():
    text = build_memory_text({
        "profile": {"style": "休闲", "favorite_color": "白色"},
        "recent_history": [{"id": 1}],
        "feedback_summary": {"like_count": 2, "dislike_count": 1},
    })
    assert "休闲" in text
    assert "最近有1次推荐记录" in text
