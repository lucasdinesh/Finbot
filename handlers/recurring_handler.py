"""Handler for recurring expense commands."""
from handlers.base_handler import BaseHandler
from services.expense_service import ExpenseService
from telebot import types
from messages import (
    RECURRING_NAME_PROMPT, RECURRING_VALUE_PROMPT, RECURRING_DAY_PROMPT,
    RECURRING_ADD_SUCCESS, RECURRING_HEADER, RECURRING_FORMAT,
    NO_RECURRING, RECURRING_DELETED, RECURRING_SELECT_DELETE,
    ADD_PAYMENT_PROMPT, PAYMENT_PIX, PAYMENT_DINHEIRO, PAYMENT_CREDITO,
    ADD_CATEGORY_PROMPT, CATEGORY_OTHER, ADD_CATEGORY_CUSTOM_PROMPT,
    VALUE_INVALID, VALUE_MUST_BE_POSITIVE, NAME_EMPTY, NAME_TOO_LONG,
)
from utils.validators import ExpenseValidator

PAYMENT_METHODS = {
    "RPAYMENT_PIX": "pix",
    "RPAYMENT_DINHEIRO": "dinheiro",
    "RPAYMENT_CREDITO": "credito",
}


class RecurringHandler(BaseHandler):

    def __init__(self, bot, state_manager, expense_service: ExpenseService):
        super().__init__(bot, state_manager)
        self.expense_service = expense_service
        self.validator = ExpenseValidator()

    def handle_add_recurring(self, message) -> None:
        self.send_info(message.chat.id, RECURRING_NAME_PROMPT)
        self.register_next_handler(message, self.process_name)

    def process_name(self, message) -> None:
        name = message.text.strip()
        if self.is_cancel_command(name):
            return self.handle_cancel(message.chat.id)
        if not name:
            self.send_error(message.chat.id, NAME_EMPTY)
            self.register_next_handler(message, self.process_name)
            return
        if len(name) > 50:
            self.send_error(message.chat.id, NAME_TOO_LONG)
            self.register_next_handler(message, self.process_name)
            return

        self.state.update_user_state(message.from_user.id, "rec_name", name)
        self.send_info(message.chat.id, RECURRING_VALUE_PROMPT)
        self.register_next_handler(message, self.process_value)

    def process_value(self, message) -> None:
        val_str = message.text.strip()
        if self.is_cancel_command(val_str):
            return self.handle_cancel(message.chat.id)

        is_valid, value, err = self.validator.validate_value(val_str)
        if not is_valid:
            self.send_error(message.chat.id, VALUE_INVALID)
            self.register_next_handler(message, self.process_value)
            return

        self.state.update_user_state(message.from_user.id, "rec_amount", str(value))

        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(PAYMENT_PIX, callback_data="RPAYMENT_PIX"),
            types.InlineKeyboardButton(PAYMENT_DINHEIRO, callback_data="RPAYMENT_DINHEIRO"),
            types.InlineKeyboardButton(PAYMENT_CREDITO, callback_data="RPAYMENT_CREDITO"),
        )
        self.bot.send_message(message.chat.id, ADD_PAYMENT_PROMPT, reply_markup=keyboard)

    def handle_payment_callback(self, call) -> None:
        payment = PAYMENT_METHODS.get(call.data)
        if not payment:
            return
        self.state.update_user_state(call.from_user.id, "rec_payment", payment)
        self.bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
        self._ask_category(call.message.chat.id, call.from_user.id)
        self.bot.answer_callback_query(call.id)

    def _ask_category(self, chat_id: int, user_id: int) -> None:
        categories = self.expense_service.get_categories(user_id)
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        for cat_id, cat_name in categories:
            keyboard.add(
                types.InlineKeyboardButton(cat_name, callback_data=f"RCAT_{cat_id}")
            )
        keyboard.add(types.InlineKeyboardButton(CATEGORY_OTHER, callback_data="RCAT_OTHER"))
        self.state.update_user_state(user_id, "rec_cat_data", categories)
        self.bot.send_message(chat_id, ADD_CATEGORY_PROMPT, reply_markup=keyboard)

    def handle_category_callback(self, call) -> None:
        user_id = call.from_user.id
        chat_id = call.message.chat.id

        if call.data == "RCAT_OTHER":
            self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
            msg = self.bot.send_message(chat_id, ADD_CATEGORY_CUSTOM_PROMPT)
            self.bot.register_next_step_handler(msg, self.process_custom_category)
            self.bot.answer_callback_query(call.id)
            return

        cat_id = int(call.data.replace("RCAT_", ""))
        self.state.update_user_state(user_id, "rec_category_id", cat_id)
        self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        self.bot.answer_callback_query(call.id)
        self._ask_day(chat_id, user_id)

    def process_custom_category(self, message) -> None:
        name = message.text.strip()
        chat_id = message.chat.id
        user_id = message.from_user.id

        if self.is_cancel_command(name):
            return self.handle_cancel(chat_id)
        if not name:
            self.send_error(chat_id, NAME_EMPTY)
            self.register_next_handler(message, self.process_custom_category)
            return

        cat_id = self.expense_service.create_category(name, user_id)
        self.state.update_user_state(user_id, "rec_category_id", cat_id)
        self._ask_day(chat_id, user_id)

    def _ask_day(self, chat_id: int, user_id: int) -> None:
        msg = self.bot.send_message(chat_id, RECURRING_DAY_PROMPT)
        self.bot.register_next_step_handler(msg, self.process_day)

    def process_day(self, message) -> None:
        day_str = message.text.strip()
        chat_id = message.chat.id
        user_id = message.from_user.id

        if self.is_cancel_command(day_str):
            return self.handle_cancel(chat_id)

        try:
            day = int(day_str)
            if day < 1 or day > 31:
                raise ValueError
        except ValueError:
            self.send_error(chat_id, "❌ Dia inválido! Digite um número entre 1 e 31.")
            self.register_next_handler(message, self.process_day)
            return

        user_state = self.state.get_user_state(user_id)
        name = user_state.get("rec_name", "")
        amount = float(user_state.get("rec_amount", 0))
        payment = user_state.get("rec_payment")
        cat_id = user_state.get("rec_category_id")

        self.expense_service.add_recurring_expense(user_id, name, amount, cat_id, payment, day)
        self.state.clear_user_state(user_id)
        self.send_success(chat_id, RECURRING_ADD_SUCCESS.format(name=name, day=day))

    def handle_list_recurring(self, message) -> None:
        items = self.expense_service.get_recurring_expenses(message.from_user.id)
        if not items:
            self.send_info(message.chat.id, NO_RECURRING)
            return

        text = RECURRING_HEADER
        for r in items:
            pm = r["payment_method"] or "-"
            text += RECURRING_FORMAT.format(
                name=r["name"],
                amount=r["amount"],
                day=r["day_of_month"],
                payment=pm,
            )
        self.send_info(message.chat.id, text)

    def handle_delete_recurring(self, message) -> None:
        items = self.expense_service.get_recurring_expenses(message.from_user.id)
        if not items:
            self.send_info(message.chat.id, NO_RECURRING)
            return

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for r in items:
            keyboard.add(
                types.InlineKeyboardButton(
                    f"{r['name']} — R$ {r['amount']:.2f} (dia {r['day_of_month']})",
                    callback_data=f"RDEL_{r['id']}",
                )
            )
        self.bot.send_message(message.chat.id, RECURRING_SELECT_DELETE, reply_markup=keyboard)
        self.state.update_user_state(message.from_user.id, "rec_delete_items", items)

    def handle_delete_callback(self, call) -> None:
        rec_id = int(call.data.replace("RDEL_", ""))
        self.expense_service.delete_recurring_expense(rec_id)
        self.bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
        self.bot.send_message(call.message.chat.id, RECURRING_DELETED)
        self.bot.answer_callback_query(call.id)
        self.state.clear_user_state(call.from_user.id)
