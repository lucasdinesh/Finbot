import pytest
from utils.validators import ExpenseValidator


class TestValidateValue:
    def test_valid_positive_integer(self):
        is_valid, value, error = ExpenseValidator.validate_value("150")
        assert is_valid is True
        assert value == 150.0
        assert error == ""

    def test_valid_positive_decimal(self):
        is_valid, value, error = ExpenseValidator.validate_value("99.90")
        assert is_valid is True
        assert value == 99.90
        assert error == ""

    def test_zero_rejected(self):
        is_valid, value, error = ExpenseValidator.validate_value("0")
        assert is_valid is False
        assert value == 0.0
        assert error == "VALUE_MUST_BE_POSITIVE"

    def test_negative_rejected(self):
        is_valid, value, error = ExpenseValidator.validate_value("-50")
        assert is_valid is False
        assert value == 0.0
        assert error == "VALUE_MUST_BE_POSITIVE"

    def test_empty_string_rejected(self):
        is_valid, value, error = ExpenseValidator.validate_value("")
        assert is_valid is False
        assert value == 0.0
        assert error == "VALUE_INVALID"

    def test_non_numeric_rejected(self):
        is_valid, value, error = ExpenseValidator.validate_value("abc")
        assert is_valid is False
        assert value == 0.0
        assert error == "VALUE_INVALID"

    def test_european_format_with_commas_rejected(self):
        is_valid, value, error = ExpenseValidator.validate_value("1.234,56")
        assert is_valid is False
        assert value == 0.0
        assert error == "VALUE_INVALID"

    def test_spaces_stripped(self):
        is_valid, value, error = ExpenseValidator.validate_value("  250  ")
        assert is_valid is True
        assert value == 250.0
        assert error == ""


class TestValidateName:
    def test_valid_name(self):
        is_valid, error = ExpenseValidator.validate_name("Supermercado")
        assert is_valid is True
        assert error == ""

    def test_valid_name_with_spaces(self):
        is_valid, error = ExpenseValidator.validate_name("Mercado Central")
        assert is_valid is True
        assert error == ""

    def test_valid_name_with_numbers(self):
        is_valid, error = ExpenseValidator.validate_name("Loja 1000")
        assert is_valid is True
        assert error == ""

    def test_valid_name_nao_especificado_allowed(self):
        is_valid, error = ExpenseValidator.validate_name("Não especificado")
        assert is_valid is True
        assert error == ""

    def test_valid_name_nao_especificado_lowercase_allowed(self):
        is_valid, error = ExpenseValidator.validate_name("não especificado")
        assert is_valid is True
        assert error == ""

    def test_empty_name_rejected(self):
        is_valid, error = ExpenseValidator.validate_name("")
        assert is_valid is False
        assert error == "NAME_EMPTY"

    def test_whitespace_only_rejected(self):
        is_valid, error = ExpenseValidator.validate_name("   ")
        assert is_valid is False
        assert error == "NAME_EMPTY"

    def test_name_too_long_rejected(self):
        is_valid, error = ExpenseValidator.validate_name("A" * 51)
        assert is_valid is False
        assert error == "NAME_TOO_LONG"

    def test_name_exactly_50_chars_accepted(self):
        is_valid, error = ExpenseValidator.validate_name("A" * 50)
        assert is_valid is True
        assert error == ""

    def test_special_chars_rejected(self):
        is_valid, error = ExpenseValidator.validate_name("Mercado@123!")
        assert is_valid is False
        assert error == "NAME_NOT_ALPHANUMERIC"

    def test_special_chars_with_dash_accepted(self):
        is_valid, error = ExpenseValidator.validate_name("Loja - Centro")
        assert is_valid is True
        assert error == ""


class TestValidateInstallments:
    def test_valid_installments(self):
        is_valid, value, error = ExpenseValidator.validate_installments("3")
        assert is_valid is True
        assert value == 3
        assert error == ""

    def test_single_installment(self):
        is_valid, value, error = ExpenseValidator.validate_installments("1")
        assert is_valid is True
        assert value == 1
        assert error == ""

    def test_max_installments(self):
        is_valid, value, error = ExpenseValidator.validate_installments("1000")
        assert is_valid is True
        assert value == 1000
        assert error == ""

    def test_zero_rejected(self):
        is_valid, value, error = ExpenseValidator.validate_installments("0")
        assert is_valid is False
        assert value == 0
        assert error == "INSTALLMENTS_INVALID"

    def test_negative_rejected(self):
        is_valid, value, error = ExpenseValidator.validate_installments("-1")
        assert is_valid is False
        assert value == 0
        assert error == "INSTALLMENTS_INVALID"

    def test_too_large_rejected(self):
        is_valid, value, error = ExpenseValidator.validate_installments("1001")
        assert is_valid is False
        assert value == 0
        assert error == "INSTALLMENTS_TOO_LARGE"

    def test_non_numeric_rejected(self):
        is_valid, value, error = ExpenseValidator.validate_installments("abc")
        assert is_valid is False
        assert value == 0
        assert error == "INSTALLMENTS_INVALID"

    def test_decimal_rejected(self):
        is_valid, value, error = ExpenseValidator.validate_installments("3.5")
        assert is_valid is False
        assert value == 0
        assert error == "INSTALLMENTS_INVALID"

    def test_whitespace_stripped(self):
        is_valid, value, error = ExpenseValidator.validate_installments("  6  ")
        assert is_valid is True
        assert value == 6
        assert error == ""
