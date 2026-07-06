from app.main import create_app
from fastapi.testclient import TestClient


def test_status_endpoint_returns_request_id() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/api/v1/status")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json()["status"] == "running"


def test_db_health_endpoint() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.get("/api/v1/health/db")

    assert response.status_code == 200
    assert response.json()["service"] == "db"
