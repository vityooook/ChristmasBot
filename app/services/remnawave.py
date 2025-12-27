"""Клиент Remnawave для проверки VPN подключения."""
from __future__ import annotations

from typing import Optional

from loguru import logger
from remnawave import RemnawaveSDK
from remnawave.exceptions.general import ApiError, NotFoundError

from app.utils.config import settings


_sdk: Optional[RemnawaveSDK] = None


def _get_sdk() -> Optional[RemnawaveSDK]:
    """Получить SDK Remnawave (singleton)."""
    global _sdk
    
    if _sdk is not None:
        return _sdk
    
    if not settings.remnawave_api_url or not settings.remnawave_api_key:
        return None
    
    _sdk = RemnawaveSDK(
        base_url=settings.remnawave_api_url.rstrip("/"),
        token=settings.remnawave_api_key.strip(),
    )
    return _sdk


async def check_vpn_connected(telegram_id: int, prefix: int | str = 1) -> bool:
    """
    Проверить, подключил ли пользователь VPN.
    
    Возвращает True если first_connected не пустое.
    """
    sdk = _get_sdk()
    if sdk is None:
        return False
    
    username = f"{prefix}_{telegram_id}"
    
    try:
        user = await sdk.users.get_user_by_username(username=username)
        return user.first_connected is not None
    except NotFoundError:
        return False
    except ApiError as e:
        logger.error(f"Remnawave error: {e}")
        return False
