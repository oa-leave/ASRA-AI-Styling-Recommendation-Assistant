from collections import Counter
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database.models import RecommendationHistory


def _constraints(history: RecommendationHistory) -> Dict[str, Any]:
    return (history.request_context or {}).get("constraints", {})


def _outcome(history: RecommendationHistory) -> Dict[str, Any]:
    return (history.response_snapshot or {}).get("outcome", {})


def _items(history: RecommendationHistory) -> List[Dict[str, Any]]:
    return (history.response_snapshot or {}).get("items", []) or []


def _names_text(history: RecommendationHistory) -> str:
    parts = []
    for item in _items(history):
        parts.append(str(item.get("name") or ""))
        parts.append(str(item.get("slot") or ""))
    return " ".join(parts)


def _required_satisfied(history: RecommendationHistory) -> bool:
    constraints = _constraints(history)
    if not constraints:
        return False

    required = constraints.get("required_item_keywords") or []
    excluded = constraints.get("excluded_item_keywords") or []
    required_colors = constraints.get("required_colors") or []
    allowed = constraints.get("allowed_item_keywords") or []
    allowed_colors = constraints.get("allowed_colors") or []
    avoid_colors = constraints.get("avoid_colors") or []
    names = _names_text(history)

    if any(keyword and keyword not in names for keyword in required):
        return False
    if any(keyword and keyword in names for keyword in excluded):
        return False

    item_colors = [
        str(item.get("color") or "")
        for item in _items(history)
    ]
    item_texts = [
        f"{item.get('name') or ''} {item.get('slot') or ''}"
        for item in _items(history)
    ]
    if allowed and not all(
        any(keyword in text for keyword in allowed)
        for text in item_texts
    ):
        return False
    if any(
        color and not any(color in item_color for item_color in item_colors)
        for color in required_colors
    ):
        return False
    if any(
        color and any(color in item_color for item_color in item_colors)
        for color in avoid_colors
    ):
        return False
    if allowed_colors and not all(
        any(color in item_color for item_color in item_colors)
        for color in allowed_colors
    ):
        return False

    return True


def _style_matches(style: Optional[str], expected: Optional[str]) -> bool:
    if not expected:
        return False
    if expected in {"商务", "正式"}:
        return style in {"商务", "正式"}
    return style == expected


def _style_hit(history: RecommendationHistory) -> bool:
    constraints = _constraints(history)
    expected = constraints.get("requested_style")
    if not expected:
        return False
    return any(
        _style_matches(item.get("style"), expected)
        for item in _items(history)
    )


def compute_metrics(
    db: Session,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    query = db.query(RecommendationHistory)
    if user_id is not None:
        query = query.filter(RecommendationHistory.user_id == user_id)
    histories = query.all()

    outcomes = [_outcome(history) for history in histories]
    total = len(histories)
    success_count = sum(
        1
        for outcome in outcomes
        if outcome.get("has_recommendation")
    )
    no_recommendation_reasons = Counter(
        outcome.get("no_reason")
        for outcome in outcomes
        if not outcome.get("has_recommendation")
        and outcome.get("no_reason")
    )

    constrained = [
        history
        for history in histories
        if _constraints(history)
    ]
    constraint_satisfied = sum(
        1
        for history in constrained
        if _outcome(history).get("has_recommendation")
        and _required_satisfied(history)
    )

    style_records = [
        history
        for history in histories
        if _constraints(history).get("requested_style")
        and _outcome(history).get("has_recommendation")
    ]
    style_hits = sum(
        1
        for history in style_records
        if _style_hit(history)
    )

    return {
        "total_requests": total,
        "recommendation_success_rate": (
            round(success_count / total, 4)
            if total
            else 0
        ),
        "constraint_satisfaction_rate": (
            round(constraint_satisfied / len(constrained), 4)
            if constrained
            else 0
        ),
        "style_hit_rate": (
            round(style_hits / len(style_records), 4)
            if style_records
            else None
        ),
        "no_recommendation_reasons": dict(
            no_recommendation_reasons
        ),
    }
