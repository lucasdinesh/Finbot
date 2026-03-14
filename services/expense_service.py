"""Business logic for expense operations."""
from typing import List
from domain.models import Expenses
from database import IExpenseRepository


class ExpenseService:
    """Service layer for expense operations."""

    def __init__(self, repository: IExpenseRepository):
        """
        Initialize expense service.
        
        Args:
            repository: IExpenseRepository implementation
        """
        self.repository = repository

    def create_expense(
        self, 
        user_id: int, 
        name: str, 
        amount: float, 
        installments: int
    ) -> None:
        """
        Create a new expense.
        
        Args:
            user_id: User ID
            name: Expense name
            amount: Total amount
            installments: Number of installments
        """
        self.repository.add(
            name=name,
            amount=str(amount),
            installment=str(installments),
            user_id=user_id
        )

    def get_user_expenses(self, user_id: int) -> List[Expenses]:
        """Get all expenses for a user."""
        return self.repository.get_by_user(user_id)

    def get_expenses_by_month(
        self, 
        user_id: int, 
        year: int, 
        month: int
    ) -> List[Expenses]:
        """Get expenses for a specific month."""
        return self.repository.get_by_user_and_month(user_id, year, month)

    def get_total_by_month(
        self, 
        user_id: int, 
        year: int, 
        month: int
    ) -> float:
        """Get total expenses for a month."""
        return self.repository.get_total_by_month(user_id, year, month)

    def get_expenses_by_date_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> List[Expenses]:
        """
        Get expenses within a date range.
        
        Args:
            start_date: Start date (DD-MM-YYYY format)
            end_date: End date (DD-MM-YYYY format)
        """
        return self.repository.get_by_date_interval(start_date, end_date)

    def get_expense_by_id(self, expense_id: int) -> Expenses:
        """Get a single expense by ID."""
        return self.repository.get(expense_id)

    def delete_expense(self, expense_id: int) -> None:
        """Delete an expense by ID."""
        self.repository.delete(expense_id)
