"""Pydantic schemas mirroring openapi.yaml."""

from datetime import datetime
from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator


class Priority(str, Enum):
    """Card priority level."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Text = Annotated[str, StringConstraints(strip_whitespace=True)]


class Column(BaseModel):
    """A status column on the single board."""

    id: UUID
    title: str
    order: int


class Card(BaseModel):
    """A task card belonging to exactly one column."""

    id: UUID
    column_id: UUID
    title: str
    description: str = ""
    priority: Priority
    created_at: datetime
    due_date: str = ""
    position: int


class Board(BaseModel):
    """The complete board state, returned by every endpoint."""

    columns: list[Column]
    cards: list[Card]


class CreateColumnRequest(BaseModel):
    title: Title


class CreateCardRequest(BaseModel):
    column_id: UUID
    title: Title
    description: Text = ""
    priority: Priority = Priority.MEDIUM
    due_date: str = ""


class UpdateCardRequest(BaseModel):
    """Partial card update; at least one field must be provided."""

    title: Title | None = None
    description: Text | None = None
    priority: Priority | None = None
    due_date: str | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "UpdateCardRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class MoveCardRequest(BaseModel):
    column_id: UUID
    position: int = Field(ge=0)
