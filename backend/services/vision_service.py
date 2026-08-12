"""视觉识别服务：优先调用本地 OpenAI 兼容视觉模型，失败时回退到 HSV + 文件名规则。"""
import base64
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
import json5
from PIL import Image

from backend.core.config import settings
from backend.services.recommendation_config import CATEGORIES, SEASONS, STYLES
from backend.services.recommendation_engine import normalize_colors


MODEL_CATEGORY_ALIASES = {
    "上衣": "上衣",
    "top": "上衣",
    "shirt": "上衣",
    "tee": "上衣",
    "sweater": "上衣",
    "cardigan": "上衣",
    "t-shirt": "上衣",
    "blouse": "上衣",
    "sweater": "上衣",
    "裤子": "裤子",
    "pants": "裤子",
    "trousers": "裤子",
    "jeans": "裤子",
    "shorts": "裤子",
    "bottoms": "裤子",
    "bottom": "裤子",
    "裙子": "裙子",
    "skirt": "裙子",
    "dress": "连衣裙",
    "连衣裙": "连衣裙",
    "one-piece": "连衣裙",
    "旗袍": "旗袍",
    "cheongsam": "旗袍",
    "汉服": "汉服",
    "外套": "外套",
    "jacket": "外套",
    "coat": "外套",
    "blazer": "外套",
    "鞋子": "鞋子",
    "shoes": "鞋子",
    "shoe": "鞋子",
    "sneakers": "鞋子",
    "sneaker": "鞋子",
    "footwear": "鞋子",
    "sports shoes": "鞋子",
    "boots": "鞋子",
    "配饰": "配饰",
    "accessory": "配饰",
    "帽子": "帽子",
    "hat": "帽子",
    "包包": "包包",
    "bag": "包包",
    "内搭": "内搭",
}

MODEL_STYLE_ALIASES = {
    "休闲": "休闲",
    "casual": "休闲",
    "商务": "商务",
    "formal": "商务",
    "business": "商务",
    "运动": "运动",
    "sport": "运动",
    "sports": "运动",
    "sporty": "运动",
    "athletic": "运动",
    "sneakers": "运动",
    "peacoat": "正式",
    "crew neck": "基础款",
    "日系": "日系",
    "japanese": "日系",
    "极简": "极简",
    "minimal": "极简",
    "中式": "中式",
    "chinese": "中式",
}

MODEL_FIT_ALIASES = {
    "基础款": "基础款",
    "regular": "基础款",
    "standard": "基础款",
    "修身": "修身",
    "slim": "修身",
    "slim fit": "修身",
    "宽松": "宽松",
    "loose": "宽松",
    "oversized": "宽松",
    "baggy": "宽松",
    "直筒": "直筒",
    "straight": "直筒",
    "紧身": "紧身",
    "skinny": "紧身",
}

MODEL_OCCASION_ALIASES = {
    "日常": "日常",
    "everyday": "日常",
    "daily": "日常",
    "casual": "日常",
    "通勤": "通勤",
    "work": "通勤",
    "office": "通勤",
    "约会": "约会",
    "date": "约会",
    "运动": "运动",
    "sport": "运动",
    "workout": "运动",
    "旅行": "旅行",
    "travel": "旅行",
    "正式": "正式",
    "formal": "正式",
    "婚礼": "婚礼",
    "wedding": "婚礼",
    "宴会": "宴会",
    "party": "宴会",
}

MODEL_NAME_TRANSLATIONS = {
    "jeans": "牛仔裤",
    "sneaker": "运动鞋",
    "sneakers": "运动鞋",
    "t-shirt": "T恤",
    "shirt": "衬衫",
    "dress": "连衣裙",
    "skirt": "半身裙",
    "jacket": "外套",
    "coat": "大衣",
    "sweater": "毛衣",
    "hoodie": "卫衣",
}

MODEL_SEASON_ALIASES = {
    "春季": "春季",
    "spring": "春季",
    "夏季": "夏季",
    "summer": "夏季",
    "秋季": "秋季",
    "autumn": "秋季",
    "fall": "秋季",
    "冬季": "冬季",
    "winter": "冬季",
    "四季": "四季",
    "all-season": "四季",
}


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


def _as_list(value) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _match_alias(value, aliases):
    text = str(value or "").lower().strip()
    for alias, canonical in aliases.items():
        if alias in text:
            return canonical
    return None


def _translate_tags(tags, aliases):
    translated = []
    for tag in tags:
        translated.append(_match_alias(tag, aliases) or tag)
    return translated


def _translate_clothing_name(name: str, color: str = "", category: str = "") -> str:
    text = str(name or "").lower()
    keyword = None
    if any(word in text for word in ("sneaker", "shoe", "shoes", "footwear", "boots")):
        keyword = "运动鞋"
    elif any(word in text for word in ("jeans", "pants", "trousers", "bottoms")):
        keyword = "牛仔裤" if "jeans" in text else "裤子"
    elif any(word in text for word in ("peacoat", "overcoat", "coat")):
        keyword = "大衣"
    elif any(word in text for word in ("jacket", "blazer")):
        keyword = "外套"
    elif any(word in text for word in ("t恤", "t-shirt", "tee", "短袖")):
        keyword = "T恤"
    elif any(word in text for word in ("sweater", "cardigan")):
        keyword = "毛衣"
    elif any(word in text for word in ("hoodie",)):
        keyword = "卫衣"
    elif any(word in text for word in ("shirt",)):
        keyword = "衬衫"
    elif any(word in text for word in ("dress",)):
        keyword = "连衣裙"
    elif any(word in text for word in ("skirt",)):
        keyword = "半身裙"

    if keyword:
        prefix = color.strip() if color and color.strip() else ""
        return f"{prefix}{keyword}" if prefix else keyword
    return MODEL_NAME_TRANSLATIONS.get(name.lower(), str(name or "").strip() or "识别衣物")


def _infer_season(name: str) -> str:
    text = name.lower()
    if any(word in text for word in ("短袖", "t恤", "tee", "短裤", "凉鞋", "背心", "tank")):
        return "夏季"
    if any(word in text for word in ("羽绒", "棉服", "毛衣", "厚外套", "winter")):
        return "冬季"
    if any(word in text for word in ("外套", "风衣", "夹克", "衬衫", "jacket", "coat")):
        return "春秋"
    return "四季"


def _normalize_model_result(
    data: Any,
    original_name: str,
) -> Dict[str, Any]:
    if not isinstance(data, dict):
        return None

    category = _match_alias(data.get("category"), MODEL_CATEGORY_ALIASES)
    if not category:
        category = _infer_category(original_name)

    color_groups = normalize_colors(str(data.get("color") or ""))
    if not color_groups:
        return None
    color = color_groups[0]

    style = _match_alias(data.get("style"), MODEL_STYLE_ALIASES)
    if not style:
        style = _infer_style(original_name)

    season = _match_alias(data.get("season"), MODEL_SEASON_ALIASES) or "四季"

    raw_name = str(data.get("name") or "").strip() or "识别衣物"
    name = _translate_clothing_name(raw_name, color, category)
    color_tags = normalize_colors(_as_list(data.get("color_tags")))
    if not color_tags:
        color_tags = [color]
    if color not in color_tags:
        color_tags = [color, *color_tags]

    style_tags = _translate_tags(
        _as_list(data.get("style_tags")),
        MODEL_STYLE_ALIASES,
    ) or [style]
    fit_tags = _translate_tags(
        _as_list(data.get("fit_tags")),
        MODEL_FIT_ALIASES,
    ) or [_infer_fit(original_name)]
    occasion_tags = _translate_tags(
        _as_list(data.get("occasion_tags")),
        MODEL_OCCASION_ALIASES,
    )
    if not occasion_tags:
        occasion_tags = _infer_occasion(original_name)

    name_hint = (
        f"{raw_name} {name} {' '.join(color_tags)} "
        f"{' '.join(style_tags)} {' '.join(occasion_tags)}"
    ).lower()
    if any(word in name_hint for word in ("sneaker", "shoe", "shoes", "footwear", "boots")):
        category = "鞋子"
    elif any(word in name_hint for word in ("pants", "trousers", "jeans", "bottoms", "shorts")):
        category = "裤子"
    elif any(word in name_hint for word in ("dress", "one-piece")):
        category = "连衣裙"
    elif any(word in name_hint for word in ("skirt",)):
        category = "裙子"
    elif any(word in name_hint for word in ("jacket", "coat", "blazer")):
        category = "外套"
    elif any(
        word in name_hint
        for word in ("t恤", "短袖", "tee", "shirt", "top", "sweater", "cardigan")
    ):
        category = "上衣"

    return {
        "name": name,
        "category": category,
        "color": color,
        "style": style,
        "season": season,
        "color_tags": color_tags,
        "style_tags": style_tags,
        "fit_tags": fit_tags,
        "occasion_tags": occasion_tags,
    }


def _encode_image_for_model(image_path: Path) -> str:
    image = Image.open(image_path).convert("RGB")
    image.thumbnail((
        settings.vision_max_image_size,
        settings.vision_max_image_size,
    ))
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _ollama_api_root() -> str:
    url = settings.vision_base_url.rstrip("/")
    if url.endswith("/v1"):
        return url[:-3].rstrip("/")
    return url


def _parse_model_json(content):
    if isinstance(content, dict):
        return content
    text = str(content or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    return json5.loads(text)


def _recognize_with_ollama_native(
    image_path: Path,
    original_name: str,
) -> Dict[str, Any]:
    encoded_image = _encode_image_for_model(image_path)
    response = requests.post(
        f"{_ollama_api_root()}/api/chat",
        json={
            "model": settings.vision_model,
            "format": "json",
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是ASRA的衣物识别模型。"
                        "只输出一个JSON对象，不要解释，不要Markdown。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "识别这张衣物图片。返回JSON，字段：name、category、"
                        "color、style、season、color_tags、style_tags、"
                        "fit_tags、occasion_tags。category必须是：内搭、上衣、"
                        "裤子、裙子、连衣裙、旗袍、汉服、外套、鞋子、配饰、"
                        "帽子、包包。"
                    ),
                    "images": [encoded_image],
                },
            ],
            "options": {
                "temperature": 0,
                "num_predict": 500,
            },
        },
        timeout=settings.vision_timeout,
    )
    response.raise_for_status()
    content = response.json()["message"]["content"]
    data = _parse_model_json(content)
    return _normalize_model_result(data, original_name)


def _recognize_with_openai_compatible(
    image_path: Path,
    original_name: str,
) -> Dict[str, Any]:
    encoded_image = _encode_image_for_model(image_path)
    response = requests.post(
        f"{settings.vision_base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.vision_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.vision_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是ASRA的衣物识别模型。只输出JSON，字段："
                        "name、category、color、style、season、"
                        "color_tags、style_tags、fit_tags、occasion_tags。"
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "识别这张衣物图片。"
                                f"文件名：{original_name}。"
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            },
                        },
                    ],
                },
            ],
            "temperature": 0,
            "max_tokens": 500,
            "response_format": {"type": "json_object"},
        },
        timeout=settings.vision_timeout,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    data = _parse_model_json(content)
    return _normalize_model_result(data, original_name)


def recognize_with_vision_model(
    image_path: Path,
    original_name: str = "",
) -> Dict[str, Any]:
    if not settings.vision_enabled:
        return None

    try:
        result = _recognize_with_ollama_native(image_path, original_name)
        if result:
            return result
    except Exception:
        pass

    try:
        return _recognize_with_openai_compatible(image_path, original_name)
    except Exception:
        return None


def _heuristic_vision_result(
    image_path: Path,
    original_name: str = "",
) -> Dict[str, Any]:
    """从图片提取颜色并生成待确认的衣物标签。"""
    rgb = _dominant_rgb(image_path)
    color = _color_name_from_hsv(rgb)
    name = Path(original_name).stem.strip() or "识别衣物"

    color_tags: List[str] = [color]
    if color in {"白色", "黑色", "灰色"}:
        color_tags.append("中性色")

    return {
        "name": name,
        "category": _infer_category(original_name),
        "color": color,
        "style": _infer_style(original_name),
        "season": _infer_season(original_name),
        "color_tags": color_tags,
        "style_tags": [_infer_style(original_name)],
        "fit_tags": [_infer_fit(original_name)],
        "occasion_tags": _infer_occasion(original_name),
    }


def extract_vision_result(
    image_path: Path,
    original_name: str = "",
) -> Dict[str, Any]:
    """优先使用真实视觉模型，失败时回退到启发式识别。"""
    model_result = recognize_with_vision_model(image_path, original_name)
    if model_result:
        return model_result
    return _heuristic_vision_result(image_path, original_name)
