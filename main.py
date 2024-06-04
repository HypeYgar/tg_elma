import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, ApplicationBuilder, ContextTypes

TELEGRAM_BOT_TOKEN = '6819907271:AAGmbKe8oTAyU77XKrG9dxIu24sGlwAjVgU'
ELMA365_API_URL = 'https://fittest.bimup.dev/pub/v1/app/general_mail/EMailOutgoing/list'
TOKEN = '309cf20e-9dd3-4262-911c-3f795dde24f3'
current_page = 1
page_size = 10

def get_elma_data():
  headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
  }
  payload = {
    'active': True,
    'from': (current_page - 1) * page_size,
    'size': page_size,
  }
  try:
    response = requests.post(ELMA365_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()
  except requests.exceptions.RequestException as e:
    print(f"Error making API request: {e}")
    return None

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('хайп')

async def get_all(update: Update, context: CallbackContext) -> None:
  data = get_elma_data()
  if data:
    try:
      if data.get('success') and 'result' in data and isinstance(data['result']['result'], list):
        buttons = []
        for item in data['result']['result']:
          if isinstance(item, dict):
            text = item.get('text', 'No Text')
            email = item.get('email_from')
            if email:
                email = email[0].get('email', 'No Email')
            else:
                email = 'No Email'
            button_text = f"{text} ({email})"
            callback_data = item.get('__id')
            buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        else:
          print("Unexpected item format:", item)

        buttons.append([
            InlineKeyboardButton("⬅️", callback_data="prev_page"),
            InlineKeyboardButton("➡️", callback_data="next_page")
        ])
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text('Выберите письмо:', reply_markup=reply_markup)
      else:
        await update.message.reply_text(f"Error retrieving data: {data.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        await update.message.reply_text("An error occurred. Please try again later.")
  else:
    await update.message.reply_text('API request failed.')

async def button(update: Update, context: CallbackContext) -> None:
  query = update.callback_query
  await query.answer()
  callback_data = query.data
  if callback_data == "next_page":
    global current_page
    current_page += 1
  elif callback_data == "prev_page":
    if current_page > 1:
      current_page -= 1
  else:
    data = get_elma_data()
    if data:
      try:
        if data.get('success') and 'result' in data and isinstance(data['result']['result'], list):
          for item in data['result']['result']:
            if item.get('__id') == callback_data:
              text = item.get('text', 'No Text')
              email = item.get('email_from')
              if email:
                  email = email[0].get('email', 'No Email')
              else:
                  email = 'No Email'
              await query.edit_message_text(text=f"ID: {callback_data}\nText: {text}\nEmail: {email}")
              break
          else:
            await query.edit_message_text(text="Нет доступных данных.")
            return
      except Exception as e:
        print(f"Unexpected error handling email: {e}")
        await query.edit_message_text("An error occurred. Please try again later.")
    else:
      await query.edit_message_text('API request failed.')
  data = get_elma_data()
  has_next_page = False
  has_prev_page = False
  if data:
    try:
      if data.get('success') and 'result' in data:
        has_next_page = data['result'].get('hasNext', False)
        has_prev_page = data['result'].get('hasPrev', False)
    except Exception as e:
      print(f"Error retrieving pagination flags: {e}")
  buttons = []
  if data:
    try:
      if data.get('success') and 'result' in data and isinstance(data['result']['result'], list):
        for item in data['result']['result']:
          if isinstance(item, dict):
            text = item.get('text', 'No Text')
            email = item.get('email_from')
            if email:
                email = email[0].get('email', 'No Email')
            else:
                email = 'No Email'
            button_text = f"{text} ({email})"
            callback_data = item.get('__id')
            buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        buttons.append([
            InlineKeyboardButton("⬅️", callback_data="prev_page"),
            InlineKeyboardButton("➡️", callback_data="next_page")
        ])
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text('Выберите письмо:', reply_markup=reply_markup)
      else:
        await query.edit_message_text(f"Error retrieving data: {data.get('message', 'Unknown error')}")
    except Exception as e:
      print(f"Unexpected error handling pagination: {e}")
      await query.edit_message_text("An error occurred. Please try again later.")
  else:
    await query.edit_message_text('API request failed.')

def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("get", get_all))
    application.add_handler(CallbackQueryHandler(button))
    application.run_polling()

if __name__ == '__main__':
    main()
