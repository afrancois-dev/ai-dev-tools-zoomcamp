"""KanbanLite FastAPI application."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import CardNotFound, ColumnNotFound
from .dependencies import init_db, repository
from .routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Safe to call repeatedly: create_all and seeding are idempotent.
    init_db()
    repository.ensure_seeded()
    yield


app = FastAPI(
    title="KanbanLite API",
    version="1.0.0",
    description=(
        "Backend for the KanbanLite Mini Kanban Board. Open access: no "
        "endpoint requires authentication. Persistence is database-agnostic "
        "SQLAlchemy (SQLite by default) configured through DATABASE_URL."
    ),
    lifespan=lifespan,
)

# The frontend calls the API from a different origin during development
# (Vite on :5173). Authentication is not used yet, so a permissive policy is
# acceptable for the MVP.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.exception_handler(CardNotFound)
async def card_not_found_handler(
    _request: Request, exc: CardNotFound
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ColumnNotFound)
async def column_not_found_handler(
    _request: Request, exc: ColumnNotFound
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})
