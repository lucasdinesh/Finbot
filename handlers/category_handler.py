"""Handler for category commands."""
from handlers.base_handler import BaseHandler
from services.expense_service import ExpenseService
from telebot import types
from messages import CATEGORIES_HEADER, NO_CATEGORIES, ADD_CATEGORY_CUSTOM_PROMPT, NAME_EMPTY, NAME_TOO_LONG


class CategoryHandler(BaseHandler):

    def __init__(self, bot, state_manager, expense_service: ExpenseService):
        super().__init__(bot, state_manager)
        self.expense_service = expense_service

    def handle_list_categories(self, message) -> None:
        user_id = message.from_user.id
        categories = self.expense_service.get_categories(user_id)
        if not categories:
            self.send_info(message.chat.id, NO_CATEGORIES)
            return

        text = CATEGORIES_HEADER
        for cat_id, cat_name in categories:
            text += f"📂 {cat_name}\n"

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("➕ Nova Categoria", callback_data="CATEGORY_CREATE"))
        self.bot.send_message(message.chat.id, text, reply_markup=keyboard)

    def handle_create_category_start(self, call) -> None:
        self.bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
        msg = self.bot.send_message(call.message.chat.id, ADD_CATEGORY_CUSTOM_PROMPT)
        self.register_next_handler(msg, self.handle_create_category_name)
        self.bot.answer_callback_query(call.id)

    def handle_create_category_name(self, message) -> None:
        name = message.text.strip()
        chat_id = message.chat.id
        user_id = message.from_user.id

        if self.is_cancel_command(name):
            return self.handle_cancel(chat_id)

        if not name:
            self.send_error(chat_id, NAME_EMPTY)
            self.register_next_handler(message, self.handle_create_category_name)
            return

        if len(name) > 50:
            self.send_error(chat_id, NAME_TOO_LONG)
            self.register_next_handler(message, self.handle_create_category_name)
            return

        self.expense_service.create_category(name, user_id)
        self.send_success(chat_id, f"✅ Categoria *{name}* criada!")
