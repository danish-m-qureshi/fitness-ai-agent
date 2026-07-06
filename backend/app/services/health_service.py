import socket
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx
from app.core.config import Settings
from app.schemas.health import HealthAggregateResponse, ServiceHealthResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


class HealthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def aggregate(self, db: Session) -> HealthAggregateResponse:
        services = {
            "app": self.app(),
            "db": self.db(db),
            "redis": self.redis(),
            "qdrant": self.qdrant(),
            "ollama": self.ollama(),
        }
        status = "ok"
        if any(item.status == "unavailable" for item in services.values()):
            status = "degraded"
        elif any(item.status == "degraded" for item in services.values()):
            status = "degraded"

        return HealthAggregateResponse(
            status=status,
            checked_at_utc=datetime.now(UTC),
            services=services,
        )

    def app(self) -> ServiceHealthResponse:
        return self._response(
            service="app",
            status="ok",
            details={
                "name": self.settings.app_name,
                "version": self.settings.app_version,
                "environment": self.settings.environment,
            },
        )

    def db(self, db: Session) -> ServiceHealthResponse:
        try:
            db.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            return self._response(
                service="db",
                status="unavailable",
                details={"error": str(exc.__class__.__name__)},
            )

        return self._response(service="db", status="ok")

    def redis(self) -> ServiceHealthResponse:
        if not self.settings.redis_url:
            return self._response(
                service="redis",
                status="disabled",
                details={"reason": "REDIS_URL is not configured."},
            )

        parsed = urlparse(self.settings.redis_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6379

        try:
            with socket.create_connection((host, port), timeout=2) as sock:
                sock.sendall(b"*1\r\n$4\r\nPING\r\n")
                response = sock.recv(16)
        except OSError as exc:
            return self._response(
                service="redis",
                status="unavailable",
                details={"host": host, "port": port, "error": str(exc)},
            )

        if response.startswith(b"+PONG"):
            return self._response(
                service="redis",
                status="ok",
                details={"host": host, "port": port},
            )

        return self._response(
            service="redis",
            status="degraded",
            details={
                "host": host,
                "port": port,
                "response": response.decode("utf-8", "ignore"),
            },
        )

    def qdrant(self) -> ServiceHealthResponse:
        url = f"http://{self.settings.qdrant_host}:{self.settings.qdrant_port}"
        try:
            response = httpx.get(f"{url}/collections", timeout=5)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return self._response(
                service="qdrant",
                status="unavailable",
                details={"url": url, "error": str(exc)},
            )

        return self._response(
            service="qdrant",
            status="ok",
            details={"url": url, "collection": self.settings.qdrant_collection_name},
        )

    def ollama(self) -> ServiceHealthResponse:
        try:
            response = httpx.get(
                f"{self.settings.ollama_base_url.rstrip('/')}/api/tags",
                timeout=5,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return self._response(
                service="ollama",
                status="unavailable",
                details={"url": self.settings.ollama_base_url, "error": str(exc)},
            )

        models = response.json().get("models", [])
        model_names = [item.get("name") for item in models if isinstance(item, dict)]
        return self._response(
            service="ollama",
            status="ok",
            details={
                "url": self.settings.ollama_base_url,
                "vision_model": self.settings.vision_model,
                "vision_model_available": self._model_available(
                    self.settings.vision_model,
                    model_names,
                ),
                "embedding_model": self.settings.embedding_model_name,
                "embedding_model_available": self._model_available(
                    self.settings.embedding_model_name,
                    model_names,
                ),
            },
        )

    def _response(
        self,
        service: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> ServiceHealthResponse:
        return ServiceHealthResponse(
            service=service,
            status=status,
            checked_at_utc=datetime.now(UTC),
            details=details or {},
        )

    def _model_available(self, model: str, model_names: list[str | None]) -> bool:
        return any(
            name == model or (isinstance(name, str) and name.split(":")[0] == model)
            for name in model_names
        )
