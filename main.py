import asyncio  
import urllib.parse  
import json  
import os  
from datetime import datetime, timedelta  
import aiohttp  

from aiogram import Bot, Dispatcher, types  
from aiogram.filters import CommandStart, Command  
from aiogram.types import BotCommand  
from aiogram.fsm.context import FSMContext  
from aiogram.fsm.state import State, StatesGroup  

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:  
    raise ValueError("❌ BOT_TOKEN не найден")

bot = Bot(token=TOKEN)
dp = Dispatcher()

class BotMemory(StatesGroup):
    waiting_for_image_prompt = State()

async def set_bot_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск 🚀"),
        BotCommand(command="image", description="Картинка 🎨")
    ])

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer("🎮 AliYTGame бот работает 🚀")

@dp.message(Command("image"))
async def image_cmd(message: types.Message, state: FSMContext):
    await message.answer("🎨 Напиши что нарисовать:")
    await state.set_state(BotMemory.waiting_for_image_prompt)

@dp.message(BotMemory.waiting_for_image_prompt)
async def image_gen(message: types.Message, state: FSMContext):
    prompt = urllib.parse.quote(message.text)

    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024"

    await message.answer_photo(photo=url, caption="🖼 Готово!")
    await state.clear()

async def main():
    await set_bot_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())