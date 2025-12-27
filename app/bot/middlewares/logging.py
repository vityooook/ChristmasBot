"""Middleware для логирования сообщений и callback."""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from loguru import logger


class MessageLoggingMiddleware(BaseMiddleware):
    """Логирует входящие сообщения."""

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        logger.info(
            f"📨 Message from {event.from_user.id} (@{event.from_user.username}): "
            f"{event.text or event.caption or '[media]'}"
        )
        return await handler(event, data)


class CallbackLoggingMiddleware(BaseMiddleware):
    """Логирует входящие callback."""

    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:
        logger.info(
            f"🔘 Callback from {event.from_user.id} (@{event.from_user.username}): {event.data}"
        )
        return await handler(event, data)
