import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, CallbackContext

class ElmaBot:
    def __init__(self, token, page_size=10):
        self.TELEGRAM_BOT_TOKEN = token
        self.ELMA365_API_URL = 'https://fittest.bimup.dev/pub/v1/app/general_mail/EMailIncoming/list'
        self.TOKEN = '309cf20e-9dd3-4262-911c-3f795dde24f3'
        self.page_size = page_size
        self.current_page = 1
        self.URLS = {
            'emails': 'https://fittest.bimup.dev/pub/v1/app/general_mail/EMailOutgoing/list',
            'incoming_emails': 'https://fittest.bimup.dev/pub/v1/app/general_mail/EMailIncoming/list',
            'objects': 'https://fittest.bimup.dev/pub/v1/app/_system_catalogs/obekt/list',
            'employees': 'https://fittest.bimup.dev/pub/v1/app/human_resource/employee_search/list'
        }
        self.PAYLOADS = {
            'emails': {'active': True, 'from': 0, 'size': self.page_size},
            'incoming_emails': {'active': True, 'from': 0, 'size': self.page_size},
            'objects': {'active': True, 'from': 0, 'size': self.page_size},
            'employees': {'active': True, 'from': 0, 'size': self.page_size}
        }

    def get_elma_data(self, endpoint_key, page):
        headers = {
            'Authorization': f'Bearer {self.TOKEN}',
            'Content-Type': 'application/json'
        }
        payload = self.PAYLOADS[endpoint_key].copy()
        payload['from'] = (page - 1) * self.page_size

        try:
            response = requests.post(self.URLS[endpoint_key], headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            return None

    async def start(self, update: Update, context: CallbackContext) -> None:
        keyboard = [
            [KeyboardButton("/emails"), KeyboardButton("/objects"), KeyboardButton("/employees")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text('Выберите команду:', reply_markup=reply_markup)

    async def get_all(self, update: Update, context: CallbackContext, endpoint_key) -> None:
        self.current_page = 1

        data = self.get_elma_data(endpoint_key, self.current_page)
        if data and data.get('success') and isinstance(data['result'].get('result'), list):
            buttons = []
            for item in data['result']['result']:
                text = item.get('text', 'No Text')
                email_info = item.get('email_from')
                email = email_info[0].get('email', 'No Email') if email_info else 'No Email'
                buttons.append([InlineKeyboardButton(f"{text} ({email})", callback_data=item.get('__id'))])

            buttons.append([
                InlineKeyboardButton("⬅️", callback_data="prev_page"),
                InlineKeyboardButton("➡️", callback_data="next_page")
            ])
            reply_markup = InlineKeyboardMarkup(buttons)
            await update.message.reply_text('Выберите письмо:', reply_markup=reply_markup)
        else:
            await update.message.reply_text(
                f"Error retrieving data: {data.get('message', 'Unknown error')}" if data else 'API request failed.')

    async def button(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()

        if query.data == "next_page":
            self.current_page += 1
        elif query.data == "prev_page":
            if self.current_page > 1:
                self.current_page -= 1
        else:
            data = self.get_elma_data('emails', self.current_page)
            if data and data.get('success') and isinstance(data['result'].get('result'), list):
                for item in data['result']['result']:
                    if item.get('__id') == query.data:
                        text = item.get('text', 'No Text')
                        email_info = item.get('email_from')
                        email = email_info[0].get('email', 'No Email') if email_info else 'No Email'
                        await query.message.reply_text(
                            text=f"ID: {query.data}\nText: {text}\nEmail: {email}",
                            reply_markup=InlineKeyboardMarkup(
                                [[InlineKeyboardButton("Ответить на письмо", callback_data=f"reply_{query.data}")]])
                        )
                        return

        data = self.get_elma_data('emails', self.current_page)
        if data and data.get('success') and isinstance(data['result'].get('result'), list):
            buttons = []
            for item in data['result']['result']:
                text = item.get('text', 'No Text')
                email_info = item.get('email_from')
                email = email_info[0].get('email', 'No Email') if email_info else 'No Email'
                buttons.append([InlineKeyboardButton(f"{text} ({email})", callback_data=item.get('__id'))])

            buttons.append([
                InlineKeyboardButton("⬅️", callback_data="prev_page"),
                InlineKeyboardButton("➡️", callback_data="next_page")
            ])
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.edit_message_text('Выберите письмо:', reply_markup=reply_markup)
        else:
            await query.edit_message_text(
                f"Error retrieving data: {data.get('message', 'Unknown error')}" if data else 'API request failed.')

    async def get_emails(self, update: Update, context: CallbackContext) -> None:
        await self.get_all(update, context, 'emails')

    async def get_objects(self, update: Update, context: CallbackContext) -> None:
        await self.get_all(update, context, 'objects')

    async def get_employees(self, update: Update, context: CallbackContext) -> None:
        await self.get_all(update, context, 'employees')

    async def get_incoming_emails(self, update: Update, context: CallbackContext) -> None:
      await self.get_all(update, context, 'incoming_emails')

    def main(self) -> None:
      application = ApplicationBuilder().token(self.TELEGRAM_BOT_TOKEN).build()
      application.add_handler(CommandHandler("start", self.start))
      application.add_handler(CommandHandler("emails", self.get_emails))
      application.add_handler(CommandHandler("incoming_emails", self.get_incoming_emails))
      application.add_handler(CommandHandler("objects", self.get_objects))
      application.add_handler(CommandHandler("employees", self.get_employees))
      application.add_handler(CallbackQueryHandler(self.button))
      application.run_polling()



if __name__ == '__main__':
    bot = ElmaBot('6819907271:AAGmbKe8oTAyU77XKrG9dxIu24sGlwAjVgU')
    bot.main()
