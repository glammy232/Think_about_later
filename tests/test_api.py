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


def test_frontend_is_served_with_backend_integration():
    response = client.get("/demo")
    assert response.status_code == 200
    assert 'id="create-group-form"' in response.text
    assert "Финансовый помощник" in response.text
    assert client.get("/app/api.js").status_code == 200


def test_clean_start_creates_group_owner_and_zero_dashboard(monkeypatch):
    clean_storage = InMemoryStorage(seed_demo=False)
    monkeypatch.setattr(main_module, "storage", clean_storage)
    created = client.post(
        "/api/groups",
        json={"name": "Наша группа", "owner_name": "Дмитрий"},
    )
    assert created.status_code == 201
    body = created.json()
    group_id = body["group"]["id"]
    owner_id = body["owner"]["id"]
    assert body["group"]["member_ids"] == [owner_id]

    dashboard = client.get(
        f"/api/groups/{group_id}/dashboard",
        headers={"X-User-Id": owner_id},
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["summary"] == {
        "group_id": group_id,
        "current_user_id": owner_id,
        "total_expenses": 0.0,
        "user_expenses": 0.0,
        "owed_to_user": 0.0,
        "user_owes": 0.0,
    }
    assert dashboard.json()["recent_operations"] == []


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
        {"user_id": "user-2", "amount": 3000.0, "percentage": 60.0},
        {"user_id": "user-3", "amount": 2000.0, "percentage": 40.0},
    ]


def test_equal_split_returns_amounts_and_percentages():
    response = client.post(
        "/api/groups/group-1/operations",
        json={
            "type": "expense",
            "title": "Пицца",
            "amount": 3000,
            "category": "Кафе и рестораны",
            "payer_id": "user-1",
            "participant_ids": ["user-1", "user-2", "user-3"],
            "split_type": "equal",
        },
    )
    assert response.status_code == 201
    shares = response.json()["shares"]
    assert [share["amount"] for share in shares] == [1000.0, 1000.0, 1000.0]
    assert sum(share["percentage"] for share in shares) == 100


def test_percentage_split_calculates_exact_amounts():
    response = client.post(
        "/api/groups/group-1/operations",
        json={
            "type": "expense",
            "title": "Аренда",
            "amount": 10000,
            "category": "Дом",
            "payer_id": "user-1",
            "participant_ids": ["user-1", "user-2", "user-3"],
            "split_type": "percentage",
            "shares": [
                {"user_id": "user-1", "percentage": 20},
                {"user_id": "user-2", "percentage": 30},
                {"user_id": "user-3", "percentage": 50},
            ],
        },
    )
    assert response.status_code == 201
    shares = response.json()["shares"]
    assert [share["amount"] for share in shares] == [2000.0, 3000.0, 5000.0]
    assert [share["percentage"] for share in shares] == [20.0, 30.0, 50.0]


def test_percentage_split_rounding_keeps_full_amount():
    response = client.post(
        "/api/groups/group-1/operations",
        json={
            "type": "expense",
            "title": "Деление с копейками",
            "amount": 100,
            "category": "Другое",
            "payer_id": "user-1",
            "participant_ids": ["user-1", "user-2", "user-3"],
            "split_type": "percentage",
            "shares": [
                {"user_id": "user-1", "percentage": 33.33},
                {"user_id": "user-2", "percentage": 33.33},
                {"user_id": "user-3", "percentage": 33.34},
            ],
        },
    )
    assert response.status_code == 201
    shares = response.json()["shares"]
    assert [share["amount"] for share in shares] == [33.33, 33.33, 33.34]
    assert sum(share["amount"] for share in shares) == 100
    assert sum(share["percentage"] for share in shares) == 100


def test_percentage_split_must_total_one_hundred():
    response = client.post(
        "/api/groups/group-1/operations",
        json={
            "type": "expense",
            "title": "Аренда",
            "amount": 10000,
            "category": "Дом",
            "payer_id": "user-1",
            "participant_ids": ["user-1", "user-2"],
            "split_type": "percentage",
            "shares": [
                {"user_id": "user-1", "percentage": 40},
                {"user_id": "user-2", "percentage": 50},
            ],
        },
    )
    assert response.status_code == 422


def test_suggested_and_custom_categories():
    categories = client.get("/api/groups/group-1/categories")
    assert categories.status_code == 200
    assert "Продукты" in [item["name"] for item in categories.json()["suggested"]]

    custom_operation = client.post(
        "/api/groups/group-1/operations",
        json={
            "type": "expense",
            "title": "Корм",
            "amount": 500,
            "category": "Питомцы",
            "payer_id": "user-1",
            "participant_ids": ["user-1"],
            "split_type": "equal",
        },
    )
    assert custom_operation.status_code == 201
    categories = client.get("/api/groups/group-1/categories").json()
    assert "Питомцы" in categories["custom"]


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
