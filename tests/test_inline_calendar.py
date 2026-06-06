import pytest
from inline_calendar import (
    create_callback_data,
    separate_callback_data,
    create_calendar,
)


class TestCreateCallbackData:
    def test_create_day_selection(self):
        data = create_callback_data("DAY", 2026, 6, 15)
        assert isinstance(data, str)
        assert data == "DAY;2026;6;15"

    def test_create_navigation(self):
        data = create_callback_data("MONTH", 2026, 6, 0)
        assert data == "MONTH;2026;6;0"

    def test_create_ignore(self):
        data = create_callback_data("IGNORE", 0, 0, 0)
        assert data == "IGNORE;0;0;0"


class TestSeparateCallbackData:
    def test_separate_day(self):
        result = separate_callback_data("DAY;2026;6;15")
        assert result == ["DAY", "2026", "6", "15"]

    def test_separate_month(self):
        result = separate_callback_data("MONTH;2026;6;0")
        assert result == ["MONTH", "2026", "6", "0"]

    def test_separate_ignore(self):
        result = separate_callback_data("IGNORE;0;0;0")
        assert result == ["IGNORE", "0", "0", "0"]

    def test_roundtrip(self):
        data = create_callback_data("DAY", 2026, 6, 15)
        parts = separate_callback_data(data)
        assert parts[0] == "DAY"
        assert parts[1] == "2026"
        assert parts[2] == "6"
        assert parts[3] == "15"


class TestCreateCalendar:
    def test_calendar_returns_json_string(self):
        result = create_calendar()
        assert isinstance(result, str)
        assert result.startswith("{")

    def test_calendar_contains_inline_keyboard(self):
        result = create_calendar()
        assert "inline_keyboard" in result

    def test_calendar_with_custom_year_month(self):
        result = create_calendar(year=2026, month=6)
        assert "2026" in result
        assert "June" in result or "Junho" in result

    def test_calendar_with_prefix(self):
        result = create_calendar(prefix="TEST")
        assert "TESTDAY" in result or "TESTIGNORE" in result

    def test_calendar_portuguese(self):
        result = create_calendar(year=2026, month=6, language="pt")
        assert "Junho" in result

    def test_calendar_english(self):
        result = create_calendar(year=2026, month=6, language="en")
        assert "June" in result

    def test_calendar_has_days(self):
        result = create_calendar(year=2026, month=6)
        assert '"1"' in result or '"1"' in result

    def test_calendar_default_month_is_current(self):
        from datetime import datetime
        now = datetime.now()
        result = create_calendar()
        assert str(now.year) in result

    def test_calendar_february_2024_leap(self):
        result = create_calendar(year=2024, month=2)
        assert '"29"' in result

    def test_calendar_february_2023_non_leap(self):
        result = create_calendar(year=2023, month=2)
        assert '"29"' not in result

    def test_calendar_has_navigation_buttons(self):
        result = create_calendar(year=2026, month=6)
        assert "<" in result
        assert ">" in result

    def test_calendar_has_weekday_headers(self):
        result = create_calendar(year=2026, month=6, language="en")
        assert "Mo" in result
        assert "Su" in result
