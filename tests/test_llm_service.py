import json
import pytest
from services.llm_service import LlamaService


@pytest.fixture
def llm_service():
    return LlamaService(
        api_key="test-key",
        model="test-model",
        base_url="https://test.com/v1",
        enabled=False,
    )


class TestParseOutput:
    def test_parse_valid_json(self, llm_service):
        raw = '{"amount": 123.45, "date": "31-12-2024", "store_name": "Supermercado"}'
        result = llm_service._parse_output(raw)
        assert result is not None
        assert result["amount"] == 123.45
        assert result["date"] == "31-12-2024"
        assert result["store_name"] == "Supermercado"

    def test_parse_with_markdown_code_block(self, llm_service):
        raw = '```json\n{"amount": 99.90, "date": "15-06-2026", "store_name": "Farmácia"}\n```'
        result = llm_service._parse_output(raw)
        assert result is not None
        assert result["amount"] == 99.90
        assert result["store_name"] == "Farmácia"

    def test_parse_with_extra_text(self, llm_service):
        raw = 'Here is the result: {"amount": 50.0, "date": "01-01-2026", "store_name": "Loja"}'
        result = llm_service._parse_output(raw)
        assert result is not None
        assert result["amount"] == 50.0

    def test_parse_invalid_json(self, llm_service):
        raw = "this is not json"
        result = llm_service._parse_output(raw)
        assert result is None

    def test_parse_empty_string(self, llm_service):
        result = llm_service._parse_output("")
        assert result is None

    def test_parse_nao_especificado_store(self, llm_service):
        raw = '{"amount": 100.0, "date": "01-06-2026", "store_name": "Não especificado"}'
        result = llm_service._parse_output(raw)
        assert result is not None
        assert result["store_name"] == "Não especificado"
        assert result["amount"] == 100.0
        assert result["date"] == "01-06-2026"

    def test_parse_none_amount(self, llm_service):
        raw = '{"amount": 0.0, "date": "01-06-2026", "store_name": "Loja"}'
        result = llm_service._parse_output(raw)
        assert result is not None
        assert result["amount"] == 0.0

    def test_parse_missing_fields(self, llm_service):
        raw = '{"amount": 100.0}'
        result = llm_service._parse_output(raw)
        assert result is not None
        assert "date" not in result
        assert "store_name" not in result

    def test_parse_nested_unrelated(self, llm_service):
        raw = 'Some text {"amount": 200.0, "date": "20-05-2026", "store_name": "Posto"} trailing'
        result = llm_service._parse_output(raw)
        assert result is not None
        assert result["store_name"] == "Posto"

    def test_parse_no_json_brace_returns_none(self, llm_service):
        raw = "amount: 100, date: 01-06-2026"
        result = llm_service._parse_output(raw)
        assert result is None


class TestFixDateYear:
    def test_fix_current_year(self, llm_service):
        from datetime import datetime
        current_year = datetime.now().year
        result = {"amount": 100.0, "date": f"01-06-{current_year}", "store_name": "Teste"}
        fixed = llm_service._fix_date_year(result)
        assert fixed["date"] == f"01-06-{current_year}"

    def test_fix_old_year(self, llm_service):
        from datetime import datetime
        current_year = datetime.now().year
        result = {"amount": 100.0, "date": "01-06-2024", "store_name": "Teste"}
        fixed = llm_service._fix_date_year(result)
        assert fixed["date"] == f"01-06-{current_year}"

    def test_fix_no_date_key(self, llm_service):
        result = {"amount": 100.0, "store_name": "Teste"}
        fixed = llm_service._fix_date_year(result)
        assert "date" not in fixed

    def test_fix_none_date(self, llm_service):
        result = {"amount": 100.0, "date": None, "store_name": "Teste"}
        fixed = llm_service._fix_date_year(result)
        assert fixed["date"] is None

    def test_fix_empty_date(self, llm_service):
        result = {"amount": 100.0, "date": "", "store_name": "Teste"}
        fixed = llm_service._fix_date_year(result)
        assert fixed["date"] == ""


class TestTruncate:
    def test_truncate_long_text(self, llm_service):
        text = "A" * 5000
        truncated = llm_service._truncate(text)
        assert len(truncated) <= 3000

    def test_truncate_short_text(self, llm_service):
        text = "Short text"
        truncated = llm_service._truncate(text)
        assert truncated == "Short text"

    def test_truncate_empty_text(self, llm_service):
        truncated = llm_service._truncate("")
        assert truncated == ""


class TestDisabled:
    def test_disabled_returns_none(self):
        service = LlamaService(
            api_key="test", model="test", base_url="test", enabled=False
        )
        result = service.extract_receipt_fields("some text")
        assert result is None
