import os


class Settings:
    app_name = "Круг API"
    version = "0.1.0"
    frontend_origins = [
        item.strip()
        for item in os.getenv(
            "FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173"
        ).split(",")
        if item.strip()
    ]


settings = Settings()

