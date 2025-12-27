from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers.private.start import router as start_router
from app.bot.handlers.private.admin import router as admin_router
from app.bot.middlewares.logging import MessageLoggingMiddleware, CallbackLoggingMiddleware


def build_dp() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    
    # Middleware для логирования
    dp.message.middleware(MessageLoggingMiddleware())
    dp.callback_query.middleware(CallbackLoggingMiddleware())
    
    # Роутеры (admin первым для приоритета команд)
    dp.include_router(admin_router)
    dp.include_router(start_router)
    return dp


def build_bot(bot_token: str) -> Bot:
    return Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
