from unittest.mock import create_autospec
import pytest
from database import IExpenseRepository, Expenses
from services.report_service import ReportService
from reports import MonthlySummary, QuickReport


@pytest.fixture
def mock_repo():
    return create_autospec(IExpenseRepository, instance=True)


@pytest.fixture
def sample_expenses():
    return [
        Expenses(id=1, user_id=1, name="Supermercado", date="01-06-2026",
                 amount=150.50, installment=1, category_id=1,
                 payment_method="pix", local_id=1),
        Expenses(id=2, user_id=1, name="Gasolina", date="02-06-2026",
                 amount=80.00, installment=1, category_id=2,
                 payment_method="dinheiro", local_id=2),
    ]


@pytest.fixture
def sample_categories():
    return [
        (1, "Alimentação"),
        (2, "Transporte"),
    ]


class TestReportService:
    def test_get_monthly_summary(self, mock_repo, sample_expenses, sample_categories):
        mock_repo.get_by_user_and_month.return_value = sample_expenses
        mock_repo.get_all_categories.return_value = sample_categories
        service = ReportService(mock_repo)

        summary = service.get_monthly_summary(1, 2026, 6)

        assert isinstance(summary, MonthlySummary)
        assert summary.total_expenses == 2
        assert summary.total_amount == pytest.approx(230.50, 0.01)

    def test_get_monthly_summary_no_expenses(self, mock_repo):
        mock_repo.get_by_user_and_month.return_value = []
        mock_repo.get_all_categories.return_value = []
        service = ReportService(mock_repo)

        summary = service.get_monthly_summary(1, 2026, 6)

        assert summary.total_expenses == 0
        assert summary.total_amount == 0.0

    def test_get_quick_report(self, mock_repo, sample_expenses):
        from datetime import datetime
        mock_repo.get_by_user_and_month.side_effect = [sample_expenses, []]
        mock_repo.get_total_by_month.side_effect = [230.50, 0.0]
        mock_repo.get_all_categories.return_value = []
        service = ReportService(mock_repo)

        report = service.get_quick_report(1)

        assert isinstance(report, QuickReport)
        assert report.current_month_total == pytest.approx(230.50, 0.01)

    def test_format_monthly_summary(self, mock_repo, sample_expenses, sample_categories):
        mock_repo.get_by_user_and_month.return_value = sample_expenses
        mock_repo.get_all_categories.return_value = sample_categories
        service = ReportService(mock_repo)
        summary = service.get_monthly_summary(1, 2026, 6)

        output = service.format_monthly_summary(summary)

        assert isinstance(output, str)
        assert "Supermercado" in output

    def test_format_quick_report(self, mock_repo, sample_expenses):
        mock_repo.get_by_user_and_month.side_effect = [sample_expenses, []]
        mock_repo.get_total_by_month.side_effect = [230.50, 0.0]
        mock_repo.get_all_categories.return_value = []
        service = ReportService(mock_repo)
        report = service.get_quick_report(1)

        output = service.format_quick_report(report)

        assert isinstance(output, str)
