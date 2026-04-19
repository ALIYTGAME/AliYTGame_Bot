import asyncio
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ChatType

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8149119273
CHANNEL_ID = -100XXXXXXXXXX  # ⚠️ ВСТАВЬ ID КАНАЛА (НЕ @username!)

if not TOKEN:
    raise ValueError("BOT_TOKEN не найден")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Быстрый set вместо list
BAD_WORDS = {"пиар", "подпишись", "канал", "взаимка", "t.me", "http", "сука", "блять", "хуй", "лох"}


# 🔥 СТАРТ
@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Бот работает!")


# 🔥 ФИЛЬТР
@dp.message()
async def filter_messages(message: types.Message):
    # ❌ игнор всего кроме канала/группы
    if message.chat.type == ChatType.PRIVATE:
        return

    if not message.text:
        return

    text = message.text.lower()

    # 🔍 проверка мата
    if any(word in text for word in BAD_WORDS):
        user = message.from_user

        if user.id == ADMIN_ID:
            return

        try:
            await message.delete()

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚫 Бан", callback_data=f"ban_{user.id}")],
                [InlineKeyboardButton(text="⏳ Мут 1д", callback_data=f"mute_{user.id}")]
            ])

            await bot.send_message(
                ADMIN_ID,
                f"🚨 Нарушение:\n{user.full_name}\n@{user.username}\n\n{message.text}",
                reply_markup=kb
            )

        except:
            pass


# 🔥 КНОПКИ
@dp.callback_query()
async def actions(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return

    data = callback.data.split("_")
    action = data[0]
    user_id = int(data[1])

    try:
        if action == "ban":
            await bot.ban_chat_member(CHANNEL_ID, user_id)
            text = "🚫 Забанен"

        elif action == "mute":
            await bot.restrict_chat_member(
                CHANNEL_ID,
                user_id,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(days=1)
            )
            text = "⏳ Мут 1 день"

        await callback.message.edit_text(text)

    except Exception as e:
        await callback.answer(str(e))


# 🔥 ЗАПУСК (оптимизирован polling)
async def main():
    await dp.start_polling(bot, polling_timeout=60)


if __name__ == "__main__":
    asyncio.run(main())