import pytest
from state.conversation_manager import ConversationManager


class TestUserState:
    def test_set_and_get_user_state(self):
        manager = ConversationManager()
        manager.set_user_state(1, {"step": "awaiting_value", "valor": None})

        state = manager.get_user_state(1)
        assert state == {"step": "awaiting_value", "valor": None}

    def test_get_user_state_default(self):
        manager = ConversationManager()
        state = manager.get_user_state(999)
        assert state == {}

    def test_update_user_state(self):
        manager = ConversationManager()
        manager.set_user_state(1, {"step": "awaiting_value"})
        manager.update_user_state(1, "valor_despesa", "150.00")

        state = manager.get_user_state(1)
        assert state["step"] == "awaiting_value"
        assert state["valor_despesa"] == "150.00"

    def test_clear_user_state(self):
        manager = ConversationManager()
        manager.set_user_state(1, {"step": "done"})
        manager.clear_user_state(1)

        state = manager.get_user_state(1)
        assert state == {}

    def test_clear_user_state_nonexistent(self):
        manager = ConversationManager()
        manager.clear_user_state(999)
        state = manager.get_user_state(999)
        assert state == {}

    def test_multiple_users_independent(self):
        manager = ConversationManager()
        manager.set_user_state(1, {"step": "step1"})
        manager.set_user_state(2, {"step": "step2"})

        assert manager.get_user_state(1) == {"step": "step1"}
        assert manager.get_user_state(2) == {"step": "step2"}

    def test_update_creates_state_if_not_exists(self):
        manager = ConversationManager()
        manager.update_user_state(1, "key", "value")

        state = manager.get_user_state(1)
        assert state == {"key": "value"}


class TestDateSelectionState:
    def test_init_date_selection(self):
        manager = ConversationManager()
        manager.init_date_selection(100, 2026, 6)

        state = manager.get_date_selection_state(100)
        assert state["start_selected"] is False
        assert state["end_selected"] is False
        assert state["start_date"] is None
        assert state["end_date"] is None

    def test_init_date_selection_sets_shown_date(self):
        manager = ConversationManager()
        manager.init_date_selection(100, 2026, 6)
        assert manager.get_shown_date(100) == (2026, 6)

    def test_update_date_selection_state(self):
        manager = ConversationManager()
        manager.init_date_selection(100, 2026, 6)
        manager.update_date_selection_state(100, "start_date", "01-06-2026")

        state = manager.get_date_selection_state(100)
        assert state["start_date"] == "01-06-2026"

    def test_get_date_selection_default(self):
        manager = ConversationManager()
        state = manager.get_date_selection_state(999)
        assert state == {}

    def test_clear_date_selection(self):
        manager = ConversationManager()
        manager.init_date_selection(100, 2026, 6)
        manager.clear_date_selection(100)

        state = manager.get_date_selection_state(100)
        assert state == {}

    def test_shown_date(self):
        manager = ConversationManager()
        manager.set_shown_date(100, 2026, 6)

        shown = manager.get_shown_date(100)
        assert shown == (2026, 6)

    def test_shown_date_default(self):
        from datetime import datetime
        manager = ConversationManager()
        shown = manager.get_shown_date(999)
        assert shown == (datetime.now().year, datetime.now().month)

    def test_multiple_chats_independent(self):
        manager = ConversationManager()
        manager.init_date_selection(100, 2026, 6)
        manager.init_date_selection(200, 2025, 1)

        s1 = manager.get_date_selection_state(100)
        s2 = manager.get_date_selection_state(200)
        assert s1["end_selected"] is False
        assert s2["end_selected"] is False
        assert manager.get_shown_date(100) == (2026, 6)
        assert manager.get_shown_date(200) == (2025, 1)


class TestReceiptState:
    def test_set_and_get_receipt_state(self):
        manager = ConversationManager()
        data = {"step": "confirming", "parsed_data": {"amount": 150.0}}
        manager.set_receipt_state(1, data)

        state = manager.get_receipt_state(1)
        assert state == data

    def test_get_receipt_state_default(self):
        manager = ConversationManager()
        state = manager.get_receipt_state(999)
        assert state == {}

    def test_update_receipt_state(self):
        manager = ConversationManager()
        manager.set_receipt_state(1, {"step": "confirming", "parsed_data": {}})
        manager.update_receipt_state(1, "payment_method", "pix")

        state = manager.get_receipt_state(1)
        assert state["step"] == "confirming"
        assert state["payment_method"] == "pix"

    def test_update_receipt_state_with_nested(self):
        manager = ConversationManager()
        manager.set_receipt_state(1, {"step": "confirming", "parsed_data": {"amount": 100.0}})
        manager.update_receipt_state(1, "parsed_data", {
            **manager.get_receipt_state(1).get("parsed_data", {}),
            "store_name": "Supermercado",
        })

        state = manager.get_receipt_state(1)
        assert state["parsed_data"]["amount"] == 100.0
        assert state["parsed_data"]["store_name"] == "Supermercado"

    def test_clear_receipt_state(self):
        manager = ConversationManager()
        manager.set_receipt_state(1, {"step": "done"})
        manager.clear_receipt_state(1)

        state = manager.get_receipt_state(1)
        assert state == {}
