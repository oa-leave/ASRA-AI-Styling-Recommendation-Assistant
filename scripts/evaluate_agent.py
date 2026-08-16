import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(
    0,
    str(Path(__file__).resolve().parent.parent),
)

from backend.agent.decision import deterministic_decision
from backend.services.conversation_service import parse_adjustments


FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "tests"
    / "fixtures"
    / "eval_queries.json"
)


def _subset(actual: List[str], expected: List[str]) -> bool:
    return set(expected or []).issubset(set(actual or []))


def _evaluate_case(case: Dict[str, Any]) -> Dict[str, Any]:
    query = case["query"]
    context = parse_adjustments(query, {})
    plan = deterministic_decision(
        query,
        case.get("city"),
        case.get("occasion"),
        None,
    )
    expect = case.get("expect", {})
    checks: Dict[str, bool] = {}

    for key in (
        "required_item_keywords",
        "exclude_item_keywords",
        "allowed_item_keywords",
        "avoid_colors",
        "required_colors",
        "item_conflicts",
        "style_conflicts",
    ):
        if key in expect:
            checks[key] = _subset(context.get(key, []), expect[key])

    if "style" in expect:
        checks["style"] = plan.get("style") == expect["style"]
    if "scene_type" in expect:
        checks["scene_type"] = (
            plan.get("scene_type") == expect["scene_type"]
        )
    if "business_requested" in expect:
        checks["business_requested"] = (
            bool(context.get("business_requested"))
            == expect["business_requested"]
        )
    if "formal_requested" in expect:
        checks["formal_requested"] = (
            bool(context.get("formal_requested"))
            == expect["formal_requested"]
        )
    if "requested_season" in expect:
        checks["requested_season"] = (
            context.get("requested_season") == expect["requested_season"]
        )

    passed = all(checks.values())
    return {
        "id": case.get("id"),
        "query": query,
        "passed": passed,
        "checks": checks,
        "parsed": {
            "scene_type": plan.get("scene_type"),
            "style": plan.get("style"),
            "required_item_keywords": context.get(
                "required_item_keywords"
            ),
            "exclude_item_keywords": context.get(
                "exclude_item_keywords"
            ),
            "allowed_item_keywords": context.get(
                "allowed_item_keywords"
            ),
            "avoid_colors": context.get("avoid_colors"),
            "required_colors": context.get("required_colors"),
            "style_conflicts": context.get("style_conflicts"),
            "item_conflicts": context.get("item_conflicts"),
        },
    }


def evaluate_queries(path: Path = FIXTURE_PATH) -> Dict[str, Any]:
    cases = json.loads(path.read_text(encoding="utf-8"))
    results = [_evaluate_case(case) for case in cases]
    total = len(results)
    passed = sum(1 for result in results if result["passed"])
    return {
        "total_cases": total,
        "passed_cases": passed,
        "intent_accuracy": round(passed / total, 4) if total else 0,
        "failures": [
            result
            for result in results
            if not result["passed"]
        ],
    }


if __name__ == "__main__":
    print(
        json.dumps(
            evaluate_queries(),
            ensure_ascii=False,
            indent=2,
        )
    )
