from copy import deepcopy
from datetime import date
from typing import Protocol
from uuid import uuid4

from app.models import (
    Debt,
    DirectDebtCreate,
    Group,
    MemberCreate,
    Operation,
    OperationCreate,
    OperationType,
    Payment,
    PaymentCreate,
    ShareInput,
    SplitType,
    User,
)


class Storage(Protocol):
    def get_group(self, group_id: str) -> Group | None: ...
    def list_users(self, group_id: str) -> list[User]: ...
    def add_member(self, group_id: str, data: MemberCreate) -> User: ...
    def get_user(self, user_id: str) -> User | None: ...
    def update_user_profile(
        self, user_id: str, name: str | None = None, avatar_url: str | None = None
    ) -> User | None: ...
    def update_group_name(self, group_id: str, name: str) -> Group | None: ...
    def list_operations(self, group_id: str) -> list[Operation]: ...
    def create_operation(self, group_id: str, data: OperationCreate) -> Operation: ...
    def delete_operation(self, operation_id: str) -> bool: ...
    def list_direct_debts(self, group_id: str) -> list[Debt]: ...
    def create_direct_debt(self, group_id: str, data: DirectDebtCreate) -> Debt: ...
    def settle_debt(self, debt_id: str) -> Debt | None: ...
    def list_payments(self, group_id: str) -> list[Payment]: ...
    def create_payment(self, group_id: str, data: PaymentCreate) -> Payment: ...


class InMemoryStorage:
    """Temporary hackathon storage. Replace this class with DBStorage later."""

    def __init__(self):
        self.users: dict[str, User] = {}
        self.groups: dict[str, Group] = {}
        self.operations: dict[str, Operation] = {}
        self.debts: dict[str, Debt] = {}
        self.payments: dict[str, Payment] = {}
        self.settings: dict[str, dict] = {}
        self._seed()

    def _seed(self):
        names = ["Алексей", "Мария", "Иван", "Вы", "Павел"]
        for index, name in enumerate(names, start=1):
            user = User(id=f"user-{index}", name=name)
            self.users[user.id] = user
        self.groups["group-1"] = Group(
            id="group-1",
            name="Квартира на Ленина",
            member_ids=list(self.users),
        )
        seed = [
            ("Продукты в магазине", 1245, "Продукты", "user-1", date.today()),
            ("Коммунальные услуги", 3860, "Коммуналка", "user-2", date(2026, 5, 14)),
            ("Такси", 560, "Транспорт", "user-3", date(2026, 5, 13)),
            ("Кафе", 1320, "Кафе и рестораны", "user-4", date(2026, 5, 12)),
        ]
        for title, amount, category, payer, operation_date in seed:
            self.create_operation(
                "group-1",
                OperationCreate(
                    type=OperationType.expense,
                    title=title,
                    amount=amount,
                    category=category,
                    payer_id=payer,
                    participant_ids=list(self.users),
                    split_type=SplitType.equal,
                    operation_date=operation_date,
                ),
            )
        self.create_operation(
            "group-1",
            OperationCreate(
                type=OperationType.income,
                title="Доход",
                amount=45000,
                category="Зарплата",
                payer_id="user-1",
                participant_ids=["user-1"],
                operation_date=date(2026, 5, 10),
            ),
        )

    def get_group(self, group_id: str) -> Group | None:
        return deepcopy(self.groups.get(group_id))

    def list_users(self, group_id: str) -> list[User]:
        group = self.groups.get(group_id)
        return [deepcopy(self.users[user_id]) for user_id in group.member_ids] if group else []

    def get_user(self, user_id: str) -> User | None:
        return deepcopy(self.users.get(user_id))

    def update_user_profile(
        self, user_id: str, name: str | None = None, avatar_url: str | None = None
    ) -> User | None:
        user = self.users.get(user_id)
        if not user:
            return None
        if name is not None:
            user.name = name
        if avatar_url is not None:
            user.avatar_url = avatar_url
        return deepcopy(user)

    def update_group_name(self, group_id: str, name: str) -> Group | None:
        group = self.groups.get(group_id)
        if not group:
            return None
        group.name = name
        return deepcopy(group)

    def add_member(self, group_id: str, data: MemberCreate) -> User:
        user = User(id=f"user-{uuid4().hex[:10]}", **data.model_dump())
        self.users[user.id] = user
        self.groups[group_id].member_ids.append(user.id)
        return deepcopy(user)

    def list_operations(self, group_id: str) -> list[Operation]:
        result = [o for o in self.operations.values() if o.group_id == group_id]
        return deepcopy(sorted(result, key=lambda item: (item.operation_date, item.created_at), reverse=True))

    def create_operation(self, group_id: str, data: OperationCreate) -> Operation:
        if data.type == OperationType.expense:
            shares = data.shares or self._equal_shares(data.amount, data.participant_ids)
        else:
            shares = []
        operation = Operation(
            id=f"op-{uuid4().hex[:10]}",
            group_id=group_id,
            shares=shares,
            **data.model_dump(exclude={"shares"}),
        )
        self.operations[operation.id] = operation
        return deepcopy(operation)

    @staticmethod
    def _equal_shares(amount: float, participant_ids: list[str]) -> list[ShareInput]:
        cents = round(amount * 100)
        base, remainder = divmod(cents, len(participant_ids))
        return [
            ShareInput(user_id=user_id, amount=(base + (1 if index < remainder else 0)) / 100)
            for index, user_id in enumerate(participant_ids)
        ]

    def delete_operation(self, operation_id: str) -> bool:
        return self.operations.pop(operation_id, None) is not None

    def list_direct_debts(self, group_id: str) -> list[Debt]:
        return deepcopy([d for d in self.debts.values() if d.group_id == group_id])

    def create_direct_debt(self, group_id: str, data: DirectDebtCreate) -> Debt:
        debt = Debt(id=f"debt-{uuid4().hex[:10]}", group_id=group_id, **data.model_dump())
        self.debts[debt.id] = debt
        return deepcopy(debt)

    def settle_debt(self, debt_id: str) -> Debt | None:
        from app.models import DebtStatus, utc_now

        debt = self.debts.get(debt_id)
        if not debt:
            return None
        debt.status = DebtStatus.settled
        debt.settled_at = utc_now()
        return deepcopy(debt)

    def list_payments(self, group_id: str) -> list[Payment]:
        return deepcopy([p for p in self.payments.values() if p.group_id == group_id])

    def create_payment(self, group_id: str, data: PaymentCreate) -> Payment:
        payment = Payment(id=f"payment-{uuid4().hex[:10]}", group_id=group_id, **data.model_dump())
        self.payments[payment.id] = payment
        return deepcopy(payment)


storage: Storage = InMemoryStorage()
