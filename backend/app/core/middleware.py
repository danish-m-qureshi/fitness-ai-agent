import hmac
import logging
import time
import uuid
from contextvars import ContextVar

from app.core.config import Settings
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)
request_id_context: ContextVar[str] = ContextVar(
    "request_id",
    default="-",
)


class RequestContextAndAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        token = request_id_context.set(request_id)
        request.state.request_id = request_id
        started_at = time.perf_counter()

        try:
            auth_response = self._auth_response_if_needed(request, request_id)
            if auth_response is not None:
                response = auth_response
                return auth_response

            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            status_code = locals().get("response")
            status_value = getattr(status_code, "status_code", "-")
            logger.info(
                "request completed method=%s path=%s status_code=%s duration_ms=%s",
                request.method,
                request.url.path,
                status_value,
                duration_ms,
            )
            if "response" in locals():
                response.headers["X-Request-ID"] = request_id
            request_id_context.reset(token)

    def _auth_response_if_needed(
        self,
        request: Request,
        request_id: str,
    ) -> JSONResponse | None:
        if not self.settings.api_key_enabled or self._is_public_path(request.url.path):
            return None

        configured_key = self.settings.api_key or ""
        provided_key = request.headers.get("X-API-Key") or ""

        if configured_key and hmac.compare_digest(provided_key, configured_key):
            return None

        status_code = 401 if configured_key else 503
        error_code = "invalid_api_key" if configured_key else "api_key_not_configured"
        message = (
            "Invalid or missing API key."
            if configured_key
            else "API key auth is enabled but API_KEY is not configured."
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": {},
                    "request_id": request_id,
                }
            },
            headers={"X-Request-ID": request_id},
        )

    def _is_public_path(self, path: str) -> bool:
        webhook_path = f"{self.settings.api_v1_prefix}/webhooks/whatsapp"
        public_prefixes = (f"{webhook_path}/",)
        return path == webhook_path or any(
            path.startswith(prefix) for prefix in public_prefixes
        )
