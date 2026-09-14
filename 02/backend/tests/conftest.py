"""Shared pytest fixtures.

Each test gets a brand-new in-memory SQLite database and repository, injected
through FastAPI's dependency-override mechanism so tests never share state.

`DATABASE_URL` is pinned before the app is imported so that importing it never
creates the on-disk `kanbanlite.db`.
"""

import os

os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base, BoardRepository, create_engine_and_session_factory
from app.dependencies import get_repository
from app.main import app


@pytest.fixture()
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine, factory = create_engine_and_session_factory("sqlite://")
    Base.metadata.create_all(engine)
    try:
        yield factory
    finally:
        engine.dispose()


@pytest.fixture()
def repository(session_factory: sessionmaker[Session]) -> BoardRepository:
    # Constructing the repository seeds the five default columns.
    return BoardRepository(session_factory)


@pytest.fixture()
def client(repository: BoardRepository) -> Iterator[TestClient]:
    app.dependency_overrides[get_repository] = lambda: repository
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
