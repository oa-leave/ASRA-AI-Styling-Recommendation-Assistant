"""Local ASRA load test for health and recommendation endpoints."""

import concurrent.futures
import json
import os
import time
import uuid
from collections import Counter

import requests


BASE_URL = os.getenv("ASRA_BASE_URL", "http://127.0.0.1:8011")
ROOT_TOTAL = int(os.getenv("ASRA_ROOT_TOTAL", "300"))
ROOT_WORKERS = int(os.getenv("ASRA_ROOT_WORKERS", "30"))
RECOMMEND_TOTAL = int(os.getenv("ASRA_RECOMMEND_TOTAL", "60"))
RECOMMEND_WORKERS = int(os.getenv("ASRA_RECOMMEND_WORKERS", "10"))


def _percentile(values, ratio):
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = (len(ordered) - 1) * ratio
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * weight, 2)


def _summary(results):
    statuses = Counter(str(status) for status, _duration, _ok in results)
    success = sum(1 for _status, _duration, ok in results if ok)
    latencies = [duration * 1000 for _status, duration, _ok in results]
    return {
        "total": len(results),
        "success": success,
        "failed": len(results) - success,
        "error_rate": round((len(results) - success) / len(results), 4) if results else 0,
        "status_counts": dict(statuses),
        "latency_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "max": round(max(latencies), 2) if latencies else 0,
        },
    }


def _post(path, headers=None, json_body=None, form=None):
    response = requests.post(
        f"{BASE_URL}{path}",
        headers=headers,
        json=json_body,
        data=form,
        timeout=30,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"{path} -> {response.status_code}: {response.text}")
    return response.json()


def _get(path, headers=None):
    response = requests.get(f"{BASE_URL}{path}", headers=headers, timeout=30)
    if response.status_code >= 400:
        raise RuntimeError(f"{path} -> {response.status_code}: {response.text}")
    return response.json()


def _root_request(_index):
    start = time.perf_counter()
    try:
        response = requests.get(f"{BASE_URL}/", timeout=30)
        return response.status_code, time.perf_counter() - start, response.status_code == 200
    except Exception as exc:
        return 0, time.perf_counter() - start, False


def _recommend_request(_index):
    start = time.perf_counter()
    try:
        response = requests.post(
            f"{BASE_URL}/agent/recommend",
            headers=HEADERS,
            json={
                "query": "只推荐蓝色上衣，不要黑色",
                "city": "沈阳",
                "occasion": "日常",
            },
            timeout=30,
        )
        items = response.json().get("recommendation", {}).get("items", [])
        ok = response.status_code == 200 and bool(items)
        return response.status_code, time.perf_counter() - start, ok
    except Exception:
        return 0, time.perf_counter() - start, False


def _run(total, workers, task):
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(task, range(total)))
    elapsed = time.perf_counter() - start
    return results, elapsed


def main():
    suffix = uuid.uuid4().hex[:8]
    username = f"load_{suffix}"
    password = "Password123!"
    _post(
        "/user/register",
        json_body={
            "username": username,
            "email": f"{username}@example.com",
            "password": password,
        },
    )
    login = _post("/auth/login", form={"username": username, "password": password})
    global HEADERS
    HEADERS = {"Authorization": f"Bearer {login['access_token']}"}
    _post(
        "/profile/create",
        headers=HEADERS,
        json_body={
            "style": "休闲",
            "favorite_color": "蓝色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色"],
            "avoid_colors": [],
        },
    )
    _post(
        "/wardrobe/add",
        headers=HEADERS,
        json_body={
            "name": "蓝色衬衫",
            "category": "上衣",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
    )

    _get("/", headers=HEADERS)
    root_results, root_elapsed = _run(ROOT_TOTAL, ROOT_WORKERS, _root_request)
    root_report = _summary(root_results)
    root_report["qps"] = round(ROOT_TOTAL / root_elapsed, 2)

    recommend_results, recommend_elapsed = _run(
        RECOMMEND_TOTAL,
        RECOMMEND_WORKERS,
        _recommend_request,
    )
    recommend_report = _summary(recommend_results)
    recommend_report["qps"] = round(RECOMMEND_TOTAL / recommend_elapsed, 2)

    print(
        json.dumps(
            {
                "target": BASE_URL,
                "username": username,
                "health_endpoint": root_report,
                "recommend_endpoint": recommend_report,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
