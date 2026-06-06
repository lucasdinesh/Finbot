# Example Cloud Database Implementation (Firebase)
# This file is a template showing how to create a cloud-based repository implementation

from database import IExpenseRepository, Expenses
from typing import List, Optional
# from firebase_admin import db  # Uncomment when implementing
# import firebase_admin  # Uncomment when implementing


def _run_migration(conn, sql: str):
    """Run a migration SQL in its own transaction, ignoring errors."""
    import psycopg2
    try:
        conn.rollback()
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
        pass


class PostgresRepository(IExpenseRepository):
    """
    PostgreSQL implementation of IExpenseRepository.

    To use this:
    1. Install psycopg2: pip install psycopg2-binary
    2. Set DATABASE_URL environment variable with your connection string
       Format: postgresql://user:password@host/database
    """

    def __init__(self, connection_string: str = None):
        """Initialize PostgreSQL connection."""
        import os
        import psycopg2

        self.connection_string = connection_string or os.getenv('DATABASE_URL')
        if not self.connection_string:
            raise ValueError("DATABASE_URL not set. Provide connection string or set environment variable.")

        self.conn = psycopg2.connect(self.connection_string)
        self._create_table()

    def _create_table(self) -> None:
        """Create tables if they don't exist."""
        # Clear any aborted transaction from a prior failed connection
        self._reset_conn()

        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    local_id INTEGER NOT NULL DEFAULT 0,
                    name VARCHAR(255) NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    installment INTEGER NOT NULL,
                    date DATE NOT NULL,
                    category_id INTEGER,
                    payment_method VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, local_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    user_id BIGINT,
                    UNIQUE(name, user_id)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS budgets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    category_id INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    UNIQUE(user_id, category_id, month, year)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS savings_goals (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    target_amount DECIMAL(10, 2) NOT NULL,
                    current_amount DECIMAL(10, 2) NOT NULL DEFAULT 0,
                    deadline VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS recurring_expenses (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    category_id INTEGER,
                    payment_method VARCHAR(20),
                    day_of_month INTEGER NOT NULL,
                    last_generated VARCHAR(10),
                    active BOOLEAN NOT NULL DEFAULT TRUE
                )
            """)
            from config import DEFAULT_CATEGORIES
            cur.execute("SELECT COUNT(*) FROM categories WHERE user_id IS NULL")
            if cur.fetchone()[0] == 0:
                for name in DEFAULT_CATEGORIES:
                    cur.execute(
                        "INSERT INTO categories (name, user_id) VALUES (%s, NULL) ON CONFLICT DO NOTHING",
                        (name,),
                    )
            self.conn.commit()

        # Migrations — each in its own transaction to avoid aborted-transaction cascade
        _run_migration(self.conn, f"""
            ALTER TABLE expenses ALTER COLUMN user_id TYPE BIGINT
        """)
        _run_migration(self.conn, f"""
            ALTER TABLE categories ALTER COLUMN user_id TYPE BIGINT
        """)
        _run_migration(self.conn, f"""
            ALTER TABLE budgets ALTER COLUMN user_id TYPE BIGINT
        """)
        _run_migration(self.conn, f"""
            ALTER TABLE savings_goals ALTER COLUMN user_id TYPE BIGINT
        """)
        _run_migration(self.conn, f"""
            ALTER TABLE recurring_expenses ALTER COLUMN user_id TYPE BIGINT
        """)
        _run_migration(self.conn, """
            ALTER TABLE expenses ADD COLUMN IF NOT EXISTS local_id INTEGER
        """)
        # Add UNIQUE constraint; IF NOT NOT EXISTS not supported for constraints pre-PG13
        _run_migration(self.conn, """
            ALTER TABLE expenses ADD CONSTRAINT expenses_user_id_local_id UNIQUE (user_id, local_id)
        """)
        # Backfill local_id for existing rows that have NULL or 0
        _run_migration(self.conn, """
            UPDATE expenses e
            SET local_id = base.start_at + base.rn
            FROM (
                SELECT e2.id,
                       COALESCE(m.max_local, 0) AS start_at,
                       ROW_NUMBER() OVER (PARTITION BY e2.user_id ORDER BY e2.id, e2.date) AS rn
                FROM expenses e2
                LEFT JOIN (
                    SELECT user_id, MAX(local_id) AS max_local
                    FROM expenses WHERE local_id IS NOT NULL AND local_id > 0
                    GROUP BY user_id
                ) m ON m.user_id = e2.user_id
                WHERE e2.local_id IS NULL OR e2.local_id = 0
            ) base
            WHERE e.id = base.id AND (e.local_id IS NULL OR e.local_id = 0)
        """)

    def _reset_conn(self):
        """Rollback any aborted transaction so the connection is usable again."""
        try:
            self.conn.rollback()
        except Exception:
            pass

    def _row_to_expense(self, row):
        date_val = row[6]
        if hasattr(date_val, 'strftime'):
            date_val = date_val.strftime('%d-%m-%Y')
        return Expenses(id=row[0], user_id=row[1], local_id=row[2], name=row[3],
                        amount=row[4], installment=row[5], date=date_val,
                        category_id=row[7], payment_method=row[8])

    EXPENSE_COLS = "id, user_id, local_id, name, amount, installment, date, category_id, payment_method"

    def get(self, id: int) -> Expenses:
        """Get a single expense by ID."""
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT {self.EXPENSE_COLS} FROM expenses WHERE id = %s", (id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"Expense with id {id} does not exist")
            return self._row_to_expense(row)

    def get_all(self) -> List[Expenses]:
        """Get all expenses."""
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT {self.EXPENSE_COLS} FROM expenses ORDER BY date DESC")
            return [self._row_to_expense(row) for row in cur.fetchall()]

    def get_by_user(self, user_id: int) -> List[Expenses]:
        """Get all expenses for a specific user."""
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT {self.EXPENSE_COLS} FROM expenses WHERE user_id = %s ORDER BY date DESC",
                (user_id,))
            return [self._row_to_expense(row) for row in cur.fetchall()]

    def get_by_date_interval(self, start_date: str, end_date: str) -> List[Expenses]:
        """Get expenses within a date interval."""
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT {self.EXPENSE_COLS} FROM expenses WHERE date >= TO_DATE(%s, 'DD-MM-YYYY') AND date <= TO_DATE(%s, 'DD-MM-YYYY') ORDER BY date DESC",
                (start_date, end_date))
            return [self._row_to_expense(row) for row in cur.fetchall()]

    def get_by_user_and_month(self, user_id: int, year: int, month: int) -> List[Expenses]:
        """Get all expenses for a specific user in a given month."""
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT {self.EXPENSE_COLS} FROM expenses WHERE user_id = %s AND TO_CHAR(date, 'YYYY-MM') = %s ORDER BY date DESC",
                (user_id, f"{year}-{month:02}"))
            return [self._row_to_expense(row) for row in cur.fetchall()]

    def get_total_by_month(self, user_id: int, year: int, month: int) -> float:
        """Get total expense amount for a user in a given month."""
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT SUM(amount) FROM expenses WHERE user_id = %s AND TO_CHAR(date, 'YYYY-MM') = %s",
                (user_id, f"{year}-{month:02}"))
            result = cur.fetchone()
            return float(result[0]) if result[0] is not None else 0.0

    def add(self, **kwargs: object) -> None:
        """Add a new expense."""
        from datetime import datetime

        required_fields = {'name', 'amount', 'installment', 'user_id'}
        if not required_fields.issubset(kwargs.keys()):
            raise ValueError(f"Must provide: {required_fields}")

        raw_date = kwargs.get('date', datetime.now().strftime('%d-%m-%Y'))
        parts = raw_date.split('-')
        if len(parts) == 3 and len(parts[2]) == 4:
            iso_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
        else:
            iso_date = raw_date

        user_id = kwargs['user_id']

        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(local_id), 0) + 1 FROM expenses WHERE user_id = %s", (user_id,))
                next_local_id = cur.fetchone()[0]
                cur.execute(
                    """INSERT INTO expenses (user_id, local_id, name, amount, installment, date, category_id, payment_method)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (user_id, next_local_id, kwargs['name'], kwargs['amount'], kwargs['installment'], iso_date,
                     kwargs.get('category_id'), kwargs.get('payment_method'))
                )
                self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def update(self, id: int, **kwargs: object) -> None:
        """Update an expense."""
        update_fields = {}
        for key in ['name', 'amount', 'installment', 'date', 'category_id', 'payment_method']:
            if key not in kwargs:
                continue
            val = kwargs[key]
            if key == 'date' and isinstance(val, str):
                parts = val.split('-')
                if len(parts) == 3 and len(parts[2]) == 4:
                    val = f"{parts[2]}-{parts[1]}-{parts[0]}"
            update_fields[key] = val

        if not update_fields:
            raise ValueError("Must provide at least one field to update")

        set_clause = ", ".join([f"{key} = %s" for key in update_fields.keys()])
        values = list(update_fields.values()) + [id]

        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute(f"UPDATE expenses SET {set_clause} WHERE id = %s", values)
                self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def delete(self, id: int) -> None:
        """Delete an expense."""
        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM expenses WHERE id = %s", (id,))
                self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def search_by_name(self, user_id: int, query: str) -> list[Expenses]:
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT {self.EXPENSE_COLS} FROM expenses WHERE user_id = %s AND name ILIKE %s ORDER BY date DESC",
                (user_id, f"%{query}%"),
            )
            return [self._row_to_expense(row) for row in cur.fetchall()]

    def get_by_user_and_local_id(self, user_id: int, local_id: int) -> Expenses:
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                f"SELECT {self.EXPENSE_COLS} FROM expenses WHERE user_id = %s AND local_id = %s",
                (user_id, local_id),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"Expense with user_id={user_id} and local_id={local_id} does not exist")
            return self._row_to_expense(row)

    def get_all_categories(self, user_id: int | None = None) -> list[tuple]:
        self._reset_conn()
        with self.conn.cursor() as cur:
            if user_id is not None:
                cur.execute(
                    "SELECT id, name FROM categories WHERE user_id IS NULL OR user_id = %s ORDER BY name",
                    (user_id,),
                )
            else:
                cur.execute("SELECT id, name FROM categories WHERE user_id IS NULL ORDER BY name")
            return cur.fetchall()

    def create_category(self, name: str, user_id: int | None = None) -> int:
        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO categories (name, user_id) VALUES (%s, %s) ON CONFLICT (name, user_id) DO NOTHING RETURNING id",
                    (name, user_id),
                )
                row = cur.fetchone()
                self.conn.commit()
                if row:
                    return row[0]
                if user_id is not None:
                    cur.execute(
                        "SELECT id FROM categories WHERE name = %s AND user_id = %s",
                        (name, user_id),
                    )
                else:
                    cur.execute(
                        "SELECT id FROM categories WHERE name = %s AND user_id IS NULL",
                        (name,),
                    )
                return cur.fetchone()[0]
        except Exception:
            self.conn.rollback()
            raise

    def get_category_total_for_month(self, user_id: int, category_id: int, month: int, year: int) -> float:
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT SUM(amount) FROM expenses WHERE user_id = %s AND category_id = %s AND TO_CHAR(date, 'YYYY-MM') = %s",
                (user_id, category_id, f"{year}-{month:02}"),
            )
            result = cur.fetchone()
            return float(result[0]) if result[0] is not None else 0.0

    def set_budget(self, user_id: int, category_id: int, month: int, year: int, amount: float) -> None:
        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO budgets (user_id, category_id, month, year, amount)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (user_id, category_id, month, year) DO UPDATE SET amount = EXCLUDED.amount""",
                    (user_id, category_id, month, year, amount),
                )
                self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def get_budgets_for_month(self, user_id: int, month: int, year: int) -> list[dict]:
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                """SELECT b.id, b.category_id, c.name, b.amount
                   FROM budgets b
                   JOIN categories c ON c.id = b.category_id
                   WHERE b.user_id = %s AND b.month = %s AND b.year = %s
                   ORDER BY c.name""",
                (user_id, month, year),
            )
            return [
                {"id": r[0], "category_id": r[1], "category_name": r[2], "amount": r[3]}
                for r in cur.fetchall()
            ]

    def add_savings_goal(self, user_id: int, name: str, target_amount: float, deadline: str | None) -> int:
        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO savings_goals (user_id, name, target_amount, deadline) VALUES (%s, %s, %s, %s) RETURNING id",
                    (user_id, name, target_amount, deadline),
                )
                self.conn.commit()
                return cur.fetchone()[0]
        except Exception:
            self.conn.rollback()
            raise

    def get_savings_goals(self, user_id: int) -> list[dict]:
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, target_amount, current_amount, deadline, created_at FROM savings_goals WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            return [
                {"id": r[0], "name": r[1], "target_amount": r[2], "current_amount": r[3], "deadline": r[4], "created_at": r[5]}
                for r in cur.fetchall()
            ]

    def contribute_to_goal(self, goal_id: int, amount: float) -> None:
        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE savings_goals SET current_amount = current_amount + %s WHERE id = %s", (amount, goal_id))
                self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def delete_savings_goal(self, goal_id: int) -> None:
        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM savings_goals WHERE id = %s", (goal_id,))
                self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def add_recurring_expense(self, user_id: int, name: str, amount: float, category_id: int | None, payment_method: str | None, day_of_month: int) -> int:
        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO recurring_expenses (user_id, name, amount, category_id, payment_method, day_of_month) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                    (user_id, name, amount, category_id, payment_method, day_of_month),
                )
                self.conn.commit()
                return cur.fetchone()[0]
        except Exception:
            self.conn.rollback()
            raise

    def get_recurring_expenses(self, user_id: int) -> list[dict]:
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, name, amount, category_id, payment_method, day_of_month, last_generated, active FROM recurring_expenses WHERE user_id = %s ORDER BY name",
                (user_id,),
            )
            return [
                {"id": r[0], "name": r[1], "amount": r[2], "category_id": r[3], "payment_method": r[4], "day_of_month": r[5], "last_generated": r[6], "active": bool(r[7])}
                for r in cur.fetchall()
            ]

    def get_due_recurring_expenses(self) -> list[dict]:
        self._reset_conn()
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, amount, category_id, payment_method, day_of_month, last_generated FROM recurring_expenses WHERE active = TRUE",
            )
            from datetime import datetime
            now = datetime.now()
            current_ym = f"{now.month:02d}-{now.year}"
            results = []
            for row in cur.fetchall():
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
        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute("UPDATE recurring_expenses SET last_generated = %s WHERE id = %s", (date, recurring_id))
                self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def delete_recurring_expense(self, recurring_id: int) -> None:
        self._reset_conn()
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM recurring_expenses WHERE id = %s", (recurring_id,))
                self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise


# Option 4: Neon PostgreSQL
# from cloud_database import PostgresRepository
# ExpenseRepositorySingleton._instance = PostgresRepository("postgresql://user:password@host/database")
# Or use environment variable: ExpenseRepositorySingleton._instance = PostgresRepository()

