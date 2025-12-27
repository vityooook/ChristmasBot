from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.enums import ChatType
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.exceptions import TelegramBadRequest

from loguru import logger

from app.bot.keyboards.inline import build_main_menu, build_conditions_failed
from app.bot.handlers.callback.my_callback import GiveawayCallback
from app.database.repositories.user import (
    create_user_if_absent,
    get_user,
    update_user_subscription,
    mark_gift_received,
    set_pending_gift,
)
from app.services.remnawave import check_vpn_connected
from app.services.bot_state import is_bot_paused
from app.i18n import tr
from app.utils.config import settings


router = Router(name="private_start")
router.message.filter(F.chat.type == ChatType.PRIVATE)


WELCOME_PIC_PATH = "pics/welcome.png"


def _get_channel_url() -> str:
    return f"https://t.me/{settings.required_channel}"


def _get_vpn_bot_url() -> str:
    return f"https://t.me/{settings.vpn_bot_username}"


async def _safe_edit_message(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    """Безопасное редактирование сообщения (игнорирует ошибки если контент не изменился)."""
    try:
        # Пробуем edit_caption (для фото)
        await callback.message.edit_caption(caption=text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return  # Контент тот же — ничего не делаем
        # Пробуем edit_text (для текста без фото)
        try:
            await callback.message.edit_text(text=text, reply_markup=reply_markup)
        except TelegramBadRequest as e2:
            if "message is not modified" not in str(e2):
                logger.warning(f"Failed to edit message: {e2}")


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start."""
    user_id = message.from_user.id
    username = message.from_user.username
    
    logger.info(f"/start from {user_id} (@{username})")

    # Создаём пользователя
    try:
        await create_user_if_absent(user_id=user_id, username=username)
    except Exception as e:
        logger.error(f"Error creating user {user_id}: {e}")
        await message.answer("❌ Ошибка. Попробуй позже.")
        return

    # Проверяем паузу
    if is_bot_paused():
        await message.answer(tr("start.paused"))
        return

    # Проверяем статус пользователя
    user = await get_user(user_id)
    if user and user.gift_received:
        await message.answer(tr("start.already_received"))
        return
    
    if user and user.pending_gift:
        await message.answer(tr("start.pending_gift"))
        return

    # Отправляем приветствие
    keyboard = build_main_menu(_get_channel_url(), _get_vpn_bot_url())
    
    try:
        photo = FSInputFile(WELCOME_PIC_PATH)
        await message.answer_photo(photo=photo, caption=tr("start.welcome"), reply_markup=keyboard)
    except Exception as e:
        logger.warning(f"Не удалось отправить картинку: {e}")
        await message.answer(text=tr("start.welcome"), reply_markup=keyboard)


@router.callback_query(GiveawayCallback.filter(F.act == "check"))
async def check_conditions(callback: CallbackQuery, bot: Bot):
    """Проверка условий и отправка подарка."""
    user_id = callback.from_user.id
    
    # Проверяем паузу
    if is_bot_paused():
        await callback.answer(tr("start.paused"), show_alert=True)
        return

    # Получаем пользователя
    user = await get_user(user_id)
    if not user:
        await callback.answer(tr("errors.user_not_found"), show_alert=True)
        return

    if user.gift_received:
        await callback.answer(tr("start.already_received"), show_alert=True)
        return

    if user.pending_gift:
        await callback.answer(tr("start.pending_gift"), show_alert=True)
        return

    # Проверяем условия
    is_subscribed = await _check_channel_subscription(bot, user_id)
    await update_user_subscription(user_id, is_subscribed)
    
    is_vpn_connected = await check_vpn_connected(user_id)
    
    # Все условия выполнены — отправляем подарок
    if is_subscribed and is_vpn_connected:
        await _send_gift(callback, bot, user_id)
        return
    
    # Условия НЕ выполнены
    text = tr("start.conditions_not_met")
    keyboard = build_conditions_failed(
        channel_url=_get_channel_url(),
        bot_url=_get_vpn_bot_url(),
        is_subscribed=is_subscribed,
        is_vpn_connected=is_vpn_connected,
    )
    
    await _safe_edit_message(callback, text, keyboard)
    await callback.answer()


async def _send_gift(callback: CallbackQuery, bot: Bot, user_id: int) -> None:
    """Отправка Telegram Gift."""
    
    # Проверяем баланс
    try:
        balance = await bot.get_my_star_balance()
        if balance.amount < settings.gift_star_cost:
            await _add_to_pending(callback, bot, user_id, balance.amount)
            return
    except Exception as e:
        logger.error(f"Failed to check balance: {e}")
    
    # Отправляем подарок
    try:
        await bot.send_gift(
            gift_id=settings.gift_id,
            user_id=user_id,
            text=tr("gift.message"),
        )
        
        await mark_gift_received(user_id)
        await _safe_edit_message(callback, tr("start.gift_sent"))
        await callback.answer(tr("gift.sent_alert"), show_alert=True)
        logger.info(f"Gift sent to {user_id}")
        
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        if "not enough" in error_msg or "balance" in error_msg:
            await _add_to_pending(callback, bot, user_id, 0)
        else:
            logger.error(f"Telegram error: {e}")
            await callback.answer(tr("errors.gift_send_failed"), show_alert=True)
            
    except Exception as e:
        logger.error(f"Error sending gift: {e}")
        await callback.answer(tr("errors.gift_send_failed"), show_alert=True)


async def _add_to_pending(callback: CallbackQuery, bot: Bot, user_id: int, balance: int) -> None:
    """Добавить пользователя в очередь на подарок."""
    await set_pending_gift(user_id, True)
    await _notify_admins_low_balance(bot, balance)
    await _safe_edit_message(callback, tr("start.pending_gift"))
    await callback.answer(tr("gift.pending_alert"), show_alert=True)
    logger.warning(f"User {user_id} added to pending (balance: {balance})")


async def _notify_admins_low_balance(bot: Bot, current_balance: int) -> None:
    """Уведомить админов о низком балансе."""
    admin_ids = settings.get_admin_ids()
    
    text = (
        f"⚠️ <b>Внимание!</b>\n\n"
        f"Не хватает звёзд для подарка!\n"
        f"Баланс: {current_balance} ⭐\n\n"
        f"Пополни: /donate"
    )
    
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")


async def _check_channel_subscription(bot: Bot, user_id: int) -> bool:
    """Проверить подписку на канал."""
    try:
        member = await bot.get_chat_member(
            chat_id=f"@{settings.required_channel}",
            user_id=user_id,
        )
        return member.status in ("member", "administrator", "creator")
    except TelegramBadRequest as e:
        logger.warning(f"Subscription check failed for {user_id}: {e}")
        return False
