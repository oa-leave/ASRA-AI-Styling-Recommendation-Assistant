import os
import tempfile
from pathlib import Path


tmp_dir = tempfile.mkdtemp(prefix="asra_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(tmp_dir, 'test.db').as_posix()}"
os.environ["SECRET_KEY"] = "test-secret-key"

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_home():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_register_login_wardrobe_profile_and_feedback():
    payload = {
        "email": "test@example.com",
        "username": "test_user",
        "password": "password123",
    }
    register_response = client.post("/user/register", json=payload)
    assert register_response.status_code == 201

    duplicate_response = client.post("/user/register", json=payload)
    assert duplicate_response.status_code == 409

    login_response = client.post(
        "/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    unauthorized_wardrobe = client.get("/wardrobe/")
    assert unauthorized_wardrobe.status_code == 401

    wardrobe_response = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "color_tags": ["白色", "基础色"],
            "style_tags": ["休闲"],
            "fit_tags": ["宽松"],
        },
    )
    assert wardrobe_response.status_code == 201

    list_response = client.get("/wardrobe/", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["color_tags"] == ["白色", "基础色"]

    profile_response = client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "基础色"],
            "style_tags": ["休闲", "极简"],
        },
    )
    assert profile_response.status_code == 201
    assert profile_response.json()["favorite_colors"] == ["白色", "基础色"]
    assert profile_response.json()["style_tags"] == ["休闲", "极简"]

    feedback_response = client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "like",
            "outfit_score": 350,
            "outfit_snapshot": {"上衣": "白色T恤"},
            "reason": ["整体风格统一"],
        },
    )
    assert feedback_response.status_code == 201

    feedback_list = client.get("/feedback/", headers=headers)
    assert feedback_list.status_code == 200
    assert len(feedback_list.json()) == 1
