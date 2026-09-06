from datetime import datetime
from uuid import uuid4

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.models import (
    Debt,
    DirectDebtCreate,
    Group,
    GroupCreate,
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


def _numeric_id(value: str) -> int:
    """Accept both database IDs ("12") and API-prefixed IDs ("user-12")."""
    try:
        return int(value.rsplit("-", 1)[-1])
    except (TypeError, ValueError):
        # Old browser sessions can contain in-memory IDs such as group-ab12cd.
        # Treat them as a missing row so the API returns its normal 404 response.
        return -1


def _date(value):
    return value.date() if isinstance(value, datetime) else value


class PostgresStorage:
    """PostgreSQL implementation of the storage contract used by FastAPI."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        # Kept for AI prompt compatibility; currency is fixed to RUB by the API.
        self.settings: dict[str, dict] = {}
        self.pool = ConnectionPool(
            conninfo=database_url,
            min_size=1,
            max_size=10,
            open=True,
            kwargs={"row_factory": dict_row, "prepare_threshold": None},
        )
        self.pool.wait(timeout=15)
        with self._connection() as connection:
            connection.execute("SELECT 1")

    def _connection(self):
        # Supabase transaction pooler reuses server connections between clients;
        # named prepared statements can therefore collide across requests.
        return self.pool.connection()

    @staticmethod
    def _shares(data: OperationCreate) -> list[ShareInput]:
        if data.type == OperationType.income:
            return []
        if data.split_type == SplitType.equal:
            cents = round(data.amount * 100)
            base, remainder = divmod(cents, len(data.participant_ids))
            amounts = [
                (user_id, (base + (index < remainder)) / 100)
                for index, user_id in enumerate(data.participant_ids)
            ]
        elif data.split_type == SplitType.custom:
            amounts = [
                (share.user_id, float(share.amount or 0)) for share in data.shares or []
            ]
        else:
            total_cents = round(data.amount * 100)
            allocated = 0
            amounts = []
            for index, share in enumerate(data.shares or []):
                share_cents = (
                    total_cents - allocated
                    if index == len(data.shares or []) - 1
                    else round(total_cents * float(share.percentage or 0) / 100)
                )
                allocated += share_cents
                amounts.append((share.user_id, share_cents / 100))
        result = []
        allocated_percentage = 0.0
        for index, (user_id, amount) in enumerate(amounts):
            percentage = (
                round(100 - allocated_percentage, 2)
                if index == len(amounts) - 1
                else round(amount / data.amount * 100, 2)
            )
            allocated_percentage += percentage
            result.append(
                ShareInput(user_id=user_id, amount=amount, percentage=percentage)
            )
        return result

    def get_group(self, group_id: str) -> Group | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, name FROM groups WHERE id = %s", (_numeric_id(group_id),)
            ).fetchone()
            if not row:
                return None
            members = connection.execute(
                "SELECT user_id FROM group_members WHERE group_id = %s ORDER BY id",
                (row["id"],),
            ).fetchall()
        return Group(
            id=str(row["id"]),
            name=row["name"],
            member_ids=[str(item["user_id"]) for item in members],
        )

    def create_group(self, data: GroupCreate) -> tuple[Group, User]:
        token = uuid4().hex
        with self._connection() as connection:
            owner = connection.execute(
                "INSERT INTO users(name, email, password_hash) VALUES (%s, %s, %s) RETURNING id, name",
                (data.owner_name, f"local-{token}@krug.invalid", "local-account"),
            ).fetchone()
            group = connection.execute(
                "INSERT INTO groups(name, created_by) VALUES (%s, %s) RETURNING id, name",
                (data.name, owner["id"]),
            ).fetchone()
            connection.execute(
                "INSERT INTO group_members(user_id, group_id, role) VALUES (%s, %s, 'admin')",
                (owner["id"], group["id"]),
            )
        user = User(id=str(owner["id"]), name=owner["name"])
        return Group(
            id=str(group["id"]), name=group["name"], member_ids=[user.id]
        ), user

    def list_users(self, group_id: str) -> list[User]:
        with self._connection() as connection:
            rows = connection.execute(
                """SELECT u.id, u.name FROM users u
                   JOIN group_members gm ON gm.user_id = u.id
                   WHERE gm.group_id = %s ORDER BY gm.id""",
                (_numeric_id(group_id),),
            ).fetchall()
        return [User(id=str(row["id"]), name=row["name"]) for row in rows]

    def add_member(self, group_id: str, data: MemberCreate) -> User:
        token = uuid4().hex
        with self._connection() as connection:
            user = connection.execute(
                "INSERT INTO users(name, email, password_hash) VALUES (%s, %s, %s) RETURNING id, name",
                (data.name, f"local-{token}@krug.invalid", "local-account"),
            ).fetchone()
            connection.execute(
                "INSERT INTO group_members(user_id, group_id, role) VALUES (%s, %s, 'member')",
                (user["id"], _numeric_id(group_id)),
            )
        return User(id=str(user["id"]), name=user["name"])

    def get_user(self, user_id: str) -> User | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT id, name FROM users WHERE id = %s", (_numeric_id(user_id),)
            ).fetchone()
        return User(id=str(row["id"]), name=row["name"]) if row else None

    def update_user_profile(self, user_id: str, name: str | None = None) -> User | None:
        if name is None:
            return self.get_user(user_id)
        with self._connection() as connection:
            row = connection.execute(
                "UPDATE users SET name = %s WHERE id = %s RETURNING id, name",
                (name, _numeric_id(user_id)),
            ).fetchone()
        return User(id=str(row["id"]), name=row["name"]) if row else None

    def update_group_name(self, group_id: str, name: str) -> Group | None:
        with self._connection() as connection:
            row = connection.execute(
                "UPDATE groups SET name = %s WHERE id = %s RETURNING id",
                (name, _numeric_id(group_id)),
            ).fetchone()
        return self.get_group(str(row["id"])) if row else None

    def list_operations(self, group_id: str) -> list[Operation]:
        numeric_group_id = _numeric_id(group_id)
        result: list[Operation] = []
        with self._connection() as connection:
            expenses = connection.execute(
                """SELECT e.*, COALESCE(e.title, e.description, 'Расход') AS effective_title,
                          c.name AS category,
                          COALESCE(
                              json_agg(json_build_object('user_id', ep.user_id, 'share', ep.share)
                                       ORDER BY ep.id) FILTER (WHERE ep.id IS NOT NULL),
                              '[]'::json
                          ) AS participant_shares
                   FROM expenses e
                   JOIN categories c ON c.id = e.category_id
                   LEFT JOIN expense_participants ep ON ep.expense_id = e.id
                   WHERE e.group_id = %s
                   GROUP BY e.id, c.name
                   ORDER BY e.expense_date DESC, e.created_at DESC""",
                (numeric_group_id,),
            ).fetchall()
            for row in expenses:
                shares = [
                    ShareInput(
                        user_id=str(item["user_id"]),
                        amount=float(item["share"]),
                        percentage=round(
                            float(item["share"]) / float(row["amount"]) * 100, 2
                        ),
                    )
                    for item in row["participant_shares"]
                ]
                result.append(
                    Operation(
                        id=f"expense-{row['id']}",
                        group_id=str(row["group_id"]),
                        type="expense",
                        title=row["effective_title"],
                        amount=float(row["amount"]),
                        category=row["category"],
                        payer_id=str(row["paid_by"]),
                        participant_ids=[item.user_id for item in shares],
                        split_type=row["split_type"],
                        shares=shares,
                        operation_date=_date(row["expense_date"]),
                        comment=row["comment"],
                        source=row["source"],
                        created_at=row["created_at"],
                    )
                )
            incomes = connection.execute(
                "SELECT * FROM incomes WHERE group_id = %s ORDER BY income_date DESC, created_at DESC",
                (numeric_group_id,),
            ).fetchall()
            result.extend(
                Operation(
                    id=f"income-{row['id']}",
                    group_id=str(row["group_id"]),
                    type="income",
                    title=row["title"],
                    amount=float(row["amount"]),
                    category=row["category"],
                    payer_id=str(row["received_by"]),
                    participant_ids=[str(row["received_by"])],
                    split_type="equal",
                    shares=[],
                    operation_date=row["income_date"],
                    comment=row["comment"],
                    source=row["source"],
                    created_at=row["created_at"],
                )
                for row in incomes
            )
        return sorted(
            result,
            key=lambda item: (item.operation_date, item.created_at),
            reverse=True,
        )

    def create_operation(self, group_id: str, data: OperationCreate) -> Operation:
        numeric_group_id = _numeric_id(group_id)
        shares = self._shares(data)
        with self._connection() as connection:
            if data.type == OperationType.income:
                row = connection.execute(
                    """INSERT INTO incomes(group_id, received_by, title, category, amount, income_date, comment, source)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                    (
                        numeric_group_id,
                        _numeric_id(data.payer_id),
                        data.title,
                        data.category,
                        data.amount,
                        data.operation_date,
                        data.comment,
                        data.source,
                    ),
                ).fetchone()
                operation_id = f"income-{row['id']}"
            else:
                category = connection.execute(
                    """INSERT INTO categories(name) VALUES (%s)
                       ON CONFLICT(name) DO UPDATE SET name = EXCLUDED.name RETURNING id""",
                    (data.category,),
                ).fetchone()
                row = connection.execute(
                    """INSERT INTO expenses(group_id, paid_by, category_id, amount, description, expense_date,
                                              title, split_type, comment, source)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                    (
                        numeric_group_id,
                        _numeric_id(data.payer_id),
                        category["id"],
                        data.amount,
                        data.comment,
                        data.operation_date,
                        data.title,
                        data.split_type.value,
                        data.comment,
                        data.source,
                    ),
                ).fetchone()
                for share in shares:
                    connection.execute(
                        "INSERT INTO expense_participants(expense_id, user_id, share) VALUES (%s,%s,%s)",
                        (row["id"], _numeric_id(share.user_id), share.amount),
                    )
                operation_id = f"expense-{row['id']}"
        return next(
            item for item in self.list_operations(group_id) if item.id == operation_id
        )

    def delete_operation(self, operation_id: str) -> bool:
        table = "incomes" if operation_id.startswith("income-") else "expenses"
        with self._connection() as connection:
            row = connection.execute(
                f"DELETE FROM {table} WHERE id = %s RETURNING id",
                (_numeric_id(operation_id),),
            ).fetchone()
        return row is not None

    def list_direct_debts(self, group_id: str) -> list[Debt]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM direct_debts WHERE group_id = %s ORDER BY created_at DESC",
                (_numeric_id(group_id),),
            ).fetchall()
        return [
            Debt(
                id=f"debt-{row['id']}",
                group_id=str(row["group_id"]),
                debtor_id=str(row["debtor_id"]),
                creditor_id=str(row["creditor_id"]),
                amount=float(row["amount"]),
                description=row["description"],
                status=row["status"],
                due_date=row["due_date"],
                created_at=row["created_at"],
                settled_at=row["settled_at"],
            )
            for row in rows
        ]

    def create_direct_debt(self, group_id: str, data: DirectDebtCreate) -> Debt:
        with self._connection() as connection:
            row = connection.execute(
                """INSERT INTO direct_debts(group_id, debtor_id, creditor_id, amount, description, due_date)
                   VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                (
                    _numeric_id(group_id),
                    _numeric_id(data.debtor_id),
                    _numeric_id(data.creditor_id),
                    data.amount,
                    data.description,
                    data.due_date,
                ),
            ).fetchone()
        return next(
            item
            for item in self.list_direct_debts(group_id)
            if item.id == f"debt-{row['id']}"
        )

    def settle_debt(self, debt_id: str) -> Debt | None:
        with self._connection() as connection:
            row = connection.execute(
                """UPDATE direct_debts SET status = 'settled', settled_at = now()
                   WHERE id = %s RETURNING group_id""",
                (_numeric_id(debt_id),),
            ).fetchone()
        if not row:
            return None
        return next(
            item
            for item in self.list_direct_debts(str(row["group_id"]))
            if item.id == debt_id
        )

    def list_payments(self, group_id: str) -> list[Payment]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM settlements WHERE group_id = %s ORDER BY settled_at DESC",
                (_numeric_id(group_id),),
            ).fetchall()
        return [
            Payment(
                id=f"payment-{row['id']}",
                group_id=str(row["group_id"]),
                from_user_id=str(row["from_user_id"]),
                to_user_id=str(row["to_user_id"]),
                amount=float(row["amount"]),
                comment=row["comment"],
                created_at=row["settled_at"],
            )
            for row in rows
        ]

    def create_payment(self, group_id: str, data: PaymentCreate) -> Payment:
        with self._connection() as connection:
            row = connection.execute(
                """INSERT INTO settlements(group_id, from_user_id, to_user_id, amount, comment)
                   VALUES (%s,%s,%s,%s,%s) RETURNING *""",
                (
                    _numeric_id(group_id),
                    _numeric_id(data.from_user_id),
                    _numeric_id(data.to_user_id),
                    data.amount,
                    data.comment,
                ),
            ).fetchone()
        return Payment(
            id=f"payment-{row['id']}",
            group_id=str(row["group_id"]),
            from_user_id=str(row["from_user_id"]),
            to_user_id=str(row["to_user_id"]),
            amount=float(row["amount"]),
            comment=row["comment"],
            created_at=row["settled_at"],
        )
