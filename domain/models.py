"""Domain models for financial tracking."""
from dataclasses import dataclass
from typing import Optional
from database import Expenses


@dataclass
class ExpenseDetailWithInstallment:
    """Expense with calculated installment details."""
    expense: Expenses
    monthly_amount: float  # Pro-rata amount for the current month
    current_installment: int  # Current installment number
    total_installments: int  # Total installments


@dataclass
class Category:
    id: int
    name: str


@dataclass
class Budget:
    id: int
    user_id: int
    category_id: int
    category_name: str
    month: int
    year: int
    amount: float
    spent: float = 0.0


@dataclass
class SavingsGoal:
    id: int
    user_id: int
    name: str
    target_amount: float
    current_amount: float
    deadline: Optional[str]
    created_at: str


@dataclass
class RecurringExpense:
    id: int
    user_id: int
    name: str
    amount: float
    category_id: Optional[int]
    payment_method: Optional[str]
    day_of_month: int
    last_generated: Optional[str]
    active: bool
