import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Router
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Определение настроек с использованием pydantic BaseSettings
class Settings(BaseSettings):
    elma_initial_token: str
    elma_initial_url: str
    elma_command_url: str

    class Config:
        env_file = ".env"
# Инициализация настроек
settings = Settings()

# Функция для получения данных из ELMA API
async def fetch_data(api_url, elma_token):
    headers = {
        "Authorization": f"Bearer {elma_token}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(api_url, json={"active": True}, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("result", {}).get("result", [])
            else:
                logging.error(f"Failed to fetch data: {response.status} - {await response.text()}")
                return None

# Функция для запуска Telegram бота
async def start_bot(telegram_token):
    bot = Bot(token=telegram_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    router = Router()

    @router.message(F.text == '/start')
    async def send_welcome(message: types.Message):
        # Получение последних команд из ELMA API
        commands_data = await fetch_data(settings.elma_command_url, settings.elma_initial_token)
        if commands_data:
            commands = [item.get("__name") for item in commands_data if "__name" in item]
        else:
            commands = []

        # Создание динамической клавиатуры с последними командами
        keyboard_buttons = [
            [types.InlineKeyboardButton(text=command, callback_data=command)]
            for command in commands
        ]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        await message.reply("хайп!", reply_markup=keyboard)

    dp.include_router(router)
    await dp.start_polling(bot)

async def init_microservice():
    initial_token = settings.elma_initial_token
    initial_url = settings.elma_initial_url
    command_url = settings.elma_command_url
    print(initial_url)
    # Получение начальных данных
    data = await fetch_data(initial_url, initial_token)
    if data:
        first_result = data[0] if data else {}
        telegram_token = first_result.get("telegram_token")
        elma_token = first_result.get("elma_token")

        if telegram_token:
            # Запуск бота с начальными командами
            await start_bot(telegram_token)
        else:
            logging.error("Telegram token not found.")
    else:
        logging.error("Failed to fetch initial data.")

if __name__ == "__main__":
    asyncio.run(init_microservice())
