import json
from types import SimpleNamespace

import pytest

from app.ai_service import DeepSeekAssistant, assistant_state
from app.storage import InMemoryStorage


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, exclude_none=True):
        result = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            result["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in self.tool_calls
            ]
        return {key: value for key, value in result.items() if value is not None}


class FakeClient:
    def __init__(self, messages):
        self.messages = iter(messages)
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: next(self.messages))
        )


def completion(message):
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def tool_call(name, arguments):
    return SimpleNamespace(
        id="call-1",
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )


@pytest.fixture(autouse=True)
def clean_ai_state():
    assistant_state.reset()


def test_ai_prepares_expense_without_mutating_storage():
    storage = InMemoryStorage()
    count_before = len(storage.list_operations("group-1"))
    client = FakeClient(
        [
            completion(
                FakeMessage(
                    tool_calls=[
                        tool_call(
                            "prepare_expense",
                            {
                                "title": "Продукты",
                                "amount": 5000,
                                "category": "Продукты",
                                "payer_id": "user-1",
                                "participant_ids": ["user-2", "user-3"],
                                "split_type": "custom",
                                "shares": [
                                    {"user_id": "user-2", "amount": 2000},
                                    {"user_id": "user-3", "amount": 3000},
                                ],
                            },
                        )
                    ]
                )
            ),
            completion(FakeMessage("Черновик готов. Подтвердить?")),
        ]
    )
    answer, conversation_id, pending = DeepSeekAssistant(storage, client).ask(
        "group-1", "user-1", "Потратил 5000 на продукты", None
    )
    assert answer == "Черновик готов. Подтвердить?"
    assert conversation_id.startswith("chat-")
    assert pending["amount"] == 5000
    assert len(storage.list_operations("group-1")) == count_before

    result = DeepSeekAssistant(storage, object()).confirm(
        "group-1", "user-1", pending["action_id"]
    )
    assert result["status"] == "confirmed"
    assert len(storage.list_operations("group-1")) == count_before + 1

    repeated = DeepSeekAssistant(storage, object()).confirm(
        "group-1", "user-1", pending["action_id"]
    )
    assert repeated["idempotent"] is True
    assert len(storage.list_operations("group-1")) == count_before + 1


def test_draft_cannot_be_confirmed_by_another_user():
    storage = InMemoryStorage()
    service = DeepSeekAssistant(storage, object())
    draft = service.execute_tool(
        "group-1",
        "user-1",
        "prepare_debt",
        {
            "debtor_id": "user-2",
            "creditor_id": "user-1",
            "amount": 1000,
            "description": "За продукты",
        },
    )
    with pytest.raises(ValueError, match="action not found"):
        DeepSeekAssistant(storage, object()).confirm(
            "group-1", "user-2", draft["action_id"]
        )


def test_ai_analytics_uses_backend_data():
    service = DeepSeekAssistant(InMemoryStorage(), object())
    result = service.execute_tool("group-1", "user-1", "get_balances", {})
    assert result["status"] == "ok"
    assert len(result["balances"]) == 5
