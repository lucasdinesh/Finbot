from domain.models import (
    Category, Budget, SavingsGoal, RecurringExpense, ExpenseDetailWithInstallment
)
from database import Expenses


class TestCategory:
    def test_create_category(self):
        cat = Category(id=1, name="Alimentação")
        assert cat.id == 1
        assert cat.name == "Alimentação"

    def test_category_str(self):
        cat = Category(id=2, name="Transporte")
        assert str(cat) == "Category(id=2, name='Transporte')"


class TestBudget:
    def test_create_budget(self):
        budget = Budget(
            id=1, user_id=1, category_id=1, category_name="Alimentação",
            month=6, year=2026, amount=500.0
        )
        assert budget.id == 1
        assert budget.amount == 500.0
        assert budget.spent == 0.0

    def test_budget_with_spent(self):
        budget = Budget(
            id=2, user_id=1, category_id=2, category_name="Transporte",
            month=6, year=2026, amount=200.0, spent=150.0
        )
        assert budget.spent == 150.0


class TestSavingsGoal:
    def test_create_goal_with_deadline(self):
        goal = SavingsGoal(
            id=1, user_id=1, name="Viagem", target_amount=5000.0,
            current_amount=1000.0, deadline="31-12-2026", created_at="01-01-2026"
        )
        assert goal.name == "Viagem"
        assert goal.current_amount == 1000.0
        assert goal.deadline == "31-12-2026"

    def test_create_goal_without_deadline(self):
        goal = SavingsGoal(
            id=2, user_id=1, name="Reserva", target_amount=10000.0,
            current_amount=0.0, deadline=None, created_at="01-01-2026"
        )
        assert goal.deadline is None


class TestRecurringExpense:
    def test_create_recurring(self):
        rec = RecurringExpense(
            id=1, user_id=1, name="Netflix", amount=55.90,
            category_id=8, payment_method="credito",
            day_of_month=15, last_generated=None, active=True
        )
        assert rec.name == "Netflix"
        assert rec.day_of_month == 15
        assert rec.active is True

    def test_recurring_inactive(self):
        rec = RecurringExpense(
            id=2, user_id=1, name="Spotify", amount=34.90,
            category_id=None, payment_method="credito",
            day_of_month=10, last_generated="01-06-2026", active=False
        )
        assert rec.active is False
        assert rec.last_generated == "01-06-2026"


class TestExpenseDetailWithInstallment:
    def test_create_detail(self):
        expense = Expenses(
            id=1, user_id=1, name="Curso", date="10-04-2026",
            amount=300.00, installment=3, category_id=4,
            payment_method="credito", local_id=1
        )
        detail = ExpenseDetailWithInstallment(
            expense=expense,
            monthly_amount=100.0,
            current_installment=2,
            total_installments=3,
        )
        assert detail.expense.name == "Curso"
        assert detail.monthly_amount == 100.0
        assert detail.current_installment == 2
        assert detail.total_installments == 3

    def test_single_installment(self):
        expense = Expenses(
            id=2, user_id=1, name="Compra", date="01-06-2026",
            amount=50.0, installment=1, category_id=1,
            payment_method="pix", local_id=2
        )
        detail = ExpenseDetailWithInstallment(
            expense=expense,
            monthly_amount=50.0,
            current_installment=1,
            total_installments=1,
        )
        assert detail.monthly_amount == 50.0


class TestExpensesDataclass:
    def test_create_expense_all_fields(self):
        exp = Expenses(
            id=1, user_id=1, name="Teste", date="01-06-2026",
            amount=100.0, installment=1, category_id=1,
            payment_method="pix", local_id=1
        )
        assert exp.id == 1
        assert exp.name == "Teste"
        assert exp.amount == 100.0
        assert exp.date == "01-06-2026"

    def test_expense_minimal_fields(self):
        exp = Expenses(
            id=None, user_id=1, name="Teste", date="01-06-2026",
            amount=50.0, installment=1
        )
        assert exp.id is None
        assert exp.category_id is None
        assert exp.payment_method is None
        assert exp.local_id is None

    def test_database_import(self):
        from database import Expenses
        assert Expenses is not None


class TestExpensesComparison:
    def test_expenses_equality(self):
        e1 = Expenses(id=1, user_id=1, name="A", date="01-06-2026",
                      amount=10.0, installment=1)
        e2 = Expenses(id=1, user_id=1, name="A", date="01-06-2026",
                      amount=10.0, installment=1)
        assert e1 == e2
