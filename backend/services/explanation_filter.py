"""解释过滤：避免推荐解释和知识库引用用户回避的颜色。"""
from typing import List, Optional, Set


def build_forbidden_tokens(avoid_colors: Optional[List[str]]) -> Set[str]:
    tokens = set(avoid_colors or [])
    if "黑色" in tokens or "白色" in tokens:
        tokens.add("黑白")
    if "黑色" in tokens or "白色" in tokens or "灰色" in tokens:
        tokens.add("黑白灰")
    return tokens


def filter_summary(
    summary: List[str],
    avoid_colors: Optional[List[str]],
) -> List[str]:
    tokens = build_forbidden_tokens(avoid_colors)
    if not tokens:
        return summary
    return [
        item
        for item in summary
        if not any(token in item for token in tokens)
    ]


def filter_text(text: Optional[str], avoid_colors: Optional[List[str]]) -> str:
    if not text:
        return ""
    tokens = build_forbidden_tokens(avoid_colors)
    if not tokens:
        return text
    return "；".join(
        sentence
        for sentence in text.split("；")
        if not any(token in sentence for token in tokens)
    )
