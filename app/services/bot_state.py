"""Состояние бота (пауза и т.д.)."""

# Глобальное состояние паузы
_is_paused: bool = False


def is_bot_paused() -> bool:
    """Проверить, на паузе ли бот."""
    return _is_paused


def set_bot_paused(paused: bool) -> None:
    """Установить состояние паузы."""
    global _is_paused
    _is_paused = paused

