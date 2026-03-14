"""Domain models for financial tracking."""
from dataclasses import dataclass
from database import Expenses


@dataclass
class ExpenseDetailWithInstallment:
    """Expense with calculated installment details."""
    expense: Expenses
    monthly_amount: float  # Pro-rata amount for the current month
    current_installment: int  # Current installment number
    total_installments: int  # Total installments
