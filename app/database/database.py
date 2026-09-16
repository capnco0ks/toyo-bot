import os
import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.config import settings
from app.database.models import Base

logger = logging.getLogger(__name__)


def get_engine(db_url: str | None = None) -> AsyncEngine:
    url = db_url or settings.DATABASE_URL
    if url.startswith("sqlite+aiosqlite:///"):
        db_path = url.replace("sqlite+aiosqlite:///", "")
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    return create_async_engine(
        url,
        echo=False,
        future=True,
    )


engine = get_engine()
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


def _migrate_sqlite_columns_sync(connection):
    """
    Safely adds new columns to existing SQLite tables if they do not exist.
    """
    user_columns = {
        "saved_full_name": "VARCHAR(255)",
        "company_name": "VARCHAR(255)",
        "phone": "VARCHAR(64)",
        "city": "VARCHAR(128)",
        "delivery_address": "TEXT",
    }
    order_columns = {
        "customer_name": "VARCHAR(255)",
        "company_name": "VARCHAR(255)",
        "phone": "VARCHAR(64)",
        "city": "VARCHAR(128)",
        "delivery_address": "TEXT",
    }

    # Check users table
    try:
        res = connection.execute(text("PRAGMA table_info(users)"))
        existing_cols = {row[1] for row in res.fetchall()}
        for col_name, col_type in user_columns.items():
            if col_name not in existing_cols and len(existing_cols) > 0:
                logger.info(f"Adding missing column {col_name} to users table...")
                connection.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
    except Exception as e:
        logger.warning(f"Users table migration check: {e}")

    # Check orders table
    try:
        res = connection.execute(text("PRAGMA table_info(orders)"))
        existing_cols = {row[1] for row in res.fetchall()}
        for col_name, col_type in order_columns.items():
            if col_name not in existing_cols and len(existing_cols) > 0:
                logger.info(f"Adding missing column {col_name} to orders table...")
                connection.execute(text(f"ALTER TABLE orders ADD COLUMN {col_name} {col_type}"))
    except Exception as e:
        logger.warning(f"Orders table migration check: {e}")


async def init_db(engine_instance: AsyncEngine | None = None) -> None:
    eng = engine_instance or engine
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_sqlite_columns_sync)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
