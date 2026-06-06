"""Business logic for expense operations."""
import logging
import unicodedata
from typing import Optional, List
from datetime import datetime
from domain.models import Expenses
from database import IExpenseRepository

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _normalize(text: str) -> str:
    return unicodedata.normalize('NFC', text.strip().lower())


class ExpenseService:
    """Service layer for expense operations."""

    def __init__(self, repository: IExpenseRepository):
        self.repository = repository

    def create_expense(
        self,
        user_id: int,
        name: str,
        amount: float,
        installments: int,
        date: str = None,
        category_id: int = None,
        payment_method: str = None,
    ) -> Optional[str]:
        if date and _normalize(date) == "não especificado":
            raise ValueError("DATE_NOT_SPECIFIED")

        logger.info(
            "Saving expense: user=%d, name=%s, amount=%.2f, installments=%d, date=%s, category_id=%s, payment_method=%s",
            user_id, name, amount, installments, date or "today", category_id, payment_method,
        )
        self.repository.add(
            name=name,
            amount=amount,
            installment=installments,
            user_id=user_id,
            date=date,
            category_id=category_id,
            payment_method=payment_method,
        )
        logger.info("Expense saved successfully")

        alert = self._check_budget_alert(user_id, category_id)
        return alert

    def _check_budget_alert(self, user_id: int, category_id: int | None) -> Optional[str]:
        if category_id is None:
            return None
        now = datetime.now()
        budgets = self.repository.get_budgets_for_month(user_id, now.month, now.year)
        for b in budgets:
            if b["category_id"] == category_id:
                total = self.repository.get_category_total_for_month(
                    user_id, category_id, now.month, now.year
                )
                if total > b["amount"]:
                    from messages import BUDGET_OVER
                    return BUDGET_OVER.format(total=total, budget=b["amount"], category=b["category_name"])
        return None

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

    def get_expense_by_user_and_local_id(self, user_id: int, local_id: int) -> Expenses:
        logger.info("get_expense_by_user_and_local_id(user=%d, local_id=%d)", user_id, local_id)
        return self.repository.get_by_user_and_local_id(user_id, local_id)

    def delete_expense(self, expense_id: int) -> None:
        logger.info("delete_expense(id=%d)", expense_id)
        self.repository.delete(expense_id)

    def search_expenses_by_name(self, user_id: int, query: str) -> list[Expenses]:
        logger.info("search_expenses_by_name(user=%d, query=%s)", user_id, query)
        return self.repository.search_by_name(user_id, query)

    def update_expense(self, expense_id: int, **kwargs) -> None:
        logger.info("update_expense(id=%d, kwargs=%s)", expense_id, kwargs)
        self.repository.update(expense_id, **kwargs)

    def get_categories(self, user_id: int | None = None) -> list[tuple]:
        return self.repository.get_all_categories(user_id)

    def create_category(self, name: str, user_id: int | None = None) -> int:
        return self.repository.create_category(name, user_id)

    def get_category_total_for_month(self, user_id: int, category_id: int, month: int, year: int) -> float:
        return self.repository.get_category_total_for_month(user_id, category_id, month, year)

    def set_budget(self, user_id: int, category_id: int, month: int, year: int, amount: float) -> None:
        self.repository.set_budget(user_id, category_id, month, year, amount)

    def get_budgets_for_month(self, user_id: int, month: int, year: int) -> list[dict]:
        return self.repository.get_budgets_for_month(user_id, month, year)

    def add_savings_goal(self, user_id: int, name: str, target_amount: float, deadline: str | None) -> int:
        return self.repository.add_savings_goal(user_id, name, target_amount, deadline)

    def get_savings_goals(self, user_id: int) -> list[dict]:
        return self.repository.get_savings_goals(user_id)

    def contribute_to_goal(self, goal_id: int, amount: float) -> None:
        self.repository.contribute_to_goal(goal_id, amount)

    def delete_savings_goal(self, goal_id: int) -> None:
        self.repository.delete_savings_goal(goal_id)

    def add_recurring_expense(self, user_id: int, name: str, amount: float,
                              category_id: int | None, payment_method: str | None,
                              day_of_month: int) -> int:
        return self.repository.add_recurring_expense(user_id, name, amount, category_id, payment_method, day_of_month)

    def get_recurring_expenses(self, user_id: int) -> list[dict]:
        return self.repository.get_recurring_expenses(user_id)

    def get_due_recurring_expenses(self) -> list[dict]:
        return self.repository.get_due_recurring_expenses()

    def mark_recurring_generated(self, recurring_id: int, date: str) -> None:
        self.repository.mark_recurring_generated(recurring_id, date)

    def delete_recurring_expense(self, recurring_id: int) -> None:
        self.repository.delete_recurring_expense(recurring_id)
