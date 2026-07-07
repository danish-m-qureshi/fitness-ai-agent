import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.models  # noqa: E402,F401
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402


@pytest.fixture(autouse=True)
def isolate_test_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    monkeypatch.setenv("API_KEY_ENABLED", "false")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DOCS_ENABLED", "true")
    get_settings.cache_clear()

    try:
        yield
    finally:
        get_settings.cache_clear()


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
