import pytest
from unittest.mock import MagicMock, call
from domain.models import Expenses
from services.expense_service import ExpenseService


class TestCreateExpense:
    def test_create_success(self, mock_repository, sample_expenses):
        mock_repository.add.return_value = None
        mock_repository.get_budgets_for_month.return_value = []
        service = ExpenseService(mock_repository)

        result = service.create_expense(
            user_id=1, name="Teste", amount=100.0,
            installments=1, date="01-06-2026",
            category_id=1, payment_method="pix"
        )

        assert result is None
        mock_repository.add.assert_called_once_with(
            name="Teste", amount=100.0, installment=1,
            user_id=1, date="01-06-2026",
            category_id=1, payment_method="pix"
        )

    def test_create_without_date_defaults_today(self, mock_repository):
        mock_repository.add.return_value = None
        mock_repository.get_budgets_for_month.return_value = []
        service = ExpenseService(mock_repository)

        service.create_expense(
            user_id=1, name="Teste", amount=50.0,
            installments=1, date=None,
            category_id=None, payment_method=None
        )

        mock_repository.add.assert_called_once()
        args, kwargs = mock_repository.add.call_args
        assert kwargs["date"] is None

    def test_create_with_name_nao_especificado_allowed(self, mock_repository):
        mock_repository.add.return_value = None
        mock_repository.get_budgets_for_month.return_value = []
        service = ExpenseService(mock_repository)

        result = service.create_expense(
            user_id=1, name="Não especificado", amount=50.0,
            installments=1, date="01-06-2026",
            category_id=None, payment_method="pix"
        )

        assert result is None
        mock_repository.add.assert_called_once()

    def test_create_with_date_nao_especificado_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="DATE_NOT_SPECIFIED"):
            service.create_expense(
                user_id=1, name="Teste", amount=50.0,
                installments=1, date="Não especificado",
                category_id=None, payment_method="pix"
            )

        mock_repository.add.assert_not_called()

    def test_create_with_date_nao_especificado_lowercase_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="DATE_NOT_SPECIFIED"):
            service.create_expense(
                user_id=1, name="Teste", amount=50.0,
                installments=1, date="não especificado",
                category_id=None, payment_method="pix"
            )

        mock_repository.add.assert_not_called()

    def test_create_triggers_budget_alert(self, mock_repository):
        mock_repository.add.return_value = None
        mock_repository.get_budgets_for_month.return_value = [
            {"category_id": 1, "category_name": "Alimentação",
             "amount": 200.0, "month": 6, "year": 2026}
        ]
        mock_repository.get_category_total_for_month.return_value = 250.0
        service = ExpenseService(mock_repository)

        result = service.create_expense(
            user_id=1, name="Teste", amount=100.0,
            installments=1, date="01-06-2026",
            category_id=1, payment_method="pix"
        )

        assert result is not None
        assert "Alimentação" in result

    def test_create_no_alert_when_within_budget(self, mock_repository):
        mock_repository.add.return_value = None
        mock_repository.get_budgets_for_month.return_value = [
            {"category_id": 1, "category_name": "Alimentação",
             "amount": 300.0, "month": 6, "year": 2026}
        ]
        mock_repository.get_category_total_for_month.return_value = 150.0
        service = ExpenseService(mock_repository)

        result = service.create_expense(
            user_id=1, name="Teste", amount=100.0,
            installments=1, date="01-06-2026",
            category_id=1, payment_method="pix"
        )

        assert result is None

    def test_create_no_alert_without_category(self, mock_repository):
        mock_repository.add.return_value = None
        service = ExpenseService(mock_repository)

        result = service.create_expense(
            user_id=1, name="Teste", amount=100.0,
            installments=1, date="01-06-2026",
            category_id=None, payment_method="pix"
        )

        assert result is None
        mock_repository.get_budgets_for_month.assert_not_called()

    # --- Amount validation ---

    def test_create_with_zero_amount_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.create_expense(
                user_id=1, name="Teste", amount=0.0,
                installments=1, date="01-06-2026",
                category_id=None, payment_method="pix"
            )

        mock_repository.add.assert_not_called()

    def test_create_with_negative_amount_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.create_expense(
                user_id=1, name="Teste", amount=-50.0,
                installments=1, date="01-06-2026",
                category_id=None, payment_method="pix"
            )

        mock_repository.add.assert_not_called()

    # --- Name validation ---

    def test_create_with_empty_name_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="NAME_EMPTY"):
            service.create_expense(
                user_id=1, name="", amount=50.0,
                installments=1, date="01-06-2026",
                category_id=None, payment_method="pix"
            )

        mock_repository.add.assert_not_called()

    def test_create_with_name_too_long_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="NAME_TOO_LONG"):
            service.create_expense(
                user_id=1, name="A" * 51, amount=50.0,
                installments=1, date="01-06-2026",
                category_id=None, payment_method="pix"
            )

        mock_repository.add.assert_not_called()

    # --- Installment validation ---

    def test_create_with_installment_zero_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="INSTALLMENTS_INVALID"):
            service.create_expense(
                user_id=1, name="Teste", amount=50.0,
                installments=0, date="01-06-2026",
                category_id=None, payment_method="pix"
            )

        mock_repository.add.assert_not_called()

    def test_create_with_installment_negative_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="INSTALLMENTS_INVALID"):
            service.create_expense(
                user_id=1, name="Teste", amount=50.0,
                installments=-1, date="01-06-2026",
                category_id=None, payment_method="pix"
            )

        mock_repository.add.assert_not_called()

    def test_create_with_installment_too_large_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="INSTALLMENTS_INVALID"):
            service.create_expense(
                user_id=1, name="Teste", amount=50.0,
                installments=1001, date="01-06-2026",
                category_id=None, payment_method="pix"
            )

        mock_repository.add.assert_not_called()

    # --- Payment method validation ---

    def test_create_with_invalid_payment_method_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="PAYMENT_METHOD_INVALID"):
            service.create_expense(
                user_id=1, name="Teste", amount=50.0,
                installments=1, date="01-06-2026",
                category_id=None, payment_method="boleto"
            )

        mock_repository.add.assert_not_called()


class TestGetUserExpenses:
    def test_get_user_expenses(self, mock_repository, sample_expenses):
        mock_repository.get_by_user.return_value = [e for e in sample_expenses if e.user_id == 1]
        service = ExpenseService(mock_repository)

        result = service.get_user_expenses(1)

        assert len(result) == 3
        mock_repository.get_by_user.assert_called_once_with(1)

    def test_get_user_expenses_empty(self, mock_repository):
        mock_repository.get_by_user.return_value = []
        service = ExpenseService(mock_repository)

        result = service.get_user_expenses(999)

        assert result == []


class TestGetExpensesByMonth:
    def test_get_by_month(self, mock_repository, sample_expenses):
        mock_repository.get_by_user_and_month.return_value = sample_expenses[:2]
        service = ExpenseService(mock_repository)

        result = service.get_expenses_by_month(1, 2026, 6)

        assert len(result) == 2
        mock_repository.get_by_user_and_month.assert_called_once_with(1, 2026, 6)


class TestGetTotalByMonth:
    def test_get_total(self, mock_repository):
        mock_repository.get_total_by_month.return_value = 530.50
        service = ExpenseService(mock_repository)

        result = service.get_total_by_month(1, 2026, 6)

        assert result == 530.50
        mock_repository.get_total_by_month.assert_called_once_with(1, 2026, 6)

    def test_get_total_no_expenses(self, mock_repository):
        mock_repository.get_total_by_month.return_value = 0.0
        service = ExpenseService(mock_repository)

        result = service.get_total_by_month(1, 2026, 6)

        assert result == 0.0


class TestGetExpensesByDateRange:
    def test_get_by_date_range(self, mock_repository, sample_expenses):
        mock_repository.get_by_date_interval.return_value = sample_expenses[:3]
        service = ExpenseService(mock_repository)

        result = service.get_expenses_by_date_range("01-06-2026", "30-06-2026")

        assert len(result) == 3
        mock_repository.get_by_date_interval.assert_called_once_with(
            "01-06-2026", "30-06-2026"
        )


class TestGetExpenseById:
    def test_get_by_id(self, mock_repository, sample_expenses):
        mock_repository.get.return_value = sample_expenses[0]
        service = ExpenseService(mock_repository)

        result = service.get_expense_by_id(1)

        assert result.name == "Supermercado"
        assert result.amount == 150.50
        mock_repository.get.assert_called_once_with(1)


class TestGetExpenseByUserAndLocalId:
    def test_get_by_user_and_local_id(self, mock_repository, sample_expenses):
        mock_repository.get_by_user_and_local_id.return_value = sample_expenses[0]
        service = ExpenseService(mock_repository)

        result = service.get_expense_by_user_and_local_id(1, 1)

        assert result is not None
        mock_repository.get_by_user_and_local_id.assert_called_once_with(1, 1)


class TestDeleteExpense:
    def test_delete(self, mock_repository):
        service = ExpenseService(mock_repository)

        service.delete_expense(1)

        mock_repository.delete.assert_called_once_with(1)


class TestSearchExpensesByName:
    def test_search_found(self, mock_repository, sample_expenses):
        mock_repository.search_by_name.return_value = [sample_expenses[1]]
        service = ExpenseService(mock_repository)

        result = service.search_expenses_by_name(1, "Gasolina")

        assert len(result) == 1
        assert result[0].name == "Gasolina"
        mock_repository.search_by_name.assert_called_once_with(1, "Gasolina")

    def test_search_not_found(self, mock_repository):
        mock_repository.search_by_name.return_value = []
        service = ExpenseService(mock_repository)

        result = service.search_expenses_by_name(1, "Inexistente")

        assert result == []


class TestUpdateExpense:
    def test_update(self, mock_repository):
        service = ExpenseService(mock_repository)

        service.update_expense(1, name="Novo Nome", amount=200.0)

        mock_repository.update.assert_called_once_with(1, name="Novo Nome", amount=200.0)

    def test_update_with_zero_amount_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.update_expense(1, amount=0.0)

        mock_repository.update.assert_not_called()

    def test_update_with_invalid_name_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="NAME_EMPTY"):
            service.update_expense(1, name="")

        mock_repository.update.assert_not_called()

    def test_update_with_invalid_date_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="DATE_NOT_SPECIFIED"):
            service.update_expense(1, date="invalida")

        mock_repository.update.assert_not_called()

    def test_update_with_invalid_payment_method_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="PAYMENT_METHOD_INVALID"):
            service.update_expense(1, payment_method="cheque")

        mock_repository.update.assert_not_called()


class TestCategories:
    def test_get_categories(self, mock_repository, sample_categories):
        mock_repository.get_all_categories.return_value = sample_categories
        service = ExpenseService(mock_repository)

        result = service.get_categories(1)

        assert len(result) == 4
        assert result[0] == (1, "Alimentação")
        mock_repository.get_all_categories.assert_called_once_with(1)

    def test_create_category(self, mock_repository):
        mock_repository.create_category.return_value = 10
        service = ExpenseService(mock_repository)

        result = service.create_category("Nova Categoria", 1)

        assert result == 10
        mock_repository.create_category.assert_called_once_with("Nova Categoria", 1)

    def test_create_category_empty_name_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="NAME_EMPTY"):
            service.create_category("", 1)

        mock_repository.create_category.assert_not_called()

    def test_create_category_name_too_long_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="NAME_TOO_LONG"):
            service.create_category("A" * 101, 1)

        mock_repository.create_category.assert_not_called()


class TestCategoryTotal:
    def test_get_category_total(self, mock_repository):
        mock_repository.get_category_total_for_month.return_value = 350.0
        service = ExpenseService(mock_repository)

        result = service.get_category_total_for_month(1, 1, 6, 2026)

        assert result == 350.0
        mock_repository.get_category_total_for_month.assert_called_once_with(1, 1, 6, 2026)


class TestBudgets:
    def test_set_budget(self, mock_repository):
        service = ExpenseService(mock_repository)

        service.set_budget(1, 1, 6, 2026, 500.0)

        mock_repository.set_budget.assert_called_once_with(1, 1, 6, 2026, 500.0)

    def test_set_budget_with_zero_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.set_budget(1, 1, 6, 2026, 0.0)

        mock_repository.set_budget.assert_not_called()

    def test_set_budget_with_negative_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.set_budget(1, 1, 6, 2026, -100.0)

        mock_repository.set_budget.assert_not_called()

    def test_get_budgets(self, mock_repository, sample_budgets):
        mock_repository.get_budgets_for_month.return_value = sample_budgets
        service = ExpenseService(mock_repository)

        result = service.get_budgets_for_month(1, 6, 2026)

        assert len(result) == 2
        mock_repository.get_budgets_for_month.assert_called_once_with(1, 6, 2026)


class TestSavingsGoals:
    def test_add_goal(self, mock_repository):
        mock_repository.add_savings_goal.return_value = 1
        service = ExpenseService(mock_repository)

        result = service.add_savings_goal(1, "Viagem", 5000.0, "31-12-2026")

        assert result == 1
        mock_repository.add_savings_goal.assert_called_once_with(
            1, "Viagem", 5000.0, "31-12-2026"
        )

    def test_get_goals(self, mock_repository, sample_savings_goals):
        mock_repository.get_savings_goals.return_value = sample_savings_goals
        service = ExpenseService(mock_repository)

        result = service.get_savings_goals(1)

        assert len(result) == 2
        mock_repository.get_savings_goals.assert_called_once_with(1)

    def test_add_goal_with_zero_target_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.add_savings_goal(1, "Viagem", 0.0, "31-12-2026")

        mock_repository.add_savings_goal.assert_not_called()

    def test_add_goal_with_negative_target_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.add_savings_goal(1, "Viagem", -100.0, "31-12-2026")

        mock_repository.add_savings_goal.assert_not_called()

    def test_add_goal_with_empty_name_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="NAME_EMPTY"):
            service.add_savings_goal(1, "", 5000.0, "31-12-2026")

        mock_repository.add_savings_goal.assert_not_called()

    def test_add_goal_with_invalid_deadline_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="DATE_NOT_SPECIFIED"):
            service.add_savings_goal(1, "Viagem", 5000.0, "invalida")

        mock_repository.add_savings_goal.assert_not_called()

    def test_add_goal_with_none_deadline_accepted(self, mock_repository):
        mock_repository.add_savings_goal.return_value = 1
        service = ExpenseService(mock_repository)

        result = service.add_savings_goal(1, "Viagem", 5000.0, None)

        assert result == 1
        mock_repository.add_savings_goal.assert_called_once_with(1, "Viagem", 5000.0, None)

    def test_contribute_to_goal(self, mock_repository):
        service = ExpenseService(mock_repository)

        service.contribute_to_goal(1, 500.0)

        mock_repository.contribute_to_goal.assert_called_once_with(1, 500.0)

    def test_contribute_to_goal_with_zero_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.contribute_to_goal(1, 0.0)

        mock_repository.contribute_to_goal.assert_not_called()

    def test_contribute_to_goal_with_negative_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.contribute_to_goal(1, -50.0)

        mock_repository.contribute_to_goal.assert_not_called()

    def test_delete_goal(self, mock_repository):
        service = ExpenseService(mock_repository)

        service.delete_savings_goal(1)

        mock_repository.delete_savings_goal.assert_called_once_with(1)


class TestRecurringExpenses:
    def test_add_recurring(self, mock_repository):
        mock_repository.add_recurring_expense.return_value = 1
        service = ExpenseService(mock_repository)

        result = service.add_recurring_expense(
            1, "Netflix", 55.90, 8, "credito", 15
        )

        assert result == 1
        mock_repository.add_recurring_expense.assert_called_once_with(
            1, "Netflix", 55.90, 8, "credito", 15
        )

    def test_add_recurring_with_zero_amount_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.add_recurring_expense(1, "Netflix", 0.0, 8, "credito", 15)

        mock_repository.add_recurring_expense.assert_not_called()

    def test_add_recurring_with_negative_amount_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="VALUE_MUST_BE_POSITIVE"):
            service.add_recurring_expense(1, "Netflix", -10.0, 8, "credito", 15)

        mock_repository.add_recurring_expense.assert_not_called()

    def test_add_recurring_with_empty_name_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="NAME_EMPTY"):
            service.add_recurring_expense(1, "", 55.90, 8, "credito", 15)

        mock_repository.add_recurring_expense.assert_not_called()

    def test_add_recurring_with_invalid_day_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="DAY_INVALID"):
            service.add_recurring_expense(1, "Netflix", 55.90, 8, "credito", 0)

        mock_repository.add_recurring_expense.assert_not_called()

    def test_add_recurring_with_day_too_large_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="DAY_INVALID"):
            service.add_recurring_expense(1, "Netflix", 55.90, 8, "credito", 32)

        mock_repository.add_recurring_expense.assert_not_called()

    def test_add_recurring_with_invalid_payment_method_rejected(self, mock_repository):
        service = ExpenseService(mock_repository)

        with pytest.raises(ValueError, match="PAYMENT_METHOD_INVALID"):
            service.add_recurring_expense(1, "Netflix", 55.90, 8, "boleto", 15)

        mock_repository.add_recurring_expense.assert_not_called()

    def test_get_recurring(self, mock_repository, sample_recurring_expenses):
        mock_repository.get_recurring_expenses.return_value = sample_recurring_expenses
        service = ExpenseService(mock_repository)

        result = service.get_recurring_expenses(1)

        assert len(result) == 2
        mock_repository.get_recurring_expenses.assert_called_once_with(1)

    def test_get_due_recurring(self, mock_repository, sample_recurring_expenses):
        mock_repository.get_due_recurring_expenses.return_value = [sample_recurring_expenses[0]]
        service = ExpenseService(mock_repository)

        result = service.get_due_recurring_expenses()

        assert len(result) == 1
        assert result[0]["name"] == "Netflix"
        mock_repository.get_due_recurring_expenses.assert_called_once()

    def test_mark_recurring_generated(self, mock_repository):
        service = ExpenseService(mock_repository)

        service.mark_recurring_generated(1, "01-06-2026")

        mock_repository.mark_recurring_generated.assert_called_once_with(1, "01-06-2026")

    def test_delete_recurring(self, mock_repository):
        service = ExpenseService(mock_repository)

        service.delete_recurring_expense(1)

        mock_repository.delete_recurring_expense.assert_called_once_with(1)
