import contextlib
import sqlite3
from abc import abstractmethod, ABC
from dataclasses import dataclass
from config import DATABASE
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

class ExpenseRepository(IExpenseRepository):
    def __init__(self) -> None:
        self.db_path = DATABASE
        self.create_table()

    @contextlib.contextmanager
    def connect(self):
        with sqlite3.connect(self.db_path) as conn:
            yield conn.cursor()

    def create_table(self) -> None:
        with self.connect() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL, 
                    name TEXT NOT NULL, 
                    date TEXT NOT NULL DEFAULT (strftime('%d-%m-%Y', 'now')), 
                    amount REAL NOT NULL,
                    installment INTEGER
                )"""
            )
            user_id = 1287959334
            # cursor.execute(
            #     "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
            #     ("Refrigerator", 2000.00, 1, 1287959334),
            # )
            # cursor.execute(
            #     "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
            #     ("Washing Machine", 1500.00, 2, 1287959334),
            # )
            # cursor.execute(
            #     "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
            #     ("Microwave", 300.00, 3, 1287959334),
            # )
            # cursor.execute(
            #     "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
            #     ("TV", 1000.00, 4, 1287959334),
            # )
            # cursor.execute(
            #     "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
            #     ("Sofa", 2500.00, 5, 1287959334),
            # )
            # cursor.execute(
            #     "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
            #     ("Bed", 1800.00, 6, 1287959334),
            # )
            # cursor.execute(
            #     "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
            #     ("Dining Table", 1200.00, 7, 1287959334),
            # )
            # cursor.execute(
            #     "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
            #     ("Air Conditioner", 3000.00, 8, 1287959334),
            # )
            # cursor.execute(
            #     "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
            #     ("Laptop", 2500.00, 9, 1287959334),
            # )
            # cursor.execute(
            #     "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
            #     ("Wardrobe", 2200.00, 10, 1287959334),
            # )

    def get(self, id: int) -> Expenses:
        with self.connect() as cursor:
            cursor.execute("SELECT * FROM expenses WHERE id=?", (id,))
            expense = cursor.fetchone()
            if expense is None:
                raise ValueError(f"Expense with id {id} does not exist")
            return Expenses(*expense)

    def get_all(self) -> list[Expenses]:
        with self.connect() as cursor:
            cursor.execute("SELECT * FROM expenses")
            return [Expenses(*expense) for expense in cursor.fetchall()]

    def get_by_user(self, user_id: int) -> list[Expenses]:
        with self.connect() as cursor:
            cursor.execute("SELECT * FROM expenses WHERE user_id=?", (user_id,))
            return [Expenses(*expense) for expense in cursor.fetchall()]

    def get_by_date_interval(self, start_date: str, end_date: str) -> list[Expenses]:
        with self.connect() as cursor:
            cursor.execute("SELECT * FROM expenses WHERE date BETWEEN ? AND ?", (start_date, end_date))
            return [Expenses(*expense) for expense in cursor.fetchall()]

    def get_by_user_and_month(self, user_id: int, year: int, month: int) -> list[Expenses]:
        with self.connect() as cursor:
            print(f"Fetching expenses for user_id={user_id}, year={year}, month={month:02}")
            # Convert DD-MM-YYYY to YYYY-MM for comparison
            cursor.execute(
                "SELECT * FROM expenses WHERE user_id=? AND substr(date, 7, 4) || '-' || substr(date, 4, 2) = ?",
                (user_id, f"{year}-{month:02}"),
            )
            return [Expenses(*expense) for expense in cursor.fetchall()]

    def get_total_by_month(self, user_id: int, year: int, month: int) -> float:
        with self.connect() as cursor:
            print(f"Calculating total for user_id={user_id}, year={year}, month={month:02}")
            # Convert DD-MM-YYYY to YYYY-MM for comparison
            cursor.execute(
                "SELECT SUM(amount) FROM expenses WHERE user_id=? AND substr(date, 7, 4) || '-' || substr(date, 4, 2) = ?",
                (user_id, f"{year}-{month:02}"),
            )
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0.0

    def add(self, **kwargs: object) -> None:
        if "name" in kwargs and "amount" in kwargs and "installment" in kwargs and "user_id" in kwargs:
            with self.connect() as cursor:
                cursor.execute(
                    "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                    (kwargs["name"], kwargs["amount"], kwargs["installment"], kwargs["user_id"]),
                )
        else:
            raise ValueError("Must provide either name or amount")

    def update(self, id: int, **kwargs: object) -> None:
        if "name" in kwargs and "user_id" in kwargs:
            with self.connect() as cursor:
                cursor.execute(
                    "UPDATE expenses SET title=?, content=? WHERE id=?",
                    (kwargs["title"], kwargs["content"], id),
                )
        elif "content" in kwargs:
            with self.connect() as cursor:
                cursor.execute(
                    "UPDATE expenses SET content=? WHERE id=?", (kwargs["content"], id)
                )
        elif "title" in kwargs:
            with self.connect() as cursor:
                cursor.execute(
                    "UPDATE expenses SET title=? WHERE id=?", (kwargs["title"], id)
                )
        else:
            raise ValueError("Must provide either content or title")

    def delete(self, id: int) -> None:
        with self.connect() as cursor:
            cursor.execute("DELETE FROM expenses WHERE id=?", (id,))
