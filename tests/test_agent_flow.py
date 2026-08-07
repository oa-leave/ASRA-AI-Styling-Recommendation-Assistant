from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_agent_full_flow():
    payload = {
        "email": "flow@example.com",
        "username": "flow_user",
        "password": "password123",
    }
    register_response = client.post("/user/register", json=payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        data={
            "username": payload["username"],
            "password": payload["password"],
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile_response = client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色"],
            "style_tags": ["休闲"],
            "fit_tags": ["宽松"],
            "avoid_colors": [],
            "occasion_preferences": ["日常"],
        },
    )
    assert profile_response.status_code == 201

    wardrobe_response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "color_tags": ["白色"],
            "style_tags": ["休闲"],
            "fit_tags": ["宽松"],
            "occasion_tags": ["日常"],
        },
    )
    assert wardrobe_response.status_code == 201

    agent_response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "今天穿什么",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert agent_response.status_code == 200

    data = agent_response.json()
    for key in [
        "weather",
        "scene",
        "tool_plan",
        "recommendation",
        "memory",
        "explanation",
        "history_id",
    ]:
        assert key in data

    history_response = client.get("/history/", headers=headers)
    assert history_response.status_code == 200
    assert len(history_response.json()) >= 1

    scene_agent_response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "上海约会穿什么",
            "city": "上海",
            "occasion": "约会",
            "style": "日系",
        },
    )
    assert scene_agent_response.status_code == 200
    assert scene_agent_response.json()["scene"]["style"] == "日系"
    assert scene_agent_response.json()["scene"]["occasion_tags"] == ["约会"]

    first_items = data["recommendation"]["items"]
    liked_item = next(item for item in first_items if item["name"] == "白色T恤")
    first_score = liked_item["score"]

    feedback_response = client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "like",
            "outfit_score": data["recommendation"]["outfit_score"],
            "outfit_snapshot": {"上衣": "白色T恤"},
            "reason": ["喜欢这套"],
        },
    )
    assert feedback_response.status_code == 201

    memory_agent_response = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "今天穿什么",
            "city": "沈阳",
            "occasion": "日常",
            "style": "休闲",
        },
    )
    assert memory_agent_response.status_code == 200
    second_items = memory_agent_response.json()["recommendation"]["items"]
    liked_item_after = next(
        item for item in second_items if item["name"] == "白色T恤"
    )
    assert liked_item_after["score"] > first_score
