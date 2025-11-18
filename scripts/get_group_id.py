#!/usr/bin/env python3
"""
Script to get Telegram group ID
Run this locally to find the correct group ID
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Bot
from dotenv import load_dotenv

load_dotenv()

async def get_group_info():
    """Get information about your group"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env")
        return

    bot = Bot(token=token)

    print("\n" + "="*60)
    print("TELEGRAM GROUP ID FINDER")
    print("="*60)
    print("\nВарианты:\n")
    print("1. Перешлите любое сообщение из группы в личку боту")
    print("2. Или введите username группы (@choovakee)")
    print("\nВведите username группы (с @ или без):")

    username = input().strip()

    if not username:
        print("❌ Username не введен")
        return

    # Remove @ if present
    if username.startswith('@'):
        username = username[1:]

    try:
        print(f"\n🔍 Ищу группу @{username}...")
        chat = await bot.get_chat(f"@{username}")

        print("\n" + "="*60)
        print("✅ ГРУППА НАЙДЕНА!")
        print("="*60)
        print(f"\nНазвание: {chat.title}")
        print(f"Тип: {chat.type}")
        print(f"Username: @{chat.username if chat.username else 'нет'}")
        print(f"\n🎯 ПРАВИЛЬНЫЙ ID: {chat.id}")
        print("\n" + "="*60)
        print("\nДОБАВЬТЕ ЭТО ЗНАЧЕНИЕ В VERCEL:")
        print(f"PROJECT_TELEGRAM_GROUP_ID={chat.id}")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\nПопробуйте другой способ:")
        print("1. Добавьте @userinfobot в группу")
        print("2. Он покажет ID группы")

if __name__ == "__main__":
    asyncio.run(get_group_info())
