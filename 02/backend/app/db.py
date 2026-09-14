"""Mock (in-memory) database.

This is a stand-in for the real persistence layer. The repository interface is
deliberately small so it can be swapped for a database-backed implementation
later without touching the routes.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .models import Board, Card, Column, Priority

DEFAULT_COLUMN_TITLES = [
    "To Do",
    "In Progress",
    "Deployed in Staging",
    "Deployed in Production",
    "On Hold",
]


class CardNotFound(LookupError):
    def __init__(self, card_id: UUID) -> None:
        super().__init__(f"Card {card_id} not found")


class ColumnNotFound(LookupError):
    def __init__(self, column_id: UUID) -> None:
        super().__init__(f"Column {column_id} not found")


class InMemoryBoardRepository:
    """Thread-safe, in-memory board store seeded with the default columns."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._columns: list[Column] = []
        self._cards: list[Card] = []
        self.reset()

    def reset(self) -> None:
        """Restore the initial state: five empty default columns."""
        with self._lock:
            self._columns = [
                Column(id=uuid4(), title=title, order=order)
                for order, title in enumerate(DEFAULT_COLUMN_TITLES)
            ]
            self._cards = []

    def get_board(self) -> Board:
        with self._lock:
            return self._snapshot()

    def create_column(self, title: str) -> Board:
        with self._lock:
            next_order = max((column.order for column in self._columns), default=-1)
            self._columns.append(
                Column(id=uuid4(), title=title, order=next_order + 1)
            )
            return self._snapshot()

    def create_card(
        self,
        *,
        column_id: UUID,
        title: str,
        description: str,
        priority: Priority,
        due_date: str,
    ) -> Board:
        with self._lock:
            if self._find_column(column_id) is None:
                raise ColumnNotFound(column_id)

            position = sum(
                1 for card in self._cards if card.column_id == column_id
            )
            self._cards.append(
                Card(
                    id=uuid4(),
                    column_id=column_id,
                    title=title,
                    description=description,
                    priority=priority,
                    created_at=datetime.now(timezone.utc),
                    due_date=due_date,
                    position=position,
                )
            )
            return self._snapshot()

    def update_card(
        self,
        card_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        due_date: str | None = None,
    ) -> Board:
        with self._lock:
            card = self._find_card(card_id)
            if card is None:
                raise CardNotFound(card_id)

            if title is not None:
                card.title = title
            if description is not None:
                card.description = description
            if priority is not None:
                card.priority = priority
            if due_date is not None:
                card.due_date = due_date

            return self._snapshot()

    def delete_card(self, card_id: UUID) -> Board:
        with self._lock:
            if self._find_card(card_id) is None:
                raise CardNotFound(card_id)

            self._cards = [card for card in self._cards if card.id != card_id]
            self._renormalize_positions()
            return self._snapshot()

    def move_card(self, card_id: UUID, *, column_id: UUID, position: int) -> Board:
        with self._lock:
            card = self._find_card(card_id)
            if card is None:
                raise CardNotFound(card_id)
            if self._find_column(column_id) is None:
                raise ColumnNotFound(column_id)

            # Detach the card, then make room for it at the target position.
            self._cards = [candidate for candidate in self._cards if candidate.id != card_id]
            target = sorted(
                (candidate for candidate in self._cards if candidate.column_id == column_id),
                key=lambda candidate: candidate.position,
            )
            index = max(0, min(position, len(target)))

            card.column_id = column_id
            card.position = index
            for candidate in target:
                if candidate.position >= index:
                    candidate.position += 1

            self._cards.append(card)
            self._renormalize_positions()
            return self._snapshot()

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _find_column(self, column_id: UUID) -> Column | None:
        return next(
            (column for column in self._columns if column.id == column_id), None
        )

    def _find_card(self, card_id: UUID) -> Card | None:
        return next((card for card in self._cards if card.id == card_id), None)

    def _renormalize_positions(self) -> None:
        for column in self._columns:
            cards = sorted(
                (card for card in self._cards if card.column_id == column.id),
                key=lambda card: card.position,
            )
            for index, card in enumerate(cards):
                card.position = index

    def _snapshot(self) -> Board:
        columns = sorted(self._columns, key=lambda column: column.order)
        column_order = {column.id: column.order for column in columns}
        cards = sorted(
            self._cards,
            key=lambda card: (column_order.get(card.column_id, 0), card.position),
        )
        return Board(
            columns=[column.model_copy() for column in columns],
            cards=[card.model_copy() for card in cards],
        )
