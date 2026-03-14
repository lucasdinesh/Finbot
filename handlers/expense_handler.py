"""Handler for expense-related commands."""
from handlers.base_handler import BaseHandler
from services.expense_service import ExpenseService
from utils.validators import ExpenseValidator
from messages import (
    ADD_VALUE_PROMPT, ADD_NAME_PROMPT, ADD_INSTALLMENTS_PROMPT, ADD_SUCCESS,
    VALUE_INVALID, VALUE_MUST_BE_POSITIVE, NAME_EMPTY, NAME_TOO_LONG,
    NAME_NOT_ALPHANUMERIC, INSTALLMENTS_INVALID, INSTALLMENTS_TOO_LARGE,
    DELETE_PROMPT, DELETE_ID_INVALID, DELETE_NOT_FOUND,
    DELETE_CONFIRM_PROMPT, DELETE_SUCCESS, DELETE_CANCELLED
)

# Map error keys to message constants
ERROR_MESSAGES = {
    "VALUE_INVALID": VALUE_INVALID,
    "VALUE_MUST_BE_POSITIVE": VALUE_MUST_BE_POSITIVE,
    "NAME_EMPTY": NAME_EMPTY,
    "NAME_TOO_LONG": NAME_TOO_LONG,
    "NAME_NOT_ALPHANUMERIC": NAME_NOT_ALPHANUMERIC,
    "INSTALLMENTS_INVALID": INSTALLMENTS_INVALID,
    "INSTALLMENTS_TOO_LARGE": INSTALLMENTS_TOO_LARGE,
}


class ExpenseHandler(BaseHandler):
    """Handles expense-related commands and conversations."""

    def __init__(self, bot, state_manager, expense_service: ExpenseService):
        """
        Initialize expense handler.
        
        Args:
            bot: TeleBot instance
            state_manager: ConversationManager
            expense_service: ExpenseService for business logic
        """
        super().__init__(bot, state_manager)
        self.expense_service = expense_service
        self.validator = ExpenseValidator()

    def handle_add_command(self, message) -> None:
        """Handle /add command - start of expense creation flow."""
        self.send_info(message.chat.id, ADD_VALUE_PROMPT)
        self.register_next_handler(message, self.process_value)

    def process_value(self, message) -> None:
        """Step 2: Validate and process expense value."""
        valor_str = message.text.strip()
        
        # Check for cancel
        if self.is_cancel_command(valor_str):
            return self.handle_cancel(message.chat.id)
        
        # Validate value
        is_valid, value, error_key = self.validator.validate_value(valor_str)
        if not is_valid:
            error_msg = ERROR_MESSAGES.get(error_key, "Invalid input")
            self.send_error(message.chat.id, error_msg)
            self.register_next_handler(message, self.process_value)
            return
        
        # Save value and ask for name
        self.state.update_user_state(message.from_user.id, "valor_despesa", str(value))
        self.send_info(message.chat.id, ADD_NAME_PROMPT)
        self.register_next_handler(message, self.process_name)

    def process_name(self, message) -> None:
        """Step 3: Validate and process expense name."""
        name = message.text.strip()
        
        # Check for cancel
        if self.is_cancel_command(name):
            return self.handle_cancel(message.chat.id)
        
        # Validate name
        is_valid, error_key = self.validator.validate_name(name)
        if not is_valid:
            error_msg = ERROR_MESSAGES.get(error_key, "Invalid input")
            self.send_error(message.chat.id, error_msg)
            self.register_next_handler(message, self.process_name)
            return
        
        # Save name and ask for installments
        self.state.update_user_state(message.from_user.id, "name_despesa", name)
        self.send_info(message.chat.id, ADD_INSTALLMENTS_PROMPT)
        self.register_next_handler(message, self.process_installments)

    def process_installments(self, message) -> None:
        """Step 4: Validate and process installment count, then save to repository."""
        parcelas_str = message.text.strip()
        
        # Check for cancel
        if self.is_cancel_command(parcelas_str):
            return self.handle_cancel(message.chat.id)
        
        # Validate installments
        is_valid, parcelas, error_key = self.validator.validate_installments(parcelas_str)
        if not is_valid:
            error_msg = ERROR_MESSAGES.get(error_key, "Invalid input")
            self.send_error(message.chat.id, error_msg)
            self.register_next_handler(message, self.process_installments)
            return
        
        # Get saved data and create expense
        user_state = self.state.get_user_state(message.from_user.id)
        valor_despesa = float(user_state.get("valor_despesa", 0))
        name_despesa = user_state.get("name_despesa", "")
        
        # Save to repository
        self.expense_service.create_expense(
            user_id=message.from_user.id,
            name=name_despesa,
            amount=valor_despesa,
            installments=parcelas
        )
        
        # Clear state
        self.state.clear_user_state(message.from_user.id)
        
        # Confirmation message
        success_msg = ADD_SUCCESS.format(
            name=name_despesa,
            value=valor_despesa,
            installments=parcelas
        )
        self.send_success(message.chat.id, success_msg)

    def handle_delete_command(self, message) -> None:
        """Handle /delete command - start of expense deletion flow."""
        self.send_info(message.chat.id, DELETE_PROMPT)
        self.register_next_handler(message, self.process_delete_id)

    def process_delete_id(self, message) -> None:
        """Step 1: Get and validate expense ID for deletion."""
        expense_id_str = message.text.strip()
        
        # Check for cancel
        if self.is_cancel_command(expense_id_str):
            return self.handle_cancel(message.chat.id)
        
        # Validate ID is a number
        try:
            expense_id = int(expense_id_str)
            if expense_id <= 0:
                self.send_error(message.chat.id, DELETE_ID_INVALID)
                self.register_next_handler(message, self.process_delete_id)
                return
        except ValueError:
            self.send_error(message.chat.id, DELETE_ID_INVALID)
            self.register_next_handler(message, self.process_delete_id)
            return
        
        # Fetch the expense
        try:
            expense = self.expense_service.get_expense_by_id(expense_id)
            if not expense or expense.user_id != message.from_user.id:
                self.send_error(message.chat.id, DELETE_NOT_FOUND.format(id=expense_id))
                self.register_next_handler(message, self.process_delete_id)
                return
        except Exception:
            self.send_error(message.chat.id, DELETE_NOT_FOUND.format(id=expense_id))
            self.register_next_handler(message, self.process_delete_id)
            return
        
        # Save expense to state
        self.state.update_user_state(message.from_user.id, "delete_expense_id", expense_id)
        self.state.update_user_state(message.from_user.id, "delete_expense", expense)
        
        # Ask for confirmation
        confirm_msg = DELETE_CONFIRM_PROMPT.format(
            name=expense.name,
            amount=expense.amount,
            installments=expense.installment
        )
        self.send_info(message.chat.id, confirm_msg)
        self.register_next_handler(message, self.process_delete_confirmation)

    def process_delete_confirmation(self, message) -> None:
        """Step 2: Process deletion confirmation."""
        confirmation = message.text.strip().lower()
        
        # Check for cancel
        if self.is_cancel_command(confirmation):
            return self.handle_cancel(message.chat.id)
        
        if confirmation in ['sim', 'yes', 's', 'y']:
            # Get saved expense ID
            user_state = self.state.get_user_state(message.from_user.id)
            expense_id = user_state.get("delete_expense_id")
            
            if expense_id:
                try:
                    # Delete the expense
                    self.expense_service.delete_expense(expense_id)
                    self.send_success(message.chat.id, DELETE_SUCCESS)
                except Exception as e:
                    self.send_error(message.chat.id, f"❌ Erro ao deletar despesa: {str(e)}")
            
            # Clear state
            self.state.clear_user_state(message.from_user.id)
        elif confirmation in ['não', 'no', 'n']:
            self.send_info(message.chat.id, DELETE_CANCELLED)
            self.state.clear_user_state(message.from_user.id)
        else:
            self.send_error(message.chat.id, "❌ Resposta inválida. Por favor, responda 'sim' ou 'não'.")
            self.register_next_handler(message, self.process_delete_confirmation)

