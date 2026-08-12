import json

from PIL import Image

from backend.core.config import settings
from backend.services.vision_service import extract_vision_result


def _image(path):
    image = Image.new("RGB", (64, 64), (0, 0, 255))
    image.save(path, format="JPEG")
    return path


def test_vision_model_result_is_used_when_enabled(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "vision_enabled", True)
    path = _image(tmp_path / "blue.jpg")

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": json.dumps({
                        "name": "Blue Jeans",
                        "category": "Pants",
                        "color": "Blue",
                        "style": "Casual",
                        "season": "Spring",
                        "color_tags": ["Blue"],
                        "style_tags": ["Casual"],
                        "fit_tags": ["Straight"],
                        "occasion_tags": ["Daily"],
                    }, ensure_ascii=False),
                }
            }

    monkeypatch.setattr(
        "backend.services.vision_service.requests.post",
        lambda *args, **kwargs: FakeResponse(),
    )

    result = extract_vision_result(path, "photo.jpg")
    assert result["name"] == "Blue Jeans"
    assert result["category"] == "裤子"
    assert result["color"] == "蓝色"
    assert result["style"] == "休闲"
    assert result["season"] == "春季"
    assert result["occasion_tags"] == ["Daily"]


def test_vision_model_failure_falls_back_to_heuristics(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "vision_enabled", True)
    path = _image(tmp_path / "blue-pants.jpg")

    class BadResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "not json"}}]}

    monkeypatch.setattr(
        "backend.services.vision_service.requests.post",
        lambda *args, **kwargs: BadResponse(),
    )

    result = extract_vision_result(path, "blue-pants.jpg")
    assert result["category"] == "裤子"
    assert result["color"] == "蓝色"


def test_vision_model_parses_loose_json_and_english_aliases(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "vision_enabled", True)
    path = _image(tmp_path / "shoe.jpg")

    class LooseResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": (
                        '{"name": "White Sneakers",'
                        '"category": "Accessory",'
                        '"category": "Accessory",'
                        '"color": "White",'
                        '"style": "Sporty",'
                        '"season": "Spring/Summer",'
                        '"color_tags": ["White"],'
                        '"style_tags": ["Athletic"],'
                        '"fit_tags": ["Standard"],'
                        '"occasion_tags": ["Everyday"],}'
                    )
                }
            }

    monkeypatch.setattr(
        "backend.services.vision_service.requests.post",
        lambda *args, **kwargs: LooseResponse(),
    )

    result = extract_vision_result(path, "shoe.jpg")
    assert result["category"] == "鞋子"
    assert result["color"] == "白色"
    assert result["style"] == "运动"


def test_vision_model_is_skipped_when_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "vision_enabled", False)
    path = _image(tmp_path / "blue.jpg")

    def unexpected_call(*args, **kwargs):
        raise AssertionError("vision endpoint should not be called")

    monkeypatch.setattr(
        "backend.services.vision_service.requests.post",
        unexpected_call,
    )

    result = extract_vision_result(path, "blue.jpg")
    assert result["category"] == "上衣"
    assert result["color"] == "蓝色"
