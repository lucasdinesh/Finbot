"""
Local SQLite repository implementation for expenses.
"""

import contextlib
import sqlite3
from config import DATABASE
from database import IExpenseRepository, Expenses


class LocalRepository(IExpenseRepository):
    """SQLite-based implementation of IExpenseRepository."""

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
            raise ValueError("Must provide name, amount, installment, and user_id")

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
