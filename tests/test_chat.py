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
        json={"session_id": session_id, "message": "不要蓝色"},
    )
    assert second.status_code == 200
    assert second.json()["session_id"] == session_id

    conversation = client.get(f"/chat/conversations/{session_id}", headers=headers)
    assert conversation.status_code == 200
    assert len(conversation.json()["messages"]) >= 2
    assert "蓝色" in conversation.json()["context"]["avoid_colors"]
