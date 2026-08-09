from backend.services.knowledge_service import (
    build_knowledge_text,
    retrieve_fashion_rules,
)


def test_retrieve_fashion_rules_by_style_and_occasion():
    rules = retrieve_fashion_rules(
        style="日系",
        occasion="通勤",
    )
    assert len(rules) >= 1


def test_build_knowledge_text():
    rules = [{"content": "白色和黑色属于低风险搭配。"}]
    text = build_knowledge_text(rules)
    assert "低风险" in text
