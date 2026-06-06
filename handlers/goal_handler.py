"""Handler for savings goal commands."""
import re
from handlers.base_handler import BaseHandler
from services.expense_service import ExpenseService
from telebot import types
from messages import (
    GOAL_NAME_PROMPT, GOAL_TARGET_PROMPT, GOAL_DEADLINE_PROMPT,
    GOAL_ADD_SUCCESS, GOAL_HEADER, GOAL_FORMAT, GOAL_NO_DEADLINE,
    NO_GOALS, GOAL_CONTRIBUTE_PROMPT, GOAL_CONTRIBUTE_SUCCESS,
    GOAL_SELECT_PROMPT, VALUE_INVALID, VALUE_MUST_BE_POSITIVE,
    NAME_EMPTY, NAME_TOO_LONG,
)
from utils.validators import ExpenseValidator


class GoalHandler(BaseHandler):

    def __init__(self, bot, state_manager, expense_service: ExpenseService):
        super().__init__(bot, state_manager)
        self.expense_service = expense_service
        self.validator = ExpenseValidator()

    def handle_add_goal(self, message) -> None:
        self.send_info(message.chat.id, GOAL_NAME_PROMPT)
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

        self.state.update_user_state(message.from_user.id, "goal_name", name)
        self.send_info(message.chat.id, GOAL_TARGET_PROMPT)
        self.register_next_handler(message, self.process_target)

    def process_target(self, message) -> None:
        val_str = message.text.strip()
        if self.is_cancel_command(val_str):
            return self.handle_cancel(message.chat.id)

        is_valid, value, err = self.validator.validate_value(val_str)
        if not is_valid:
            self.send_error(message.chat.id, VALUE_INVALID)
            self.register_next_handler(message, self.process_target)
            return

        self.state.update_user_state(message.from_user.id, "goal_target", str(value))
        self.send_info(message.chat.id, GOAL_DEADLINE_PROMPT)
        self.register_next_handler(message, self.process_deadline)

    def process_deadline(self, message) -> None:
        deadline_str = message.text.strip()
        chat_id = message.chat.id
        user_id = message.from_user.id

        if self.is_cancel_command(deadline_str):
            return self.handle_cancel(chat_id)

        deadline = None
        if deadline_str != "0":
            date_pattern = re.compile(r'^\d{2}-\d{2}-\d{4}$')
            if not date_pattern.match(deadline_str):
                self.send_error(chat_id, "❌ Data inválida! Use DD-MM-YYYY ou digite 0 para não ter prazo.")
                self.register_next_handler(message, self.process_deadline)
                return
            deadline = deadline_str

        user_state = self.state.get_user_state(user_id)
        name = user_state.get("goal_name", "")
        target = float(user_state.get("goal_target", 0))

        self.expense_service.add_savings_goal(user_id, name, target, deadline)
        self.state.clear_user_state(user_id)
        self.send_success(chat_id, GOAL_ADD_SUCCESS.format(name=name))

    def handle_list_goals(self, message) -> None:
        goals = self.expense_service.get_savings_goals(message.from_user.id)
        if not goals:
            self.send_info(message.chat.id, NO_GOALS)
            return

        text = GOAL_HEADER
        for g in goals:
            target = g["target_amount"]
            current = g["current_amount"]
            percent = (current / target) * 100 if target > 0 else 0
            deadline = g["deadline"] or GOAL_NO_DEADLINE

            text += GOAL_FORMAT.format(
                name=g["name"],
                current=current,
                target=target,
                percent=percent,
                deadline=deadline,
            )
        self.send_info(message.chat.id, text)

    def handle_contribute_start(self, message) -> None:
        goals = self.expense_service.get_savings_goals(message.from_user.id)
        if not goals:
            self.send_info(message.chat.id, NO_GOALS)
            return

        keyboard = types.InlineKeyboardMarkup(row_width=1)
        for g in goals:
            keyboard.add(
                types.InlineKeyboardButton(
                    f"{g['name']} — R$ {g['current_amount']:.2f} / R$ {g['target_amount']:.2f}",
                    callback_data=f"GOAL_CONT_{g['id']}",
                )
            )
        self.bot.send_message(message.chat.id, GOAL_SELECT_PROMPT, reply_markup=keyboard)

    def handle_contribute_select(self, call) -> None:
        goal_id = int(call.data.replace("GOAL_CONT_", ""))
        goals = self.expense_service.get_savings_goals(call.from_user.id)
        goal_name = next((g["name"] for g in goals if g["id"] == goal_id), "Meta")

        self.state.update_user_state(call.from_user.id, "contribute_goal_id", goal_id)
        self.state.update_user_state(call.from_user.id, "contribute_goal_name", goal_name)
        self.bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
        msg = self.bot.send_message(
            call.message.chat.id,
            GOAL_CONTRIBUTE_PROMPT.format(name=goal_name),
            parse_mode="Markdown",
        )
        self.register_next_handler(msg, self.process_contribute_value)
        self.bot.answer_callback_query(call.id)

    def process_contribute_value(self, message) -> None:
        val_str = message.text.strip()
        chat_id = message.chat.id
        user_id = message.from_user.id

        if self.is_cancel_command(val_str):
            return self.handle_cancel(chat_id)

        is_valid, value, err = self.validator.validate_value(val_str)
        if not is_valid:
            self.send_error(chat_id, VALUE_INVALID)
            self.register_next_handler(message, self.process_contribute_value)
            return

        user_state = self.state.get_user_state(user_id)
        goal_id = user_state.get("contribute_goal_id")
        goal_name = user_state.get("contribute_goal_name", "Meta")

        self.expense_service.contribute_to_goal(goal_id, value)
        self.state.clear_user_state(user_id)
        self.send_success(chat_id, GOAL_CONTRIBUTE_SUCCESS.format(amount=value, name=goal_name))
