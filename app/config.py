from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = Field(default="", description="Telegram Bot API Token")
    ADMIN_IDS: List[int] = Field(default_factory=list, description="List of Admin Telegram IDs")
    # Optional whitelist of managers allowed to press order buttons in the managers group.
    # Empty list = any member of ORDER_CHAT_ID may process orders.
    MANAGER_IDS: List[int] = Field(default_factory=list, description="List of Manager Telegram IDs")
    ORDER_CHAT_ID: int = Field(default=0, description="Telegram Chat/Group ID for manager order notifications")
    MANAGER_USERNAME: str = Field(default="manager", description="Manager Telegram username without @")
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///data/database.db", description="Database connection URL")
    # Local timezone offset for displayed dates (Kazakhstan = UTC+5)
    TZ_OFFSET_HOURS: int = Field(default=5, description="Timezone offset from UTC in hours")
    DEFAULT_PRICE_PATH: str = Field(
        default=r"C:\Users\User\Desktop\ПРАЙС TOYO 01.09.2026.xls",
        description="Path to default price Excel file"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("ADMIN_IDS", "MANAGER_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, (int, float)):
            return [int(v)]
        if isinstance(v, list):
            return [int(x) for x in v]
        return []

    @field_validator("ORDER_CHAT_ID", mode="before")
    @classmethod
    def parse_order_chat_id(cls, v):
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return 0
            return int(v_str)
        if isinstance(v, (int, float)):
            return int(v)
        return 0

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v):
        """
        Accepts provider-style Postgres URLs (postgres://... from Neon/Supabase/Render)
        and converts them to the async SQLAlchemy driver form.
        """
        if not isinstance(v, str) or not v.strip():
            return "sqlite+aiosqlite:///data/database.db"
        url = v.strip()
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        return url


settings = Settings()
