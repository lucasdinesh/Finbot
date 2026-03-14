"""Report generation service."""
from reports import ReportGenerator, MonthlySummary, QuickReport
from database import IExpenseRepository


class ReportService:
    """Service layer for report operations."""

    def __init__(self, repository: IExpenseRepository):
        """
        Initialize report service.
        
        Args:
            repository: IExpenseRepository implementation
        """
        self.report_generator = ReportGenerator(repository)

    def get_monthly_summary(
        self, 
        user_id: int, 
        year: int, 
        month: int
    ) -> MonthlySummary:
        """
        Get monthly summary for a user.
        
        Args:
            user_id: User ID
            year: Year
            month: Month (1-12)
            
        Returns:
            MonthlySummary object
        """
        return self.report_generator.get_monthly_summary(user_id, year, month)

    def get_quick_report(self, user_id: int) -> QuickReport:
        """
        Get quick report comparing current and previous month.
        
        Args:
            user_id: User ID
            
        Returns:
            QuickReport object
        """
        return self.report_generator.get_quick_report(user_id)

    def format_monthly_summary(self, summary: MonthlySummary) -> str:
        """Format monthly summary as text."""
        return self.report_generator.format_monthly_summary(summary)

    def format_quick_report(self, report: QuickReport) -> str:
        """Format quick report as text."""
        return self.report_generator.format_quick_report(report)
