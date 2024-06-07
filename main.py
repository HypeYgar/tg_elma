import json
from datetime import datetime
import requests
from telegram.ext import MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, Bot, KeyboardButton, \
  ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, ApplicationBuilder, ContextTypes
import re
TELEGRAM_BOT_TOKEN = '6819907271:AAGmbKe8oTAyU77XKrG9dxIu24sGlwAjVgU'
ELMA365_API_URL = 'https://fittest.bimup.dev/pub/v1/app/general_mail/EMailOutgoing/list'
TOKEN = '309cf20e-9dd3-4262-911c-3f795dde24f3'
current_page = 1
page_size = 10

URLS = {
    'emails': 'https://fittest.bimup.dev/pub/v1/app/general_mail/EMailOutgoing/list',
    'zadachi': 'https://fittest.bimup.dev/pub/v1/app/employee_task/incoming_tasks/list',
    'users': 'https://fittest.bimup.dev/pub/v1/user/list'
}
PAYLOADS = {
    'emails': {'active': True, 'from': 0, 'size': page_size},
    'zadachi': {'active': True, 'fields': {'*': True}, 'from': 0, 'size': 100}
}
def get_elma_data(endpoint_key, page=1, responsible_id=None):
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = PAYLOADS[endpoint_key].copy()
    payload['from'] = (page - 1) * page_size
    if endpoint_key == 'zadachi' and responsible_id:
        payload['filter'] = {'responsible': [responsible_id]}
    try:
        response = requests.post(URLS[endpoint_key], headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return None
def get_user_name(user_id):
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {'from': 0, 'ids': [user_id]}
    try:
        response = requests.post(URLS['users'], headers=headers, json=payload)
        print(response.json())
        response.raise_for_status()
        user_data = response.json()
        if user_data and user_data.get('success') and isinstance(user_data['result'].get('result'), list):
            return user_data['result']['result'][0].get('__name', 'No Name')
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return 'No Name'
def format_date(date_str):
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return date_str
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await check_and_request_phone(update, context):
        keyboard = [[KeyboardButton("/zadachi")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text('Выберите команду:', reply_markup=reply_markup)
async def check_and_request_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_phone = get_user_phone(update.message.from_user.id)
    if not user_phone:
        await update.message.reply_text('Пожалуйста, введите ваш номер телефона:')
        context.user_data['awaiting_phone_number'] = True
        return False
    context.user_data['user_phone'] = user_phone
    return True
async def get_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_and_request_phone(update, context):
        return
    endpoint_key = context.user_data['endpoint_key']
    telegram_id = update.message.from_user.id
    elma_id = get_elma_id_from_json(telegram_id)
    if not elma_id:
        await update.message.reply_text('Для вашего пользователя не найден elma_id. Пожалуйста, уточните данные.')
        return
    wait_message = await update.message.reply_text('Подождите, идет запрос...')
    data = get_elma_data(endpoint_key, current_page)
    await context.bot.delete_message(chat_id=update.message.chat_id, message_id=wait_message.message_id)
    if data and data.get('success') and isinstance(data['result'].get('result'), list):
        buttons = [
            [InlineKeyboardButton(f"{item.get('__name', 'No Name')} ({item.get('date_end', 'No Date')})",
                                  callback_data=f"{endpoint_key}_{item.get('__id')}")]
            for item in data['result'].get('result') if 'responsible' in item and elma_id in item['responsible']
        ]
        buttons.append([
            InlineKeyboardButton("⬅️", callback_data=f"{endpoint_key}_prev_page"),
            InlineKeyboardButton("➡️", callback_data=f"{endpoint_key}_next_page")
        ])
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text('Выберите элемент:', reply_markup=reply_markup)
    else:
        await update.message.reply_text('Что-то пошло не так. Пожалуйста, попробуйте позже.')
def get_elma_id_from_json(telegram_id):
    try:
        with open('user_data.json', 'r') as file:
            json_data = json.load(file)
            if isinstance(json_data, list):
                for user in json_data:
                    if user['telegram_id'] == telegram_id:
                        return user['elma_id']
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error reading JSON file: {e}")
    return None
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    global current_page
    data = query.data.split('_')
    endpoint_key, action = data[0], data[1]
    responsible_id = context.user_data.get('elma_id')
    if action in ["next_page", "prev_page"]:
        current_page += 1 if action == "next_page" else -1 if action == "prev_page" and current_page > 1 else 0
        await update_pagination_message(query, context, endpoint_key, responsible_id)
    elif action == "back":
        await query.message.delete()
        await update_pagination_message(query, context, endpoint_key, responsible_id)
    else:
        await update_task_message(query, context, endpoint_key, action, responsible_id)
async def update_pagination_message(query, context, endpoint_key, responsible_id):
    data = get_elma_data(endpoint_key, current_page, responsible_id)
    if data and data.get('success') and isinstance(data['result'].get('result'), list):
        buttons = [
            [InlineKeyboardButton(f"{item.get('__name', 'No Name')}", callback_data=f"{endpoint_key}_{item.get('__id')}")]
            for item in data['result'].get('result')
        ]
        buttons.append([
            InlineKeyboardButton("⬅️", callback_data=f"{endpoint_key}_prev_page"),
            InlineKeyboardButton("➡️", callback_data=f"{endpoint_key}_next_page")
        ])
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text('Выберите элемент:', reply_markup=reply_markup)
    else:
        await query.message.edit_text('Что-то пошло не так. Пожалуйста, попробуйте позже.')
async def update_task_message(query, context, endpoint_key, endpoint_id, responsible_id):
    data = get_elma_data(endpoint_key, current_page, responsible_id)
    if data and data.get('success') and isinstance(data['result'].get('result'), list):
        for item in data['result'].get('result'):
            if item.get('__id') == endpoint_id:
                task_name = item.get('__name', 'No Name')
                priority_info = item.get('priority')
                if priority_info:
                    priority = priority_info[0].get('name', 'Приоритет отсутствует')
                else:
                    priority = 'No Priority'
                date_start = format_date(item.get('date_start', 'No Start Date'))
                date_end = format_date(item.get('date_end', 'No End Date'))
                responsible_ids = item.get('responsible', [])
                responsible_names = [get_user_name(responsible_id) for responsible_id in responsible_ids]
                responsible_names_str = ', '.join(responsible_names)
                executor_ids = item.get('executor', [])
                executor_names = [get_user_name(executor_id) for executor_id in executor_ids]
                executor_names_str = ', '.join(executor_names)
                task_details = (
                    f"ID: {endpoint_id}\n"
                    f"Название Задачи: {task_name}\n"
                    f"Испольнитель задачи: {executor_names_str}\n"
                    f"Приоритет задачи: {priority}\n"
                    f"Начало задачи: {date_start}\n"
                    f"Окончание задачи: {date_end}\n"
                    f"Ответсвенный задачи: {responsible_names_str}"
                )
                await query.message.reply_text(
                    text=task_details,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [InlineKeyboardButton("Задача выполнена", callback_data=f"complete_{endpoint_id}")],
                            [InlineKeyboardButton("Назад", callback_data=f"{endpoint_key}_back")]
                        ]
                    )
                )
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
                return
async def get_zadachi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['endpoint_key'] = 'zadachi'
    await get_data(update, context)
async def handle_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('awaiting_phone_number'):
        user_phone = update.message.text.strip()
        context.user_data['awaiting_phone_number'] = False
        if re.match(r'^8\d{10}$', user_phone):
            user_phone = f"+7{user_phone[1:]}"
        wait_message = await update.message.reply_text('Подождите, идет запрос...')
        data = get_elma_data('users', 1)
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=wait_message.message_id)
        if data and data.get('success') and isinstance(data['result'].get('result'), list):
            for item in data['result']['result']:
                phone_numbers = [phone['tel'] for phone in item.get('mobilePhone', []) + item.get('workPhone', [])]
                if user_phone in phone_numbers:
                    elma_id = item['__id']
                    telegram_id = update.message.from_user.id
                    save_ids_to_json(telegram_id, elma_id, user_phone)
                    await update.message.reply_text(f"Найден ID пользователя: {elma_id}")
                    context.user_data['user_phone'] = user_phone
                    keyboard = [
                        [KeyboardButton("/emails"), KeyboardButton("/zadachi"), KeyboardButton("/employees")]
                    ]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    await update.message.reply_text('Выберите команду:', reply_markup=reply_markup)
                    return
        await update.message.reply_text('Пользователь с таким номером телефона не найден.')
def save_ids_to_json(telegram_id, elma_id, user_phone):
    try:
        with open('user_data.json', 'r') as file:
            json_data = json.load(file)
    except (IOError, json.JSONDecodeError):
        json_data = []
    for user in json_data:
        if user['telegram_id'] == telegram_id:
            user['elma_id'] = elma_id
            user['user_phone'] = user_phone
            break
    else:
        json_data.append({'telegram_id': telegram_id, 'elma_id': elma_id, 'user_phone': user_phone})
    with open('user_data.json', 'w') as file:
        json.dump(json_data, file, indent=4)
def get_user_phone(telegram_id):
    try:
        with open('user_data.json', 'r') as file:
            json_data = json.load(file)
            if isinstance(json_data, list):
                for user in json_data:
                    if user['telegram_id'] == telegram_id:
                        return user['phone_number']
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error reading JSON file: {e}")
    return None
def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("zadachi", get_zadachi))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_number))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()

if __name__ == '__main__':
    main()
