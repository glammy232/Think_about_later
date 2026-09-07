import os
from typing import ClassVar

from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_name = "Круг API"
    version = "0.1.0"
    frontend_origins: ClassVar[list[str]] = [
        item.strip()
        for item in os.getenv(
            "FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173"
        ).split(",")
        if item.strip()
    ]
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    # deepseek-v4-flash is not a generally available chat model; keep the
    # legacy value from breaking requests after an upgrade.
    deepseek_model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    if deepseek_model == "deepseek-v4-flash":
        deepseek_model = "deepseek-chat"
    database_url = os.getenv("DATABASE_URL", "")
    app_timezone = os.getenv("APP_TIMEZONE", "Asia/Yekaterinburg")
    gigachat_credentials = os.getenv("GIGACHAT_CREDENTIALS", "")
    gigachat_model = os.getenv("GIGACHAT_MODEL", "GigaChat-2-Pro")


settings = Settings()
