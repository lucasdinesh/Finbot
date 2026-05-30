import contextlib
import sqlite3
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional

T = TypeVar('T')  # Define a generic type variable for Repository


@dataclass
class Expenses:
    id: Optional[int]
    user_id: int
    name: str
    date: str
    amount: float
    installment: int
    category_id: Optional[int] = None
    payment_method: Optional[str] = None


class IExpenseRepository(ABC):
    """Interface/Abstract base class for Expense Repository implementations.

    This abstraction layer allows for multiple implementations (SQLite, Cloud DB, etc.)
    without changing the business logic in main.py. Similar to Java interfaces.
    """

    @abstractmethod
    def get(self, id: int) -> Expenses:
        """Get a single expense by ID."""
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list[Expenses]:
        """Get all expenses."""
        raise NotImplementedError

    @abstractmethod
    def get_by_user(self, user_id: int) -> list[Expenses]:
        """Get all expenses for a specific user."""
        raise NotImplementedError

    @abstractmethod
    def get_by_date_interval(self, start_date: str, end_date: str) -> list[Expenses]:
        """Get expenses within a date interval (format: DD-MM-YYYY)."""
        raise NotImplementedError

    @abstractmethod
    def get_by_user_and_month(self, user_id: int, year: int, month: int) -> list[Expenses]:
        """Get all expenses for a specific user in a given month."""
        raise NotImplementedError

    @abstractmethod
    def get_total_by_month(self, user_id: int, year: int, month: int) -> float:
        """Get total expense amount for a user in a given month."""
        raise NotImplementedError

    @abstractmethod
    def add(self, **kwargs: object) -> None:
        """Add a new expense. Required kwargs: name, amount, installment, user_id."""
        raise NotImplementedError

    @abstractmethod
    def update(self, id: int, **kwargs: object) -> None:
        """Update an expense by ID."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, id: int) -> None:
        """Delete an expense by ID."""
        raise NotImplementedError

    @abstractmethod
    def search_by_name(self, user_id: int, query: str) -> list[Expenses]:
        """Search expenses by name (LIKE)."""
        raise NotImplementedError

    # --- Category ---

    @abstractmethod
    def get_all_categories(self, user_id: int | None = None) -> list[tuple]:
        """Return list of (id, name). If user_id given, includes global + user's custom."""
        raise NotImplementedError

    @abstractmethod
    def create_category(self, name: str, user_id: int | None = None) -> int:
        """Create a new category. user_id=None means global."""
        raise NotImplementedError

    @abstractmethod
    def get_category_total_for_month(self, user_id: int, category_id: int, month: int, year: int) -> float:
        """Sum of expenses in a category for a given month."""
        raise NotImplementedError

    # --- Budget ---

    @abstractmethod
    def set_budget(self, user_id: int, category_id: int, month: int, year: int, amount: float) -> None:
        """Upsert a monthly budget for a category."""
        raise NotImplementedError

    @abstractmethod
    def get_budgets_for_month(self, user_id: int, month: int, year: int) -> list[dict]:
        """Return list of {category_id, category_name, amount} for the month."""
        raise NotImplementedError

    # --- Savings Goal ---

    @abstractmethod
    def add_savings_goal(self, user_id: int, name: str, target_amount: float, deadline: str | None) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_savings_goals(self, user_id: int) -> list[dict]:
        """Return list of {id, name, target_amount, current_amount, deadline, created_at}."""
        raise NotImplementedError

    @abstractmethod
    def contribute_to_goal(self, goal_id: int, amount: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_savings_goal(self, goal_id: int) -> None:
        raise NotImplementedError

    # --- Recurring Expense ---

    @abstractmethod
    def add_recurring_expense(
        self, user_id: int, name: str, amount: float,
        category_id: int | None, payment_method: str | None,
        day_of_month: int,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    def get_recurring_expenses(self, user_id: int) -> list[dict]:
        """Return list of recurring expense dicts."""
        raise NotImplementedError

    @abstractmethod
    def get_due_recurring_expenses(self) -> list[dict]:
        """Return all active recurring expenses where last_generated < this month."""
        raise NotImplementedError

    @abstractmethod
    def mark_recurring_generated(self, recurring_id: int, date: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_recurring_expense(self, recurring_id: int) -> None:
        raise NotImplementedError
