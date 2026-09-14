"""KanbanLite FastAPI application."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import CardNotFound, ColumnNotFound
from .routes import router

app = FastAPI(
    title="KanbanLite API",
    version="1.0.0",
    description=(
        "Backend for the KanbanLite Mini Kanban Board. Open access: no "
        "endpoint requires authentication. Uses an in-memory mock database "
        "that will be replaced by real persistence later."
    ),
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
