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
    'zadachi': 'https://fittest.bimup.dev/pub/v1/app/_system_catalogs/obekt/list',
    'employees': 'https://fittest.bimup.dev/pub/v1/app/human_resource/employee_search/list',
    'users': 'https://fittest.bimup.dev/pub/v1/user/list'
}

PAYLOADS = {
    'emails': {'active': True, 'from': 0, 'size': page_size},
    'zadachi': {'active': True, 'from': 0, 'size': page_size},
    'employees': {'active': True, 'from': 0, 'size': page_size},
    'users': {'from': 0, 'size': 100}
}


def get_elma_data(endpoint_key, page=1):
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = PAYLOADS[endpoint_key]
    payload['from'] = (page - 1) * page_size

    try:
        response = requests.post(URLS[endpoint_key], headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}")
        return None


async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [KeyboardButton("/emails"), KeyboardButton("/zadachi"), KeyboardButton("/employees")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text('Выберите команду:', reply_markup=reply_markup)


async def get_data(update: Update, context: CallbackContext) -> None:
    endpoint_key = context.user_data['endpoint_key']
    data = get_elma_data(endpoint_key, current_page)
    if data and data.get('success') and isinstance(data['result'].get('result'), list):
        buttons = []
        for item in data['result']['result']:
            text = item.get('text', 'No Text') if 'text' in item else item.get('name', 'No Name')
            email_info = item.get('email_from')
            email = email_info[0].get('email', 'No Email') if email_info else 'No Email'
            buttons.append(
                [InlineKeyboardButton(f"{text} ({email})", callback_data=f"{endpoint_key}_{item.get('__id')}")])

        buttons.append([
            InlineKeyboardButton("⬅️", callback_data=f"{endpoint_key}_prev_page"),
            InlineKeyboardButton("➡️", callback_data=f"{endpoint_key}_next_page")
        ])
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text('Выберите элемент:', reply_markup=reply_markup)
    else:
        await update.message.reply_text(
            f"Error retrieving data: {data.get('message', 'Unknown error')}" if data else 'API request failed.')


async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    global current_page

    data = query.data.split('_')
    endpoint_key, action = data[0], data[1]

    if action == "next_page":
        current_page += 1
    elif action == "prev_page":
        if current_page > 1:
            current_page -= 1
    else:
        endpoint_id = data[1]
        data = get_elma_data(endpoint_key, current_page)
        if data and data.get('success') and isinstance(data['result'].get('result'), list):
            for item in data['result'].get('result'):
                if item.get('__id') == endpoint_id:
                    text = item.get('text', 'No Text') if 'text' in item else item.get('name', 'No Name')
                    email_info = item.get('email_from')
                    email = email_info[0].get('email', 'No Email') if email_info else 'No Email'
                    await query.message.reply_text(
                        text=f"ID: {endpoint_id}\nText: {text}\nEmail: {email}",
                        reply_markup=InlineKeyboardMarkup(
                            [[InlineKeyboardButton("Ответить на письмо", callback_data=f"reply_{endpoint_id}")]])
                    )
                    return

    data = get_elma_data(endpoint_key, current_page)
    if data and data.get('success') and isinstance(data['result'].get('result'), list):
        buttons = []
        for item in data['result'].get('result'):
            text = item.get('text', 'No Text') if 'text' in item else item.get('name', 'No Name')
            email_info = item.get('email_from')
            email = email_info[0].get('email', 'No Email') if email_info else 'No Email'
            buttons.append(
                [InlineKeyboardButton(f"{text} ({email})", callback_data=f"{endpoint_key}_{item.get('__id')}")])

        buttons.append([
            InlineKeyboardButton("⬅️", callback_data=f"{endpoint_key}_prev_page"),
            InlineKeyboardButton("➡️", callback_data=f"{endpoint_key}_next_page")
        ])
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text('Выберите элемент:', reply_markup=reply_markup)
    else:
        await query.edit_message_text(
            f"Error retrieving data: {data.get('message', 'Unknown error')}" if data else 'API request failed.')


async def get_emails(update: Update, context: CallbackContext) -> None:
    context.user_data['endpoint_key'] = 'emails'
    await get_data(update, context)


async def get_zadachi(update: Update, context: CallbackContext) -> None:
    context.user_data['endpoint_key'] = 'zadachi'

    # Request the user's phone number
    await update.message.reply_text('Пожалуйста, введите ваш номер телефона:')
    context.user_data['awaiting_phone_number'] = True


async def get_employees(update: Update, context: CallbackContext) -> None:
    context.user_data['endpoint_key'] = 'employees'
    await get_data(update, context)


import re

async def handle_phone_number(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('awaiting_phone_number'):
        user_phone = update.message.text.strip()
        context.user_data['awaiting_phone_number'] = False

        if re.match(r'^8\d{10}$', user_phone):
            user_phone = f"+7{user_phone[1:]}"

        data = get_elma_data('users', 1)
        if data and data.get('success') and isinstance(data['result'].get('result'), list):
            for item in data['result']['result']:
                mobile_phones = item.get('mobilePhone') or []
                work_phones = item.get('workPhone') or []
                phone_numbers = [phone['tel'] for phone in mobile_phones + work_phones]
                if user_phone in phone_numbers:
                    await update.message.reply_text(f"Найден ID пользователя: {item['__id']}")
                    return

        await update.message.reply_text('Пользователь с таким номером телефона не найден.')




def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("emails", get_emails))
    application.add_handler(CommandHandler("zadachi", get_zadachi))
    application.add_handler(CommandHandler("employees", get_employees))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone_number))
    application.run_polling()


if __name__ == '__main__':
    main()
