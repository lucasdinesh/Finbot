# Example Cloud Database Implementation (Firebase)
# This file is a template showing how to create a cloud-based repository implementation

from database import IExpenseRepository, Expenses
from typing import List, Optional
# from firebase_admin import db  # Uncomment when implementing
# import firebase_admin  # Uncomment when implementing


class NeonPostgresRepository(IExpenseRepository):
    """
    Neon.tech PostgreSQL implementation of IExpenseRepository.

    To use this:
    1. Create a Neon account at https://neon.tech
    2. Create a new project and database
    3. Install psycopg2: pip install psycopg2-binary
    4. Set DATABASE_URL environment variable with your Neon connection string
       Format: postgresql://user:password@host/database
    """

    def __init__(self, connection_string: str = None):
        """Initialize Neon PostgreSQL connection."""
        import os
        import psycopg2

        self.connection_string = connection_string or os.getenv('DATABASE_URL')
        if not self.connection_string:
            raise ValueError("DATABASE_URL not set. Provide connection string or set environment variable.")

        self.conn = psycopg2.connect(self.connection_string)
        self._create_table()

    def _create_table(self) -> None:
        """Create expenses table if it doesn't exist."""
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    installment INTEGER NOT NULL,
                    date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()

    def get(self, id: int) -> Expenses:
        """Get a single expense by ID."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, user_id, name, amount, installment, date FROM expenses WHERE id = %s", (id,))
            row = cur.fetchone()
            if row is None:
                raise ValueError(f"Expense with id {id} does not exist")
            return Expenses(id=row[0], user_id=row[1], name=row[2], amount=row[3], installment=row[4], date=row[5])

    def get_all(self) -> List[Expenses]:
        """Get all expenses."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT id, user_id, name, amount, installment, date FROM expenses ORDER BY date DESC")
            rows = cur.fetchall()
            return [Expenses(id=row[0], user_id=row[1], name=row[2], amount=row[3], installment=row[4], date=row[5]) for
                    row in rows]

    def get_by_user(self, user_id: int) -> List[Expenses]:
        """Get all expenses for a specific user."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, amount, installment, date FROM expenses WHERE user_id = %s ORDER BY date DESC",
                (user_id,))
            rows = cur.fetchall()
            return [Expenses(id=row[0], user_id=row[1], name=row[2], amount=row[3], installment=row[4], date=row[5]) for
                    row in rows]

    def get_by_date_interval(self, start_date: str, end_date: str) -> List[Expenses]:
        """Get expenses within a date interval."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, amount, installment, date FROM expenses WHERE date >= %s AND date <= %s ORDER BY date DESC",
                (start_date, end_date))
            rows = cur.fetchall()
            return [Expenses(id=row[0], user_id=row[1], name=row[2], amount=row[3], installment=row[4], date=row[5]) for
                    row in rows]

    def get_by_user_and_month(self, user_id: int, year: int, month: int) -> List[Expenses]:
        """Get all expenses for a specific user in a given month."""
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, amount, installment, date FROM expenses WHERE user_id = %s AND TO_CHAR(date, 'YYYY-MM') = %s ORDER BY date DESC",
                (user_id, f"{year}-{month:02}"))
            rows = cur.fetchall()
            return [Expenses(id=row[0], user_id=row[1], name=row[2], amount=row[3], installment=row[4], date=row[5]) for
                    row in rows]

    def get_total_by_month(self, user_id: int, year: int, month: int) -> float:
        """Get total expense amount for a user in a given month."""
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

        date = kwargs.get('date', datetime.now().strftime('%d-%m-%Y'))

        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO expenses (user_id, name, amount, installment, date) VALUES (%s, %s, %s, %s, %s)",
                (kwargs['user_id'], kwargs['name'], kwargs['amount'], kwargs['installment'], date)
            )
            self.conn.commit()

    def update(self, id: int, **kwargs: object) -> None:
        """Update an expense."""
        update_fields = {key: kwargs[key] for key in ['name', 'amount', 'installment', 'date'] if key in kwargs}

        if not update_fields:
            raise ValueError("Must provide at least one field to update")

        set_clause = ", ".join([f"{key} = %s" for key in update_fields.keys()])
        values = list(update_fields.values()) + [id]

        with self.conn.cursor() as cur:
            cur.execute(f"UPDATE expenses SET {set_clause} WHERE id = %s", values)
            self.conn.commit()

    def delete(self, id: int) -> None:
        """Delete an expense."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM expenses WHERE id = %s", (id,))
            self.conn.commit()

# Option 4: Neon PostgreSQL
# from cloud_database import NeonPostgresRepository
# ExpenseRepositorySingleton._instance = NeonPostgresRepository("postgresql://user:password@host/database")
# Or use environment variable: ExpenseRepositorySingleton._instance = NeonPostgresRepository()

