import asyncio
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from loguru import logger

from app.loader import build_bot, build_dp
from app.utils.config import settings


def setup_logging(level: str = "INFO") -> None:
    """Настройка loguru."""
    logger.remove()
    logger.add(
        sys.stdout,
        level=level,
        backtrace=False,
        diagnose=False,
        enqueue=True,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}",
    )


async def init_database() -> None:
    """
    Инициализация БД при старте.
    
    БЕЗОПАСНО для перезапуска:
    - create_all() создаёт таблицы ТОЛЬКО если их нет (данные НЕ удаляются)
    - ON CONFLICT DO UPDATE — если админ уже есть, просто обновит флаг
    """
    from sqlalchemy import text, inspect
    from app.database.engine import engine, Base, async_session_maker
    from app.database.models.user import User  # noqa: F401 — нужен для metadata
    
    # Проверяем существуют ли таблицы
    async with engine.begin() as conn:
        def check_tables(sync_conn):
            inspector = inspect(sync_conn)
            return "user" in inspector.get_table_names()
        
        tables_exist = await conn.run_sync(check_tables)
        
        if tables_exist:
            logger.info("БД: таблицы уже существуют ✓")
        else:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("БД: таблицы созданы")
    
    # Убеждаемся что админы имеют флаг is_admin=true
    admin_ids = settings.get_admin_ids()
    if admin_ids:
        async with async_session_maker() as session:
            for admin_id in admin_ids:
                # UPSERT: создать или обновить
                await session.execute(
                    text("""
                        INSERT INTO "user" (id, is_admin, created_at, updated_at)
                        VALUES (:id, true, timezone('utc', now()), timezone('utc', now()))
                        ON CONFLICT (id) DO UPDATE SET is_admin = true
                    """),
                    {"id": admin_id}
                )
            await session.commit()
            logger.debug(f"Админы проверены: {admin_ids}")


async def run_polling() -> None:
    # Инициализируем БД
    await init_database()
    
    dp = build_dp()
    bot = build_bot(settings.bot_token)
    
    logger.info("🎄 Бот запускается...")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


def main() -> None:
    setup_logging(level=settings.log_level)
    logger.info(f"Bot: @{settings.bot_username} | Channel: @{settings.required_channel}")
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
