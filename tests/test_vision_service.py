from backend.services.vision_service import (
    _color_name_from_hsv,
    _infer_category,
    _infer_fit,
    _infer_occasion,
    _infer_style,
)


def test_purple_is_not_gray():
    assert _color_name_from_hsv((142, 115, 160)) == "紫色"


def test_gray_white_black():
    assert _color_name_from_hsv((128, 128, 128)) == "灰色"
    assert _color_name_from_hsv((255, 255, 255)) == "白色"
    assert _color_name_from_hsv((0, 0, 0)) == "黑色"


def test_filename_heuristics():
    assert _infer_category("黑色西裤.jpg") == "西裤"
    assert _infer_category("黑色西装.jpg") == "西装"
    assert _infer_style("商务西装.jpg") == "商务"
    assert _infer_fit("宽松衬衫.jpg") == "宽松"
    assert _infer_occasion("通勤衬衫.jpg") == ["通勤"]


def test_filename_heuristics_recognize_more_styles():
    assert _infer_style("复古上衣.jpg") == "复古"
    assert _infer_style("学院风卫衣.jpg") == "学院"
    assert _infer_style("简约T恤.jpg") == "简约"
    assert _infer_style("新中式外套.jpg") == "新中式"
