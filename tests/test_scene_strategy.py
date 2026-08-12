import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.scene_strategy import (
    apply_scene_preferences,
    build_scene_feedback,
)


client = TestClient(app)


def _unique(name):
    return f"{name}_{uuid.uuid4().hex[:8]}"


def test_formal_scene_returns_missing_slots_and_suggestions():
    outfit = {
        "上衣": {"name": "灰色T恤", "category": "上衣"},
    }
    feedback = build_scene_feedback(
        {"style": "商务", "occasion_tags": ["通勤"]},
        outfit,
    )
    assert feedback["missing_slots"] == ["裤子", "鞋子"]
    assert "白色衬衫" in feedback["suggestions"]
    assert "当前衣柜缺少裤子、鞋子" in feedback["warning"]


def test_complete_formal_outfit_has_no_warning():
    outfit = {
        "上衣": {"name": "白色衬衫", "category": "上衣"},
        "裤子": {"name": "深色直筒裤", "category": "裤子"},
        "鞋子": {"name": "黑色皮鞋", "category": "鞋子"},
    }
    feedback = build_scene_feedback(
        {"style": "商务", "occasion_tags": ["通勤"]},
        outfit,
    )
    assert feedback["missing_slots"] == []
    assert feedback["warning"] is None


def test_date_scene_uses_soft_and_formal_suggestions():
    outfit = {
        "上衣": {"name": "灰色T恤", "category": "上衣"},
        "裤子": {"name": "牛仔裤", "category": "裤子"},
        "鞋子": {"name": "运动鞋", "category": "鞋子"},
    }
    feedback = build_scene_feedback(
        {"style": "休闲", "occasion_tags": ["约会"]},
        outfit,
    )
    assert feedback["suggestions"] == ["柔和色上衣", "直筒裤", "乐福鞋"]
    assert feedback["warning"] is not None


def test_apply_scene_preferences_boosts_all_matching_slots():
    items = [
        {"name": "灰色T恤", "category": "上衣", "occasion_tags": ["日常"], "score": 100},
        {"name": "白色衬衫", "category": "上衣", "occasion_tags": ["商务会议"], "score": 100},
        {"name": "牛仔裤", "category": "裤子", "occasion_tags": ["日常"], "score": 100},
        {"name": "黑色西裤", "category": "裤子", "occasion_tags": ["通勤"], "score": 100},
        {"name": "白色运动鞋", "category": "鞋子", "occasion_tags": ["日常"], "score": 100},
        {"name": "黑色皮鞋", "category": "鞋子", "occasion_tags": ["商务"], "score": 100},
    ]
    adjusted = apply_scene_preferences(
        items,
        {"style": "商务", "occasion_tags": ["正式", "通勤"]},
    )
    scores = {item["name"]: item["score"] for item in adjusted}
    assert scores["白色衬衫"] > scores["灰色T恤"]
    assert scores["黑色西裤"] > scores["牛仔裤"]
    assert scores["黑色皮鞋"] > scores["白色运动鞋"]


def test_agent_formal_response_includes_scene_feedback():
    username = _unique("formal_scene")
    client.post(
        "/user/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "password123",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色", "白色"],
            "avoid_colors": ["蓝色"],
        },
    )
    client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "灰色T恤",
            "category": "上衣",
            "color": "灰色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
    )

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={"city": "沈阳", "style": "商务"},
    )
    assert response.status_code == 200
    data = response.json()
    feedback = data["recommendation"]["scene_feedback"]
    assert feedback is not None
    assert "裤子" in feedback["missing_slots"]
    assert "鞋子" in feedback["missing_slots"]
    assert data["occasion"] == "正式"


def test_agent_formal_prefers_shirt_over_tshirt():
    username = _unique("formal_shirt")
    client.post(
        "/user/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "password123",
        },
    )
    login = client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["灰色", "白色"],
            "avoid_colors": [],
        },
    )
    for item in [
        {
            "name": "灰色T恤",
            "category": "上衣",
            "color": "灰色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
        {
            "name": "白色的长袖男士手工制作的纯棉衬衣",
            "category": "上衣",
            "color": "白色",
            "season": "春季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["工作", "婚礼", "商务会议"],
        },
    ]:
        client.post("/wardrobe/add", headers=headers, json=item)

    response = client.post(
        "/agent/recommend",
        headers=headers,
        json={"city": "沈阳", "occasion": "通勤", "style": "商务"},
    )
    assert response.status_code == 200
    items = response.json()["recommendation"]["items"]
    assert any("衬衣" in item["name"] for item in items)
