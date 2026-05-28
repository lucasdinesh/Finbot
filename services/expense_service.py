"""Business logic for expense operations."""
import logging
from typing import List
from domain.models import Expenses
from database import IExpenseRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
        installments: int,
        date: str = None,
    ) -> None:
        """
        Create a new expense.
        
        Args:
            user_id: User ID
            name: Expense name
            amount: Total amount
            installments: Number of installments
            date: Date in DD-MM-YYYY format (defaults to current date)
        """
        logger.info(
            "Saving expense: user=%d, name=%s, amount=%.2f, installments=%d, date=%s",
            user_id, name, amount, installments, date or "today",
        )
        self.repository.add(
            name=name,
            amount=str(amount),
            installment=str(installments),
            user_id=user_id,
            date=date,
        )
        logger.info("Expense saved successfully")

    def get_user_expenses(self, user_id: int) -> List[Expenses]:
        result = self.repository.get_by_user(user_id)
        logger.info("get_user_expenses(user=%d): %d expenses", user_id, len(result))
        return result

    def get_expenses_by_month(
        self, 
        user_id: int, 
        year: int, 
        month: int
    ) -> List[Expenses]:
        result = self.repository.get_by_user_and_month(user_id, year, month)
        logger.info("get_expenses_by_month(user=%d, %d-%02d): %d expenses",
                     user_id, year, month, len(result))
        return result

    def get_total_by_month(
        self, 
        user_id: int, 
        year: int, 
        month: int
    ) -> float:
        total = self.repository.get_total_by_month(user_id, year, month)
        logger.info("get_total_by_month(user=%d, %d-%02d): R$ %.2f",
                     user_id, year, month, total)
        return total

    def get_expenses_by_date_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> List[Expenses]:
        result = self.repository.get_by_date_interval(start_date, end_date)
        logger.info("get_expenses_by_date_range(%s to %s): %d expenses",
                     start_date, end_date, len(result))
        return result

    def get_expense_by_id(self, expense_id: int) -> Expenses:
        logger.info("get_expense_by_id(id=%d)", expense_id)
        return self.repository.get(expense_id)

    def delete_expense(self, expense_id: int) -> None:
        logger.info("delete_expense(id=%d)", expense_id)
        self.repository.delete(expense_id)
