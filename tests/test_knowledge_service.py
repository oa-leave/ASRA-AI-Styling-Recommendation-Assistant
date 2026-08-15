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


def test_hiking_query_excludes_unrelated_occasion_rules():
    rules = retrieve_fashion_rules(
        style="运动",
        occasion="旅行",
        season="夏季",
        colors=["白色", "灰色"],
        tags=["休闲"],
    )
    contents = [rule["content"] for rule in rules]
    assert any("速干" in content for content in contents)
    assert not any("约会" in content for content in contents)
    assert not any("通勤" in content for content in contents)


def test_daily_query_returns_common_rules():
    rules = retrieve_fashion_rules(
        style="休闲",
        occasion="日常",
        season="夏季",
        tags=["休闲"],
    )
    contents = [rule["content"] for rule in rules]
    assert any("日常和休闲场景" in content for content in contents)
    assert not any("约会" in content for content in contents)


def test_interview_query_returns_interview_rules():
    rules = retrieve_fashion_rules(
        style="商务",
        occasion="通勤",
        tags=["休闲"],
    )
    contents = [rule["content"] for rule in rules]
    assert any("面试场景" in content for content in contents)


def test_build_knowledge_text():
    rules = [{"content": "白色和黑色属于低风险搭配。"}]
    text = build_knowledge_text(rules)
    assert "低风险" in text
