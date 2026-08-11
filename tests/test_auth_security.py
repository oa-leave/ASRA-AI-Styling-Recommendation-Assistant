import uuid

from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def _unique(name):
    return f"{name}_{uuid.uuid4().hex[:8]}"


def _register(username):
    response = client.post(
        "/user/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "password123",
        },
    )
    assert response.status_code == 201


def _login(username):
    response = client.post(
        "/auth/login",
        data={"username": username, "password": "password123"},
    )
    assert response.status_code == 200
    return response.json()


def test_login_returns_refresh_token():
    username = _unique("login_refresh")
    _register(username)
    data = _login(username)
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]


def test_refresh_token_rotation_revokes_old_token():
    username = _unique("refresh_rotation")
    _register(username)
    first = _login(username)

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert refreshed.status_code == 200
    second = refreshed.json()
    assert second["refresh_token"] != first["refresh_token"]

    reused = client.post(
        "/auth/refresh",
        json={"refresh_token": first["refresh_token"]},
    )
    assert reused.status_code == 401


def test_logout_revokes_refresh_token():
    username = _unique("logout_revoke")
    _register(username)
    login = _login(username)

    logout = client.post(
        "/auth/logout",
        json={"refresh_token": login["refresh_token"]},
    )
    assert logout.status_code == 200

    refreshed = client.post(
        "/auth/refresh",
        json={"refresh_token": login["refresh_token"]},
    )
    assert refreshed.status_code == 401


def test_login_locks_after_repeated_failures():
    username = _unique("login_lockout")
    _register(username)

    for _ in range(5):
        failed = client.post(
            "/auth/login",
            data={"username": username, "password": "wrong-password"},
        )
        assert failed.status_code == 401

    locked = client.post(
        "/auth/login",
        data={"username": username, "password": "wrong-password"},
    )
    assert locked.status_code == 429


def test_cors_denies_unconfigured_origin():
    response = client.options(
        "/",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
