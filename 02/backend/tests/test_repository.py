"""Repository-level tests for the SQLAlchemy persistence layer.

These complement the HTTP tests in `test_api.py` by exercising behaviour the
API cannot show: seeding, real on-disk persistence across engines, and
timezone handling.
"""

from collections.abc import Callable, Iterator
from uuid import uuid4

import pytest
from sqlalchemy import Engine

from app.db import (
    DEFAULT_COLUMN_TITLES,
    Base,
    BoardRepository,
    CardNotFound,
    ColumnNotFound,
    create_engine_and_session_factory,
)
from app.dependencies import get_repository
from app.models import Priority

MakeRepository = Callable[[str], BoardRepository]


@pytest.fixture()
def make_repository() -> Iterator[MakeRepository]:
    engines: list[Engine] = []

    def _make(database_url: str = "sqlite://") -> BoardRepository:
        engine, factory = create_engine_and_session_factory(database_url)
        Base.metadata.create_all(engine)
        engines.append(engine)
        return BoardRepository(factory)

    yield _make

    for engine in engines:
        engine.dispose()


def create_card(repository: BoardRepository, **overrides) -> None:
    column = repository.get_board().columns[0]
    repository.create_card(
        column_id=overrides.pop("column_id", column.id),
        title=overrides.pop("title", "Card"),
        description=overrides.pop("description", ""),
        priority=overrides.pop("priority", Priority.MEDIUM),
        due_date=overrides.pop("due_date", ""),
    )


class TestSeeding:
    def test_seeds_the_five_default_columns_on_init(
        self, make_repository: MakeRepository
    ):
        repository = make_repository()
        titles = [column.title for column in repository.get_board().columns]
        assert titles == DEFAULT_COLUMN_TITLES

    def test_ensure_seeded_is_idempotent(self, make_repository: MakeRepository):
        repository = make_repository()
        repository.ensure_seeded()
        repository.ensure_seeded()
        assert len(repository.get_board().columns) == 5

    def test_reset_clears_cards_and_reseeds_columns(
        self, make_repository: MakeRepository
    ):
        repository = make_repository()
        create_card(repository, title="Temporary")

        repository.reset()

        board = repository.get_board()
        assert board.cards == []
        assert [column.title for column in board.columns] == DEFAULT_COLUMN_TITLES


class TestPersistence:
    def test_data_survives_rebuilding_the_engine(
        self, make_repository: MakeRepository, tmp_path
    ):
        database_url = f"sqlite:///{tmp_path / 'kanbanlite-test.db'}"

        first = make_repository(database_url)
        create_card(first, title="Persisted", priority=Priority.HIGH)

        # A brand-new engine + repository on the same file must see the data.
        second = make_repository(database_url)
        board = second.get_board()
        assert [card.title for card in board.cards] == ["Persisted"]
        # Seeding must not duplicate columns for an existing database.
        assert len(board.columns) == 5

    def test_created_at_is_timezone_aware_utc(
        self, make_repository: MakeRepository
    ):
        repository = make_repository()
        create_card(repository, title="Timestamped")

        created_at = repository.get_board().cards[0].created_at
        assert created_at.tzinfo is not None
        assert created_at.utcoffset().total_seconds() == 0


class TestErrors:
    def test_updating_an_unknown_card_raises(
        self, make_repository: MakeRepository
    ):
        repository = make_repository()
        with pytest.raises(CardNotFound):
            repository.update_card(uuid4(), title="Ghost")

    def test_deleting_an_unknown_card_raises(
        self, make_repository: MakeRepository
    ):
        repository = make_repository()
        with pytest.raises(CardNotFound):
            repository.delete_card(uuid4())

    def test_creating_a_card_in_an_unknown_column_raises(
        self, make_repository: MakeRepository
    ):
        repository = make_repository()
        with pytest.raises(ColumnNotFound):
            create_card(repository, column_id=uuid4())

    def test_moving_a_card_to_an_unknown_column_raises(
        self, make_repository: MakeRepository
    ):
        repository = make_repository()
        create_card(repository, title="Move me")
        card = repository.get_board().cards[0]
        with pytest.raises(ColumnNotFound):
            repository.move_card(card.id, column_id=uuid4(), position=0)


class TestWiring:
    def test_default_dependency_returns_a_seeded_repository(self):
        # Regression guard: the app-level dependency (not a test override) must
        # resolve to a working repository.
        repository = get_repository()
        assert isinstance(repository, BoardRepository)
        assert len(repository.get_board().columns) == 5


class TestOrdering:
    def test_cards_are_returned_ordered_by_column_then_position(
        self, make_repository: MakeRepository
    ):
        repository = make_repository()
        board = repository.get_board()
        first_column, second_column = board.columns[0], board.columns[1]

        create_card(repository, column_id=second_column.id, title="Second-0")
        create_card(repository, column_id=first_column.id, title="First-0")
        create_card(repository, column_id=first_column.id, title="First-1")

        ordered = [card.title for card in repository.get_board().cards]
        assert ordered == ["First-0", "First-1", "Second-0"]

    def test_move_renormalizes_positions_across_columns(
        self, make_repository: MakeRepository
    ):
        repository = make_repository()
        columns = repository.get_board().columns
        source, destination = columns[0], columns[1]

        create_card(repository, column_id=source.id, title="A")
        create_card(repository, column_id=source.id, title="B")
        create_card(repository, column_id=destination.id, title="C")
        card_b = next(
            card for card in repository.get_board().cards if card.title == "B"
        )

        repository.move_card(card_b.id, column_id=destination.id, position=0)

        board = repository.get_board()
        destination_cards = sorted(
            (card for card in board.cards if card.column_id == destination.id),
            key=lambda card: card.position,
        )
        source_cards = sorted(
            (card for card in board.cards if card.column_id == source.id),
            key=lambda card: card.position,
        )
        assert [card.title for card in destination_cards] == ["B", "C"]
        assert [card.position for card in destination_cards] == [0, 1]
        assert [card.title for card in source_cards] == ["A"]
        assert [card.position for card in source_cards] == [0]
