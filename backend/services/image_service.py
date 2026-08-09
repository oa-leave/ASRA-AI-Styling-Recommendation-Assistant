"""衣物图片识别服务：先提取主色，后续可接入 CLIP 等模型。"""
import uuid
from pathlib import Path
from typing import Any, Dict

from PIL import Image

from backend.core.config import BASE_DIR


UPLOAD_DIR = BASE_DIR / "uploads"

RGB_COLOR_MAP = {
    "黑色": (0, 0, 0),
    "白色": (255, 255, 255),
    "灰色": (128, 128, 128),
    "蓝色": (0, 0, 255),
    "红色": (255, 0, 0),
    "绿色": (0, 128, 0),
    "黄色": (255, 255, 0),
    "粉色": (255, 192, 203),
    "紫色": (128, 0, 128),
    "橙色": (255, 165, 0),
    "棕色": (139, 69, 19),
    "米色": (245, 245, 220),
}


def _distance(color_a: tuple, color_b: tuple) -> float:
    return sum((a - b) ** 2 for a, b in zip(color_a, color_b))


def _nearest_color_name(rgb: tuple) -> str:
    return min(
        RGB_COLOR_MAP,
        key=lambda name: _distance(rgb, RGB_COLOR_MAP[name]),
    )


def _load_center_image(image_path: Path) -> Image.Image:
    """读取图片并裁剪中央主体区域，减少背景颜色干扰。"""
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    return image.crop((
        width // 4,
        height // 4,
        width * 3 // 4,
        height * 3 // 4,
    ))


def extract_dominant_color(image_path: Path) -> str:
    """裁剪中央区域后统计主色。"""
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
    average_rgb = tuple(
        round(sum(pixel[i] for pixel in pixels if (
            pixel[0] // 64 * 64,
            pixel[1] // 64 * 64,
            pixel[2] // 64 * 64,
        ) == dominant_bucket) / buckets[dominant_bucket])
        for i in range(3)
    )
    return _nearest_color_name(average_rgb)


def extract_dominant_colors(image_path: Path, top_n: int = 3) -> list:
    """返回中央主体区域占比最高的几个颜色标签。"""
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

    ordered_buckets = sorted(
        buckets.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    result = []
    for bucket, _ in ordered_buckets[:top_n]:
        items = [
            pixel
            for pixel in pixels
            if (
                pixel[0] // 64 * 64,
                pixel[1] // 64 * 64,
                pixel[2] // 64 * 64,
            ) == bucket
        ]
        average_rgb = tuple(
            round(sum(item[i] for item in items) / len(items))
            for i in range(3)
        )
        color_name = _nearest_color_name(average_rgb)
        if color_name not in result:
            result.append(color_name)
    return result


def save_upload_image(content: bytes, original_name: str) -> Path:
    """把上传图片保存到 uploads 目录并返回路径。"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_name).suffix or ".jpg"
    file_name = f"{uuid.uuid4().hex}{suffix}"
    file_path = UPLOAD_DIR / file_name
    file_path.write_bytes(content)
    return file_path


def analyze_image(file_path: Path, original_name: str) -> Dict[str, Any]:
    """识别图片并生成待确认的衣柜数据。"""
    colors = extract_dominant_colors(file_path)
    color = colors[0] if colors else "未知"
    return {
        "name": "识别衣物",
        "category": "上衣",
        "color": color,
        "season": "四季",
        "style": "休闲",
        "color_tags": colors,
        "style_tags": ["休闲"],
        "fit_tags": ["基础款"],
        "occasion_tags": ["日常"],
        "image_path": str(file_path),
        "recognition_status": "pending",
    }
