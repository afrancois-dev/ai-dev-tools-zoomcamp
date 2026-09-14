"""HTTP routes for the KanbanLite API.

Paths keep the `/api` prefix so the served URLs match the OpenAPI `servers`
entry (`http://localhost:8000/api`). Every state-changing operation returns the
full board.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from .db import InMemoryBoardRepository
from .dependencies import get_repository
from .models import (
    Board,
    CreateCardRequest,
    CreateColumnRequest,
    MoveCardRequest,
    UpdateCardRequest,
)

router = APIRouter(prefix="/api")


@router.get("/board", response_model=Board, tags=["Board"], summary="Fetch the whole board")
def get_board(
    repository: InMemoryBoardRepository = Depends(get_repository),
) -> Board:
    return repository.get_board()


@router.post(
    "/columns",
    response_model=Board,
    status_code=status.HTTP_201_CREATED,
    tags=["Columns"],
    summary="Create a column",
)
def create_column(
    payload: CreateColumnRequest,
    repository: InMemoryBoardRepository = Depends(get_repository),
) -> Board:
    return repository.create_column(payload.title)


@router.post(
    "/cards",
    response_model=Board,
    status_code=status.HTTP_201_CREATED,
    tags=["Cards"],
    summary="Create a card",
)
def create_card(
    payload: CreateCardRequest,
    repository: InMemoryBoardRepository = Depends(get_repository),
) -> Board:
    return repository.create_card(
        column_id=payload.column_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
    )


@router.patch(
    "/cards/{id}",
    response_model=Board,
    tags=["Cards"],
    summary="Update a card",
)
def update_card(
    id: UUID,
    payload: UpdateCardRequest,
    repository: InMemoryBoardRepository = Depends(get_repository),
) -> Board:
    return repository.update_card(
        id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
    )


@router.delete(
    "/cards/{id}",
    response_model=Board,
    tags=["Cards"],
    summary="Delete a card",
)
def delete_card(
    id: UUID,
    repository: InMemoryBoardRepository = Depends(get_repository),
) -> Board:
    return repository.delete_card(id)


@router.patch(
    "/cards/{id}/move",
    response_model=Board,
    tags=["Cards"],
    summary="Move a card",
)
def move_card(
    id: UUID,
    payload: MoveCardRequest,
    repository: InMemoryBoardRepository = Depends(get_repository),
) -> Board:
    return repository.move_card(
        id, column_id=payload.column_id, position=payload.position
    )
