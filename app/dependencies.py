from typing import Annotated

from fastapi import Header


def current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Demo auth: frontend may send X-User-Id; defaults to Алексей."""
    return x_user_id or "user-1"

