from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Boolean, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.engine import Base


class User(Base):
    """Участник розыгрыша."""
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    
    # Админ
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    
    # Кэш статуса подписки (обновляется при проверке)
    is_subscribed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    
    # Получил ли подарок
    gift_received: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    gift_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    
    # Ожидает подарок (не хватило звёзд при проверке)
    pending_gift: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=text("timezone('utc', now())"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=text("timezone('utc', now())"),
        onupdate=text("timezone('utc', now())"),
        nullable=False,
    )
