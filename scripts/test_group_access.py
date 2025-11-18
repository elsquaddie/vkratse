#!/usr/bin/env python3
"""
Test bot access to project group
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

async def test_group_access():
    """Test if bot can access the project group"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    group_id = os.getenv('PROJECT_TELEGRAM_GROUP_ID')

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found")
        return

    if not group_id:
        print("❌ PROJECT_TELEGRAM_GROUP_ID not found")
        return

    bot = Bot(token=token)

    print("\n" + "="*60)
    print("BOT GROUP ACCESS TEST")
    print("="*60)
    print(f"\nБот токен: {token[:20]}...")
    print(f"ID группы из .env: {group_id}")
    print("\n" + "-"*60)

    # Try to get chat info
    try:
        group_id_int = int(group_id)
        print(f"\n🔍 Проверяю доступ к группе с ID: {group_id_int}")

        chat = await bot.get_chat(group_id_int)

        print("\n✅ УСПЕХ! Бот имеет доступ к группе:")
        print(f"   Название: {chat.title}")
        print(f"   Тип: {chat.type}")
        print(f"   ID: {chat.id}")
        if chat.username:
            print(f"   Username: @{chat.username}")

        # Try to get member count
        try:
            member_count = await bot.get_chat_member_count(group_id_int)
            print(f"   Участников: {member_count}")
        except Exception as e:
            print(f"   ⚠️ Не удалось получить количество участников: {e}")

        print("\n✅ Бот правильно настроен для проверки подписки!")

    except TelegramError as e:
        print(f"\n❌ ОШИБКА: {e}")
        print("\nВозможные причины:")
        print("1. Бот НЕ добавлен в группу")
        print("2. ID группы неправильный")
        print("3. Группа была удалена или бот был удален из неё")
        print("\nЧто делать:")
        print("1. Добавьте бота в группу https://t.me/choovakee")
        print("2. Дайте боту права администратора (или хотя бы право читать сообщения)")
        print("3. Получите правильный ID через @userinfobot:")
        print("   - Добавьте @userinfobot в группу")
        print("   - Он покажет правильный ID группы")

    except ValueError:
        print(f"\n❌ ОШИБКА: ID группы должен быть числом, а не '{group_id}'")

    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_group_access())
