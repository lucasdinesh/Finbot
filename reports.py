"""
Report generation module for financial expenses.
Provides monthly summaries, quick reports, and expense analysis.
"""

from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
from database import Expenses, IExpenseRepository
from messages import MONTH_NAMES


@dataclass
class ExpenseDetailWithInstallment:
    """Data class for expense with installment details."""
    expense: Expenses
    monthly_amount: float  # Pro-rata amount for the current month
    current_installment: int  # Current installment number
    total_installments: int  # Total installments


@dataclass
class MonthlySummary:
    """Data class for monthly expense summary."""
    year: int
    month: int
    total_amount: float  # Total pro-rata amount for the month
    total_expenses: int
    expenses: List[Expenses]  # Original expenses list
    expenses_with_installments: List[ExpenseDetailWithInstallment]  # Enhanced with installment info
    top_expenses: List[tuple]  # List of (name, amount) tuples


@dataclass
class QuickReport:
    """Data class for quick expense report."""
    current_month_total: float
    current_month_expenses: int
    last_month_total: float
    last_month_expenses: int
    month_over_month_change: float  # Percentage change
    total_installments: int
    top_3_categories: List[tuple]  # List of (name, amount) tuples


class ReportGenerator:
    """Generate various financial reports from expense data."""

    def __init__(self, repository: IExpenseRepository):
        """
        Initialize report generator with a repository.

        Args:
            repository: IExpenseRepository instance for data access
        """
        self.repository = repository

    def _calculate_installment_info(self, expense: Expenses, target_year: int, target_month: int) -> tuple:
        """
        Calculate which installment we're on for a given target month.

        Args:
            expense: The expense object
            target_year: Target year
            target_month: Target month (1-12)

        Returns:
            Tuple of (monthly_amount, current_installment, total_installments)
        """
        # Parse expense date (format: DD-MM-YYYY)
        date_parts = expense.date.split('-')
        purchase_day = int(date_parts[0])
        purchase_month = int(date_parts[1])
        purchase_year = int(date_parts[2])

        # Calculate months elapsed since purchase
        months_elapsed = (target_year - purchase_year) * 12 + (target_month - purchase_month)

        # Calculate monthly pro-rata amount and round to 2 decimal places
        monthly_amount = round(float(expense.amount) / expense.installment, 2)

        # Calculate current installment number (1-indexed)
        current_installment = months_elapsed + 1

        # Clamp current installment to total installments
        current_installment = min(current_installment, expense.installment)
        current_installment = max(current_installment, 1)

        return monthly_amount, current_installment, expense.installment

    def get_monthly_summary(self, user_id: int, year: int, month: int) -> MonthlySummary:
        """
        Generate a comprehensive monthly summary for a user.

        Args:
            user_id: User ID
            year: Year (YYYY format)
            month: Month (1-12)

        Returns:
            MonthlySummary object with detailed expense information
        """
        expenses = self.repository.get_by_user_and_month(user_id, year, month)
        total_amount = self.repository.get_total_by_month(user_id, year, month)

        # Calculate installment details for each expense
        expenses_with_installments = []
        pro_rata_total = 0.0
        
        for expense in expenses:
            monthly_amount, current_installment, total_installments = self._calculate_installment_info(
                expense, year, month
            )
            expenses_with_installments.append(
                ExpenseDetailWithInstallment(
                    expense=expense,
                    monthly_amount=monthly_amount,
                    current_installment=current_installment,
                    total_installments=total_installments
                )
            )
            pro_rata_total += monthly_amount

        # Get top 5 expenses by pro-rata amount
        top_expenses = sorted(
            [(detail.expense.name, detail.monthly_amount) for detail in expenses_with_installments],
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return MonthlySummary(
            year=year,
            month=month,
            total_amount=pro_rata_total,
            total_expenses=len(expenses),
            expenses=expenses,
            expenses_with_installments=expenses_with_installments,
            top_expenses=top_expenses,
        )

    def get_quick_report(self, user_id: int) -> QuickReport:
        """
        Generate a quick report comparing current and previous month.

        Args:
            user_id: User ID

        Returns:
            QuickReport object with comparative analysis
        """
        now = datetime.now()
        current_month = now.month
        current_year = now.year

        # Get previous month
        if current_month == 1:
            prev_month = 12
            prev_year = current_year - 1
        else:
            prev_month = current_month - 1
            prev_year = current_year

        # Current month data
        current_total = self.repository.get_total_by_month(user_id, current_year, current_month)
        current_expenses = self.repository.get_by_user_and_month(user_id, current_year, current_month)
        current_count = len(current_expenses)

        # Previous month data
        prev_total = self.repository.get_total_by_month(user_id, prev_year, prev_month)
        prev_expenses = self.repository.get_by_user_and_month(user_id, prev_year, prev_month)
        prev_count = len(prev_expenses)

        # Calculate month-over-month change percentage
        if prev_total == 0:
            month_over_month_change = 0.0 if current_total == 0 else 100.0
        else:
            month_over_month_change = ((current_total - prev_total) / prev_total) * 100

        # Get top 3 categories (by total amount) from current month
        category_totals: Dict[str, float] = {}
        for expense in current_expenses:
            category_totals[expense.name] = category_totals.get(expense.name, 0.0) + float(expense.amount)

        top_3_categories = sorted(
            category_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # Total active installments across all expenses
        total_installments = sum(e.installment for e in current_expenses)

        return QuickReport(
            current_month_total=current_total,
            current_month_expenses=current_count,
            last_month_total=prev_total,
            last_month_expenses=prev_count,
            month_over_month_change=month_over_month_change,
            total_installments=total_installments,
            top_3_categories=top_3_categories,
        )

    def format_monthly_summary(self, summary: MonthlySummary) -> str:
        """
        Format monthly summary as readable text.

        Args:
            summary: MonthlySummary object

        Returns:
            Formatted string representation
        """
        from messages import MONTHLY_SUMMARY_HEADER, MONTHLY_SUMMARY_TOTAL, MONTHLY_SUMMARY_COUNT, MONTHLY_SUMMARY_TOP

        text = MONTHLY_SUMMARY_HEADER.format(month_name=MONTH_NAMES[summary.month - 1], year=summary.year)
        text += MONTHLY_SUMMARY_TOTAL.format(total=summary.total_amount)
        text += MONTHLY_SUMMARY_COUNT.format(count=summary.total_expenses)

        if summary.expenses_with_installments:
            text += f"\n{MONTHLY_SUMMARY_TOP}"
            for i, detail in enumerate(summary.expenses_with_installments[:5], 1):
                text += f"{i}. {detail.expense.name}\n"
                text += f"   💰 R${detail.monthly_amount:,.2f} | 📦 {detail.current_installment}/{detail.total_installments}\n"

        return text

    def format_quick_report(self, report: QuickReport) -> str:
        """
        Format quick report as readable text.

        Args:
            report: QuickReport object

        Returns:
            Formatted string representation
        """
        from messages import (QUICK_REPORT_HEADER, QUICK_REPORT_CURRENT_MONTH, QUICK_REPORT_CURRENT_TOTAL,
                            QUICK_REPORT_CURRENT_COUNT, QUICK_REPORT_LAST_MONTH, QUICK_REPORT_LAST_TOTAL,
                            QUICK_REPORT_LAST_COUNT, QUICK_REPORT_TREND_UP, QUICK_REPORT_TREND_DOWN,
                            QUICK_REPORT_TREND_EQUAL, QUICK_REPORT_TREND_LABEL, QUICK_REPORT_INSTALLMENTS,
                            QUICK_REPORT_TOP_3)
        
        now = datetime.now()
        current_month_name = MONTH_NAMES[now.month - 1]
        if now.month == 1:
            prev_month_name = MONTH_NAMES[11]
        else:
            prev_month_name = MONTH_NAMES[now.month - 2]

        text = QUICK_REPORT_HEADER
        text += QUICK_REPORT_CURRENT_MONTH.format(month_name=current_month_name)
        text += QUICK_REPORT_CURRENT_TOTAL.format(total=report.current_month_total)
        text += QUICK_REPORT_CURRENT_COUNT.format(count=report.current_month_expenses)

        text += QUICK_REPORT_LAST_MONTH.format(month_name=prev_month_name)
        text += QUICK_REPORT_LAST_TOTAL.format(total=report.last_month_total)
        text += QUICK_REPORT_LAST_COUNT.format(count=report.last_month_expenses)

        # Month-over-month change indicator
        if report.month_over_month_change > 0:
            trend = QUICK_REPORT_TREND_UP.format(percentage=report.month_over_month_change)
        elif report.month_over_month_change < 0:
            trend = QUICK_REPORT_TREND_DOWN.format(percentage=report.month_over_month_change)
        else:
            trend = QUICK_REPORT_TREND_EQUAL

        text += QUICK_REPORT_TREND_LABEL.format(trend=trend)
        text += QUICK_REPORT_INSTALLMENTS.format(count=report.total_installments)

        if report.top_3_categories:
            text += f"\n{QUICK_REPORT_TOP_3}"
            for i, (name, amount) in enumerate(report.top_3_categories, 1):
                text += f"{i}. {name}: R${amount:,.2f}\n"

        return text

    def format_expense_list(self, expenses: List[Expenses]) -> str:
        """
        Format a list of expenses as readable text.

        Args:
            expenses: List of Expenses objects

        Returns:
            Formatted string representation
        """
        if not expenses:
            return "Nenhuma despesa encontrada."

        text = "📋 *Despesas:*\n\n"
        for expense in expenses:
            text += f"• {expense.name}\n"
            text += f"  💵 R${float(expense.amount):,.2f} | "
            text += f"📅 {expense.date} | "
            text += f"📦 {expense.installment}x\n"

        return text


