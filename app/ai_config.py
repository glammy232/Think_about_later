import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.models import User

AI_DIR = Path(__file__).resolve().parent.parent / "ai"
PROMPT_PATH = AI_DIR / "finance_assistant_prompt.txt"
TOOLS_PATH = AI_DIR / "tools.json"


def load_tool_definitions() -> list[dict]:
    return json.loads(TOOLS_PATH.read_text(encoding="utf-8"))


def build_system_prompt(
    *,
    group_id: str,
    currency: str,
    user: User,
    members: list[User],
    categories: list[str],
    current_date: date | None = None,
) -> str:
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    replacements = {
        "{{current_date}}": (
            current_date or datetime.now(timezone.utc).date()
        ).isoformat(),
        "{{group_id}}": group_id,
        "{{currency}}": currency,
        "{{user_id}}": user.id,
        "{{user_name}}": user.name,
        "{{members_json}}": json.dumps(
            [member.model_dump(mode="json") for member in members], ensure_ascii=False
        ),
        "{{categories_json}}": json.dumps(categories, ensure_ascii=False),
    }
    for variable, value in replacements.items():
        prompt = prompt.replace(variable, value)
    return prompt
