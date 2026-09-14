"""Shared pytest fixtures.

Each test gets a brand-new in-memory repository, injected through FastAPI's
dependency-override mechanism so tests never share state.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.db import InMemoryBoardRepository
from app.dependencies import get_repository
from app.main import app


@pytest.fixture()
def repository() -> InMemoryBoardRepository:
    return InMemoryBoardRepository()


@pytest.fixture()
def client(repository: InMemoryBoardRepository) -> Iterator[TestClient]:
    app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
