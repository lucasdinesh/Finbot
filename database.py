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
