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


async def run_polling() -> None:
    dp = build_dp()
    bot = build_bot(settings.bot_token)
    
    logger.info("🎄 Бот запускается...")
    
    # Удаляем webhook на случай если был (без лишних логов)
    await bot.delete_webhook(drop_pending_updates=True)
    
    await dp.start_polling(bot)


def main() -> None:
    setup_logging(level=settings.log_level)
    logger.info(f"Bot: @{settings.bot_username} | Channel: @{settings.required_channel}")
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
