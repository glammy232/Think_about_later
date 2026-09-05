from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import parse_qs

from app.models import (
    BalanceItem,
    DashboardSummary,
    DebtStatus,
    OperationType,
    ReceiptDraft,
    Transfer,
)
from app.storage import Storage


def calculate_net_balances(storage: Storage, group_id: str) -> dict[str, float]:
    users = storage.list_users(group_id)
    balances = {user.id: 0.0 for user in users}
    for operation in storage.list_operations(group_id):
        if operation.type != OperationType.expense:
            continue
        balances[operation.payer_id] += operation.amount
        for share in operation.shares:
            balances[share.user_id] -= share.amount
    for debt in storage.list_direct_debts(group_id):
        if debt.status != DebtStatus.active:
            continue
        balances[debt.debtor_id] -= debt.amount
        balances[debt.creditor_id] += debt.amount
    for payment in storage.list_payments(group_id):
        balances[payment.from_user_id] += payment.amount
        balances[payment.to_user_id] -= payment.amount
    return {user_id: round(value, 2) for user_id, value in balances.items()}


def get_balance_items(storage: Storage, group_id: str) -> list[BalanceItem]:
    balances = calculate_net_balances(storage, group_id)
    result = []
    for user in storage.list_users(group_id):
        balance = balances[user.id]
        status = "is_owed" if balance > 0 else "owes" if balance < 0 else "settled"
        result.append(
            BalanceItem(
                user_id=user.id, user_name=user.name, balance=balance, status=status
            )
        )
    return result


def simplify_transfers(storage: Storage, group_id: str) -> list[Transfer]:
    balances = calculate_net_balances(storage, group_id)
    names = {user.id: user.name for user in storage.list_users(group_id)}
    debtors = [
        [user_id, -amount] for user_id, amount in balances.items() if amount < -0.009
    ]
    creditors = [
        [user_id, amount] for user_id, amount in balances.items() if amount > 0.009
    ]
    debtors.sort(key=lambda item: item[1], reverse=True)
    creditors.sort(key=lambda item: item[1], reverse=True)
    result: list[Transfer] = []
    debtor_index = creditor_index = 0
    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor_id, owes = debtors[debtor_index]
        creditor_id, gets = creditors[creditor_index]
        amount = round(min(owes, gets), 2)
        result.append(
            Transfer(
                from_user_id=debtor_id,
                from_user_name=names[debtor_id],
                to_user_id=creditor_id,
                to_user_name=names[creditor_id],
                amount=amount,
            )
        )
        debtors[debtor_index][1] = round(owes - amount, 2)
        creditors[creditor_index][1] = round(gets - amount, 2)
        if debtors[debtor_index][1] <= 0.009:
            debtor_index += 1
        if creditors[creditor_index][1] <= 0.009:
            creditor_index += 1
    return result


def dashboard_summary(
    storage: Storage, group_id: str, user_id: str
) -> DashboardSummary:
    operations = storage.list_operations(group_id)
    total_expenses = sum(
        o.amount for o in operations if o.type == OperationType.expense
    )
    user_expenses = sum(
        o.amount
        for o in operations
        if o.type == OperationType.expense and o.payer_id == user_id
    )
    transfers = simplify_transfers(storage, group_id)
    return DashboardSummary(
        group_id=group_id,
        current_user_id=user_id,
        total_expenses=round(total_expenses, 2),
        user_expenses=round(user_expenses, 2),
        owed_to_user=round(
            sum(t.amount for t in transfers if t.to_user_id == user_id), 2
        ),
        user_owes=round(
            sum(t.amount for t in transfers if t.from_user_id == user_id), 2
        ),
    )


def analytics(storage: Storage, group_id: str) -> dict:
    operations = [
        o for o in storage.list_operations(group_id) if o.type == OperationType.expense
    ]
    by_category: dict[str, float] = defaultdict(float)
    by_month: dict[str, float] = defaultdict(float)
    by_user: dict[str, float] = defaultdict(float)
    for operation in operations:
        by_category[operation.category] += operation.amount
        by_month[operation.operation_date.strftime("%Y-%m")] += operation.amount
        by_user[operation.payer_id] += operation.amount
    return {
        "total": round(sum(o.amount for o in operations), 2),
        "by_category": [
            {"name": k, "amount": round(v, 2)} for k, v in sorted(by_category.items())
        ],
        "by_month": [
            {"month": k, "amount": round(v, 2)} for k, v in sorted(by_month.items())
        ],
        "by_user": [
            {"user_id": k, "amount": round(v, 2)} for k, v in sorted(by_user.items())
        ],
    }


def parse_receipt_qr(qr_data: str) -> ReceiptDraft:
    """Parse common Russian receipt QR fields without calling an external OFD/FNS API."""
    params = parse_qs(qr_data.replace("?", "&"))
    raw_total = params.get("s", ["0"])[0]
    raw_time = params.get("t", [""])[0]
    try:
        purchased_at = datetime.strptime(raw_time[:13], "%Y%m%dT%H%M").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        purchased_at = datetime.now(timezone.utc)
    amount = float(raw_total) if raw_total.replace(".", "", 1).isdigit() else 0
    return ReceiptDraft(
        merchant="Магазин (уточните название)",
        amount=amount,
        purchased_at=purchased_at,
        category="Продукты",
        fiscal_fields={key: values[0] for key, values in params.items()},
        items=[],
    )
