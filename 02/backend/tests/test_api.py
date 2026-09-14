"""Endpoint tests for the KanbanLite API.

These tests were written before the implementation (TDD). Paths include the
`/api` prefix from the OpenAPI `servers` entry
(`http://localhost:8000/api` + `/board` == `/api/board`).
"""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

DEFAULT_COLUMN_TITLES = [
    "To Do",
    "In Progress",
    "Deployed in Staging",
    "Deployed in Production",
    "On Hold",
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def get_board(client: TestClient) -> dict:
    response = client.get("/api/board")
    assert response.status_code == 200
    return response.json()


def columns_sorted(board: dict) -> list[dict]:
    return sorted(board["columns"], key=lambda column: column["order"])


def column_id(client: TestClient, title: str) -> str:
    board = get_board(client)
    return next(
        column["id"] for column in board["columns"] if column["title"] == title
    )


def card_by_title(board: dict, title: str) -> dict:
    return next(card for card in board["cards"] if card["title"] == title)


def create_card(client: TestClient, column_id: str, title: str, **extra) -> dict:
    response = client.post(
        "/api/cards", json={"column_id": column_id, "title": title, **extra}
    )
    assert response.status_code == 201
    return response.json()


# --------------------------------------------------------------------------- #
# GET /board
# --------------------------------------------------------------------------- #
class TestGetBoard:
    def test_returns_the_five_default_columns_in_order(self, client: TestClient):
        board = get_board(client)
        assert [column["title"] for column in columns_sorted(board)] == (
            DEFAULT_COLUMN_TITLES
        )

    def test_board_is_empty_of_cards(self, client: TestClient):
        assert get_board(client)["cards"] == []

    def test_default_columns_have_uuid_ids_and_sequential_order(
        self, client: TestClient
    ):
        columns = columns_sorted(get_board(client))
        for expected_order, column in enumerate(columns):
            assert column["order"] == expected_order
            UUID(column["id"])  # raises if not a valid UUID


# --------------------------------------------------------------------------- #
# POST /columns
# --------------------------------------------------------------------------- #
class TestCreateColumn:
    def test_appends_column_with_next_order(self, client: TestClient):
        response = client.post("/api/columns", json={"title": "Blocked"})

        assert response.status_code == 201
        board = response.json()
        assert len(board["columns"]) == 6
        assert [column["title"] for column in columns_sorted(board)] == [
            *DEFAULT_COLUMN_TITLES,
            "Blocked",
        ]
        new_column = next(
            column for column in board["columns"] if column["title"] == "Blocked"
        )
        assert new_column["order"] == 5
        UUID(new_column["id"])

    def test_trims_surrounding_whitespace(self, client: TestClient):
        board = client.post("/api/columns", json={"title": "  Frozen  "}).json()
        assert any(column["title"] == "Frozen" for column in board["columns"])

    def test_returns_the_full_board(self, client: TestClient):
        board = client.post("/api/columns", json={"title": "Blocked"}).json()
        assert set(board) == {"columns", "cards"}

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({}, id="missing-title"),
            pytest.param({"title": ""}, id="empty-title"),
            pytest.param({"title": "   "}, id="whitespace-title"),
        ],
    )
    def test_rejects_invalid_title(self, client: TestClient, payload: dict):
        assert client.post("/api/columns", json=payload).status_code == 422


# --------------------------------------------------------------------------- #
# POST /cards
# --------------------------------------------------------------------------- #
class TestCreateCard:
    def test_applies_documented_defaults(self, client: TestClient):
        column = column_id(client, "To Do")
        response = client.post(
            "/api/cards", json={"column_id": column, "title": "Write tests"}
        )

        assert response.status_code == 201
        card = card_by_title(response.json(), "Write tests")
        assert card["column_id"] == column
        assert card["description"] == ""
        assert card["priority"] == "Medium"
        assert card["due_date"] == ""
        assert card["position"] == 0
        datetime.fromisoformat(card["created_at"])  # parses

    def test_accepts_all_fields(self, client: TestClient):
        column = column_id(client, "To Do")
        response = client.post(
            "/api/cards",
            json={
                "column_id": column,
                "title": "Ship it",
                "description": "Cut the release",
                "priority": "Urgent",
                "due_date": "2026-10-05",
            },
        )

        card = card_by_title(response.json(), "Ship it")
        assert card["description"] == "Cut the release"
        assert card["priority"] == "Urgent"
        assert card["due_date"] == "2026-10-05"

    def test_appends_cards_to_the_end_of_the_column(self, client: TestClient):
        column = column_id(client, "To Do")
        create_card(client, column, "First")
        board = create_card(client, column, "Second")

        assert card_by_title(board, "First")["position"] == 0
        assert card_by_title(board, "Second")["position"] == 1

    def test_unknown_column_returns_404(self, client: TestClient):
        response = client.post(
            "/api/cards", json={"column_id": str(uuid4()), "title": "Orphan"}
        )
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({"title": "No column"}, id="missing-column"),
            pytest.param({"column_id": "not-a-uuid", "title": "Bad id"}, id="bad-uuid"),
            pytest.param(
                {"column_id": str(uuid4()), "title": ""}, id="empty-title"
            ),
            pytest.param(
                {"column_id": str(uuid4()), "title": "Bad priority", "priority": "ASAP"},
                id="bad-priority",
            ),
        ],
    )
    def test_rejects_invalid_payload(self, client: TestClient, payload: dict):
        assert client.post("/api/cards", json=payload).status_code == 422


# --------------------------------------------------------------------------- #
# PATCH /cards/{id}
# --------------------------------------------------------------------------- #
class TestUpdateCard:
    def test_updates_only_the_provided_fields(self, client: TestClient):
        column = column_id(client, "To Do")
        board = create_card(
            client, column, "Draft", description="keep me", priority="Low"
        )
        card = card_by_title(board, "Draft")

        response = client.patch(
            f"/api/cards/{card['id']}",
            json={"title": "Final", "priority": "High", "due_date": "2026-11-01"},
        )

        assert response.status_code == 200
        updated = card_by_title(response.json(), "Final")
        assert updated["id"] == card["id"]
        assert updated["description"] == "keep me"
        assert updated["priority"] == "High"
        assert updated["due_date"] == "2026-11-01"
        assert updated["position"] == card["position"]
        assert updated["created_at"] == card["created_at"]

    def test_can_clear_the_due_date(self, client: TestClient):
        column = column_id(client, "To Do")
        board = create_card(client, column, "Dated", due_date="2026-11-01")
        card = card_by_title(board, "Dated")

        response = client.patch(f"/api/cards/{card['id']}", json={"due_date": ""})
        assert card_by_title(response.json(), "Dated")["due_date"] == ""

    def test_unknown_card_returns_404(self, client: TestClient):
        response = client.patch(f"/api/cards/{uuid4()}", json={"title": "Ghost"})
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({}, id="empty-body"),
            pytest.param({"title": ""}, id="empty-title"),
            pytest.param({"priority": "ASAP"}, id="bad-priority"),
        ],
    )
    def test_rejects_invalid_payload(self, client: TestClient, payload: dict):
        column = column_id(client, "To Do")
        board = create_card(client, column, "Card")
        card = card_by_title(board, "Card")

        response = client.patch(f"/api/cards/{card['id']}", json=payload)
        assert response.status_code == 422


# --------------------------------------------------------------------------- #
# DELETE /cards/{id}
# --------------------------------------------------------------------------- #
class TestDeleteCard:
    def test_removes_the_card(self, client: TestClient):
        column = column_id(client, "To Do")
        board = create_card(client, column, "Delete me")

        response = client.delete(
            f"/api/cards/{card_by_title(board, 'Delete me')['id']}"
        )

        assert response.status_code == 200
        assert all(card["title"] != "Delete me" for card in response.json()["cards"])

    def test_renormalizes_positions_of_remaining_cards(self, client: TestClient):
        column = column_id(client, "To Do")
        create_card(client, column, "A")
        board = create_card(client, column, "B")
        create_card(client, column, "C")
        middle = card_by_title(board, "B")

        board = client.delete(f"/api/cards/{middle['id']}").json()

        assert card_by_title(board, "A")["position"] == 0
        assert card_by_title(board, "C")["position"] == 1

    def test_unknown_card_returns_404(self, client: TestClient):
        assert client.delete(f"/api/cards/{uuid4()}").status_code == 404


# --------------------------------------------------------------------------- #
# PATCH /cards/{id}/move
# --------------------------------------------------------------------------- #
class TestMoveCard:
    def test_moves_a_card_to_another_column(self, client: TestClient):
        todo = column_id(client, "To Do")
        doing = column_id(client, "In Progress")
        board = create_card(client, todo, "Move me")
        card = card_by_title(board, "Move me")

        response = client.patch(
            f"/api/cards/{card['id']}/move",
            json={"column_id": doing, "position": 0},
        )

        assert response.status_code == 200
        moved = card_by_title(response.json(), "Move me")
        assert moved["column_id"] == doing
        assert moved["position"] == 0

    def test_reorders_within_the_same_column(self, client: TestClient):
        column = column_id(client, "To Do")
        create_card(client, column, "A")
        create_card(client, column, "B")
        board = create_card(client, column, "C")
        last = card_by_title(board, "C")

        response = client.patch(
            f"/api/cards/{last['id']}/move",
            json={"column_id": column, "position": 0},
        )

        board = response.json()
        assert [card["title"] for card in _cards_of(board, column)] == [
            "C",
            "A",
            "B",
        ]
        assert [card["position"] for card in _cards_of(board, column)] == [0, 1, 2]

    def test_clamps_position_beyond_the_end(self, client: TestClient):
        todo = column_id(client, "To Do")
        doing = column_id(client, "In Progress")
        create_card(client, doing, "Existing")
        board = create_card(client, todo, "Move me")
        card = card_by_title(board, "Move me")

        response = client.patch(
            f"/api/cards/{card['id']}/move",
            json={"column_id": doing, "position": 999},
        )

        board = response.json()
        assert [c["title"] for c in _cards_of(board, doing)] == [
            "Existing",
            "Move me",
        ]
        assert card_by_title(board, "Move me")["position"] == 1

    def test_unknown_card_returns_404(self, client: TestClient):
        response = client.patch(
            f"/api/cards/{uuid4()}/move",
            json={"column_id": column_id(client, "To Do"), "position": 0},
        )
        assert response.status_code == 404

    def test_unknown_destination_column_returns_404(self, client: TestClient):
        column = column_id(client, "To Do")
        board = create_card(client, column, "Move me")
        card = card_by_title(board, "Move me")

        response = client.patch(
            f"/api/cards/{card['id']}/move",
            json={"column_id": str(uuid4()), "position": 0},
        )
        assert response.status_code == 404

    def test_rejects_negative_position(self, client: TestClient):
        column = column_id(client, "To Do")
        board = create_card(client, column, "Move me")
        card = card_by_title(board, "Move me")

        response = client.patch(
            f"/api/cards/{card['id']}/move",
            json={"column_id": column, "position": -1},
        )
        assert response.status_code == 422


def _cards_of(board: dict, column_id: str) -> list[dict]:
    return sorted(
        (card for card in board["cards"] if card["column_id"] == column_id),
        key=lambda card: card["position"],
    )
