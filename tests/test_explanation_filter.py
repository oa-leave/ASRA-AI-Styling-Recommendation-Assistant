from backend.services.explanation_filter import filter_summary, filter_text


def test_filter_summary_removes_avoided_color():
    summary = ["黑白灰配色降低搭配风险", "适合夏季"]
    filtered = filter_summary(summary, ["黑色"])
    assert filtered == ["适合夏季"]


def test_filter_text_removes_avoided_color_sentence():
    text = "白色和黑色属于低风险经典搭配；夏季优先选择轻薄材质。"
    filtered = filter_text(text, ["黑色"])
    assert "黑色" not in filtered
    assert "夏季" in filtered
