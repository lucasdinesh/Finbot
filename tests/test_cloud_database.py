"""Tests for cloud_database.py PostgresRepository."""
import sys
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

# Inject mock psycopg2 before cloud_database is imported
# (psycopg2 is imported inside __init__, not at module level)
mock_psycopg2 = MagicMock()
sys.modules['psycopg2'] = mock_psycopg2

from cloud_database import PostgresRepository
from database import Expenses


@pytest.fixture
def postgres_repo():
    """Create a PostgresRepository with mocked connection."""
    mock_conn = MagicMock()
    mock_psycopg2.connect.return_value = mock_conn
    repo = PostgresRepository("postgresql://test:test@localhost/test")
    return repo


class TestRowToExpense:
    """Test _row_to_expense date conversion."""

    def test_date_object_converts_to_dd_mm_yyyy(self, postgres_repo):
        row = (1, 12345, 1, "Test", 100.0, 1, date(2026, 6, 15), 1, "pix")
        expense = postgres_repo._row_to_expense(row)
        assert expense.date == "15-06-2026"
        assert expense.id == 1
        assert expense.name == "Test"
        assert expense.amount == 100.0

    def test_date_string_passes_through(self, postgres_repo):
        row = (1, 12345, 1, "Test", 100.0, 1, "15-06-2026", 1, "pix")
        expense = postgres_repo._row_to_expense(row)
        assert expense.date == "15-06-2026"

    def test_date_none_returns_none(self, postgres_repo):
        row = (1, 12345, 1, "Test", 100.0, 1, None, None, None)
        expense = postgres_repo._row_to_expense(row)
        assert expense.date is None
