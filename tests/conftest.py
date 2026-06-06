from collections import defaultdict
from unittest.mock import MagicMock, create_autospec
from typing import Optional, Any
import pytest

from database import IExpenseRepository, Expenses
from domain.models import Category, Budget, SavingsGoal, RecurringExpense


@pytest.fixture
def mock_repository() -> MagicMock:
    return create_autospec(IExpenseRepository, instance=True)


@pytest.fixture
def sample_expenses() -> list[Expenses]:
    return [
        Expenses(id=1, user_id=1, name="Supermercado", date="01-06-2026",
                 amount=150.50, installment=1, category_id=1,
                 payment_method="pix", local_id=1),
        Expenses(id=2, user_id=1, name="Gasolina", date="02-06-2026",
                 amount=80.00, installment=1, category_id=2,
                 payment_method="dinheiro", local_id=2),
        Expenses(id=3, user_id=2, name="Aluguel", date="05-06-2026",
                 amount=1200.00, installment=1, category_id=3,
                 payment_method="pix", local_id=1),
        Expenses(id=4, user_id=1, name="Curso", date="10-06-2026",
                 amount=300.00, installment=3, category_id=4,
                 payment_method="credito", local_id=3),
    ]


@pytest.fixture
def sample_categories() -> list[tuple[int, str]]:
    return [
        (1, "Alimentação"),
        (2, "Transporte"),
        (3, "Moradia"),
        (4, "Educação"),
    ]


@pytest.fixture
def sample_budgets() -> list[dict]:
    return [
        {"category_id": 1, "category_name": "Alimentação",
         "amount": 500.0, "month": 6, "year": 2026},
        {"category_id": 2, "category_name": "Transporte",
         "amount": 200.0, "month": 6, "year": 2026},
    ]


@pytest.fixture
def sample_savings_goals() -> list[dict]:
    return [
        {"id": 1, "user_id": 1, "name": "Viagem",
         "target_amount": 5000.0, "current_amount": 1200.0,
         "deadline": "31-12-2026", "created_at": "01-01-2026"},
        {"id": 2, "user_id": 1, "name": "Reserva",
         "target_amount": 10000.0, "current_amount": 0.0,
         "deadline": None, "created_at": "01-01-2026"},
    ]


@pytest.fixture
def sample_recurring_expenses() -> list[dict]:
    return [
        {"id": 1, "user_id": 1, "name": "Netflix",
         "amount": 55.90, "category_id": 8, "payment_method": "credito",
         "day_of_month": 15, "last_generated": None, "active": True},
        {"id": 2, "user_id": 1, "name": "Academia",
         "amount": 99.90, "category_id": None, "payment_method": "pix",
         "day_of_month": 5, "last_generated": "01-06-2026", "active": True},
    ]


@pytest.fixture
def state_data() -> dict:
    return {"step": "awaiting_value", "valor_despesa": None, "name_despesa": None}
