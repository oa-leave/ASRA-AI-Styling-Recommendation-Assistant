"""视觉识别服务：先使用 HSV 颜色分类，后续可替换为 CLIP/云视觉 API。"""
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PIL import Image


def _load_center_image(image_path: Path) -> Image.Image:
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    return image.crop((
        width // 4,
        height // 4,
        width * 3 // 4,
        height * 3 // 4,
    ))


def _dominant_rgb(image_path: Path) -> Tuple[int, int, int]:
    image = _load_center_image(image_path)
    image.thumbnail((100, 100))
    pixels = list(image.get_flattened_data())

    buckets = {}
    for pixel in pixels:
        bucket = (
            pixel[0] // 64 * 64,
            pixel[1] // 64 * 64,
            pixel[2] // 64 * 64,
        )
        buckets[bucket] = buckets.get(bucket, 0) + 1

    dominant_bucket = max(buckets, key=buckets.get)
    items = [
        pixel
        for pixel in pixels
        if (
            pixel[0] // 64 * 64,
            pixel[1] // 64 * 64,
            pixel[2] // 64 * 64,
        ) == dominant_bucket
    ]
    return tuple(
        round(sum(item[i] for item in items) / len(items))
        for i in range(3)
    )


def _rgb_to_hsv(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    red, green, blue = (value / 255 for value in rgb)
    maximum = max(red, green, blue)
    minimum = min(red, green, blue)
    delta = maximum - minimum

    hue = 0.0
    if delta:
        if maximum == red:
            hue = ((green - blue) / delta) % 6
        elif maximum == green:
            hue = (blue - red) / delta + 2
        else:
            hue = (red - green) / delta + 4
        hue *= 60

    saturation = delta / maximum if maximum else 0.0
    value = maximum
    return hue, saturation, value


def _color_name_from_hsv(rgb: Tuple[int, int, int]) -> str:
    hue, saturation, value = _rgb_to_hsv(rgb)

    if saturation < 0.18:
        if value >= 0.85:
            return "白色"
        if value <= 0.2:
            return "黑色"
        return "灰色"

    hue = hue % 360
    if hue < 15 or hue >= 345:
        return "红色"
    if hue < 40:
        return "橙色"
    if hue < 70:
        return "黄色"
    if hue < 150:
        return "绿色"
    if hue < 200:
        return "青色"
    if hue < 260:
        return "蓝色"
    if hue < 300:
        return "紫色"
    return "粉色"


def _infer_category(name: str) -> str:
    text = name.lower()
    if any(word in text for word in ("裤", "pants")):
        return "裤子"
    if any(word in text for word in ("鞋", "shoes", "sneaker")):
        return "鞋子"
    if any(word in text for word in ("裙", "dress", "skirt")):
        return "裙子"
    if any(word in text for word in ("旗袍", "汉服", "one-piece")):
        return "旗袍"
    if any(word in text for word in ("外套", "西装", "jacket", "coat")):
        return "外套"
    if any(word in text for word in ("衬衫", "上衣", "shirt", "top")):
        return "上衣"
    return "上衣"


def _infer_style(name: str) -> str:
    text = name.lower()
    if any(word in text for word in ("商务", "西装", "business", "formal")):
        return "商务"
    if any(word in text for word in ("运动", "sport", "sneaker")):
        return "运动"
    if any(word in text for word in ("旗袍", "汉服", "中式")):
        return "中式"
    if any(word in text for word in ("日系", "japanese")):
        return "日系"
    if any(word in text for word in ("极简", "minimal")):
        return "极简"
    return "休闲"


def _infer_fit(name: str) -> str:
    text = name.lower()
    if "宽松" in text or "oversize" in text:
        return "宽松"
    if "修身" in text or "slim" in text:
        return "修身"
    return "基础款"


def _infer_occasion(name: str) -> List[str]:
    text = name.lower()
    if any(word in text for word in ("通勤", "work", "office")):
        return ["通勤"]
    if any(word in text for word in ("约会", "date")):
        return ["约会"]
    if any(word in text for word in ("运动", "sport")):
        return ["运动"]
    if any(word in text for word in ("旅行", "travel")):
        return ["旅行"]
    return ["日常"]


def extract_vision_result(
    image_path: Path,
    original_name: str = "",
) -> Dict[str, Any]:
    """从图片提取颜色并生成待确认的衣物标签。"""
    rgb = _dominant_rgb(image_path)
    color = _color_name_from_hsv(rgb)

    color_tags: List[str] = [color]
    if color in {"白色", "黑色", "灰色"}:
        color_tags.append("中性色")

    return {
        "name": "识别衣物",
        "category": _infer_category(original_name),
        "color": color,
        "style": _infer_style(original_name),
        "season": "四季",
        "color_tags": color_tags,
        "style_tags": [_infer_style(original_name)],
        "fit_tags": [_infer_fit(original_name)],
        "occasion_tags": _infer_occasion(original_name),
    }
