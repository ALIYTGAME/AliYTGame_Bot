import asyncio  
import urllib.parse  
import json  
import os  
from datetime import datetime, timedelta  
import aiohttp  
  
from aiogram import Bot, Dispatcher, types, F, enums, BaseMiddleware
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
ADMIN_ID = 8149119273  
CHANNEL_ID = "@AliYTGame005" 

if not TOKEN:  
    raise ValueError("❌ BOT_TOKEN не найден!")  

LOG_FILE = "bans_history.json"  
bot = Bot(token=TOKEN)  
dp = Dispatcher()  

BAD_WORDS = ["сука", "блять", "хуй", "лох", "гад", "тупой", "дебил", "пиар", "взаимка"]  

# --- ЗАЩИТА (ТОЛЬКО ДЛЯ ТЕБЯ В ЛС) ---

class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        
        # Если пишут в личку
        if isinstance(event, types.Message) and event.chat.type == enums.ChatType.PRIVATE:
            if user and user.id == ADMIN_ID:
                return await handler(event, data)
            return  # Просто игнорируем чужих, чтобы бот им даже не отвечал

        return await handler(event, data)

dp.message.middleware(AccessMiddleware())

# ---------------- ЛОГИКА ----------------  

class BotMemory(StatesGroup):  
    waiting_for_image_prompt = State()  

@dp.message(CommandStart())  
async def start(message: types.Message):
    # Отвечает только тебе в ЛС
    await message.answer("👑 Привет, Али! Я работаю в скрытом режиме. Слежу за каналом молча.")  

@dp.message(Command("image"))  
async def image_cmd(message: types.Message, state: FSMContext):  
    await message.answer("🎨 Что нарисовать?")  
    await state.set_state(BotMemory.waiting_for_image_prompt)  

@dp.message(BotMemory.waiting_for_image_prompt)  
async def image_gen(message: types.Message, state: FSMContext):  
    prompt = urllib.parse.quote(message.text)  
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024"  
    await message.answer_photo(photo=url, caption="🖼 Готово!")  
    await state.clear()  

# --- ТИХИЙ МОНИТОРИНГ И ИИ ---

@dp.message()  
async def monitor_and_ai(message: types.Message):  
    if not message.text: return  
    
    user = message.from_user
    text_lower = message.text.lower()

    # 1. Если это группа/канал — только удаляем мат БЕЗ ответов в чат
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP, enums.ChatType.CHANNEL]:
        if any(word in text_lower for word in BAD_WORDS):
            if user.id != ADMIN_ID:
                try:
                    await message.delete() # Молча удаляем
                    
                    # Отчет только тебе в личку
                    kb = InlineKeyboardMarkup(inline_keyboard=[  
                        [InlineKeyboardButton(text="🚫 БАН", callback_data=f"ban_{user.id}_{user.first_name}")],
                        [InlineKeyboardButton(text="⏳ МУТ", callback_data=f"mute_{user.id}_{user.first_name}")]
                    ])  
                    await bot.send_message(
                        ADMIN_ID, 
                        f"🚨 Удалил мат в канале от {user.full_name}\nТекст: {message.text}", 
                        reply_markup=kb
                    )
                except: pass
        return # Больше ничего в каналах не делаем

    # 2. Если это личка с тобой — работает ИИ
    if message.chat.type == enums.ChatType.PRIVATE and user.id == ADMIN_ID:
        async with aiohttp.ClientSession() as s:  
            async with s.get(f"https://text.pollinations.ai/{urllib.parse.quote(message.text)}") as r:  
                await message.answer(await r.text())  

# --- ТИХИЕ ДЕЙСТВИЯ АДМИНА ---

@dp.callback_query(F.data.startswith("ban_") | F.data.startswith("mute_"))  
async def admin_action(callback: types.CallbackQuery):  
    action, uid, name = callback.data.split("_", 2)  
    uid = int(uid)  

    try:  
        if action == "ban":  
            await bot.ban_chat_member(CHANNEL_ID, uid)
            res = "Забанен 🚫"
        else:  
            await bot.restrict_chat_member(  
                CHANNEL_ID, uid,  
                permissions=types.ChatPermissions(can_send_messages=False),  
                until_date=datetime.now() + timedelta(days=1)  
            )  
            res = "Мут ⏳"  

        # Редактируем сообщение у ТЕБЯ в личке, а не в канале
        await callback.message.edit_text(f"✅ Готово: {name} получил {res}")  
    except:  
        await callback.answer("Ошибка доступа ⚠️")  

async def main():  
    # Команды будут видны только тебе в меню
    await bot.set_my_commands(
        [BotCommand(command="start", description="Статус"), BotCommand(command="image", description="Арт")],
        scope=BotCommandScopeChat(chat_id=ADMIN_ID)
    )
    await dp.start_polling(bot)  

if __name__ == "__main__":  
    asyncio.run(main())
