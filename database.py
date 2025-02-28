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


class Repository(Generic[T], ABC):  # Generic Repository class
    @abstractmethod
    def get(self, id: int) -> T:
        raise NotImplementedError

    @abstractmethod
    def get_all(self) -> list[T]:
        raise NotImplementedError

    @abstractmethod
    def add(self, **kwargs: object) -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, id: int, **kwargs: object) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, id: int) -> None:
        raise NotImplementedError


class ExpenseRepository(Repository[Expenses]):
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
            # user_id = 1287959334
            cursor.execute(
                "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                ("Refrigerator", 2000.00, 1, 1287959334),
            )
            cursor.execute(
                "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                ("Washing Machine", 1500.00, 2, 1287959334),
            )
            cursor.execute(
                "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                ("Microwave", 300.00, 3, 1287959334),
            )
            cursor.execute(
                "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                ("TV", 1000.00, 4, 1287959334),
            )
            cursor.execute(
                "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                ("Sofa", 2500.00, 5, 1287959334),
            )
            cursor.execute(
                "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                ("Bed", 1800.00, 6, 1287959334),
            )
            cursor.execute(
                "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                ("Dining Table", 1200.00, 7, 1287959334),
            )
            cursor.execute(
                "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                ("Air Conditioner", 3000.00, 8, 1287959334),
            )
            cursor.execute(
                "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                ("Laptop", 2500.00, 9, 1287959334),
            )
            cursor.execute(
                "INSERT INTO expenses (name, amount, installment, user_id) VALUES (?, ?, ?, ?)",
                ("Wardrobe", 2200.00, 10, 1287959334),
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
        if "content" in kwargs and "title" in kwargs:
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
