"""SQLAlchemy-backed persistence layer.

The database is chosen entirely by `DATABASE_URL` (see `dependencies.py`):
SQLite by default, PostgreSQL or anything else by changing the URL. This is the
only module that knows about SQLAlchemy; routes depend on the repository
interface, never on the ORM.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Engine,
    ForeignKey,
    Integer,
    String,
    Uuid,
    create_engine,
    delete,
    event,
    func,
    select,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import TypeDecorator

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


class UTCDateTime(TypeDecorator[datetime]):
    """Timezone-aware UTC timestamps that survive every backend.

    SQLite drops `tzinfo`, so this restores UTC on read. Other dialects get a
    native `DateTime(timezone=True)`.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: datetime | None, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class Base(DeclarativeBase):
    pass


class ColumnRow(Base):
    __tablename__ = "columns"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # `order` is a reserved SQL keyword, so the attribute is named differently
    # while the database column keeps the OpenAPI field name.
    column_order: Mapped[int] = mapped_column("order", Integer, nullable=False)

    cards: Mapped[list["CardRow"]] = relationship(
        back_populates="column", cascade="all, delete-orphan"
    )


class CardRow(Base):
    __tablename__ = "cards"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    column_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("columns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    due_date: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    column: Mapped[ColumnRow] = relationship(back_populates="cards")


def create_engine_and_session_factory(
    database_url: str,
) -> tuple[Engine, sessionmaker[Session]]:
    """Build an engine and session factory for any SQLAlchemy URL."""
    engine_kwargs: dict = {}
    connect_args: dict = {}

    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if database_url.rstrip("/") in ("sqlite:", "sqlite+pysqlite:") or (
            ":memory:" in database_url
        ):
            # A shared in-memory database must reuse a single connection.
            engine_kwargs["poolclass"] = StaticPool

    engine = create_engine(database_url, connect_args=connect_args, **engine_kwargs)

    if engine.dialect.name == "sqlite":
        # SQLite disables foreign-key enforcement by default.
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine, sessionmaker(bind=engine, expire_on_commit=False)


class BoardRepository:
    """Persistence operations for the single board.

    Each method owns a short-lived session (sync routes run in FastAPI's
    threadpool, so sessions are never shared across requests). Every method
    returns a fresh Pydantic `Board` snapshot assembled inside the session.
    """

    def __init__(
        self, session_factory: sessionmaker[Session], *, seed: bool = True
    ) -> None:
        self._session_factory = session_factory
        if seed:
            self.ensure_seeded()

    def ensure_seeded(self) -> None:
        """Seed the five default columns if the board is still empty."""
        with self._session_factory() as session:
            existing = session.scalar(select(func.count()).select_from(ColumnRow))
            if existing:
                return
            self._insert_default_columns(session)
            session.commit()

    def reset(self) -> None:
        """Wipe the board and restore the default columns (used by tests)."""
        with self._session_factory() as session:
            session.execute(delete(CardRow))
            session.execute(delete(ColumnRow))
            self._insert_default_columns(session)
            session.commit()

    def get_board(self) -> Board:
        with self._session_factory() as session:
            return self._snapshot(session)

    def create_column(self, title: str) -> Board:
        with self._session_factory() as session:
            max_order = session.scalar(select(func.max(ColumnRow.column_order)))
            next_order = (max_order if max_order is not None else -1) + 1
            session.add(
                ColumnRow(id=uuid4(), title=title, column_order=next_order)
            )
            session.commit()
            return self._snapshot(session)

    def create_card(
        self,
        *,
        column_id: UUID,
        title: str,
        description: str,
        priority: Priority,
        due_date: str,
    ) -> Board:
        with self._session_factory() as session:
            if session.get(ColumnRow, column_id) is None:
                raise ColumnNotFound(column_id)

            position = session.scalar(
                select(func.count())
                .select_from(CardRow)
                .where(CardRow.column_id == column_id)
            )
            session.add(
                CardRow(
                    id=uuid4(),
                    column_id=column_id,
                    title=title,
                    description=description,
                    priority=priority.value,
                    created_at=datetime.now(timezone.utc),
                    due_date=due_date,
                    position=position or 0,
                )
            )
            session.commit()
            return self._snapshot(session)

    def update_card(
        self,
        card_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        priority: Priority | None = None,
        due_date: str | None = None,
    ) -> Board:
        with self._session_factory() as session:
            card = session.get(CardRow, card_id)
            if card is None:
                raise CardNotFound(card_id)

            if title is not None:
                card.title = title
            if description is not None:
                card.description = description
            if priority is not None:
                card.priority = priority.value
            if due_date is not None:
                card.due_date = due_date

            session.commit()
            return self._snapshot(session)

    def delete_card(self, card_id: UUID) -> Board:
        with self._session_factory() as session:
            card = session.get(CardRow, card_id)
            if card is None:
                raise CardNotFound(card_id)

            session.delete(card)
            session.flush()
            self._renormalize_positions(session)
            session.commit()
            return self._snapshot(session)

    def move_card(self, card_id: UUID, *, column_id: UUID, position: int) -> Board:
        with self._session_factory() as session:
            card = session.get(CardRow, card_id)
            if card is None:
                raise CardNotFound(card_id)
            if session.get(ColumnRow, column_id) is None:
                raise ColumnNotFound(column_id)

            target = session.scalars(
                select(CardRow)
                .where(CardRow.column_id == column_id, CardRow.id != card_id)
                .order_by(CardRow.position)
            ).all()
            index = max(0, min(position, len(target)))

            card.column_id = column_id
            card.position = index
            for candidate in target:
                if candidate.position >= index:
                    candidate.position += 1

            session.flush()
            self._renormalize_positions(session)
            session.commit()
            return self._snapshot(session)

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    def _insert_default_columns(self, session: Session) -> None:
        for order, title in enumerate(DEFAULT_COLUMN_TITLES):
            session.add(
                ColumnRow(id=uuid4(), title=title, column_order=order)
            )

    def _renormalize_positions(self, session: Session) -> None:
        for column in session.scalars(select(ColumnRow)).all():
            cards = session.scalars(
                select(CardRow)
                .where(CardRow.column_id == column.id)
                .order_by(CardRow.position)
            ).all()
            for index, card in enumerate(cards):
                card.position = index

    def _snapshot(self, session: Session) -> Board:
        """Assemble the Pydantic board while the session is still open."""
        columns = session.scalars(
            select(ColumnRow).order_by(ColumnRow.column_order)
        ).all()
        column_order = {column.id: column.column_order for column in columns}
        cards = list(session.scalars(select(CardRow)).all())
        cards.sort(key=lambda card: (column_order.get(card.column_id, 0), card.position))

        return Board(
            columns=[
                Column(id=column.id, title=column.title, order=column.column_order)
                for column in columns
            ],
            cards=[
                Card(
                    id=card.id,
                    column_id=card.column_id,
                    title=card.title,
                    description=card.description,
                    priority=Priority(card.priority),
                    created_at=card.created_at,
                    due_date=card.due_date,
                    position=card.position,
                )
                for card in cards
            ],
        )
