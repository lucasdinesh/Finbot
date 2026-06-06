"""
Local SQLite repository implementation for expenses.
"""
import contextlib
import logging
import sqlite3
from config import DATABASE, DEFAULT_CATEGORIES
from database import IExpenseRepository, Expenses

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LocalRepository(IExpenseRepository):
    """SQLite-based implementation of IExpenseRepository."""

    def __init__(self) -> None:
        self.db_path = DATABASE
        self.create_table()
        self._migrate()

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
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    user_id INTEGER,
                    UNIQUE(name, user_id)
                )"""
            )
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS budgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    category_id INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    UNIQUE(user_id, category_id, month, year)
                )"""
            )
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS savings_goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    target_amount REAL NOT NULL,
                    current_amount REAL NOT NULL DEFAULT 0,
                    deadline TEXT,
                    created_at TEXT DEFAULT (strftime('%d-%m-%Y', 'now'))
                )"""
            )
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS recurring_expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category_id INTEGER,
                    payment_method TEXT,
                    day_of_month INTEGER NOT NULL,
                    last_generated TEXT,
                    active INTEGER NOT NULL DEFAULT 1
                )"""
            )

    def _migrate(self) -> None:
        with self.connect() as cursor:
            cursor.execute("PRAGMA table_info(expenses)")
            existing = {row[1] for row in cursor.fetchall()}
            if 'category_id' not in existing:
                cursor.execute("ALTER TABLE expenses ADD COLUMN category_id INTEGER")
            if 'payment_method' not in existing:
                cursor.execute("ALTER TABLE expenses ADD COLUMN payment_method TEXT")
            if 'local_id' not in existing:
                cursor.execute("ALTER TABLE expenses ADD COLUMN local_id INTEGER DEFAULT 0")

            cursor.execute("PRAGMA table_info(categories)")
            cat_cols = {row[1] for row in cursor.fetchall()}
            if 'user_id' not in cat_cols:
                cursor.execute("ALTER TABLE categories ADD COLUMN user_id INTEGER")

            cursor.execute("SELECT COUNT(*) FROM categories WHERE user_id IS NULL")
            if cursor.fetchone()[0] == 0:
                cursor.executemany(
                    "INSERT INTO categories (name, user_id) VALUES (?, NULL)",
                    [(name,) for name in DEFAULT_CATEGORIES],
                )

    def _row_to_expense(self, row: tuple) -> Expenses:
        return Expenses(
            id=row[0],
            user_id=row[1],
            name=row[2],
            date=row[3],
            amount=row[4],
            installment=row[5],
            category_id=row[6] if len(row) > 6 else None,
            payment_method=row[7] if len(row) > 7 else None,
        )

    def get(self, id: int) -> Expenses:
        with self.connect() as cursor:
            cursor.execute("SELECT * FROM expenses WHERE id=?", (id,))
            expense = cursor.fetchone()
            if expense is None:
                raise ValueError(f"Expense with id {id} does not exist")
            return self._row_to_expense(expense)

    def get_all(self) -> list[Expenses]:
        with self.connect() as cursor:
            cursor.execute("SELECT * FROM expenses")
            return [self._row_to_expense(expense) for expense in cursor.fetchall()]

    def get_by_user(self, user_id: int) -> list[Expenses]:
        with self.connect() as cursor:
            cursor.execute("SELECT * FROM expenses WHERE user_id=?", (user_id,))
            return [self._row_to_expense(expense) for expense in cursor.fetchall()]

    def get_by_date_interval(self, start_date: str, end_date: str) -> list[Expenses]:
        with self.connect() as cursor:
            start = start_date[6:10] + '-' + start_date[3:5] + '-' + start_date[0:2]
            end = end_date[6:10] + '-' + end_date[3:5] + '-' + end_date[0:2]
            cursor.execute(
                "SELECT * FROM expenses WHERE substr(date, 7, 4) || '-' || substr(date, 4, 2) || '-' || substr(date, 1, 2) BETWEEN ? AND ?",
                (start, end),
            )
            return [self._row_to_expense(expense) for expense in cursor.fetchall()]

    def get_by_user_and_month(self, user_id: int, year: int, month: int) -> list[Expenses]:
        with self.connect() as cursor:
            logger.info("Fetching expenses for user_id=%d, year=%d, month=%02d", user_id, year, month)
            cursor.execute(
                "SELECT * FROM expenses WHERE user_id=? AND substr(date, 7, 4) || '-' || substr(date, 4, 2) = ?",
                (user_id, f"{year}-{month:02}"),
            )
            return [self._row_to_expense(expense) for expense in cursor.fetchall()]

    def get_by_user_and_local_id(self, user_id: int, local_id: int) -> Expenses:
        with self.connect() as cursor:
            cursor.execute("SELECT id, user_id, local_id, name, amount, installment, date, category_id, payment_method FROM expenses WHERE user_id = ? AND local_id = ?", (user_id, local_id))
            row = cursor.fetchone()
            if row is None:
                raise ValueError(f"Expense with user_id={user_id} and local_id={local_id} does not exist")
            return Expenses(id=row[0], user_id=row[1], local_id=row[2], name=row[3], amount=row[4], installment=row[5], date=row[6], category_id=row[7], payment_method=row[8])

    def get_total_by_month(self, user_id: int, year: int, month: int) -> float:
        with self.connect() as cursor:
            logger.info("Calculating total for user_id=%d, year=%d, month=%02d", user_id, year, month)
            cursor.execute(
                "SELECT SUM(amount) FROM expenses WHERE user_id=? AND substr(date, 7, 4) || '-' || substr(date, 4, 2) = ?",
                (user_id, f"{year}-{month:02}"),
            )
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0.0

    def search_by_name(self, user_id: int, query: str) -> list[Expenses]:
        with self.connect() as cursor:
            cursor.execute(
                "SELECT * FROM expenses WHERE user_id=? AND name LIKE ? ORDER BY substr(date, 7, 4) DESC, substr(date, 4, 2) DESC, substr(date, 1, 2) DESC",
                (user_id, f"%{query}%"),
            )
            return [self._row_to_expense(expense) for expense in cursor.fetchall()]

    def add(self, **kwargs: object) -> None:
        required = {"name", "amount", "installment", "user_id"}
        if not required.issubset(kwargs.keys()):
            raise ValueError(f"Must provide: {required}")

        name = kwargs["name"]
        amount = kwargs["amount"]
        installment = kwargs["installment"]
        user_id = kwargs["user_id"]
        date = kwargs.get("date")
        category_id = kwargs.get("category_id")
        payment_method = kwargs.get("payment_method")

        logger.info(
            "DB INSERT: name=%s, amount=%s, installment=%s, user_id=%s, date=%s, category_id=%s, payment_method=%s",
            name, amount, installment, user_id, date or "DEFAULT", category_id, payment_method,
        )
        with self.connect() as cursor:
            if date:
                cursor.execute(
                    "INSERT INTO expenses (name, amount, installment, user_id, date, category_id, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, amount, installment, user_id, date, category_id, payment_method),
                )
            else:
                cursor.execute(
                    "INSERT INTO expenses (name, amount, installment, user_id, category_id, payment_method) VALUES (?, ?, ?, ?, ?, ?)",
                    (name, amount, installment, user_id, category_id, payment_method),
                )
        logger.info("DB INSERT completed")

    def update(self, id: int, **kwargs: object) -> None:
        allowed = {"name", "amount", "installment", "date", "category_id", "payment_method"}
        update_fields = {k: v for k, v in kwargs.items() if k in allowed}

        if not update_fields:
            raise ValueError("Must provide at least one field to update")

        set_clause = ", ".join(f"{key}=?" for key in update_fields)
        values = list(update_fields.values()) + [id]

        logger.info("DB UPDATE: id=%d, fields=%s", id, update_fields)
        with self.connect() as cursor:
            cursor.execute(f"UPDATE expenses SET {set_clause} WHERE id=?", values)
        logger.info("DB UPDATE completed")

    def delete(self, id: int) -> None:
        logger.info("DB DELETE: id=%d", id)
        with self.connect() as cursor:
            cursor.execute("DELETE FROM expenses WHERE id=?", (id,))
        logger.info("DB DELETE completed")

    # --- Category ---

    def get_all_categories(self, user_id: int | None = None) -> list[tuple]:
        with self.connect() as cursor:
            if user_id is not None:
                cursor.execute(
                    "SELECT id, name FROM categories WHERE user_id IS NULL OR user_id = ? ORDER BY name",
                    (user_id,),
                )
            else:
                cursor.execute("SELECT id, name FROM categories WHERE user_id IS NULL ORDER BY name")
            return cursor.fetchall()

    def create_category(self, name: str, user_id: int | None = None) -> int:
        with self.connect() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO categories (name, user_id) VALUES (?, ?)",
                (name, user_id),
            )
            if user_id is not None:
                cursor.execute(
                    "SELECT id FROM categories WHERE name = ? AND user_id = ?",
                    (name, user_id),
                )
            else:
                cursor.execute(
                    "SELECT id FROM categories WHERE name = ? AND user_id IS NULL",
                    (name,),
                )
            return cursor.fetchone()[0]

    def get_category_total_for_month(self, user_id: int, category_id: int, month: int, year: int) -> float:
        with self.connect() as cursor:
            cursor.execute(
                "SELECT SUM(amount) FROM expenses WHERE user_id=? AND category_id=? AND substr(date, 7, 4) || '-' || substr(date, 4, 2) = ?",
                (user_id, category_id, f"{year}-{month:02}"),
            )
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0.0

    # --- Budget ---

    def set_budget(self, user_id: int, category_id: int, month: int, year: int, amount: float) -> None:
        with self.connect() as cursor:
            cursor.execute(
                """INSERT INTO budgets (user_id, category_id, month, year, amount)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, category_id, month, year) DO UPDATE SET amount=excluded.amount""",
                (user_id, category_id, month, year, amount),
            )

    def get_budgets_for_month(self, user_id: int, month: int, year: int) -> list[dict]:
        with self.connect() as cursor:
            cursor.execute(
                """SELECT b.id, b.category_id, c.name, b.amount
                   FROM budgets b
                   JOIN categories c ON c.id = b.category_id
                   WHERE b.user_id=? AND b.month=? AND b.year=?
                   ORDER BY c.name""",
                (user_id, month, year),
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "category_id": row[1],
                    "category_name": row[2],
                    "amount": row[3],
                })
            return results

    # --- Savings Goal ---

    def add_savings_goal(self, user_id: int, name: str, target_amount: float, deadline: str | None) -> int:
        with self.connect() as cursor:
            cursor.execute(
                "INSERT INTO savings_goals (user_id, name, target_amount, deadline) VALUES (?, ?, ?, ?)",
                (user_id, name, target_amount, deadline),
            )
            return cursor.lastrowid

    def get_savings_goals(self, user_id: int) -> list[dict]:
        with self.connect() as cursor:
            cursor.execute(
                "SELECT id, name, target_amount, current_amount, deadline, created_at FROM savings_goals WHERE user_id=? ORDER BY created_at DESC",
                (user_id,),
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "name": row[1],
                    "target_amount": row[2],
                    "current_amount": row[3],
                    "deadline": row[4],
                    "created_at": row[5],
                })
            return results

    def contribute_to_goal(self, goal_id: int, amount: float) -> None:
        with self.connect() as cursor:
            cursor.execute(
                "UPDATE savings_goals SET current_amount = current_amount + ? WHERE id=?",
                (amount, goal_id),
            )

    def delete_savings_goal(self, goal_id: int) -> None:
        with self.connect() as cursor:
            cursor.execute("DELETE FROM savings_goals WHERE id=?", (goal_id,))

    # --- Recurring Expense ---

    def add_recurring_expense(
        self, user_id: int, name: str, amount: float,
        category_id: int | None, payment_method: str | None,
        day_of_month: int,
    ) -> int:
        with self.connect() as cursor:
            cursor.execute(
                """INSERT INTO recurring_expenses (user_id, name, amount, category_id, payment_method, day_of_month)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_id, name, amount, category_id, payment_method, day_of_month),
            )
            return cursor.lastrowid

    def get_recurring_expenses(self, user_id: int) -> list[dict]:
        with self.connect() as cursor:
            cursor.execute(
                """SELECT id, name, amount, category_id, payment_method, day_of_month, last_generated, active
                   FROM recurring_expenses WHERE user_id=? ORDER BY name""",
                (user_id,),
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "name": row[1],
                    "amount": row[2],
                    "category_id": row[3],
                    "payment_method": row[4],
                    "day_of_month": row[5],
                    "last_generated": row[6],
                    "active": bool(row[7]),
                })
            return results

    def get_due_recurring_expenses(self) -> list[dict]:
        with self.connect() as cursor:
            cursor.execute(
                """SELECT id, user_id, name, amount, category_id, payment_method, day_of_month, last_generated
                   FROM recurring_expenses WHERE active=1""",
            )
            from datetime import datetime
            now = datetime.now()
            current_ym = f"{now.month:02d}-{now.year}"
            results = []
            for row in cursor.fetchall():
                last_gen = row[7]
                if last_gen is None or not last_gen.endswith(current_ym):
                    results.append({
                        "id": row[0],
                        "user_id": row[1],
                        "name": row[2],
                        "amount": row[3],
                        "category_id": row[4],
                        "payment_method": row[5],
                        "day_of_month": row[6],
                        "last_generated": row[7],
                    })
            return results

    def mark_recurring_generated(self, recurring_id: int, date: str) -> None:
        with self.connect() as cursor:
            cursor.execute(
                "UPDATE recurring_expenses SET last_generated=? WHERE id=?",
                (date, recurring_id),
            )

    def delete_recurring_expense(self, recurring_id: int) -> None:
        with self.connect() as cursor:
            cursor.execute("DELETE FROM recurring_expenses WHERE id=?", (recurring_id,))