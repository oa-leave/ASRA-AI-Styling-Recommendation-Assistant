from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_frontend_index_is_served():
    response = client.get("/app/")
    assert response.status_code == 200
    assert "ASRA" in response.text


def test_frontend_static_assets_are_served():
    assert client.get("/app/styles.css").status_code == 200
    assert client.get("/app/app.js").status_code == 200


def test_frontend_reset_button_present():
    index = client.get("/app/").text
    assert "reset-test-btn" in index
    assert "重置对话/反馈" in index
    app_js = client.get("/app/app.js").text
    assert "resetTestData" in app_js
