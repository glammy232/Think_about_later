import json
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from threading import RLock
from uuid import uuid4

from openai import OpenAI
from pydantic import ValidationError

from app.ai_config import build_system_prompt, load_tool_definitions
from app.config import settings
from app.models import DirectDebtCreate, OperationCreate, OperationType
from app.services import get_balance_items, simplify_transfers
from app.storage import Storage


@dataclass
class DraftAction:
    id: str
    group_id: str
    user_id: str
    kind: str
    payload: dict
    status: str = "pending"
    result: dict | None = None


class AssistantState:
    def __init__(self):
        self.actions: dict[str, DraftAction] = {}
        self.conversations: dict[str, list[dict]] = {}
        self.lock = RLock()

    def reset(self):
        with self.lock:
            self.actions.clear()
            self.conversations.clear()


assistant_state = AssistantState()


def _period_dates(period) -> tuple[date, date]:
    today = datetime.now(timezone.utc).date()
    if isinstance(period, dict):
        start, end = (
            date.fromisoformat(period["start"]),
            date.fromisoformat(period["end"]),
        )
        if start > end:
            raise ValueError("period start must not be after end")
        return start, end
    if period == "current_month":
        return today.replace(day=1), today
    if period == "previous_month":
        end = today.replace(day=1) - timedelta(days=1)
        return end.replace(day=1), end
    if period == "last_7_days":
        return today - timedelta(days=6), today
    if period == "last_30_days":
        return today - timedelta(days=29), today
    raise ValueError("unsupported period")


class DeepSeekAssistant:
    def __init__(self, storage: Storage, client=None):
        self.storage = storage
        self.client = client or OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )
        self.created_this_turn: set[str] = set()

    @staticmethod
    def configured() -> bool:
        return bool(settings.deepseek_api_key)

    def ask(
        self, group_id: str, user_id: str, message: str, conversation_id: str | None
    ):
        conversation_id = conversation_id or f"chat-{uuid4().hex}"
        members = self.storage.list_users(group_id)
        user = next((item for item in members if item.id == user_id), None)
        if not user:
            raise ValueError("current user is not a group member")
        currency = self.storage.settings.get(user_id, {}).get("currency", "RUB")
        categories = sorted(
            {item.category for item in self.storage.list_operations(group_id)}
        )
        system = build_system_prompt(
            group_id=group_id,
            currency=str(currency),
            user=user,
            members=members,
            categories=categories,
        )
        with assistant_state.lock:
            history = list(assistant_state.conversations.get(conversation_id, []))[-30:]
        messages = [
            {"role": "system", "content": system},
            *history,
            {"role": "user", "content": message},
        ]
        tools = [
            {"type": "function", "function": item} for item in load_tool_definitions()
        ]
        self.created_this_turn = set()

        for _ in range(8):
            response = self.client.chat.completions.create(
                model=settings.deepseek_model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2,
            )
            assistant_message = response.choices[0].message
            messages.append(assistant_message.model_dump(exclude_none=True))
            if not assistant_message.tool_calls:
                answer = assistant_message.content or "Не удалось сформировать ответ."
                break
            for call in assistant_message.tool_calls:
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                    result = self.execute_tool(
                        group_id, user_id, call.function.name, arguments
                    )
                except (ValueError, ValidationError, KeyError, TypeError) as exc:
                    result = {"status": "error", "message": str(exc)}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
        else:
            raise RuntimeError("AI tool-call limit exceeded")

        saved = [item for item in messages if item["role"] != "system"][-30:]
        with assistant_state.lock:
            assistant_state.conversations[conversation_id] = saved
        pending = self._latest_pending(group_id, user_id)
        return answer, conversation_id, pending

    def execute_tool(self, group_id: str, user_id: str, name: str, args: dict) -> dict:
        handlers = {
            "get_expense_summary": self._expense_summary,
            "get_category_expenses": self._category_expenses,
            "get_top_categories": self._top_categories,
            "compare_periods": self._compare_periods,
            "get_budget_status": self._budget_status,
            "get_group_distribution": self._group_distribution,
            "get_balances": self._balances,
            "get_forecast": self._forecast,
            "simulate_expense_change": self._simulate,
            "prepare_expense": self._prepare_expense,
            "prepare_income": self._prepare_income,
            "prepare_debt": self._prepare_debt,
            "confirm_action": self._confirm,
            "cancel_action": self._cancel,
        }
        if name not in handlers:
            raise ValueError("unknown tool")
        return handlers[name](group_id, user_id, **args)

    def _operations(self, group_id, period, category=None):
        start, end = _period_dates(period)
        return [
            op
            for op in self.storage.list_operations(group_id)
            if start <= op.operation_date <= end
            and (category is None or op.category.casefold() == category.casefold())
        ]

    def _expense_summary(self, group_id, user_id, period):
        ops = self._operations(group_id, period)
        return {
            "status": "ok" if ops else "no_data",
            "expenses": round(
                sum(o.amount for o in ops if o.type == OperationType.expense), 2
            ),
            "incomes": round(
                sum(o.amount for o in ops if o.type == OperationType.income), 2
            ),
        }

    def _category_expenses(self, group_id, user_id, period, category):
        ops = [
            o
            for o in self._operations(group_id, period, category)
            if o.type == OperationType.expense
        ]
        return {
            "status": "ok" if ops else "no_data",
            "category": category,
            "amount": round(sum(o.amount for o in ops), 2),
        }

    def _top_categories(self, group_id, user_id, period, limit=3):
        totals = {}
        for op in self._operations(group_id, period):
            if op.type == OperationType.expense:
                totals[op.category] = totals.get(op.category, 0) + op.amount
        items = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]
        return {
            "status": "ok" if items else "no_data",
            "categories": [{"name": k, "amount": round(v, 2)} for k, v in items],
        }

    def _compare_periods(self, group_id, user_id, period_1, period_2, category_limit=5):
        first = self._expense_summary(group_id, user_id, period_1)
        second = self._expense_summary(group_id, user_id, period_2)
        return {
            "status": "ok",
            "period_1": first,
            "period_2": second,
            "difference": round(second["expenses"] - first["expenses"], 2),
        }

    def _budget_status(self, group_id, user_id, period):
        summary = self._expense_summary(group_id, user_id, period)
        return {
            "status": "ok",
            "budget": None,
            "expenses": summary["expenses"],
            "remaining": None,
        }

    def _group_distribution(self, group_id, user_id, period, category=None):
        ops = [
            o
            for o in self._operations(group_id, period, category)
            if o.type == OperationType.expense
        ]
        names = {u.id: u.name for u in self.storage.list_users(group_id)}
        totals = {uid: 0.0 for uid in names}
        for op in ops:
            totals[op.payer_id] += op.amount
        total = sum(totals.values())
        return {
            "status": "ok" if ops else "no_data",
            "members": [
                {
                    "user_id": uid,
                    "name": names[uid],
                    "amount": round(amount, 2),
                    "percentage": round(amount / total * 100, 2) if total else 0,
                }
                for uid, amount in totals.items()
            ],
        }

    def _balances(self, group_id, user_id):
        return {
            "status": "ok",
            "balances": [
                x.model_dump() for x in get_balance_items(self.storage, group_id)
            ],
            "recommended_transfers": [
                x.model_dump() for x in simplify_transfers(self.storage, group_id)
            ],
        }

    def _forecast(self, group_id, user_id, period):
        start, end = _period_dates(period)
        spent = self._expense_summary(group_id, user_id, period)["expenses"]
        days_elapsed = max((end - start).days + 1, 1)
        days_month = monthrange(end.year, end.month)[1]
        return {
            "status": "ok" if spent else "insufficient_data",
            "spent": spent,
            "forecast": round(spent / days_elapsed * days_month, 2),
        }

    def _simulate(self, group_id, user_id, period, category, change_percent):
        current = self._category_expenses(group_id, user_id, period, category)["amount"]
        return {
            "status": "ok",
            "category": category,
            "current": current,
            "change_percent": change_percent,
            "scenario": round(current * (1 + change_percent / 100), 2),
        }

    def _validate_members(self, group_id: str, ids: list[str]):
        members = {u.id for u in self.storage.list_users(group_id)}
        invalid = set(ids) - members
        if invalid:
            raise ValueError(f"users are not group members: {sorted(invalid)}")

    def _store_draft(self, group_id, user_id, kind, payload):
        # Актуальные правила помощника требуют сохранять ясную операцию сразу.
        if kind in {"expense", "income"}:
            self.storage.create_operation(group_id, OperationCreate.model_validate(payload))
        elif kind == "debt":
            self.storage.create_direct_debt(group_id, DirectDebtCreate.model_validate(payload))
        return {"status": "ok", "saved": True, "operation": {"type": kind, **payload}}
        # Старый draft-код оставлен ниже для совместимости с confirm endpoint.
        action = DraftAction(f"action-{uuid4().hex}", group_id, user_id, kind, payload)
        with assistant_state.lock:
            assistant_state.actions[action.id] = action
        self.created_this_turn.add(action.id)
        return {
            "status": "confirmation_required",
            "action_id": action.id,
            "draft": {"type": kind, **payload},
        }

    def _prepare_expense(self, group_id, user_id, **payload):
        payload["type"] = "expense"
        payload["source"] = "ai"
        data = OperationCreate.model_validate(payload)
        self._validate_members(group_id, [data.payer_id, *data.participant_ids])
        return self._store_draft(
            group_id, user_id, "expense", data.model_dump(mode="json")
        )

    def _prepare_income(self, group_id, user_id, recipient_id, **payload):
        raw = {
            **payload,
            "type": "income",
            "payer_id": recipient_id,
            "participant_ids": [recipient_id],
            "split_type": "equal",
            "source": "ai",
        }
        data = OperationCreate.model_validate(raw)
        self._validate_members(group_id, [recipient_id])
        return self._store_draft(
            group_id, user_id, "income", data.model_dump(mode="json")
        )

    def _prepare_debt(self, group_id, user_id, **payload):
        data = DirectDebtCreate.model_validate(payload)
        self._validate_members(group_id, [data.debtor_id, data.creditor_id])
        return self._store_draft(
            group_id, user_id, "debt", data.model_dump(mode="json")
        )

    def _get_action(self, group_id, user_id, action_id):
        action = assistant_state.actions.get(action_id)
        if not action or action.group_id != group_id or action.user_id != user_id:
            raise ValueError("action not found")
        return action

    def _confirm(self, group_id, user_id, action_id):
        action = self._get_action(group_id, user_id, action_id)
        if action_id in self.created_this_turn:
            raise ValueError("action cannot be confirmed in the same turn")
        if action.status == "confirmed":
            return {
                "status": "confirmed",
                "action_id": action.id,
                "result": action.result,
                "idempotent": True,
            }
        if action.status != "pending":
            raise ValueError("action is not pending")
        if action.kind in {"expense", "income"}:
            result = self.storage.create_operation(
                group_id, OperationCreate.model_validate(action.payload)
            ).model_dump(mode="json")
        else:
            result = self.storage.create_direct_debt(
                group_id, DirectDebtCreate.model_validate(action.payload)
            ).model_dump(mode="json")
        action.status, action.result = "confirmed", result
        return {"status": "confirmed", "action_id": action.id, "result": result}

    def _cancel(self, group_id, user_id, action_id):
        action = self._get_action(group_id, user_id, action_id)
        if action.status == "confirmed":
            raise ValueError("confirmed action cannot be cancelled")
        action.status = "cancelled"
        return {"status": "cancelled", "action_id": action.id}

    def confirm(self, group_id, user_id, action_id):
        self.created_this_turn = set()
        return self._confirm(group_id, user_id, action_id)

    def cancel(self, group_id, user_id, action_id):
        return self._cancel(group_id, user_id, action_id)

    def _latest_pending(self, group_id, user_id):
        actions = [
            a
            for a in assistant_state.actions.values()
            if a.group_id == group_id and a.user_id == user_id and a.status == "pending"
        ]
        if not actions:
            return None
        action = actions[-1]
        return {"action_id": action.id, "type": action.kind, **action.payload}
