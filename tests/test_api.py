import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.storage import InMemoryStorage

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_storage(monkeypatch):
    """Every test starts with the same clean demo state."""
    monkeypatch.setattr(main_module, "storage", InMemoryStorage())


def test_health_and_docs_contract():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_contains_frontend_blocks():
    response = client.get(
        "/api/groups/group-1/dashboard", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "group",
        "summary",
        "recent_operations",
        "balances",
        "analytics",
    }
    assert data["group"]["name"] == "Квартира на Ленина"
    assert len(data["group"]["member_ids"]) == 5


def test_add_member_appears_in_group_and_balances():
    response = client.post(
        "/api/groups/group-1/members",
        json={"name": "Ольга", "avatar_url": "https://example.com/olga.png"},
    )
    assert response.status_code == 201
    user_id = response.json()["id"]
    members = client.get("/api/groups/group-1/members").json()
    assert any(item["id"] == user_id and item["name"] == "Ольга" for item in members)
    balances = client.get("/api/groups/group-1/balances").json()["balances"]
    assert any(item["user_id"] == user_id and item["balance"] == 0 for item in balances)


def test_create_equal_expense_and_recalculate_balances():
    before = client.get("/api/groups/group-1/balances").json()["balances"]
    payload = {
        "type": "expense",
        "title": "Интернет",
        "amount": 1000,
        "category": "Коммуналка",
        "payer_id": "user-1",
        "participant_ids": ["user-1", "user-2", "user-3", "user-4"],
        "split_type": "equal",
    }
    response = client.post("/api/groups/group-1/operations", json=payload)
    assert response.status_code == 201
    operation = response.json()
    assert sum(item["amount"] for item in operation["shares"]) == 1000
    assert all(item["amount"] == 250 for item in operation["shares"])
    after = client.get("/api/groups/group-1/balances").json()["balances"]
    before_alexey = next(
        item["balance"] for item in before if item["user_id"] == "user-1"
    )
    after_alexey = next(
        item["balance"] for item in after if item["user_id"] == "user-1"
    )
    assert after_alexey - before_alexey == 750


def test_create_and_settle_direct_debt():
    response = client.post(
        "/api/groups/group-1/debts",
        json={
            "debtor_id": "user-2",
            "creditor_id": "user-1",
            "amount": 300,
            "description": "Вернуть за доставку",
        },
    )
    assert response.status_code == 201
    debt_id = response.json()["id"]
    settled = client.patch(f"/api/debts/{debt_id}/settle")
    assert settled.status_code == 200
    assert settled.json()["status"] == "settled"


def test_custom_split_validation():
    response = client.post(
        "/api/groups/group-1/operations",
        json={
            "type": "expense",
            "title": "Покупка",
            "amount": 1000,
            "category": "Другое",
            "payer_id": "user-1",
            "participant_ids": ["user-1", "user-2"],
            "split_type": "custom",
            "shares": [
                {"user_id": "user-1", "amount": 400},
                {"user_id": "user-2", "amount": 500},
            ],
        },
    )
    assert response.status_code == 422


def test_custom_split_creates_exact_debts_for_each_participant():
    response = client.post(
        "/api/groups/group-1/operations",
        json={
            "type": "expense",
            "title": "Продукты на троих",
            "amount": 5000,
            "category": "Продукты",
            "payer_id": "user-1",
            "participant_ids": ["user-2", "user-3"],
            "split_type": "custom",
            "shares": [
                {"user_id": "user-2", "amount": 3000},
                {"user_id": "user-3", "amount": 2000},
            ],
        },
    )
    assert response.status_code == 201
    assert response.json()["shares"] == [
        {"user_id": "user-2", "amount": 3000.0},
        {"user_id": "user-3", "amount": 2000.0},
    ]


@pytest.mark.parametrize(
    "participant_ids,shares",
    [
        (["user-1", "user-2", "user-2"], None),
        (
            ["user-1", "user-2"],
            [
                {"user_id": "user-1", "amount": 250},
                {"user_id": "user-1", "amount": 250},
                {"user_id": "user-2", "amount": 500},
            ],
        ),
    ],
)
def test_duplicate_participants_are_rejected(participant_ids, shares):
    response = client.post(
        "/api/groups/group-1/operations",
        json={
            "type": "expense",
            "title": "Дубли участников",
            "amount": 1000,
            "category": "Другое",
            "payer_id": "user-1",
            "participant_ids": participant_ids,
            "split_type": "custom" if shares else "equal",
            "shares": shares,
        },
    )
    assert response.status_code == 422


def test_receipt_qr_draft():
    response = client.post(
        "/api/receipts/parse",
        json={"qr_data": "t=20260515T1234&s=1540.50&fn=123&fp=456&i=789&n=1"},
    )
    assert response.status_code == 200
    assert response.json()["amount"] == 1540.5
    assert response.json()["provider"] == "mock"


def test_payment_reduces_calculated_debt():
    transfers = client.get("/api/groups/group-1/balances").json()[
        "recommended_transfers"
    ]
    assert transfers
    transfer = transfers[0]
    before = transfer["amount"]
    response = client.post(
        "/api/groups/group-1/payments",
        json={
            "from_user_id": transfer["from_user_id"],
            "to_user_id": transfer["to_user_id"],
            "amount": min(100, before),
            "comment": "Погашение долга",
        },
    )
    assert response.status_code == 201
    assert response.json()["amount"] == min(100, before)


def test_payment_cannot_exceed_or_ignore_calculated_debt():
    transfer = client.get("/api/groups/group-1/balances").json()[
        "recommended_transfers"
    ][0]
    overpayment = client.post(
        "/api/groups/group-1/payments",
        json={
            "from_user_id": transfer["from_user_id"],
            "to_user_id": transfer["to_user_id"],
            "amount": transfer["amount"] + 0.01,
        },
    )
    assert overpayment.status_code == 422
    unrelated = client.post(
        "/api/groups/group-1/payments",
        json={"from_user_id": "user-1", "to_user_id": "user-5", "amount": 1},
    )
    assert unrelated.status_code == 422


def test_settings_change_name_and_currency_everywhere():
    response = client.patch(
        "/api/users/user-1/settings",
        json={
            "name": "Александр",
            "avatar_url": "https://example.com/alexander.png",
            "currency": "USD",
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "name": "Александр",
        "avatar_url": "https://example.com/alexander.png",
        "currency": "USD",
    }
    members = client.get("/api/groups/group-1/members").json()
    assert (
        next(item for item in members if item["id"] == "user-1")["name"] == "Александр"
    )
    balances = client.get("/api/groups/group-1/balances").json()["balances"]
    assert (
        next(item for item in balances if item["user_id"] == "user-1")["user_name"]
        == "Александр"
    )


def test_change_group_name():
    response = client.patch(
        "/api/groups/group-1/settings",
        json={"name": "Дом на Ленина"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Дом на Ленина"
    dashboard = client.get("/api/groups/group-1/dashboard").json()
    assert dashboard["group"]["name"] == "Дом на Ленина"


@pytest.mark.parametrize(
    "url,payload",
    [
        ("/api/users/user-1/settings", {"currency": "ZZZ"}),
        ("/api/users/user-1/settings", {"avatar_url": "не ссылка"}),
        ("/api/users/user-1/settings", {"name": "   "}),
        ("/api/groups/group-1/settings", {"name": "   "}),
    ],
)
def test_invalid_settings_are_rejected(url, payload):
    assert client.patch(url, json=payload).status_code == 422


def test_names_are_trimmed():
    group = client.patch("/api/groups/group-1/settings", json={"name": "  Наш дом  "})
    profile = client.patch("/api/users/user-1/settings", json={"name": "  Алексей  "})
    assert group.json()["name"] == "Наш дом"
    assert profile.json()["name"] == "Алексей"


def test_notifications_and_messages_are_not_in_api():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/groups/{group_id}/notifications" not in paths
    assert "/api/groups/{group_id}/messages" not in paths
