"""Handler for report-related commands."""
from datetime import datetime
from handlers.base_handler import BaseHandler
from services.report_service import ReportService
from messages import GET_ALL_EXPENSES_FORMAT


class ReportHandler(BaseHandler):
    """Handles report-related commands."""

    def __init__(self, bot, state_manager, report_service: ReportService):
        """
        Initialize report handler.
        
        Args:
            bot: TeleBot instance
            state_manager: ConversationManager
            report_service: ReportService for business logic
        """
        super().__init__(bot, state_manager)
        self.report_service = report_service

    def handle_monthly_summary(self, message) -> None:
        """Handle /monthlysummary command."""
        try:
            now = datetime.now()
            summary = self.report_service.get_monthly_summary(
                message.from_user.id,
                now.year,
                now.month
            )
            formatted_report = self.report_service.format_monthly_summary(summary)
            self.send_info(message.chat.id, formatted_report)
        except Exception as e:
            self.send_error(message.chat.id, f"❌ Error generating monthly summary: {str(e)}")

    def handle_quick_report(self, message) -> None:
        """Handle /quickreport command."""
        try:
            report = self.report_service.get_quick_report(message.from_user.id)
            formatted_report = self.report_service.format_quick_report(report)
            self.send_info(message.chat.id, formatted_report)
        except Exception as e:
            self.send_error(message.chat.id, f"❌ Error generating quick report: {str(e)}")

    def handle_get_all(self, message) -> None:
        """Handle /get command - list all expenses."""
        try:
            # Get all expenses from repository (delegate to service)
            # For now, we'll use the repository directly via bot context
            from main import ExpenseRepositorySingleton
            expense_repo = ExpenseRepositorySingleton.get_instance()
            expenses = expense_repo.get_all()
            
            for expense in expenses:
                msg = GET_ALL_EXPENSES_FORMAT.format(name=expense.name, amount=expense.amount)
                self.send_info(message.chat.id, msg)
        except Exception as e:
            self.send_error(message.chat.id, f"❌ Error retrieving expenses: {str(e)}")
