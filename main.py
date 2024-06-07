import json
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
    else:
        endpoint_id = action
        data = get_elma_data(endpoint_key, current_page, responsible_id)
        if data and data.get('success') and isinstance(data['result'].get('result'), list):
            for item in data['result'].get('result'):
                if item.get('__id') == endpoint_id:
                    await query.message.reply_text(
                        text=f"ID: {endpoint_id}\nName: {item.get('__name', 'No Name')}",
                        reply_markup=InlineKeyboardMarkup(
                            [[InlineKeyboardButton("Ответить на письмо", callback_data=f"reply_{endpoint_id}")]]
                        )
                    )
                    return

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
        await query.message.reply_text('Выберите элемент:', reply_markup=reply_markup)
    else:
        await query.message.reply_text('Что-то пошло не так. Пожалуйста, попробуйте позже.')

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

def save_ids_to_json(telegram_id, elma_id, phone_number):
    data = {
        'telegram_id': telegram_id,
        'elma_id': elma_id,
        'phone_number': phone_number
    }
    try:
        with open('user_data.json', 'r+') as file:
            try:
                json_data = json.load(file)
            except json.JSONDecodeError:
                json_data = []
            if not isinstance(json_data, list):
                json_data = []
            json_data.append(data)
            file.seek(0)
            json.dump(json_data, file, indent=4)
    except IOError as e:
        print(f"Error writing to JSON file: {e}")

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

def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    zadachi_handler = CommandHandler('zadachi', get_zadachi)
    application.add_handler(zadachi_handler)

    button_handler = CallbackQueryHandler(button)
    application.add_handler(button_handler)

    phone_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_number)
    application.add_handler(phone_handler)

    try:
        application.run_polling()
    except Exception as e:
        print(f"An error occurred: {e}")
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        error_message = "Упс! Что-то пошло не так. Мы уже работаем над этим. Пожалуйста, попробуйте позже."
        users_to_notify = [330039596]
        for user_id in users_to_notify:
            bot.send_message(chat_id=user_id, text=error_message)

if __name__ == '__main__':
    main()
