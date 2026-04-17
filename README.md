import asyncio
import urllib.parse
import json
import os
from datetime import datetime, timedelta
import aiohttp

from aiogram import Bot, Dispatcher, types, F, enums
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ---------------- НАСТРОЙКИ ----------------

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения")

ADMIN_ID = 8149119273
CHANNEL_ID = "@AliYTGame005"
LOG_FILE = "bans_history.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

BAD_WORDS = [
    "пиар", "подпишись", "канал", "взаимка",
    "t.me/", "http", "сука", "блять", "хуй", "лох"
]

# ---------------- FSM ----------------

class BotMemory(StatesGroup):
    waiting_for_image_prompt = State()

# ---------------- КОМАНДЫ ----------------

async def set_bot_commands(bot: Bot):
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота 🚀"),
            BotCommand(command="image", description="Нарисовать арт 🎨")
        ],
        scope=BotCommandScopeDefault()
    )

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Статус бота 🆗"),
            BotCommand(command="image", description="Арт 🎨"),
            BotCommand(command="banlist", description="Логи 📋"),
            BotCommand(command="unban", description="Разбан 🔓")
        ],
        scope=BotCommandScopeChat(chat_id=ADMIN_ID)
    )

    await bot.set_my_commands(
        [],
        scope=BotCommandScopeChat(chat_id=CHANNEL_ID)
    )

# ---------------- ЛОГИ ----------------

def save_log(user_id, name, username, action):
    data = []

    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            data = []

    data.append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "user_id": user_id,
        "name": name,
        "username": username,
        "action": action
    })

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ---------------- START ----------------

@dp.message(CommandStart())
async def start(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👑 Привет, Али! Бот запущен и работает стабильно ⚡")
    else:
        await message.answer("👋 Привет! Я бот AliYTGame 🤖\nНапиши /image чтобы создать арт 🎨")

# ---------------- IMAGE ----------------

@dp.message(Command("image"))
async def image_cmd(message: types.Message, state: FSMContext):
    await message.answer("🎨 Напиши, что нарисовать:")
    await state.set_state(BotMemory.waiting_for_image_prompt)

@dp.message(BotMemory.waiting_for_image_prompt)
async def image_gen(message: types.Message, state: FSMContext):
    prompt = urllib.parse.quote(message.text)

    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024"

    await message.answer_photo(photo=url, caption="🖼 Готово!")
    await state.clear()

# ---------------- BAN LIST ----------------

@dp.message(Command("banlist"))
async def banlist(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    if not os.path.exists(LOG_FILE):
        return await message.answer("📭 Пусто")

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = json.load(f)[-20:]

    text = "📋 Последние действия:\n\n"
    for b in logs:
        text += f"{b['date']} | {b['action']} | {b['name']}\n"

    await message.answer(text)

# ---------------- UNBAN ----------------

@dp.message(Command("unban"))
async def unban(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Укажи ID")

    user_id = args[1]

    try:
        await bot.unban_chat_member(CHANNEL_ID, int(user_id))
        await message.answer("✅ Разбан выполнен!")
    except:
        await message.answer("❌ Ошибка разбанa")

# ---------------- ФИЛЬТР ЧАТА ----------------

@dp.message()
async def filter_messages(message: types.Message):
    if not message.text:
        return

    is_admin = message.from_user.id == ADMIN_ID

    text_lower = message.text.lower()

    if any(word in text_lower for word in BAD_WORDS):
        await message.delete()

        if not is_admin:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🚫 БАН",
                    callback_data=f"ban_{message.from_user.id}_{message.from_user.first_name}"
                )],
                [InlineKeyboardButton(
                    text="⏳ МУТ",
                    callback_data=f"mute_{message.from_user.id}_{message.from_user.first_name}"
                )]
            ])

            await bot.send_message(
                ADMIN_ID,
                f"🚨 Нарушение от @{message.from_user.username or 'no_username'}\n\n{message.text}",
                reply_markup=kb
            )
        return

    # AI ответ в ЛС админа
    if message.chat.type == enums.ChatType.PRIVATE and is_admin:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"https://text.pollinations.ai/{urllib.parse.quote(message.text)}") as r:
                await message.answer(await r.text())

# ---------------- CALLBACK ----------------

@dp.callback_query(F.data.startswith("ban_") | F.data.startswith("mute_"))
async def callback(callback: types.CallbackQuery):
    try:
        action, uid, name = callback.data.split("_", 2)
        uid = int(uid)

        if action == "ban":
            await bot.ban_chat_member(CHANNEL_ID, uid)
            label = "🚫 БАН"

        else:
            await bot.restrict_chat_member(
                CHANNEL_ID,
                uid,
                permissions=types.ChatPermissions(can_send_messages=False),
                until_date=datetime.now() + timedelta(days=3)
            )
            label = "⏳ МУТ"

        save_log(uid, name, "none", label)

        await bot.send_message(CHANNEL_ID, f"{label} для {name}")
        await callback.message.edit_text(f"✅ Готово: {label}")

    except Exception:
        await callback.answer("Ошибка ⚠️")

# ---------------- MAIN ----------------

async def main():
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
