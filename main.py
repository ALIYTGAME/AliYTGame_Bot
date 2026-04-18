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
ADMIN_ID = 8149119273  # Твой ID
CHANNEL_ID = "@AliYTGame005"  # Твой канал
LOG_FILE = "bans_history.json"  

if not TOKEN:  
    raise ValueError("❌ BOT_TOKEN не найден!")  

bot = Bot(token=TOKEN)  
dp = Dispatcher()  

BAD_WORDS = ["пиар", "подпишись", "канал", "взаимка", "t.me/", "http", "сука", "блять", "хуй", "лох"]  

# --- ЗАЩИТА (ТОЛЬКО ДЛЯ АЛИ) ---

class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        # Если пишут в личку и это не ты — игнорим полностью
        if isinstance(event, types.Message) and event.chat.type == enums.ChatType.PRIVATE:
            if user and user.id == ADMIN_ID:
                return await handler(event, data)
            return 
        return await handler(event, data)

dp.message.middleware(AccessMiddleware())

# ---------------- FSM ----------------  

class BotMemory(StatesGroup):  
    waiting_for_image_prompt = State()  

# ---------------- ЛОГИ ----------------  

def save_log(user_id, name, action):  
    data = []  
    if os.path.exists(LOG_FILE):  
        try:  
            with open(LOG_FILE, "r", encoding="utf-8") as f:  
                data = json.load(f)  
        except: data = []  
    data.append({  
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),  
        "user_id": user_id,  
        "name": name,  
        "action": action  
    })  
    with open(LOG_FILE, "w", encoding="utf-8") as f:  
        json.dump(data, f, ensure_ascii=False, indent=4)  

# ---------------- КОМАНДЫ ----------------  

@dp.message(CommandStart())  
async def start(message: types.Message):  
    await message.answer("👑 Привет, Али! Команды banlist и unban доступны. Бот следит за каналом.")  

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

@dp.message(Command("banlist"))  
async def banlist(message: types.Message):  
    if not os.path.exists(LOG_FILE):  
        return await message.answer("📭 Пусто")  
    with open(LOG_FILE, "r", encoding="utf-8") as f:  
        logs = json.load(f)[-20:]  
    text = "📋 Последние действия:\n\n"  
    for b in logs:  
        text += f"{b['date']} | {b['action']} | {b['name']}\n"  
    await message.answer(text)  

@dp.message(Command("unban"))  
async def unban(message: types.Message):  
    args = message.text.split()  
    if len(args) < 2: return await message.answer("Укажи ID")  
    try:  
        await bot.unban_chat_member(CHANNEL_ID, int(args[1]))  
        await message.answer(f"✅ Пользователь {args[1]} разбанен!")  
    except: await message.answer("❌ Ошибка разбана")  

# ---------------- ФИЛЬТР И МОНИТОРИНГ ----------------  

@dp.message()  
async def filter_messages(message: types.Message):  
    if not message.text: return  
    
    user = message.from_user
    text_lower = message.text.lower()

    # 1. Проверка мата в канале/группе
    if any(word in text_lower for word in BAD_WORDS):
        if user.id != ADMIN_ID:
            try:
                await message.delete() # Удаляем молча
                
                # Отправляем тебе выбор действий
                kb = InlineKeyboardMarkup(inline_keyboard=[  
                    [InlineKeyboardButton(text="✅ Простить", callback_data=f"act_forgive_{user.id}_{user.first_name}")],
                    [InlineKeyboardButton(text="⚠️ Предупреждение", callback_data=f"act_warn_{user.id}_{user.first_name}")],
                    [InlineKeyboardButton(text="⏳ Мут (3 дня)", callback_data=f"act_mute_{user.id}_{user.first_name}")],
                    [InlineKeyboardButton(text="🚫 Бан навсегда", callback_data=f"act_ban_{user.id}_{user.first_name}")]
                ])  
                
                await bot.send_message(  
                    ADMIN_ID,  
                    f"🚨 Нарушение в канале!\nОт: {user.full_name} (@{user.username})\nТекст: {message.text}\n\nЧто делаем?",  
                    reply_markup=kb  
                )
                return 
            except: pass

    # 2. ИИ ответ тебе в личку
    if message.chat.type == enums.ChatType.PRIVATE:  
        async with aiohttp.ClientSession() as s:  
            async with s.get(f"https://text.pollinations.ai/{urllib.parse.quote(message.text)}") as r:  
                await message.answer(await r.text())  

# ---------------- ОБРАБОТКА ТВОИХ РЕШЕНИЙ ----------------  

@dp.callback_query(F.data.startswith("act_"))  
async def process_admin_action(callback: types.CallbackQuery):  
    # Формат: act_действие_id_имя
    _, action, uid, name = callback.data.split("_", 3)  
    uid = int(uid)  

    try:  
        if action == "forgive":
            res_text = "Прощен ✅"
        
        elif action == "warn":
            res_text = "Выдано предупреждение ⚠️"
            # Можно добавить логику счетчика варнов, если нужно
        
        elif action == "mute":
            await bot.restrict_chat_member(  
                CHANNEL_ID, uid,  
                permissions=types.ChatPermissions(can_send_messages=False),  
                until_date=datetime.now() + timedelta(days=3)  
            )  
            res_text = "Мут на 3 дня ⏳"
        
        elif action == "ban":  
            await bot.ban_chat_member(CHANNEL_ID, uid)  
            res_text = "Забанен навсегда 🚫"  

        save_log(uid, name, res_text)  
        await callback.message.edit_text(f"✅ Решение принято: {name} -> {res_text}")  
        
    except Exception as e:  
        await callback.answer(f"Ошибка: {e}")  

# ---------------- MAIN ----------------  

async def main():  
    # Установка команд в меню только для тебя
    await bot.set_my_commands(  
        [  
            BotCommand(command="start", description="Статус бота 🆗"),  
            BotCommand(command="image", description="Арт 🎨"),  
            BotCommand(command="banlist", description="Логи 📋"),  
            BotCommand(command="unban", description="Разбан 🔓")  
        ],  
        scope=BotCommandScopeChat(chat_id=ADMIN_ID)  
    )  
    await dp.start_polling(bot)  

if __name__ == "__main__":  
    asyncio.run(main())
