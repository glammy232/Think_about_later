from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_and_docs_contract():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_contains_frontend_blocks():
    response = client.get("/api/groups/group-1/dashboard", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"group", "summary", "recent_operations", "balances", "analytics"}
    assert data["group"]["name"] == "Квартира на Ленина"
    assert len(data["group"]["member_ids"]) == 5


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
    before_alexey = next(item["balance"] for item in before if item["user_id"] == "user-1")
    after_alexey = next(item["balance"] for item in after if item["user_id"] == "user-1")
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


def test_receipt_qr_draft():
    response = client.post(
        "/api/receipts/parse",
        json={"qr_data": "t=20260515T1234&s=1540.50&fn=123&fp=456&i=789&n=1"},
    )
    assert response.status_code == 200
    assert response.json()["amount"] == 1540.5
    assert response.json()["provider"] == "mock"


def test_payment_reduces_calculated_debt():
    transfers = client.get("/api/groups/group-1/balances").json()["recommended_transfers"]
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
