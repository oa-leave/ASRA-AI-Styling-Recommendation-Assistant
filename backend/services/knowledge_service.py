"""穿搭知识库：基于关键词检索穿搭规则，后续可升级为向量检索。"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "fashion_rules.json"

OCCASION_TAGS = {
    "日常",
    "通勤",
    "商务",
    "约会",
    "运动",
    "旅行",
    "户外",
    "登山",
    "正式",
    "婚礼",
    "宴会",
    "面试",
    "会议",
    "客户",
    "出差",
    "校园",
    "居家",
    "逛街",
    "聚会",
    "健身",
    "跑步",
}


def load_fashion_rules() -> List[Dict[str, Any]]:
    if not RULES_PATH.exists():
        return []
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def retrieve_fashion_rules(
    style: Optional[str] = None,
    occasion: Optional[str] = None,
    season: Optional[str] = None,
    colors: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """根据当前上下文检索最相关的穿搭知识。"""
    query_tags = set()
    if style:
        query_tags.add(style)
    if occasion:
        query_tags.add(occasion)
    if season:
        query_tags.add(season)
    for color in colors or []:
        query_tags.add(color)
    for tag in tags or []:
        query_tags.add(tag)

    if not query_tags:
        return []

    scored = []
    for rule in load_fashion_rules():
        rule_tags = set(rule.get("tags", []))
        rule_occasions = rule_tags & OCCASION_TAGS
        if rule_occasions and not (rule_occasions & query_tags):
            continue
        overlap = len(query_tags & rule_tags)
        if overlap:
            scored.append((overlap, rule))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [rule for _, rule in scored[:limit]]


def build_knowledge_text(rules: List[Dict[str, Any]]) -> str:
    return "；".join(rule["content"] for rule in rules)
