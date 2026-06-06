"""Business logic for expense operations."""
import logging
from typing import Optional, List
from datetime import datetime
from domain.models import Expenses
from database import IExpenseRepository
from utils.validators import ExpenseValidator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


_VALID_PAYMENT_METHODS = frozenset({"pix", "dinheiro", "credito"})


class ExpenseService:
    """Service layer for expense operations."""

    def __init__(self, repository: IExpenseRepository):
        self.repository = repository

    @staticmethod
    def _validate_date(date: str) -> None:
        try:
            datetime.strptime(date.strip(), "%d-%m-%Y")
        except ValueError:
            raise ValueError("DATE_NOT_SPECIFIED")

    @staticmethod
    def _validate_amount(amount: object) -> None:
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("VALUE_MUST_BE_POSITIVE")

    @staticmethod
    def _validate_name(name: str) -> None:
        is_valid, err = ExpenseValidator.validate_name(name)
        if not is_valid:
            raise ValueError(err)

    @staticmethod
    def _validate_installments(installments: object) -> None:
        if not isinstance(installments, int) or installments < 1 or installments > 1000:
            raise ValueError("INSTALLMENTS_INVALID")

    @staticmethod
    def _validate_payment_method(payment_method: object) -> None:
        if payment_method is not None:
            pm = str(payment_method).lower().strip()
            if pm not in _VALID_PAYMENT_METHODS:
                raise ValueError("PAYMENT_METHOD_INVALID")

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
        if date:
            self._validate_date(date)

        self._validate_amount(amount)
        self._validate_name(name)
        self._validate_installments(installments)
        self._validate_payment_method(payment_method)

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
        if "amount" in kwargs:
            self._validate_amount(kwargs["amount"])
        if "name" in kwargs:
            self._validate_name(kwargs["name"])
        if "installment" in kwargs:
            self._validate_installments(kwargs["installment"])
        if "date" in kwargs and kwargs["date"] is not None:
            self._validate_date(kwargs["date"])
        if "payment_method" in kwargs:
            self._validate_payment_method(kwargs["payment_method"])
        logger.info("update_expense(id=%d, kwargs=%s)", expense_id, kwargs)
        self.repository.update(expense_id, **kwargs)

    def get_categories(self, user_id: int | None = None) -> list[tuple]:
        return self.repository.get_all_categories(user_id)

    def create_category(self, name: str, user_id: int | None = None) -> int:
        if not name:
            raise ValueError("NAME_EMPTY")
        if len(name) > 100:
            raise ValueError("NAME_TOO_LONG")
        return self.repository.create_category(name, user_id)

    def get_category_total_for_month(self, user_id: int, category_id: int, month: int, year: int) -> float:
        return self.repository.get_category_total_for_month(user_id, category_id, month, year)

    def set_budget(self, user_id: int, category_id: int, month: int, year: int, amount: float) -> None:
        self._validate_amount(amount)
        self.repository.set_budget(user_id, category_id, month, year, amount)

    def get_budgets_for_month(self, user_id: int, month: int, year: int) -> list[dict]:
        return self.repository.get_budgets_for_month(user_id, month, year)

    def add_savings_goal(self, user_id: int, name: str, target_amount: float, deadline: str | None) -> int:
        if not name:
            raise ValueError("NAME_EMPTY")
        if len(name) > 100:
            raise ValueError("NAME_TOO_LONG")
        self._validate_amount(target_amount)
        if deadline is not None:
            self._validate_date(deadline)
        return self.repository.add_savings_goal(user_id, name, target_amount, deadline)

    def get_savings_goals(self, user_id: int) -> list[dict]:
        return self.repository.get_savings_goals(user_id)

    def contribute_to_goal(self, goal_id: int, amount: float) -> None:
        self._validate_amount(amount)
        self.repository.contribute_to_goal(goal_id, amount)

    def delete_savings_goal(self, goal_id: int) -> None:
        self.repository.delete_savings_goal(goal_id)

    def add_recurring_expense(self, user_id: int, name: str, amount: float,
                              category_id: int | None, payment_method: str | None,
                              day_of_month: int) -> int:
        if not name:
            raise ValueError("NAME_EMPTY")
        if len(name) > 100:
            raise ValueError("NAME_TOO_LONG")
        self._validate_amount(amount)
        if payment_method is not None:
            self._validate_payment_method(payment_method)
        if not isinstance(day_of_month, int) or day_of_month < 1 or day_of_month > 31:
            raise ValueError("DAY_INVALID")
        return self.repository.add_recurring_expense(user_id, name, amount, category_id, payment_method, day_of_month)

    def get_recurring_expenses(self, user_id: int) -> list[dict]:
        return self.repository.get_recurring_expenses(user_id)

    def get_due_recurring_expenses(self) -> list[dict]:
        return self.repository.get_due_recurring_expenses()

    def mark_recurring_generated(self, recurring_id: int, date: str) -> None:
        self.repository.mark_recurring_generated(recurring_id, date)

    def delete_recurring_expense(self, recurring_id: int) -> None:
        self.repository.delete_recurring_expense(recurring_id)
