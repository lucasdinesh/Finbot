"""Handler for date selection commands."""
import json
from datetime import datetime
from handlers.base_handler import BaseHandler
import inline_calendar
from telebot import types
from config import MAX_DATE_INTERVAL
from messages import (
    DATE_SELECT_START, DATE_SELECT_END, DATE_START_SELECTED, DATE_END_SELECTED,
    DATE_ALREADY_SELECTED_START, DATE_ALREADY_SELECTED_END, 
    DATE_SELECTED_CONFIRMATION, DATE_INTERVAL_TOO_LARGE,
    DATE_RANGE_HEADER, DATE_RANGE_EXPENSE_FORMAT, DATE_RANGE_TOTAL, DATE_RANGE_NO_RESULTS
)


class DateHandler(BaseHandler):
    """Handles date selection and date-based queries."""

    def __init__(self, bot, state_manager):
        """
        Initialize date handler.
        
        Args:
            bot: TeleBot instance
            state_manager: ConversationManager
        """
        super().__init__(bot, state_manager)

    def handle_getbydate(self, message) -> None:
        """Handle /getbydate command - initiate date selection."""
        now = datetime.now()
        chat_id = message.chat.id
        
        # Initialize date selection state
        self.state.init_date_selection(chat_id, now.year, now.month)
        
        # Create calendar markups in Portuguese
        start_calendar_json = inline_calendar.create_calendar(now.year, now.month, prefix="START-", language="pt")
        end_calendar_json = inline_calendar.create_calendar(now.year, now.month, prefix="END-", language="pt")
        
        # Parse calendars
        start_markup = self._json_to_markup(start_calendar_json)
        end_markup = self._json_to_markup(end_calendar_json)
        
        # Send calendar selections
        self.bot.send_message(chat_id, DATE_SELECT_START, reply_markup=start_markup)
        self.bot.send_message(chat_id, DATE_SELECT_END, reply_markup=end_markup)

    def handle_day_selection(self, callback) -> None:
        """Handle day selection from calendar."""
        chat_id = callback.message.chat.id
        saved_date = self.state.get_shown_date(chat_id)
        date_state = self.state.get_date_selection_state(chat_id)
        
        # Extract day from callback data
        last_sep = callback.data.rfind(';') + 1
        
        # Determine calendar type (start or end)
        if "START-" in callback.data:
            calendar_type = "start"
            if date_state.get("start_selected"):
                self.bot.answer_callback_query(callback.id, text=DATE_ALREADY_SELECTED_START)
                return
        elif "END-" in callback.data:
            calendar_type = "end"
            if date_state.get("end_selected"):
                self.bot.answer_callback_query(callback.id, text=DATE_ALREADY_SELECTED_END)
                return
        else:
            return
        
        # Parse selected day and format date
        day = int(callback.data[last_sep:])
        selected_date = datetime(
            int(saved_date[0]), 
            int(saved_date[1]), 
            day, 0, 0, 0
        ).date().strftime("%d-%m-%Y")
        
        # Update state
        if calendar_type == "start":
            self.state.update_date_selection_state(chat_id, "start_date", selected_date)
            self.state.update_date_selection_state(chat_id, "start_selected", True)
            self.send_info(chat_id, DATE_START_SELECTED.format(date=selected_date))
        else:
            self.state.update_date_selection_state(chat_id, "end_date", selected_date)
            self.state.update_date_selection_state(chat_id, "end_selected", True)
            self.send_info(chat_id, DATE_END_SELECTED.format(date=selected_date))
        
        # Remove calendar
        self.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=None
        )
        
        self.bot.answer_callback_query(callback.id, text=DATE_SELECTED_CONFIRMATION)
        
        # Check if both dates are selected
        date_state = self.state.get_date_selection_state(chat_id)
        if date_state.get("start_selected") and date_state.get("end_selected"):
            self._process_date_range_query(callback.message, chat_id, date_state)

    def _process_date_range_query(self, message, chat_id: int, date_state: dict) -> None:
        """Process expense query for date range with validation."""
        try:
            start_date_str = date_state.get("start_date")
            end_date_str = date_state.get("end_date")
            
            # Parse dates
            start_date = datetime.strptime(start_date_str, "%d-%m-%Y")
            end_date = datetime.strptime(end_date_str, "%d-%m-%Y")
            
            # Validate interval (ensure start <= end)
            if start_date > end_date:
                start_date, end_date = end_date, start_date
                start_date_str, end_date_str = end_date_str, start_date_str
            
            # Check if interval exceeds max months
            months_diff = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
            
            if months_diff > MAX_DATE_INTERVAL:
                error_msg = DATE_INTERVAL_TOO_LARGE.format(max_months=MAX_DATE_INTERVAL)
                self.send_error(chat_id, error_msg)
                self.state.clear_date_selection(chat_id)
                return
            
            # Get expenses from service
            from main import ExpenseRepositorySingleton
            expense_repo = ExpenseRepositorySingleton.get_instance()
            expenses = expense_repo.get_by_date_interval(start_date_str, end_date_str)
            
            # Filter by user
            user_id = message.from_user.id
            user_expenses = [e for e in expenses if e.user_id == user_id]
            
            # Display results
            if not user_expenses:
                result_msg = DATE_RANGE_NO_RESULTS.format(
                    start_date=start_date_str,
                    end_date=end_date_str
                )
                self.send_info(chat_id, result_msg)
            else:
                header = DATE_RANGE_HEADER.format(
                    start_date=start_date_str,
                    end_date=end_date_str
                )
                total = sum(float(e.amount) for e in user_expenses)
                
                result_msg = header
                for expense in user_expenses:
                    result_msg += DATE_RANGE_EXPENSE_FORMAT.format(
                        name=expense.name,
                        amount=float(expense.amount),
                        date=expense.date,
                        installment=expense.installment
                    )
                result_msg += DATE_RANGE_TOTAL.format(total=total)
                
                self.send_info(chat_id, result_msg)
            
            # Clear date selection state
            self.state.clear_date_selection(chat_id)
        except Exception as e:
            self.send_error(chat_id, f"❌ Erro ao processar intervalo de datas: {str(e)}")
            self.state.clear_date_selection(chat_id)

    @staticmethod
    def _json_to_markup(calendar_json: str) -> types.InlineKeyboardMarkup:
        """Convert calendar JSON to InlineKeyboardMarkup."""
        markup = types.InlineKeyboardMarkup()
        keyboard = json.loads(calendar_json)['inline_keyboard']
        
        for row in keyboard:
            markup.row(*[
                types.InlineKeyboardButton(text=btn['text'], callback_data=btn['callback_data'])
                for btn in row
            ])
        
        return markup
