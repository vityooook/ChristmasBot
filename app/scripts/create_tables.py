"""Скрипт для создания таблиц в БД."""
import asyncio

from app.database.engine import engine, Base
from app.database.models import User  # noqa: F401 — нужен для регистрации модели


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблицы созданы!")


if __name__ == "__main__":
    asyncio.run(create_tables())

