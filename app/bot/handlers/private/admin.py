"""Админ-команды: статистика, экспорт, баланс, пауза."""
import csv
import io
from datetime import datetime

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile, LabeledPrice, PreCheckoutQuery

from loguru import logger

from app.database.repositories.user import (
    is_admin,
    get_participants_count,
    get_gifts_sent_count,
    get_pending_count,
    get_all_users,
    get_pending_gift_users,
    mark_gift_received,
)
from app.services.bot_state import is_bot_paused, set_bot_paused
from app.i18n import tr
from app.utils.config import settings


router = Router(name="admin")


# ============ Фильтр админа ============

async def admin_filter(message: Message) -> bool:
    """Проверка что пользователь — админ."""
    return await is_admin(message.from_user.id)


# ============ /pause — Поставить бота на паузу ============

@router.message(Command("pause"), admin_filter)
@logger.catch(reraise=True)
async def cmd_pause(message: Message):
    """Поставить бота на паузу."""
    if is_bot_paused():
        await message.answer("⏸ Бот уже на паузе.")
        return
    
    set_bot_paused(True)
    logger.info(f"Bot paused by admin {message.from_user.id}")
    await message.answer("⏸ <b>Бот поставлен на паузу.</b>\n\nПользователи будут видеть сообщение о паузе.")


# ============ /resume — Снять бота с паузы ============

@router.message(Command("resume"), admin_filter)
@logger.catch(reraise=True)
async def cmd_resume(message: Message):
    """Снять бота с паузы."""
    if not is_bot_paused():
        await message.answer("▶️ Бот уже работает.")
        return
    
    set_bot_paused(False)
    logger.info(f"Bot resumed by admin {message.from_user.id}")
    await message.answer("▶️ <b>Бот снят с паузы.</b>\n\nРозыгрыш продолжается!")


# ============ /stats — Статистика ============

@router.message(Command("stats"), admin_filter)
@logger.catch(reraise=True)
async def cmd_stats(message: Message, bot: Bot):
    """Показать статистику розыгрыша."""
    total_users = await get_participants_count()
    gifts_sent = await get_gifts_sent_count()
    pending = await get_pending_count()
    
    # Баланс звёзд
    try:
        balance = await bot.get_my_star_balance()
        star_balance = balance.amount
    except Exception as e:
        logger.error(f"Не удалось получить баланс: {e}")
        star_balance = "?"
    
    # Статус паузы
    pause_status = "⏸ На паузе" if is_bot_paused() else "▶️ Работает"
    
    text = f"""📊 <b>Статистика розыгрыша</b>

🤖 Статус: <b>{pause_status}</b>

👥 Всего участников: <b>{total_users}</b>
🎁 Подарков отправлено: <b>{gifts_sent}</b>
⏳ Ожидают подарок: <b>{pending}</b>

⭐ Баланс бота: <b>{star_balance}</b> звёзд
💰 Стоимость подарка: <b>{settings.gift_star_cost}</b> звёзд
"""
    
    # Предупреждение если мало звёзд
    if isinstance(star_balance, int) and star_balance < settings.min_star_balance:
        text += f"\n⚠️ <b>Внимание!</b> Баланс ниже {settings.min_star_balance} звёзд!"
    
    await message.answer(text)


# ============ /export — Экспорт в CSV ============

@router.message(Command("export"), admin_filter)
@logger.catch(reraise=True)
async def cmd_export(message: Message):
    """Экспорт пользователей в CSV."""
    users = await get_all_users()
    
    # Создаём CSV в памяти
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow(["user_id", "username", "gift_received", "pending_gift", "created_at"])
    
    # Данные
    for user in users:
        writer.writerow([
            user.id,
            user.username or "",
            "да" if user.gift_received else "нет",
            "да" if user.pending_gift else "нет",
            user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "",
        ])
    
    # Отправляем файл
    csv_bytes = output.getvalue().encode("utf-8-sig")  # BOM для Excel
    filename = f"users_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    file = BufferedInputFile(csv_bytes, filename=filename)
    await message.answer_document(file, caption=f"📄 Экспорт: {len(users)} пользователей")


# ============ /balance — Баланс звёзд ============

@router.message(Command("balance"), admin_filter)
@logger.catch(reraise=True)
async def cmd_balance(message: Message, bot: Bot):
    """Показать баланс звёзд бота."""
    try:
        balance = await bot.get_my_star_balance()
        
        gifts_possible = balance.amount // settings.gift_star_cost
        pending = await get_pending_count()
        
        text = f"""⭐ <b>Баланс бота</b>

💫 Звёзд на балансе: <b>{balance.amount}</b>
🎁 Можно отправить подарков: <b>{gifts_possible}</b>
⏳ Ожидают подарок: <b>{pending}</b>
"""
        
        if balance.amount < settings.min_star_balance:
            text += f"\n⚠️ Баланс ниже {settings.min_star_balance}! Пополни бота."
        
        if pending > 0 and gifts_possible >= pending:
            text += f"\n\n✅ Достаточно звёзд для отправки всех ожидающих подарков."
            text += f"\nИспользуй /send_pending для отправки."
        
        await message.answer(text)
        
    except Exception as e:
        logger.error(f"Ошибка получения баланса: {e}")
        await message.answer("❌ Не удалось получить баланс звёзд.")


# ============ /send_pending — Отправить ожидающие подарки ============

@router.message(Command("send_pending"), admin_filter)
@logger.catch(reraise=True)
async def cmd_send_pending(message: Message, bot: Bot):
    """Отправить подарки всем ожидающим."""
    pending_users = await get_pending_gift_users()
    
    if not pending_users:
        await message.answer("✅ Нет пользователей, ожидающих подарок.")
        return
    
    # Проверяем баланс
    try:
        balance = await bot.get_my_star_balance()
        needed = len(pending_users) * settings.gift_star_cost
        
        if balance.amount < needed:
            await message.answer(
                f"❌ Недостаточно звёзд.\n\n"
                f"Нужно: {needed} ⭐\n"
                f"Есть: {balance.amount} ⭐"
            )
            return
    except Exception as e:
        logger.error(f"Ошибка проверки баланса: {e}")
        await message.answer("❌ Не удалось проверить баланс.")
        return
    
    # Отправляем подарки
    sent = 0
    failed = 0
    
    status_msg = await message.answer(f"⏳ Отправка подарков: 0/{len(pending_users)}...")
    
    for user in pending_users:
        try:
            await bot.send_gift(
                gift_id=settings.gift_id,
                user_id=user.id,
                text=tr("gift.message"),
            )
            await mark_gift_received(user.id)
            sent += 1
            logger.info(f"Pending gift sent to {user.id}")
        except Exception as e:
            logger.error(f"Failed to send pending gift to {user.id}: {e}")
            failed += 1
        
        # Обновляем статус каждые 5 отправок
        if (sent + failed) % 5 == 0:
            try:
                await status_msg.edit_text(
                    f"⏳ Отправка подарков: {sent + failed}/{len(pending_users)}..."
                )
            except Exception:
                pass
    
    await status_msg.edit_text(
        f"✅ Готово!\n\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Ошибок: {failed}"
    )


# ============ /donate — Пополнить звёзды ============

@router.message(Command("donate"), admin_filter)
@logger.catch(reraise=True)
async def cmd_donate(message: Message, bot: Bot):
    """Создать инвойс для пополнения звёзд."""
    # Количество звёзд для покупки (можно передать аргументом)
    args = message.text.split()
    amount = int(args[1]) if len(args) > 1 and args[1].isdigit() else 100
    
    await bot.send_invoice(
        chat_id=message.chat.id,
        title="Пополнение звёзд",
        description=f"Пополнение баланса бота на {amount} звёзд",
        payload=f"donate_{amount}",
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label="Звёзды", amount=amount)],
    )


# ============ Обработка платежа ============

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    """Подтверждение платежа."""
    await query.answer(ok=True)


@router.message(F.successful_payment)
@logger.catch(reraise=True)
async def successful_payment(message: Message, bot: Bot):
    """Обработка успешного платежа."""
    payment = message.successful_payment
    amount = payment.total_amount
    
    logger.info(f"Payment received: {amount} stars from {message.from_user.id}")
    
    await message.answer(
        f"✅ Оплата получена!\n\n"
        f"⭐ Добавлено: {amount} звёзд"
    )
    
    # Проверяем есть ли ожидающие подарки
    pending = await get_pending_count()
    if pending > 0:
        await message.answer(
            f"⏳ Есть {pending} пользователей, ожидающих подарок.\n"
            f"Используй /send_pending для отправки."
        )


# ============ /admin — Справка для админа ============

@router.message(Command("admin"), admin_filter)
@logger.catch(reraise=True)
async def cmd_admin_help(message: Message):
    """Справка по админ-командам."""
    text = """🔧 <b>Админ-команды</b>

<b>Управление:</b>
/pause — Поставить бота на паузу
/resume — Снять с паузы

<b>Статистика:</b>
/stats — Статистика розыгрыша
/balance — Баланс звёзд бота
/export — Экспорт пользователей в CSV

<b>Подарки:</b>
/send_pending — Отправить подарки ожидающим
/donate [кол-во] — Пополнить звёзды бота

/admin — Эта справка
"""
    await message.answer(text)
