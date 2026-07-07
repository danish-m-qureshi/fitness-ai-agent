import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_meta_webhook_verification_succeeds_without_api_key(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "test-api-key")
    monkeypatch.setenv("WHATSAPP_META_VERIFY_TOKEN", "verify-me")

    app = create_app()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-me",
                "hub.challenge": "challenge-123",
            },
        )

    assert response.status_code == 200
    assert response.text == "challenge-123"
    assert response.headers["x-request-id"]


def test_meta_webhook_verification_rejects_invalid_token(monkeypatch) -> None:
    monkeypatch.setenv("WHATSAPP_META_VERIFY_TOKEN", "expected-token")

    app = create_app()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge-123",
            },
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "whatsapp_webhook_verification_failed"


def test_api_key_auth_protects_non_webhook_routes(monkeypatch) -> None:
    monkeypatch.setenv("API_KEY_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "test-api-key")

    app = create_app()

    with TestClient(app) as client:
        missing_key = client.get("/")
        valid_key = client.get("/", headers={"X-API-Key": "test-api-key"})

    assert missing_key.status_code == 401
    assert missing_key.json()["error"]["code"] == "invalid_api_key"
    assert valid_key.status_code == 200


def test_docs_and_openapi_can_be_disabled_for_public_exposure(monkeypatch) -> None:
    monkeypatch.setenv("DOCS_ENABLED", "false")
    monkeypatch.setenv("API_KEY_ENABLED", "false")

    app = create_app()

    with TestClient(app) as client:
        docs = client.get("/docs")
        openapi = client.get("/openapi.json")

    assert docs.status_code == 404
    assert openapi.status_code == 404


def test_debug_routes_are_hidden_when_debug_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("DEBUG", "false")
    monkeypatch.setenv("API_KEY_ENABLED", "false")

    app = create_app()

    with TestClient(app) as client:
        response = client.get("/api/v1/debug/config")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "debug_route_not_found"
