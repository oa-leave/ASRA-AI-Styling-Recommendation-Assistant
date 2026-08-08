from io import BytesIO

from PIL import Image
from fastapi.testclient import TestClient

from backend.main import app
from database.connection import SessionLocal
from database.models import UserProfile


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
            "occasion_tags": ["通勤"],
        },
    )
    assert wardrobe_response.status_code == 201

    list_response = client.get("/wardrobe/", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["color_tags"] == ["白色", "基础色"]
    assert list_response.json()[0]["occasion_tags"] == ["通勤"]

    image_bytes = BytesIO()
    Image.new("RGB", (32, 32), (255, 255, 255)).save(image_bytes, format="JPEG")
    image_bytes.seek(0)
    upload_response = client.post(
        "/wardrobe/analyze-image",
        headers=headers,
        files={"file": ("white.jpg", image_bytes, "image/jpeg")},
    )
    assert upload_response.status_code == 200
    candidate = upload_response.json()
    assert candidate["color"] == "白色"
    assert candidate["image_path"]
    assert candidate["recognition_status"] == "pending"

    confirm_response = client.post(
        "/wardrobe/confirm-image",
        headers=headers,
        json={
            **candidate,
            "name": "白色T恤",
            "recognition_status": "confirmed",
        },
    )
    assert confirm_response.status_code == 201

    confirmed_list = client.get("/wardrobe/", headers=headers)
    assert len(confirmed_list.json()) == 2

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
            "fit_tags": ["宽松"],
            "avoid_colors": ["红色"],
            "occasion_preferences": ["通勤"],
        },
    )
    assert profile_response.status_code == 201
    assert profile_response.json()["favorite_colors"] == ["白色", "基础色"]
    assert profile_response.json()["style_tags"] == ["休闲", "极简"]
    assert profile_response.json()["fit_tags"] == ["宽松"]
    assert profile_response.json()["avoid_colors"] == ["红色"]
    assert profile_response.json()["occasion_preferences"] == ["通勤"]

    recommend_response = client.get("/recommend/", headers=headers)
    assert recommend_response.status_code == 200
    recommend_data = recommend_response.json()
    assert "items" in recommend_data["recommendation"]
    assert "summary" in recommend_data["recommendation"]
    assert "recommendations" in recommend_data
    assert len(recommend_data["recommendations"]) >= 1
    assert "history_id" in recommend_data

    agent_response = client.post(
        "/agent/recommend",
        headers=headers,
        json={"city": "沈阳", "occasion": "通勤", "style": "休闲"},
    )
    assert agent_response.status_code == 200
    assert "recommendation" in agent_response.json()
    assert "weather" in agent_response.json()
    assert "tool_plan" in agent_response.json()
    assert "explanation" in agent_response.json()
    assert "history_id" in agent_response.json()
    assert "memory" in agent_response.json()

    query_agent_response = client.post(
        "/agent/recommend",
        headers=headers,
        json={"query": "明天上海约会穿什么？"},
    )
    assert query_agent_response.status_code == 200
    assert query_agent_response.json()["tool_plan"] == [
        "weather",
        "scene",
        "memory",
        "recommend",
    ]

    memory_response = client.get("/memory/", headers=headers)
    assert memory_response.status_code == 200
    assert "profile" in memory_response.json()
    assert "recent_history" in memory_response.json()
    assert "preference_signals" in memory_response.json()

    history_response = client.get("/history/", headers=headers)
    assert history_response.status_code == 200
    assert len(history_response.json()) >= 1

    db = SessionLocal()
    profile_row = (
        db.query(UserProfile)
        .filter(UserProfile.user_id == profile_response.json()["user_id"])
        .first()
    )
    profile_row.favorite_colors = None
    profile_row.style_tags = None
    profile_row.fit_tags = None
    profile_row.avoid_colors = None
    profile_row.occasion_preferences = None
    db.commit()
    db.close()

    legacy_profile_response = client.get("/profile/me", headers=headers)
    assert legacy_profile_response.status_code == 200
    assert legacy_profile_response.json()["favorite_colors"] == []
    assert legacy_profile_response.json()["style_tags"] == []
    assert legacy_profile_response.json()["fit_tags"] == []
    assert legacy_profile_response.json()["avoid_colors"] == []
    assert legacy_profile_response.json()["occasion_preferences"] == []

    update_response = client.put(
        "/profile/me",
        headers=headers,
        json={
            "style": "商务",
            "favorite_color": "蓝色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色", "黑色"],
            "style_tags": ["简约", "通勤"],
            "fit_tags": ["修身"],
            "avoid_colors": ["粉色"],
            "occasion_preferences": ["通勤", "会议"],
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["style"] == "商务"
    assert update_response.json()["favorite_colors"] == ["蓝色", "黑色"]
    assert update_response.json()["avoid_colors"] == ["粉色"]

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
