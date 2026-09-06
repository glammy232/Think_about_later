from datetime import date

from app.ai_config import build_system_prompt, load_tool_definitions
from app.models import User


def test_tool_definitions_are_valid_and_unique():
    tools = load_tool_definitions()
    names = [tool["name"] for tool in tools]
    assert len(names) == len(set(names))
    assert {"prepare_expense", "prepare_income", "prepare_debt"}.issubset(names)
    assert {"confirm_action", "cancel_action", "get_balances"}.issubset(names)
    assert all(tool["parameters"]["additionalProperties"] is False for tool in tools)


def test_system_prompt_uses_backend_context_and_forbids_database_access():
    user = User(id="user-1", name="Алексей")
    prompt = build_system_prompt(
        group_id="group-1",
        currency="RUB",
        user=user,
        members=[user, User(id="user-2", name="Анна")],
        categories=["Продукты", "Дом"],
        current_date=date(2026, 9, 6),
    )
    assert "{{" not in prompt
    assert "group-1" in prompt
    assert "user-1" in prompt
    assert "2026-09-06" in prompt
    assert "не имеешь прямого доступа к базе данных" in prompt
    assert "только после однозначного подтверждения" in prompt.lower()
