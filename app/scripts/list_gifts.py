"""
Скрипт для получения списка доступных подарков.
Запускай: python -m app.scripts.list_gifts

Выведет все доступные подарки с их ID и стоимостью в звёздах.
"""
import asyncio
import os
import sys

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from aiogram import Bot
from app.utils.config import settings


async def list_available_gifts():
    bot = Bot(token=settings.bot_token)
    
    try:
        gifts = await bot.get_available_gifts()
        
        print("=" * 60)
        print("🎁 ДОСТУПНЫЕ ПОДАРКИ")
        print("=" * 60)
        
        for gift in gifts.gifts:
            remaining = f"{gift.remaining_count}/{gift.total_count}" if gift.total_count else "∞"
            print(f"""
ID: {gift.id}
⭐ Стоимость: {gift.star_count} звёзд
📦 Осталось: {remaining}
🔼 Апгрейд: {gift.upgrade_star_count or 'нет'} звёзд
---""")
        
        print(f"\nВсего подарков: {len(gifts.gifts)}")
        print("\nИспользуй GIFT_ID в .env для отправки подарков!")
        
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(list_available_gifts())

