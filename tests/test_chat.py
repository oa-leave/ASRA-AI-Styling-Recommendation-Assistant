from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_multi_turn_chat():
    payload = {
        "email": "chat@example.com",
        "username": "chat_user",
        "password": "password123",
    }
    client.post("/user/register", json=payload)
    login = client.post(
        "/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    profile_response = client.post(
        "/profile/create",
        headers=headers,
        json={
            "style": "休闲",
            "favorite_color": "白色",
            "body_type": "标准",
            "season": "夏季",
            "favorite_colors": ["白色", "黑色", "灰色"],
            "style_tags": ["休闲"],
            "fit_tags": ["宽松"],
            "avoid_colors": ["红色"],
            "occasion_preferences": ["日常"],
        },
    )
    assert profile_response.status_code == 201

    custom_session = client.post(
        "/chat/",
        headers=headers,
        json={"session_id": "custom_test", "message": "你好"},
    )
    assert custom_session.status_code == 200
    assert custom_session.json()["session_id"] == "custom_test"

    first = client.post(
        "/chat/",
        headers=headers,
        json={"message": "明天上海约会穿什么？"},
    )
    assert first.status_code == 200
    session_id = first.json()["session_id"]

    second = client.post(
        "/chat/",
        headers=headers,
        json={"session_id": session_id, "message": "不要黑色"},
    )
    assert second.status_code == 200
    assert second.json()["session_id"] == session_id

    conversation = client.get(f"/chat/conversations/{session_id}", headers=headers)
    assert conversation.status_code == 200
    assert len(conversation.json()["messages"]) >= 2
    assert "黑色" in conversation.json()["context"]["avoid_colors"]

    memory_after_avoid = client.get("/memory/", headers=headers)
    assert "黑色" not in memory_after_avoid.json()["profile"]["favorite_colors"]
    assert "黑色" not in memory_after_avoid.json()["preference_signals"]["favorite_colors"]

    third = client.post(
        "/chat/",
        headers=headers,
        json={"session_id": session_id, "message": "要黑色"},
    )
    assert third.status_code == 200
    assert "黑色" not in third.json()["reply"]["conversation_context"]["avoid_colors"]

    fourth = client.post(
        "/chat/",
        headers=headers,
        json={"session_id": session_id, "message": "最近喜欢灰色"},
    )
    assert fourth.status_code == 200

    fifth = client.post(
        "/chat/",
        headers=headers,
        json={"session_id": session_id, "message": "最近喜欢蓝色"},
    )
    assert fifth.status_code == 200

    memory_response = client.get("/memory/", headers=headers)
    assert memory_response.status_code == 200
    assert "黑色" in memory_response.json()["profile"]["favorite_colors"]
    assert "灰色" in memory_response.json()["profile"]["favorite_colors"]
    assert "蓝色" in memory_response.json()["profile"]["favorite_colors"]
