import json
from datetime import datetime
import requests
from telegram.ext import MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, Bot, KeyboardButton, \
    ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, ApplicationBuilder, \
    ContextTypes
import re
import os

TELEGRAM_BOT_TOKEN = '6819907271:AAGmbKe8oTAyU77XKrG9dxIu24sGlwAjVgU'
ELMA365_API_URL = 'https://fittest.bimup.dev/pub/v1/app/general_mail/EMailOutgoing/list'
TOKEN = '309cf20e-9dd3-4262-911c-3f795dde24f3'
COMMANDS_FILE  = 'custom_commands.json'

def load_commands():
    if os.path.exists(COMMANDS_FILE):
        with open(COMMANDS_FILE, 'r') as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return {}
    return {}


def save_commands(commands):
    with open(COMMANDS_FILE, 'w') as file:
        json.dump(commands, file, indent=4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = load_commands()
    if not commands:
        await update.message.reply_text('Команды пока не добавлены. Пожалуйста, добавьте команду с помощью /addcommand.')
    else:
        keyboard = [[InlineKeyboardButton(cmd, callback_data=cmd)] for cmd in commands]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выберите команду:', reply_markup=reply_markup)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Введите название команды:')
    context.user_data['step'] = 'name'


async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands = load_commands()
    step = context.user_data.get('step', '')

    if step == 'name':
        command_name = update.message.text
        if command_name in commands:
            await update.message.reply_text('Такая команда уже существует. Попробуйте снова.')
        else:
            commands[command_name] = {}
            save_commands(commands)
            await update.message.reply_text(f'Команда {command_name} добавлена.')
            await update.message.reply_text('Введите одно или несколько значений ключа response_key через запятую:')
            context.user_data['command_name'] = command_name
            context.user_data['step'] = 'response_keys'
    elif step == 'response_keys':
        command_name = context.user_data['command_name']
        response_keys = update.message.text.split(',')
        response_keys = [key.strip() for key in response_keys]
        commands[command_name]['response_keys'] = response_keys
        save_commands(commands)
        await update.message.reply_text('Хотите выводить все элементы из списка результатов или только первый? Введите "all" или "first".')
        context.user_data['step'] = 'output_option'
    elif step == 'output_option':
        command_name = context.user_data['command_name']
        output_option = update.message.text.lower()
        if output_option not in ['all', 'first']:
            await update.message.reply_text('Некорректный ввод. Пожалуйста, введите "all" или "first".')
            return
        commands[command_name]['output_option'] = output_option
        save_commands(commands)
        await update.message.reply_text('Теперь введите URL для этой команды:')
        context.user_data['step'] = 'url'
    elif step == 'url':
        command_name = context.user_data['command_name']
        url = update.message.text
        commands[command_name]['url'] = url
        save_commands(commands)
        await update.message.reply_text('Введите TOKEN для этой команды:')
        context.user_data['step'] = 'token'
    elif step == 'token':
        command_name = context.user_data['command_name']
        token = update.message.text
        commands[command_name]['token'] = token
        save_commands(commands)
        await update.message.reply_text('Команда добавлена успешно!')
        context.user_data.clear()
    else:
        await update.message.reply_text('Неизвестный шаг. Пожалуйста, начните с команды /addcommand')


async def handle_command_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    command_name = query.data
    commands = load_commands()

    if command_name in commands:
        context.user_data['command_name'] = command_name
        context.user_data['page'] = 0
    elif command_name == 'next_page':
        context.user_data['page'] += 1
    elif command_name == 'prev_page' and context.user_data.get('page', 0) > 0:
        context.user_data['page'] -= 1
    else:
        await query.edit_message_text('Команда не найдена.')
        return

    command_name = context.user_data['command_name']
    command_data = commands.get(command_name)
    if not command_data:
        await query.edit_message_text('Команда не найдена.')
        return

    url = command_data['url']
    token = command_data['token']
    response_keys = command_data.get('response_keys', [])
    output_option = command_data.get('output_option', 'first')

    page = context.user_data.get('page', 0)
    payload = {'active': True, 'from': page * 10, 'size': 10}

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        result = data.get('result', {}).get('result', [])

        buttons = []
        for item in result:
            item_values = [item.get(key, 'Ключ не найден в респонсе.') for key in response_keys]
            button_text = ", ".join(str(value) for value in item_values if value is not None)
            buttons.append([InlineKeyboardButton(button_text, callback_data=item['__id'])])

        buttons.append([
            InlineKeyboardButton("⬅️", callback_data="prev_page"),
            InlineKeyboardButton("➡️", callback_data="next_page")
        ])
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text('Выберите элемент:', reply_markup=reply_markup)

    except requests.exceptions.RequestException as e:
        await query.edit_message_text(f"Ошибка запроса: {e}")


def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addcommand", add_command))
    application.add_handler(CallbackQueryHandler(handle_command_selection))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_input))

    application.run_polling()


if __name__ == '__main__':
    main()
