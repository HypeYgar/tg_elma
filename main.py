import asyncio
import logging
import json
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from math import ceil

PAGE_SIZE = 10
logging.basicConfig(level=logging.INFO)
bot = Bot(token="6819907271:AAGmbKe8oTAyU77XKrG9dxIu24sGlwAjVgU")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
buttons_data = {}
def load_buttons():
    global buttons_data
    try:
        with open('buttons_data.json', 'r') as f:
            buttons_data = json.load(f)
    except FileNotFoundError:
        buttons_data = {}
    return buttons_data

def save_buttons():
    with open('buttons_data.json', 'w') as f:
        json.dump(buttons_data, f, indent=4)
class ButtonStates(StatesGroup):
    name = State()
    response_keys = State()
    url = State()
    token = State()
    output_option = State()
    edit_key = State()
    edit_value = State()
    select_button = State()

# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("нажмите на /create_button для создания команд.")

# Хэндлер на команду /create_button
@dp.message(Command("create_button"))
async def cmd_create_button(message: types.Message, state: FSMContext):
    await message.answer("Введите имя команды:")
    await state.set_state(ButtonStates.name)

@dp.message(ButtonStates.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите response keys:")
    await state.set_state(ButtonStates.response_keys)

@dp.message(ButtonStates.response_keys)
async def process_response_keys(message: types.Message, state: FSMContext):
    await state.update_data(response_keys=message.text)
    await message.answer("Введите URL:")
    await state.set_state(ButtonStates.url)

@dp.message(ButtonStates.url)
async def process_url(message: types.Message, state: FSMContext):
    await state.update_data(url=message.text)
    await message.answer("Введите token:")
    await state.set_state(ButtonStates.token)

@dp.message(ButtonStates.token)
async def process_token(message: types.Message, state: FSMContext):
    await state.update_data(token=message.text)
    await message.answer("Введите output option:")
    await state.set_state(ButtonStates.output_option)

@dp.message(ButtonStates.output_option)
async def process_output_option(message: types.Message, state: FSMContext):
    data = await state.get_data()
    data['output_option'] = message.text
    chat_id = str(message.chat.id)
    if chat_id not in buttons_data:
        buttons_data[chat_id] = []
    buttons_data[chat_id].append(data)
    save_buttons()
    await message.answer("Команда создана!")
    await state.clear()

# Хэндлер на команду /edit_button
@dp.message(Command("edit_button"))
async def cmd_edit_button(message: types.Message, state: FSMContext):
    chat_id = str(message.chat.id)
    if chat_id not in buttons_data or not buttons_data[chat_id]:
        await message.answer("Нет команд для изменений.")
        return
    buttons_list = [types.InlineKeyboardButton(text=btn['name'], callback_data=f"edit_btn_{i}")
                    for i, btn in enumerate(buttons_data[chat_id])]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[button] for button in buttons_list])
    await message.answer("Выберите что хотите изменить:", reply_markup=keyboard)
    await state.set_state(ButtonStates.select_button)

@dp.callback_query(lambda c: c.data and c.data.startswith('edit_btn_'))
async def select_button_to_edit(callback_query: types.CallbackQuery, state: FSMContext):
    button_index = int(callback_query.data.split('_')[2])
    chat_id = str(callback_query.message.chat.id)
    await state.update_data(edit_index=button_index)
    parameters = ["названия", "response_keys", "url", "token", "output_option"]
    param_buttons = [types.InlineKeyboardButton(text=param, callback_data=f"edit_param_{param}") for param in parameters]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[button] for button in param_buttons])
    await bot.send_message(chat_id, "Что вы хотите изменить?", reply_markup=keyboard)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith('edit_param_'))
async def process_edit_param(callback_query: types.CallbackQuery, state: FSMContext):
    param_to_edit = callback_query.data.split('_')[2]
    await state.update_data(edit_key=param_to_edit)
    await bot.send_message(callback_query.message.chat.id, f"Введите новое значение для {param_to_edit}:")
    await state.set_state(ButtonStates.edit_value)
    await callback_query.answer()

@dp.message(ButtonStates.edit_value)
async def process_edit_value(message: types.Message, state: FSMContext):
    data = await state.get_data()
    chat_id = str(message.chat.id)
    edit_index = data['edit_index']
    edit_key = data['edit_key']
    new_value = message.text
    buttons_data[chat_id][edit_index][edit_key] = new_value
    save_buttons()
    updated_button = buttons_data[chat_id][edit_index]
    updated_values_message = (
        f"Имя: {updated_button['name']}\n"
        f"Response Keys: {updated_button['response_keys']}\n"
        f"URL: {updated_button['url']}\n"
        f"Token: {updated_button['token']}\n"
        f"Output Option: {updated_button['output_option']}"
    )
    await message.answer("Команда обновлена!\n" + updated_values_message)
    await state.clear()

# Хэндлер на команду /show_buttons
@dp.message(Command("show_buttons"))
async def cmd_show_buttons(message: types.Message):
    chat_id = str(message.chat.id)
    if chat_id not in buttons_data or not buttons_data[chat_id]:
        await message.answer("Нет доступных команд.")
        return
    buttons_list = [types.InlineKeyboardButton(text=btn['name'], callback_data=f"btn_{i}")
                    for i, btn in enumerate(buttons_data[chat_id])]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[button] for button in buttons_list])
    await message.answer("Команды:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data and (c.data.startswith('btn_') or c.data.startswith('page_')))
async def process_button_callback(callback_query: types.CallbackQuery):
    data_parts = callback_query.data.split('_')
    if data_parts[0] == 'btn':
        button_index = int(data_parts[1])
        page = 0
    else:  # 'page'
        button_index = int(data_parts[1])
        page = int(data_parts[2])

    chat_id = str(callback_query.message.chat.id)
    button_data = buttons_data[chat_id][button_index]
    url = button_data['url']
    token = button_data['token']
    response_keys = button_data.get('response_keys', "").split(',')
    output_option = button_data.get('output_option', 'first')

    payload = {'active': True, 'from': page * PAGE_SIZE, 'size': PAGE_SIZE}
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        result = data.get('result', {}).get('result', [])
        total_results = data.get('result', {}).get('total', len(result))
        total_pages = ceil(total_results / PAGE_SIZE)

        if not result:
            await bot.send_message(callback_query.message.chat.id, "No results found.")
            return
        buttons = []
        for res in result:
            filtered_response = {key: res.get(key, 'N/A') for key in response_keys}
            buttons.extend([types.InlineKeyboardButton(text=f"{key}: {value}", callback_data="noop") for key, value in
                            filtered_response.items()])
        navigation_buttons = []
        if page > 0:
            navigation_buttons.append(
                types.InlineKeyboardButton(text="⬅️", callback_data=f"page_{button_index}_{page - 1}"))
        if page < total_pages - 1:
            navigation_buttons.append(
                types.InlineKeyboardButton(text="➡️", callback_data=f"page_{button_index}_{page + 1}"))
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[buttons[i:i + 2] for i in range(0, len(buttons), 2)] + [navigation_buttons])
        await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id,
                                            message_id=callback_query.message.message_id, reply_markup=keyboard)
    except requests.exceptions.RequestException as e:
        await bot.send_message(callback_query.message.chat.id, f"Error: {e}")

@dp.callback_query(lambda c: c.data == "noop")
async def noop_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()


# Запуск процесса поллинга новых апдейтов
async def main():
    load_buttons()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
