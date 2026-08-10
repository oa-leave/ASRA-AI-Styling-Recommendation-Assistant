from backend.agent.registry import DEFAULT_TOOL_PLAN, TOOL_REGISTRY, memory_tool
from database.connection import SessionLocal


def test_default_tool_plan_order():
    assert DEFAULT_TOOL_PLAN == [
        "weather",
        "scene",
        "memory",
        "knowledge",
        "recommend",
    ]


def test_tool_registry_contains_expected_tools():
    assert set(TOOL_REGISTRY.keys()) == {
        "weather",
        "scene",
        "memory",
        "knowledge",
        "recommend",
    }


def test_memory_tool_returns_profile_key():
    result = memory_tool({"user_id": 999999}, SessionLocal())
    assert "memory" in result
    assert "profile" in result
