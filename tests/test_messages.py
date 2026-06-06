import messages as m


class TestWelcomeMessages:
    def test_welcome_message_format(self):
        msg = m.WELCOME_MESSAGE.format(first_name="João")
        assert "João" in msg

    def test_commands_header(self):
        assert "Comandos" in m.COMMANDS_HEADER


class TestAddExpenseMessages:
    def test_add_value_prompt(self):
        assert "valor" in m.ADD_VALUE_PROMPT.lower()

    def test_add_name_prompt(self):
        assert "nome" in m.ADD_NAME_PROMPT.lower()

    def test_add_date_invalid(self):
        assert "DD-MM-YYYY" in m.ADD_DATE_INVALID

    def test_add_success_format(self):
        msg = m.ADD_SUCCESS.format(
            name="Teste", value=100.0, date="01-06-2026", installments_line=""
        )
        assert "Teste" in msg
        assert "100" in msg

    def test_add_cancelled(self):
        assert "cancelada" in m.ADD_CANCELLED


class TestValidationMessages:
    def test_value_invalid(self):
        assert "valor" in m.VALUE_INVALID.lower()

    def test_value_must_be_positive(self):
        assert "maior que zero" in m.VALUE_MUST_BE_POSITIVE

    def test_name_empty(self):
        assert "vazio" in m.NAME_EMPTY

    def test_name_too_long(self):
        assert "50" in m.NAME_TOO_LONG

    def test_name_not_alphanumeric(self):
        assert "letras" in m.NAME_NOT_ALPHANUMERIC.lower()

    def test_installments_invalid(self):
        assert "parcelas" in m.INSTALLMENTS_INVALID.lower()

    def test_installments_too_large(self):
        assert "1000" in m.INSTALLMENTS_TOO_LARGE


class TestDateMessages:
    def test_date_not_specified(self):
        assert "Não especificado" in m.DATE_NOT_SPECIFIED


class TestPaymentMessages:
    def test_payment_prompt(self):
        assert "pagamento" in m.ADD_PAYMENT_PROMPT.lower()

    def test_payment_methods_defined(self):
        assert m.PAYMENT_PIX is not None
        assert m.PAYMENT_DINHEIRO is not None
        assert m.PAYMENT_CREDITO is not None


class TestCategoryMessages:
    def test_category_prompt(self):
        assert "categoria" in m.ADD_CATEGORY_PROMPT.lower()

    def test_category_other(self):
        assert m.CATEGORY_OTHER is not None


class TestSearchMessages:
    def test_search_prompt(self):
        assert "buscar" in m.SEARCH_PROMPT.lower()

    def test_search_no_results_format(self):
        msg = m.SEARCH_NO_RESULTS.format(query="teste")
        assert "teste" in msg


class TestEditMessages:
    def test_edit_success(self):
        assert "editada" in m.EDIT_SUCCESS

    def test_edit_cancelled(self):
        assert "cancelada" in m.EDIT_CANCELLED


class TestDeleteMessages:
    def test_delete_prompt(self):
        assert "ID" in m.DELETE_PROMPT

    def test_delete_success(self):
        assert "deletada" in m.DELETE_SUCCESS

    def test_delete_cancelled(self):
        assert "cancelada" in m.DELETE_CANCELLED


class TestBudgetMessages:
    def test_budget_over_format(self):
        msg = m.BUDGET_OVER.format(
            total=300.0, budget=200.0, category="Alimentação"
        )
        assert "300" in msg
        assert "200" in msg


class TestOcrMessages:
    def test_scan_confirm_format(self):
        msg = m.SCAN_CONFIRM.format(
            store_name="Supermercado", amount=150.0, date="01-06-2026"
        )
        assert "Supermercado" in msg
        assert "150" in msg


class TestMonthNames:
    def test_month_names_count(self):
        assert len(m.MONTH_NAMES) == 12

    def test_month_names_first(self):
        assert m.MONTH_NAMES[0] == "Janeiro"

    def test_month_names_last(self):
        assert m.MONTH_NAMES[11] == "Dezembro"


class TestCalendarNames:
    def test_calendar_months_pt(self):
        assert len(m.CALENDAR_MONTH_NAMES["pt"]) == 12

    def test_calendar_months_en(self):
        assert len(m.CALENDAR_MONTH_NAMES["en"]) == 12

    def test_calendar_weekdays_pt(self):
        assert len(m.CALENDAR_WEEKDAY_NAMES["pt"]) == 7

    def test_calendar_weekdays_en(self):
        assert len(m.CALENDAR_WEEKDAY_NAMES["en"]) == 7
