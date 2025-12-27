from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select, update, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.engine import async_session_maker
from app.database.models.user import User


async def create_user_if_absent(
    user_id: int,
    *,
    username: Optional[str] = None,
    session: Optional[AsyncSession] = None,
) -> bool:
    """Возвращает True, если пользователь создан; False, если уже существовал."""
    sess = session or async_session_maker()
    async with sess as s:
        stmt = (
            insert(User)
            .values(id=user_id, username=username)
            .on_conflict_do_nothing(index_elements=[User.id])
            .returning(User.id)
        )
        res = await s.execute(stmt)
        await s.commit()
        return res.scalar_one_or_none() is not None


async def get_user(user_id: int) -> Optional[User]:
    """Получить пользователя по id."""
    async with async_session_maker() as s:
        result = await s.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def update_user_subscription(user_id: int, is_subscribed: bool) -> None:
    """Обновить статус подписки на канал."""
    async with async_session_maker() as s:
        await s.execute(
            update(User).where(User.id == user_id).values(is_subscribed=is_subscribed)
        )
        await s.commit()


async def mark_gift_received(user_id: int) -> None:
    """Отметить, что пользователь получил подарок."""
    async with async_session_maker() as s:
        await s.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                gift_received=True,
                gift_received_at=datetime.utcnow(),  # без timezone для TIMESTAMP WITHOUT TIME ZONE
                pending_gift=False,
            )
        )
        await s.commit()


async def set_pending_gift(user_id: int, pending: bool) -> None:
    """Установить флаг ожидания подарка."""
    async with async_session_maker() as s:
        await s.execute(
            update(User).where(User.id == user_id).values(pending_gift=pending)
        )
        await s.commit()


async def get_pending_gift_users() -> list[User]:
    """Получить пользователей, ожидающих подарок."""
    async with async_session_maker() as s:
        result = await s.execute(
            select(User).where(User.pending_gift.is_(True))
        )
        return list(result.scalars().all())


async def get_all_users() -> list[User]:
    """Получить всех пользователей для экспорта."""
    async with async_session_maker() as s:
        result = await s.execute(select(User).order_by(User.created_at))
        return list(result.scalars().all())


async def get_participants_count() -> int:
    """Получить количество участников."""
    async with async_session_maker() as s:
        result = await s.execute(select(func.count(User.id)))
        return result.scalar() or 0


async def get_gifts_sent_count() -> int:
    """Получить количество отправленных подарков."""
    async with async_session_maker() as s:
        result = await s.execute(
            select(func.count(User.id)).where(User.gift_received.is_(True))
        )
        return result.scalar() or 0


async def get_pending_count() -> int:
    """Получить количество ожидающих подарок."""
    async with async_session_maker() as s:
        result = await s.execute(
            select(func.count(User.id)).where(User.pending_gift.is_(True))
        )
        return result.scalar() or 0


async def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь админом."""
    from app.utils.config import settings
    
    # Сначала проверяем в конфиге
    if user_id in settings.get_admin_ids():
        return True
    
    # Потом в БД
    user = await get_user(user_id)
    return user.is_admin if user else False
