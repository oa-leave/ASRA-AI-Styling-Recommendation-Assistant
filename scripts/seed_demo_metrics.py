"""Seed demo metrics on the deployed ASRA service."""

import json
import uuid

import requests


BASE_URL = "https://asra-8f01.onrender.com"

QUERIES = [
    ("要运动风", False),
    ("只推荐蓝色上衣，不要黑色", True),
    ("只推荐蓝色上衣", True),
    ("只推荐上衣，不要黑色", True),
    ("只推荐上衣", True),
    ("只要上衣，不要黑色", True),
    ("只要蓝色上衣", True),
    ("只要上衣，不要白色", True),
    ("只要上衣，不要红色", True),
    ("要休闲风，只推荐上衣", True),
]


def _post(path, headers=None, json_body=None, form=None):
    response = requests.post(
        f"{BASE_URL}{path}",
        headers=headers,
        json=json_body,
        data=form,
        timeout=90,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"{path} -> {response.status_code}: {response.text}")
    return response.json()


def _get(path, headers=None):
    response = requests.get(
        f"{BASE_URL}{path}",
        headers=headers,
        timeout=90,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"{path} -> {response.status_code}: {response.text}")
    return response.json()


def main():
    suffix = uuid.uuid4().hex[:8]
    username = f"demo_{suffix}"
    password = "Password123!"
    email = f"{username}@example.com"

    _post(
        "/user/register",
        json_body={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    login = _post(
        "/auth/login",
        form={"username": username, "password": password},
    )
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    _post(
        "/profile/create",
        headers=headers,
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
        headers=headers,
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

    for query, should_match in QUERIES:
        result = _post(
            "/agent/recommend",
            headers=headers,
            json_body={
                "query": query,
                "city": "沈阳",
                "occasion": "日常",
            },
        )
        items = result.get("recommendation", {}).get("items", [])
        if bool(items) != should_match:
            raise RuntimeError(f"Unexpected result for: {query}")

    metrics = _get("/evaluation/metrics", headers=headers)
    print(
        json.dumps(
            {
                "username": username,
                "metrics": metrics,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
