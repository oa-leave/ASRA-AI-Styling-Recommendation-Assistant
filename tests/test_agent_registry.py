from backend.agent.registry import DEFAULT_TOOL_PLAN, TOOL_REGISTRY


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
