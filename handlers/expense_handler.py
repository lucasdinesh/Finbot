"""Handler for expense-related commands."""
from handlers.base_handler import BaseHandler
from services.expense_service import ExpenseService
from utils.validators import ExpenseValidator
from telebot import types
import re

from messages import (
    ADD_VALUE_PROMPT, ADD_NAME_PROMPT, ADD_DATE_INVALID,
    ADD_INSTALLMENTS_PROMPT, ADD_SUCCESS,
    ADD_PAYMENT_PROMPT, PAYMENT_PIX, PAYMENT_DINHEIRO, PAYMENT_CREDITO,
    ADD_CATEGORY_PROMPT, ADD_CATEGORY_CUSTOM_PROMPT, CATEGORY_OTHER,
    VALUE_INVALID, VALUE_MUST_BE_POSITIVE, NAME_EMPTY, NAME_TOO_LONG,
    NAME_NOT_ALPHANUMERIC,
    INSTALLMENTS_INVALID, INSTALLMENTS_TOO_LARGE,
    DELETE_PROMPT, DELETE_ID_INVALID, DELETE_NOT_FOUND,
    DELETE_CONFIRM_PROMPT, DELETE_SUCCESS, DELETE_CANCELLED,
    SEARCH_PROMPT, SEARCH_NO_RESULTS, SEARCH_RESULT_FORMAT,
    EDIT_PROMPT, EDIT_NOT_FOUND, EDIT_FIELD_PROMPT,
    EDIT_FIELD_VALUE, EDIT_FIELD_NAME, EDIT_FIELD_DATE,
    EDIT_FIELD_INSTALLMENTS, EDIT_FIELD_CATEGORY, EDIT_FIELD_PAYMENT,
    EDIT_NEW_VALUE, EDIT_SUCCESS, EDIT_CANCELLED,
)

ERROR_MESSAGES = {
    "VALUE_INVALID": VALUE_INVALID,
    "VALUE_MUST_BE_POSITIVE": VALUE_MUST_BE_POSITIVE,
    "NAME_EMPTY": NAME_EMPTY,
    "NAME_TOO_LONG": NAME_TOO_LONG,
    "NAME_NOT_ALPHANUMERIC": NAME_NOT_ALPHANUMERIC,
    "INSTALLMENTS_INVALID": INSTALLMENTS_INVALID,
    "INSTALLMENTS_TOO_LARGE": INSTALLMENTS_TOO_LARGE,
}

PAYMENT_METHODS = {
    "PAYMENT_PIX": "pix",
    "PAYMENT_DINHEIRO": "dinheiro",
    "PAYMENT_CREDITO": "credito",
}


class ExpenseHandler(BaseHandler):
    """Handles expense-related commands and conversations."""

    def __init__(self, bot, state_manager, expense_service: ExpenseService):
        super().__init__(bot, state_manager)
        self.expense_service = expense_service
        self.validator = ExpenseValidator()

    # ------------------------------------------------------------------
    # /add flow
    # ------------------------------------------------------------------

    def handle_add_command(self, message) -> None:
        """Handle /add command - start of expense creation flow."""
        self.send_info(message.chat.id, ADD_VALUE_PROMPT)
        self.register_next_handler(message, self.process_value)

    def process_value(self, message) -> None:
        """Step 2: Validate and process expense value."""
        valor_str = self._get_text(message)

        if self.is_cancel_command(valor_str):
            return self.handle_cancel(message.chat.id)

        is_valid, value, error_key = self.validator.validate_value(valor_str)
        if not is_valid:
            self.send_error(message.chat.id, ERROR_MESSAGES.get(error_key, "Invalid input"))
            self.register_next_handler(message, self.process_value)
            return

        self.state.update_user_state(message.from_user.id, "valor_despesa", str(value))
        self.send_info(message.chat.id, ADD_NAME_PROMPT)
        self.register_next_handler(message, self.process_name)

    def process_name(self, message) -> None:
        """Step 3: Validate and process expense name."""
        name = self._get_text(message)

        if self.is_cancel_command(name):
            return self.handle_cancel(message.chat.id)

        is_valid, error_key = self.validator.validate_name(name)
        if not is_valid:
            self.send_error(message.chat.id, ERROR_MESSAGES.get(error_key, "Invalid input"))
            self.register_next_handler(message, self.process_name)
            return

        self.state.update_user_state(message.from_user.id, "name_despesa", name)
        from datetime import datetime
        hoje = datetime.now().strftime("%d-%m-%Y")
        self.send_info(message.chat.id, f"Qual a data da despesa? (DD-MM-YYYY) - hoje ({hoje})")
        self.register_next_handler(message, self.process_date)

    def process_date(self, message) -> None:
        """Step 4: Validate date, then ask payment method."""
        from datetime import datetime
        date_str = self._get_text(message)

        if self.is_cancel_command(date_str):
            return self.handle_cancel(message.chat.id)

        if date_str.lower() == "hoje":
            date_str = datetime.now().strftime("%d-%m-%Y")
        else:
            date_pattern = re.compile(r'^\d{2}-\d{2}-\d{4}$')
            if not date_pattern.match(date_str):
                self.send_error(message.chat.id, ADD_DATE_INVALID)
                self.register_next_handler(message, self.process_date)
                return

        selected = datetime.strptime(date_str, "%d-%m-%Y")
        if selected.date() > datetime.now().date():
            self.send_error(message.chat.id, "❌ Data no futuro não permitida! Escolha uma data até hoje.")
            self.register_next_handler(message, self.process_date)
            return

        self.state.update_user_state(message.from_user.id, "date_despesa", date_str)
        self._ask_payment_method(message.chat.id)

    def _ask_payment_method(self, chat_id: int) -> None:
        """Show payment method inline buttons."""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(PAYMENT_PIX, callback_data="PAYMENT_PIX"),
            types.InlineKeyboardButton(PAYMENT_DINHEIRO, callback_data="PAYMENT_DINHEIRO"),
            types.InlineKeyboardButton(PAYMENT_CREDITO, callback_data="PAYMENT_CREDITO"),
        )
        self.bot.send_message(chat_id, ADD_PAYMENT_PROMPT, reply_markup=keyboard)

    def handle_payment_callback(self, call) -> None:
        """Handle payment method selection via inline button."""
        user_id = call.from_user.id
        chat_id = call.message.chat.id

        payment_key = call.data  # e.g. "PAYMENT_PIX"
        payment_method = PAYMENT_METHODS.get(payment_key)
        if not payment_method:
            return

        self.state.update_user_state(user_id, "payment_method", payment_method)
        self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

        if payment_method == "credito":
            self.state.update_user_state(user_id, "installment", None)
            msg = self.bot.send_message(chat_id, ADD_INSTALLMENTS_PROMPT)
            self.bot.register_next_step_handler(msg, self.process_installments)
        else:
            self.state.update_user_state(user_id, "installment", "1")
            self._ask_category(chat_id, user_id)

        self.bot.answer_callback_query(call.id)

    def process_installments(self, message) -> None:
        """Validate installments, then go to category selection."""
        parcelas_str = self._get_text(message)

        if self.is_cancel_command(parcelas_str):
            return self.handle_cancel(message.chat.id)

        is_valid, parcelas, error_key = self.validator.validate_installments(parcelas_str)
        if not is_valid:
            self.send_error(message.chat.id, ERROR_MESSAGES.get(error_key, "Invalid input"))
            self.register_next_handler(message, self.process_installments)
            return

        self.state.update_user_state(message.from_user.id, "installment", str(parcelas))
        self._ask_category(message.chat.id, message.from_user.id)

    # ------------------------------------------------------------------
    # Category selection
    # ------------------------------------------------------------------

    def _ask_category(self, chat_id: int, user_id: int) -> None:
        """Show category inline buttons."""
        categories = self.expense_service.get_categories(user_id)

        keyboard = types.InlineKeyboardMarkup(row_width=2)
        for cat_id, cat_name in categories:
            keyboard.add(
                types.InlineKeyboardButton(cat_name, callback_data=f"CATEGORY_{cat_id}")
            )
        keyboard.add(
            types.InlineKeyboardButton(CATEGORY_OTHER, callback_data="CATEGORY_OTHER")
        )

        self.state.update_user_state(user_id, "category_id", None)
        self.state.update_user_state(user_id, "categories_data", categories)
        self.bot.send_message(chat_id, ADD_CATEGORY_PROMPT, reply_markup=keyboard)

    def handle_category_callback(self, call) -> None:
        """Handle category selection via inline button."""
        user_id = call.from_user.id
        chat_id = call.message.chat.id

        if call.data == "CATEGORY_OTHER":
            self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
            msg = self.bot.send_message(chat_id, ADD_CATEGORY_CUSTOM_PROMPT)
            self.bot.register_next_step_handler(msg, self.process_custom_category)
            self.bot.answer_callback_query(call.id)
            return

        category_id = int(call.data.replace("CATEGORY_", ""))
        self.state.update_user_state(user_id, "category_id", category_id)
        self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        self.bot.answer_callback_query(call.id)

        self._save_expense(chat_id, user_id)

    def process_custom_category(self, message) -> None:
        """Handle custom category name typed by user."""
        name = self._get_text(message)
        chat_id = message.chat.id
        user_id = message.from_user.id

        if self.is_cancel_command(name):
            return self.handle_cancel(chat_id)

        if not name:
            self.send_error(chat_id, NAME_EMPTY)
            self.register_next_handler(message, self.process_custom_category)
            return

        if len(name) > 50:
            self.send_error(chat_id, NAME_TOO_LONG)
            self.register_next_handler(message, self.process_custom_category)
            return

        category_id = self.expense_service.create_category(name, user_id)
        self.state.update_user_state(user_id, "category_id", category_id)
        self._save_expense(chat_id, user_id)

    # ------------------------------------------------------------------
    # Save helper
    # ------------------------------------------------------------------

    def _save_expense(self, chat_id: int, user_id: int) -> None:
        """Save expense and clean up state."""
        user_state = self.state.get_user_state(user_id)
        valor_despesa = float(user_state.get("valor_despesa", 0))
        name_despesa = user_state.get("name_despesa", "")
        date_despesa = user_state.get("date_despesa")
        installment = int(user_state.get("installment", 1))
        category_id = user_state.get("category_id")
        payment_method = user_state.get("payment_method")

        try:
            alert = self.expense_service.create_expense(
                user_id=user_id,
                name=name_despesa,
                amount=valor_despesa,
                installments=installment,
                date=date_despesa,
                category_id=category_id,
                payment_method=payment_method,
            )
        except ValueError as e:
            error_key = str(e)
            user_msg = ERROR_MESSAGES.get(error_key,
                                           f"❌ Erro ao salvar despesa: {error_key[:100]}")
            self.send_error(chat_id, user_msg)
            self.state.clear_user_state(user_id)
            return

        self.state.clear_user_state(user_id)

        if payment_method == "credito" and installment > 1:
            inst_line = f"Parcelas: {installment}"
        else:
            inst_line = ""

        success_msg = ADD_SUCCESS.format(
            name=name_despesa,
            value=valor_despesa,
            date=date_despesa or "hoje",
            installments_line=inst_line,
        )
        self.send_success(chat_id, success_msg)

        if alert:
            self.send_warning(chat_id, alert)

    # ------------------------------------------------------------------
    # /delete flow
    # ------------------------------------------------------------------

    def handle_delete_command(self, message) -> None:
        """Handle /delete command - start of expense deletion flow."""
        self.send_info(message.chat.id, DELETE_PROMPT)
        self.register_next_handler(message, self.process_delete_id)

    def process_delete_id(self, message) -> None:
        """Step 1: Get and validate expense ID for deletion."""
        expense_id_str = self._get_text(message)

        if self.is_cancel_command(expense_id_str):
            return self.handle_cancel(message.chat.id)

        try:
            local_id = int(expense_id_str)
            if local_id <= 0:
                self.send_error(message.chat.id, DELETE_ID_INVALID)
                self.register_next_handler(message, self.process_delete_id)
                return
        except ValueError:
            self.send_error(message.chat.id, DELETE_ID_INVALID)
            self.register_next_handler(message, self.process_delete_id)
            return

        try:
            expense = self.expense_service.get_expense_by_user_and_local_id(
                message.from_user.id, local_id
            )
            if not expense:
                self.send_error(message.chat.id, DELETE_NOT_FOUND.format(id=local_id))
                self.register_next_handler(message, self.process_delete_id)
                return
        except Exception:
            self.send_error(message.chat.id, DELETE_NOT_FOUND.format(id=local_id))
            self.register_next_handler(message, self.process_delete_id)
            return

        self.state.update_user_state(message.from_user.id, "delete_expense_id", expense.id)
        self.state.update_user_state(message.from_user.id, "delete_expense", expense)

        confirm_msg = DELETE_CONFIRM_PROMPT.format(
            name=expense.name,
            amount=expense.amount,
            installments=expense.installment
        )
        self.send_info(message.chat.id, confirm_msg)
        self.register_next_handler(message, self.process_delete_confirmation)

    def process_delete_confirmation(self, message) -> None:
        """Step 2: Process deletion confirmation."""
        confirmation = self._get_text(message).lower()

        if self.is_cancel_command(confirmation):
            return self.handle_cancel(message.chat.id)

        if confirmation in ['sim', 'yes', 's', 'y']:
            user_state = self.state.get_user_state(message.from_user.id)
            expense_id = user_state.get("delete_expense_id")

            if expense_id:
                try:
                    self.expense_service.delete_expense(expense_id)
                    self.send_success(message.chat.id, DELETE_SUCCESS)
                except Exception as e:
                    self.send_error(message.chat.id, f"❌ Erro ao deletar despesa: {str(e)}")

            self.state.clear_user_state(message.from_user.id)
        elif confirmation in ['não', 'no', 'n']:
            self.send_info(message.chat.id, DELETE_CANCELLED)
            self.state.clear_user_state(message.from_user.id)
        else:
            self.send_error(message.chat.id, "❌ Resposta inválida. Por favor, responda 'sim' ou 'não'.")
            self.register_next_handler(message, self.process_delete_confirmation)

    # ------------------------------------------------------------------
    # /search flow
    # ------------------------------------------------------------------

    def handle_search_command(self, message) -> None:
        """Handle /search command."""
        self.send_info(message.chat.id, SEARCH_PROMPT)
        self.register_next_handler(message, self.process_search_query)

    def process_search_query(self, message) -> None:
        """Search expenses by name and show results."""
        query = self._get_text(message)
        chat_id = message.chat.id
        user_id = message.from_user.id

        if self.is_cancel_command(query):
            return self.handle_cancel(chat_id)

        if not query:
            self.send_error(chat_id, "❌ Digite um nome para buscar.")
            self.register_next_handler(message, self.process_search_query)
            return

        results = self.expense_service.search_expenses_by_name(user_id, query)

        if not results:
            self.send_info(chat_id, SEARCH_NO_RESULTS.format(query=query))
            return

        for exp in results:
            pm = exp.payment_method or "-"
            text = SEARCH_RESULT_FORMAT.format(
                local_id=exp.local_id,
                name=exp.name,
                amount=exp.amount,
                date=exp.date,
                installment=exp.installment,
                payment_method=pm,
            )
            self.send_info(chat_id, text)

    # ------------------------------------------------------------------
    # /edit flow
    # ------------------------------------------------------------------

    def handle_edit_command(self, message) -> None:
        """Handle /edit command."""
        self.send_info(message.chat.id, EDIT_PROMPT)
        self.register_next_handler(message, self.process_edit_id)

    def process_edit_id(self, message) -> None:
        """Get expense ID to edit."""
        expense_id_str = self._get_text(message)

        if self.is_cancel_command(expense_id_str):
            return self.handle_cancel(message.chat.id)

        try:
            local_id = int(expense_id_str)
            if local_id <= 0:
                self.send_error(message.chat.id, "❌ ID inválido!")
                self.register_next_handler(message, self.process_edit_id)
                return
        except ValueError:
            self.send_error(message.chat.id, "❌ ID inválido!")
            self.register_next_handler(message, self.process_edit_id)
            return

        try:
            expense = self.expense_service.get_expense_by_user_and_local_id(
                message.from_user.id, local_id
            )
            if not expense:
                self.send_error(message.chat.id, EDIT_NOT_FOUND.format(id=local_id))
                self.register_next_handler(message, self.process_edit_id)
                return
        except Exception:
            self.send_error(message.chat.id, EDIT_NOT_FOUND.format(id=local_id))
            self.register_next_handler(message, self.process_edit_id)
            return

        self.state.update_user_state(message.from_user.id, "edit_expense_id", expense.id)
        self._ask_edit_field(message.chat.id)

    def _ask_edit_field(self, chat_id: int) -> None:
        """Show field selection for editing."""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(EDIT_FIELD_VALUE, callback_data="EDIT_VALUE"),
            types.InlineKeyboardButton(EDIT_FIELD_NAME, callback_data="EDIT_NAME"),
            types.InlineKeyboardButton(EDIT_FIELD_DATE, callback_data="EDIT_DATE"),
            types.InlineKeyboardButton(EDIT_FIELD_INSTALLMENTS, callback_data="EDIT_INSTALLMENTS"),
            types.InlineKeyboardButton(EDIT_FIELD_CATEGORY, callback_data="EDIT_CATEGORY"),
            types.InlineKeyboardButton(EDIT_FIELD_PAYMENT, callback_data="EDIT_PAYMENT"),
        )
        self.bot.send_message(chat_id, EDIT_FIELD_PROMPT, reply_markup=keyboard)

    def handle_edit_field_callback(self, call) -> None:
        """Handle field selection for editing."""
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        field = call.data  # e.g. "EDIT_VALUE"

        if field.startswith("EDIT_PAY_"):
            payment_map = {
                "EDIT_PAY_PIX": "pix",
                "EDIT_PAY_DINHEIRO": "dinheiro",
                "EDIT_PAY_CREDITO": "credito",
            }
            pm = payment_map.get(field)
            if pm:
                self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
                self._save_edit_payment(chat_id, user_id, pm)
            self.bot.answer_callback_query(call.id)
            return

        field_map = {
            "EDIT_VALUE": "valor",
            "EDIT_NAME": "nome",
            "EDIT_DATE": "data",
            "EDIT_INSTALLMENTS": "parcelas",
            "EDIT_CATEGORY": "categoria",
            "EDIT_PAYMENT": "forma de pagamento",
        }
        field_name = field_map.get(field, "")
        if not field_name:
            return

        self.state.update_user_state(user_id, "edit_field", field)
        self.bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

        if field == "EDIT_PAYMENT":
            self._ask_edit_payment(chat_id, user_id)
        else:
            expense_id = self.state.get_user_state(user_id).get("edit_expense_id")
            current_value = ""
            if expense_id:
                expense = self.expense_service.get_expense_by_id(expense_id)
                if expense:
                    if field == "EDIT_VALUE":
                        current_value = f"R$ {expense.amount:.2f}"
                    elif field == "EDIT_NAME":
                        current_value = expense.name
                    elif field == "EDIT_DATE":
                        current_value = expense.date
                    elif field == "EDIT_INSTALLMENTS":
                        current_value = str(expense.installment)
                    elif field == "EDIT_CATEGORY":
                        cats = self.expense_service.get_categories(user_id)
                        for cid, cname in cats:
                            if cid == expense.category_id:
                                current_value = cname
                                break
                        if not current_value:
                            current_value = str(expense.category_id)

            msg = self.bot.send_message(
                chat_id,
                f"✏️ Valor atual: *{current_value}*\nDigite o novo valor ou 'ok' para manter:",
                parse_mode="Markdown",
            )
            self.bot.register_next_step_handler(msg, self.process_edit_value)
        self.bot.answer_callback_query(call.id)

    def _ask_edit_payment(self, chat_id: int, user_id: int) -> None:
        """Show payment method inline buttons during edit."""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton(PAYMENT_PIX, callback_data="EDIT_PAY_PIX"),
            types.InlineKeyboardButton(PAYMENT_DINHEIRO, callback_data="EDIT_PAY_DINHEIRO"),
            types.InlineKeyboardButton(PAYMENT_CREDITO, callback_data="EDIT_PAY_CREDITO"),
        )
        self.state.update_user_state(user_id, "edit_field", "EDIT_PAYMENT")
        self.bot.send_message(chat_id, ADD_PAYMENT_PROMPT, reply_markup=keyboard)

    def _save_edit_payment(self, chat_id: int, user_id: int, payment_method: str) -> None:
        """Save payment method edit and finish."""
        expense_id = self.state.get_user_state(user_id).get("edit_expense_id")
        if not expense_id:
            return
        self.expense_service.update_expense(expense_id, payment_method=payment_method)
        self.send_success(chat_id, EDIT_SUCCESS)
        self.state.clear_user_state(user_id)

    def process_edit_value(self, message) -> None:
        """Process the new value for the field being edited."""
        user_id = message.from_user.id
        chat_id = message.chat.id
        new_value = self._get_text(message)

        if self.is_cancel_command(new_value):
            return self.handle_cancel(chat_id)

        user_state = self.state.get_user_state(user_id)
        field = user_state.get("edit_field")
        expense_id = user_state.get("edit_expense_id")

        if not field or not expense_id:
            self.send_error(chat_id, "❌ Erro: sessão de edição expirou.")
            return

        update_kwargs = {}

        if self.is_accept_command(new_value):
            expense = self.expense_service.get_expense_by_id(expense_id)
            if not expense:
                self.send_error(chat_id, "❌ Despesa não encontrada.")
                return
            if field == "EDIT_VALUE":
                update_kwargs["amount"] = expense.amount
            elif field == "EDIT_NAME":
                update_kwargs["name"] = expense.name
            elif field == "EDIT_DATE":
                update_kwargs["date"] = expense.date
            elif field == "EDIT_INSTALLMENTS":
                update_kwargs["installment"] = expense.installment
            elif field == "EDIT_CATEGORY":
                update_kwargs["category_id"] = expense.category_id
            elif field == "EDIT_PAYMENT":
                update_kwargs["payment_method"] = expense.payment_method
            if update_kwargs:
                try:
                    self.expense_service.update_expense(expense_id, **update_kwargs)
                    self.send_success(chat_id, EDIT_SUCCESS)
                except Exception as e:
                    self.send_error(chat_id, f"❌ Erro ao editar: {str(e)[:100]}")
                self.state.clear_user_state(user_id)
            return

        if field == "EDIT_VALUE":
            is_valid, val, err = self.validator.validate_value(new_value)
            if not is_valid:
                self.send_error(chat_id, ERROR_MESSAGES.get(err, "Valor inválido"))
                msg = self.bot.send_message(chat_id, "✏️ Digite o novo valor:")
                self.bot.register_next_step_handler(msg, self.process_edit_value)
                return
            update_kwargs["amount"] = val

        elif field == "EDIT_NAME":
            is_valid, err = self.validator.validate_name(new_value)
            if not is_valid:
                self.send_error(chat_id, ERROR_MESSAGES.get(err, "Nome inválido"))
                msg = self.bot.send_message(chat_id, "✏️ Digite o novo nome:")
                self.bot.register_next_step_handler(msg, self.process_edit_value)
                return
            update_kwargs["name"] = new_value

        elif field == "EDIT_DATE":
            date_pattern = re.compile(r'^\d{2}-\d{2}-\d{4}$')
            if not date_pattern.match(new_value):
                self.send_error(chat_id, "❌ Data inválida! Use DD-MM-YYYY.")
                msg = self.bot.send_message(chat_id, "✏️ Digite a nova data:")
                self.bot.register_next_step_handler(msg, self.process_edit_value)
                return
            update_kwargs["date"] = new_value

        elif field == "EDIT_INSTALLMENTS":
            is_valid, val, err = self.validator.validate_installments(new_value)
            if not is_valid:
                self.send_error(chat_id, ERROR_MESSAGES.get(err, "Parcelas inválidas"))
                msg = self.bot.send_message(chat_id, "✏️ Digite o número de parcelas:")
                self.bot.register_next_step_handler(msg, self.process_edit_value)
                return
            update_kwargs["installment"] = val

        elif field == "EDIT_CATEGORY":
            categories = self.expense_service.get_categories(user_id)
            found = None
            for cid, cname in categories:
                if cname.lower() == new_value.lower():
                    found = cid
                    break
            if found is None:
                found = self.expense_service.create_category(new_value, user_id)
            update_kwargs["category_id"] = found

        elif field == "EDIT_PAYMENT":
            pm = new_value.lower().strip()
            if pm not in ("pix", "dinheiro", "credito"):
                self.send_error(chat_id, "❌ Forma de pagamento inválida! Use: Pix, Dinheiro ou Crédito.")
                msg = self.bot.send_message(chat_id, "✏️ Digite a forma de pagamento:")
                self.bot.register_next_step_handler(msg, self.process_edit_value)
                return
            update_kwargs["payment_method"] = pm

        if update_kwargs:
            try:
                self.expense_service.update_expense(expense_id, **update_kwargs)
                self.send_success(chat_id, EDIT_SUCCESS)
            except Exception as e:
                self.send_error(chat_id, f"❌ Erro ao editar: {str(e)[:100]}")

        self.state.clear_user_state(user_id)