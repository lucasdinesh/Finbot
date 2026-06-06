"""Handler for budget commands."""
from datetime import datetime
from handlers.base_handler import BaseHandler
from services.expense_service import ExpenseService
from telebot import types
from messages import (
    BUDGET_SET_PROMPT, BUDGET_SET_SUCCESS, BUDGET_HEADER, BUDGET_FORMAT,
    NO_BUDGETS, BUDGET_SELECT_CATEGORY, ADD_CATEGORY_CUSTOM_PROMPT,
    BUDGET_OVER, VALUE_INVALID, VALUE_MUST_BE_POSITIVE,
)

ERROR_MESSAGES = {
    "VALUE_INVALID": VALUE_INVALID,
    "VALUE_MUST_BE_POSITIVE": VALUE_MUST_BE_POSITIVE,
}
from utils.validators import ExpenseValidator


class BudgetHandler(BaseHandler):

    def __init__(self, bot, state_manager, expense_service: ExpenseService):
        super().__init__(bot, state_manager)
        self.expense_service = expense_service
        self.validator = ExpenseValidator()

    def handle_set_budget(self, message) -> None:
        categories = self.expense_service.get_categories(message.from_user.id)
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        for cat_id, cat_name in categories:
            keyboard.add(
                types.InlineKeyboardButton(cat_name, callback_data=f"BUDGET_CAT_{cat_id}")
            )
        self.bot.send_message(message.chat.id, BUDGET_SELECT_CATEGORY, reply_markup=keyboard)

    def handle_budget_category_callback(self, call) -> None:
        category_id = int(call.data.replace("BUDGET_CAT_", ""))
        categories = dict(self.expense_service.get_categories(call.from_user.id))
        cat_name = categories.get(category_id, "Desconhecida")

        self.state.update_user_state(call.from_user.id, "budget_category_id", category_id)
        self.state.update_user_state(call.from_user.id, "budget_category_name", cat_name)
        self.bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
        msg = self.bot.send_message(
            call.message.chat.id,
            BUDGET_SET_PROMPT.format(category=cat_name),
            parse_mode="Markdown",
        )
        self.bot.register_next_step_handler(msg, self.process_budget_value)
        self.bot.answer_callback_query(call.id)

    def process_budget_value(self, message) -> None:
        chat_id = message.chat.id
        user_id = message.from_user.id
        value_str = self._get_text(message)

        if self.is_cancel_command(value_str):
            return self.handle_cancel(chat_id)

        is_valid, value, error_key = self.validator.validate_value(value_str)
        if not is_valid:
            self.send_error(chat_id, ERROR_MESSAGES.get(error_key, VALUE_INVALID))
            self.register_next_handler(message, self.process_budget_value)
            return

        user_state = self.state.get_user_state(user_id)
        category_id = user_state.get("budget_category_id")
        category_name = user_state.get("budget_category_name", "Desconhecida")

        now = datetime.now()
        self.expense_service.set_budget(user_id, category_id, now.month, now.year, value)
        self.state.clear_user_state(user_id)

        self.send_success(
            chat_id,
            BUDGET_SET_SUCCESS.format(amount=value, category=category_name),
        )

    def handle_list_budgets(self, message) -> None:
        now = datetime.now()
        user_id = message.from_user.id
        budgets = self.expense_service.get_budgets_for_month(user_id, now.month, now.year)

        if not budgets:
            self.send_info(message.chat.id, NO_BUDGETS)
            return

        text = BUDGET_HEADER
        for b in budgets:
            spent = self.expense_service.get_category_total_for_month(
                user_id, b["category_id"], now.month, now.year
            )
            percent = (spent / b["amount"]) * 100 if b["amount"] > 0 else 0
            text += BUDGET_FORMAT.format(
                category=b["category_name"],
                spent=spent,
                budget=b["amount"],
                percent=percent,
            ) + "\n"
        self.send_info(message.chat.id, text)
