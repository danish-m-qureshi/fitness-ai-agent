import logging

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exception_handlers import (
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppException
from app.core.logging import configure_logging
from app.core.middleware import RequestContextAndAuthMiddleware
from app.services.scheduler.summary_scheduler import (
    shutdown_summary_scheduler,
    start_summary_scheduler,
)
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    app.add_middleware(RequestContextAndAuthMiddleware, settings=settings)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(
        api_router,
        prefix=settings.api_v1_prefix,
    )

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {
            "message": f"{settings.app_name} is running",
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
            "status": f"{settings.api_v1_prefix}/status",
        }

    @app.on_event("startup")
    def startup() -> None:
        app.state.summary_scheduler = start_summary_scheduler(settings)

    @app.on_event("shutdown")
    def shutdown() -> None:
        shutdown_summary_scheduler(
            getattr(app.state, "summary_scheduler", None),
        )

    logger.info("Application started in %s mode", settings.environment)

    return app


app = create_app()
