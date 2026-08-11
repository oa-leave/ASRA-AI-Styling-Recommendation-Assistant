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
