import uuid

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def _unique(name):
    return f"{name}_{uuid.uuid4().hex[:8]}"


def _register_and_login(username):
    payload = {
        "email": f"{username}@example.com",
        "username": username,
        "password": "password123",
    }
    response = client.post("/user/register", json=payload)
    assert response.status_code == 201
    login = client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_evaluation_metrics_endpoint():
    username = _unique("evaluation")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "蓝色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色"],
            "avoid_colors": [],
        },
    )
    response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "蓝色衬衫",
            "category": "上衣",
            "color": "蓝色",
            "season": "夏季",
            "style": "休闲",
            "fit_tags": ["标准"],
            "occasion_tags": ["日常"],
        },
    )
    assert response.status_code == 201

    no_match = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "要运动风",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert no_match.status_code == 200
    assert no_match.json()["recommendation"]["items"] == []

    matched = client.post(
        "/agent/recommend",
        headers=headers,
        json={
            "query": "只推荐蓝色上衣，不要黑色",
            "city": "沈阳",
            "occasion": "日常",
        },
    )
    assert matched.status_code == 200
    assert matched.json()["recommendation"]["items"]

    metrics = client.get("/evaluation/metrics", headers=headers)
    assert metrics.status_code == 200
    data = metrics.json()
    assert data["total_requests"] == 2
    assert data["recommendation_success_rate"] == 0.5
    assert data["no_recommendation_reasons"].get("style_not_found") == 1
    assert "constraint_satisfaction_rate" in data
    assert "style_hit_rate" in data
