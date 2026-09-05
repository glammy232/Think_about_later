from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.dependencies import current_user_id
from app.models import (
    AssistantRequest,
    AssistantResponse,
    Debt,
    DirectDebtCreate,
    GroupSettingsUpdate,
    MemberCreate,
    Operation,
    OperationCreate,
    OperationType,
    Payment,
    PaymentCreate,
    ReceiptDraft,
    ReceiptParseRequest,
    SettingsUpdate,
)
from app.services import (
    analytics,
    dashboard_summary,
    get_balance_items,
    parse_receipt_qr,
    simplify_transfers,
)
from app.storage import storage

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="REST API для сервиса совместных финансов «Круг». Временное хранилище — in-memory.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUGGESTED_CATEGORIES = [
    {"id": "groceries", "name": "Продукты"},
    {"id": "utilities", "name": "Коммунальные услуги"},
    {"id": "transport", "name": "Транспорт"},
    {"id": "cafes", "name": "Кафе и рестораны"},
    {"id": "health", "name": "Здоровье"},
    {"id": "home", "name": "Дом"},
    {"id": "entertainment", "name": "Развлечения"},
    {"id": "subscriptions", "name": "Подписки"},
    {"id": "education", "name": "Образование"},
    {"id": "other", "name": "Другое"},
]


def require_group(group_id: str):
    group = storage.get_group(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def validate_group_users(group_id: str, user_ids: list[str]):
    member_ids = {user.id for user in storage.list_users(group_id)}
    invalid = set(user_ids) - member_ids
    if invalid:
        raise HTTPException(
            status_code=422, detail=f"Users are not group members: {sorted(invalid)}"
        )


@app.get("/", tags=["system"])
def root():
    return {"service": settings.app_name, "version": settings.version, "docs": "/docs"}


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "storage": "in-memory"}


@app.get("/api/groups/{group_id}", tags=["groups"])
def get_group(group_id: str):
    return require_group(group_id)


@app.get("/api/groups/{group_id}/members", tags=["groups"])
def get_members(group_id: str):
    require_group(group_id)
    return storage.list_users(group_id)


@app.get("/api/groups/{group_id}/categories", tags=["operations"])
def get_categories(group_id: str):
    require_group(group_id)
    suggested_names = {item["name"].casefold() for item in SUGGESTED_CATEGORIES}
    custom = sorted(
        {
            operation.category
            for operation in storage.list_operations(group_id)
            if operation.category.casefold() not in suggested_names
        },
        key=str.casefold,
    )
    return {"suggested": SUGGESTED_CATEGORIES, "custom": custom}


@app.patch("/api/groups/{group_id}/settings", tags=["settings"])
def update_group_settings(group_id: str, data: GroupSettingsUpdate):
    require_group(group_id)
    return storage.update_group_name(group_id, data.name)


@app.post(
    "/api/groups/{group_id}/members",
    status_code=status.HTTP_201_CREATED,
    tags=["groups"],
)
def add_member(group_id: str, data: MemberCreate):
    require_group(group_id)
    return storage.add_member(group_id, data)


@app.get("/api/groups/{group_id}/dashboard", tags=["dashboard"])
def get_dashboard(
    group_id: str,
    user_id: Annotated[str, Depends(current_user_id)],
):
    require_group(group_id)
    validate_group_users(group_id, [user_id])
    return {
        "group": storage.get_group(group_id),
        "summary": dashboard_summary(storage, group_id, user_id),
        "recent_operations": storage.list_operations(group_id)[:5],
        "balances": get_balance_items(storage, group_id),
        "analytics": analytics(storage, group_id),
    }


@app.get(
    "/api/groups/{group_id}/operations",
    response_model=list[Operation],
    tags=["operations"],
)
def get_operations(
    group_id: str,
    operation_type: Annotated[OperationType | None, Query(alias="type")] = None,
    category: str | None = None,
):
    require_group(group_id)
    result = storage.list_operations(group_id)
    if operation_type:
        result = [item for item in result if item.type == operation_type]
    if category:
        result = [
            item for item in result if item.category.casefold() == category.casefold()
        ]
    return result


@app.post(
    "/api/groups/{group_id}/operations",
    response_model=Operation,
    status_code=status.HTTP_201_CREATED,
    tags=["operations"],
)
def create_operation(group_id: str, data: OperationCreate):
    require_group(group_id)
    validate_group_users(group_id, [data.payer_id, *data.participant_ids])
    return storage.create_operation(group_id, data)


@app.delete(
    "/api/operations/{operation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["operations"],
)
def delete_operation(operation_id: str):
    if not storage.delete_operation(operation_id):
        raise HTTPException(status_code=404, detail="Operation not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/groups/{group_id}/balances", tags=["balances"])
def get_balances(group_id: str):
    require_group(group_id)
    return {
        "balances": get_balance_items(storage, group_id),
        "recommended_transfers": simplify_transfers(storage, group_id),
    }


@app.get("/api/groups/{group_id}/debts", tags=["debts"])
def get_debts(group_id: str):
    require_group(group_id)
    return {
        "calculated": simplify_transfers(storage, group_id),
        "direct": storage.list_direct_debts(group_id),
    }


@app.post(
    "/api/groups/{group_id}/debts",
    response_model=Debt,
    status_code=status.HTTP_201_CREATED,
    tags=["debts"],
)
def create_debt(group_id: str, data: DirectDebtCreate):
    require_group(group_id)
    validate_group_users(group_id, [data.debtor_id, data.creditor_id])
    return storage.create_direct_debt(group_id, data)


@app.patch("/api/debts/{debt_id}/settle", response_model=Debt, tags=["debts"])
def settle_debt(debt_id: str):
    debt = storage.settle_debt(debt_id)
    if not debt:
        raise HTTPException(status_code=404, detail="Debt not found")
    return debt


@app.get(
    "/api/groups/{group_id}/payments", response_model=list[Payment], tags=["debts"]
)
def get_payments(group_id: str):
    require_group(group_id)
    return storage.list_payments(group_id)


@app.post(
    "/api/groups/{group_id}/payments",
    response_model=Payment,
    status_code=status.HTTP_201_CREATED,
    tags=["debts"],
)
def create_payment(group_id: str, data: PaymentCreate):
    require_group(group_id)
    validate_group_users(group_id, [data.from_user_id, data.to_user_id])
    matching_transfer = next(
        (
            transfer
            for transfer in simplify_transfers(storage, group_id)
            if transfer.from_user_id == data.from_user_id
            and transfer.to_user_id == data.to_user_id
        ),
        None,
    )
    if not matching_transfer:
        raise HTTPException(
            status_code=422, detail="No active calculated debt between these users"
        )
    if data.amount - matching_transfer.amount > 0.009:
        raise HTTPException(
            status_code=422,
            detail=f"Payment exceeds active debt of {matching_transfer.amount:.2f}",
        )
    return storage.create_payment(group_id, data)


@app.get("/api/groups/{group_id}/analytics", tags=["analytics"])
def get_analytics(group_id: str):
    require_group(group_id)
    return analytics(storage, group_id)


@app.post("/api/receipts/parse", response_model=ReceiptDraft, tags=["receipts"])
def parse_receipt(data: ReceiptParseRequest):
    return parse_receipt_qr(data.qr_data)


@app.post(
    "/api/groups/{group_id}/assistant",
    response_model=AssistantResponse,
    tags=["assistant"],
)
def ask_assistant(group_id: str, data: AssistantRequest):
    require_group(group_id)
    report = analytics(storage, group_id)
    top = max(report["by_category"], key=lambda item: item["amount"], default=None)
    if top:
        answer = f"Пока я работаю в демо-режиме. Самая крупная категория — {top['name']}: {top['amount']:.2f} ₽."
    else:
        answer = "Пока недостаточно данных для анализа расходов."
    return AssistantResponse(answer=answer)


@app.get("/api/users/{user_id}/settings", tags=["settings"])
def get_settings(user_id: str):
    user = storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    preferences = storage.settings.get(user_id, {"currency": "RUB"})
    return {"name": user.name, "avatar_url": user.avatar_url, **preferences}


@app.patch("/api/users/{user_id}/settings", tags=["settings"])
def update_settings(user_id: str, data: SettingsUpdate):
    user = storage.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if data.name is not None or data.avatar_url is not None:
        user = storage.update_user_profile(user_id, data.name, data.avatar_url)
    current = storage.settings.get(user_id, {"currency": "RUB"})
    current.update(data.model_dump(exclude={"name", "avatar_url"}, exclude_none=True))
    storage.settings[user_id] = current
    return {"name": user.name, "avatar_url": user.avatar_url, **current}
