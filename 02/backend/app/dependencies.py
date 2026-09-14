"""FastAPI dependency wiring.

`DATABASE_URL` selects the database. The default is a SQLite file next to the
backend so data persists across restarts; point it at PostgreSQL (or anything
else SQLAlchemy supports) to switch without code changes.
"""

import os
from pathlib import Path

from .db import Base, BoardRepository, create_engine_and_session_factory

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "kanbanlite.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DATABASE_PATH}")

engine, session_factory = create_engine_and_session_factory(DATABASE_URL)


def init_db() -> None:
    """Create tables if they do not exist yet."""
    Base.metadata.create_all(engine)


# Tables must exist before the repository seeds the default columns.
init_db()
repository = BoardRepository(session_factory)


def get_repository() -> BoardRepository:
    return repository
