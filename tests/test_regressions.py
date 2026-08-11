import uuid
from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient
from PIL import Image

from backend.agent.tools import get_weather
from backend.main import app
from backend.services.recommendation_engine import build_top_outfits


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


def test_invalid_login_rejected():
    username = _unique("invalid_login")
    _register_and_login(username)
    response = client.post(
        "/auth/login",
        data={"username": username, "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_invalid_token_rejected():
    response = client.get(
        "/profile/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401


def test_profile_duplicate_returns_409():
    username = _unique("duplicate_profile")
    headers = _register_and_login(username)
    payload = {
        "style": "休闲",
        "favorite_color": "白色",
        "body_type": "标准",
        "season": "夏季",
    }
    assert client.post("/profile/create", headers=headers, json=payload).status_code == 201
    assert client.post("/profile/create", headers=headers, json=payload).status_code == 409


def test_wardrobe_update_preserves_recognition_status_when_omitted():
    username = _unique("keep_status")
    headers = _register_and_login(username)
    created = client.post(
        "/wardrobe/add",
        headers=headers,
        json={
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
            "recognition_status": "confirmed",
        },
    )
    assert created.status_code == 201
    clothes_id = created.json()["clothes_id"]

    updated = client.put(
        f"/wardrobe/{clothes_id}",
        headers=headers,
        json={
            "name": "白色长袖T恤",
            "category": "上衣",
            "color": "白色",
            "season": "春秋",
            "style": "休闲",
        },
    )
    assert updated.status_code == 200

    items = client.get("/wardrobe/", headers=headers).json()
    item = next(item for item in items if item["id"] == clothes_id)
    assert item["name"] == "白色长袖T恤"
    assert item["recognition_status"] == "confirmed"


def test_invalid_image_upload_returns_400():
    username = _unique("bad_image")
    headers = _register_and_login(username)
    response = client.post(
        "/wardrobe/analyze-image",
        headers=headers,
        files={"file": ("bad.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400

    auto_response = client.post(
        "/wardrobe/upload-and-confirm",
        headers=headers,
        files={"file": ("bad.txt", b"not an image", "text/plain")},
    )
    assert auto_response.status_code == 400


def test_feedback_invalid_type_returns_422():
    username = _unique("bad_feedback")
    headers = _register_and_login(username)
    response = client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "unknown",
            "outfit_score": 100,
            "outfit_snapshot": {},
            "reason": [],
        },
    )
    assert response.status_code == 422


def test_dislike_removes_color_from_favorite_colors():
    username = _unique("dislike_color")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "蓝色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["蓝色", "白色"],
            "avoid_colors": [],
        },
    )

    response = client.post(
        "/feedback/",
        headers=headers,
        json={
            "feedback_type": "dislike",
            "outfit_score": 100,
            "outfit_snapshot": {"颜色": "蓝色"},
            "reason": ["不喜欢"],
        },
    )
    assert response.status_code == 201

    profile = client.get("/profile/me", headers=headers).json()
    assert "蓝色" in profile["avoid_colors"]
    assert "蓝色" not in profile["favorite_colors"]
    assert "白色" in profile["favorite_colors"]


def test_force_outerwear_overrides_summer_season_filter():
    profile = SimpleNamespace(season="夏季")
    clothes = [
        {
            "id": 1,
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "style": "休闲",
            "season": "夏季",
            "score": 100,
            "reason": ["风格"],
        },
        {
            "id": 2,
            "name": "黑色短裤",
            "category": "裤子",
            "color": "黑色",
            "style": "休闲",
            "season": "夏季",
            "score": 90,
            "reason": ["风格"],
        },
        {
            "id": 3,
            "name": "蓝色薄外套",
            "category": "外套",
            "color": "蓝色",
            "style": "休闲",
            "season": "夏季",
            "score": 80,
            "reason": ["风格"],
        },
    ]

    results = build_top_outfits(
        clothes,
        profile,
        force_slot=["外套"],
    )
    assert "外套" in results[0]["outfit"]


def test_wardrobe_ownership_errors():
    owner = _unique("owner_a")
    owner_headers = _register_and_login(owner)
    created = client.post(
        "/wardrobe/add",
        headers=owner_headers,
        json={
            "name": "白色T恤",
            "category": "上衣",
            "color": "白色",
            "season": "夏季",
            "style": "休闲",
        },
    )
    assert created.status_code == 201
    clothes_id = created.json()["clothes_id"]

    other_headers = _register_and_login(_unique("owner_b"))
    update_response = client.put(
        f"/wardrobe/{clothes_id}",
        headers=other_headers,
        json={
            "name": "黑色T恤",
            "category": "上衣",
            "color": "黑色",
            "season": "夏季",
            "style": "休闲",
        },
    )
    assert update_response.status_code == 403

    delete_response = client.delete(
        f"/wardrobe/{clothes_id}",
        headers=other_headers,
    )
    assert delete_response.status_code == 403
    assert client.get("/wardrobe/", headers=other_headers).json() == []


def test_chat_session_ownership_denied():
    owner_headers = _register_and_login(_unique("chat_owner"))
    session_id = _unique("session")
    created = client.post(
        "/chat/",
        headers=owner_headers,
        json={"session_id": session_id, "message": "你好"},
    )
    assert created.status_code == 200

    other_headers = _register_and_login(_unique("chat_other"))
    denied = client.post(
        "/chat/",
        headers=other_headers,
        json={"session_id": session_id, "message": "继续"},
    )
    assert denied.status_code == 403

    not_found = client.get(
        f"/chat/conversations/{session_id}",
        headers=other_headers,
    )
    assert not_found.status_code == 404


def test_recommend_without_matching_clothes_returns_friendly_message():
    username = _unique("no_match")
    headers = _register_and_login(username)
    client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "avoid_colors": ["白色"],
        },
    )

    response = client.get("/recommend/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"]["items"] == []
    assert any("没有符合条件的衣物" in item for item in data["recommendation"]["summary"])
    assert data["history_id"] is not None


def test_weather_api_failure_falls_back(monkeypatch):
    def raise_request_error(*args, **kwargs):
        raise RuntimeError("network offline")

    monkeypatch.setattr("backend.agent.tools.requests.get", raise_request_error)
    weather = get_weather("上海", use_api=True)
    assert weather["source"] == "fallback"
    assert weather["temperature"] == 28


def test_upload_analyze_and_confirm_ownership(monkeypatch):
    owner_headers = _register_and_login(_unique("task_owner"))
    image = BytesIO()
    Image.new("RGB", (32, 32), (255, 255, 255)).save(image, format="JPEG")
    image.seek(0)
    uploaded = client.post(
        "/wardrobe/analyze-image",
        headers=owner_headers,
        files={"file": ("white.jpg", image, "image/jpeg")},
    )
    assert uploaded.status_code == 200
    task_id = uploaded.json()["task_id"]

    other_headers = _register_and_login(_unique("task_other"))
    update_response = client.put(
        f"/wardrobe/task/{task_id}",
        headers=other_headers,
        json={"name": "修改后的衣物"},
    )
    assert update_response.status_code == 403

    confirm_response = client.post(
        f"/wardrobe/confirm-task/{task_id}",
        headers=other_headers,
    )
    assert confirm_response.status_code == 403
