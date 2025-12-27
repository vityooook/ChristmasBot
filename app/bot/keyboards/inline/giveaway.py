from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.bot.handlers.callback.my_callback import GiveawayCallback
from app.i18n import tr


def build_main_menu(channel_url: str, bot_url: str) -> InlineKeyboardMarkup:
    """
    Главное меню с 3 кнопками:
    - Подписаться на канал (ссылка)
    - Подключить VPN (ссылка на бота)
    - Проверить условия (callback)
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=tr("kb.subscribe_channel"), url=channel_url)
    builder.button(text=tr("kb.connect_vpn"), url=bot_url)
    builder.button(text=tr("kb.check_conditions"), callback_data=GiveawayCallback(act="check"))
    builder.adjust(1)
    return builder.as_markup()


def build_conditions_failed(
    channel_url: str,
    bot_url: str,
    is_subscribed: bool,
    is_vpn_connected: bool,
) -> InlineKeyboardMarkup:
    """
    Меню когда условия НЕ выполнены.
    Показывает статус в кнопках (✅/❌).
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопка канала со статусом
    sub_status = "✅" if is_subscribed else "❌"
    builder.button(text=f"{sub_status} Подписка на канал", url=channel_url)
    
    # Кнопка VPN со статусом
    vpn_status = "✅" if is_vpn_connected else "❌"
    builder.button(text=f"{vpn_status} Подключить VPN", url=bot_url)
    
    # Кнопка повторной проверки
    builder.button(text=tr("kb.try_again"), callback_data=GiveawayCallback(act="check"))
    
    builder.adjust(1)
    return builder.as_markup()
