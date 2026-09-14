"""FastAPI dependency wiring."""

from .db import InMemoryBoardRepository

# Single process-wide mock database. Tests override `get_repository` with a
# fresh instance so state never leaks between test cases.
_repository = InMemoryBoardRepository()


def get_repository() -> InMemoryBoardRepository:
    return _repository
