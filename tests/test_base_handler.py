from unittest.mock import MagicMock
import pytest
from handlers.base_handler import BaseHandler
from state.conversation_manager import ConversationManager


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.send_message.return_value = MagicMock()
    return bot


@pytest.fixture
def state_manager():
    return ConversationManager()


@pytest.fixture
def handler(mock_bot, state_manager):
    return BaseHandler(mock_bot, state_manager)


class TestIsCancelCommand:
    def test_cancel_exact(self, handler):
        assert handler.is_cancel_command("cancelar") is True

    def test_cancel_upper(self, handler):
        assert handler.is_cancel_command("CANCELAR") is True

    def test_cancel_mixed_case(self, handler):
        assert handler.is_cancel_command("Cancelar") is True

    def test_cancel_not(self, handler):
        assert handler.is_cancel_command("continuar") is False

    def test_cancel_empty(self, handler):
        assert handler.is_cancel_command("") is False

    def test_cancel_partial(self, handler):
        assert handler.is_cancel_command("cancelar isso") is False


class TestIsAcceptCommand:
    def test_ok(self, handler):
        assert handler.is_accept_command("ok") is True

    def test_ok_upper(self, handler):
        assert handler.is_accept_command("OK") is True

    def test_okay(self, handler):
        assert handler.is_accept_command("okay") is True

    def test_sim(self, handler):
        assert handler.is_accept_command("sim") is True

    def test_s(self, handler):
        assert handler.is_accept_command("s") is True

    def test_keep(self, handler):
        assert handler.is_accept_command("keep") is True

    def test_accept_not(self, handler):
        assert handler.is_accept_command("nao") is False

    def test_accept_empty(self, handler):
        assert handler.is_accept_command("") is False

    def test_accept_with_whitespace(self, handler):
        assert handler.is_accept_command("  ok  ") is True


class TestSendMethods:
    def test_send_error(self, handler, mock_bot):
        handler.send_error(100, "Error message")
        mock_bot.send_message.assert_called_once_with(100, "Error message", parse_mode="Markdown")

    def test_send_success(self, handler, mock_bot):
        handler.send_success(200, "Success message")
        mock_bot.send_message.assert_called_once_with(200, "Success message", parse_mode="Markdown")

    def test_send_info(self, handler, mock_bot):
        handler.send_info(300, "Info message")
        mock_bot.send_message.assert_called_once_with(300, "Info message", parse_mode="Markdown")

    def test_send_warning(self, handler, mock_bot):
        handler.send_warning(400, "Warning message")
        mock_bot.send_message.assert_called_once_with(400, "Warning message", parse_mode="Markdown")

    def test_send_message_with_retry_success(self, handler, mock_bot):
        mock_bot.send_message.return_value = "sent"
        result = handler._send_message_with_retry(100, "Hello")
        assert result is True
        mock_bot.send_message.assert_called_once_with(100, "Hello", parse_mode="Markdown")

    def test_send_message_with_retry_failure(self, handler, mock_bot):
        mock_bot.send_message.side_effect = Exception("API Error")
        result = handler._send_message_with_retry(100, "Hello")
        assert result is False

    def test_send_message_with_retry_plain_text(self, handler, mock_bot):
        mock_bot.send_message.return_value = "sent"
        result = handler._send_message_with_retry(100, "Hello", parse_mode=None)
        assert result is True
        mock_bot.send_message.assert_called_once_with(100, "Hello", parse_mode=None)


class TestRegisterNextHandler:
    def test_register(self, handler, mock_bot):
        message = MagicMock()
        message.chat.id = 100
        fake_handler = MagicMock()
        handler.register_next_handler(message, fake_handler)
        mock_bot.register_next_step_handler.assert_called_once()
        args, _ = mock_bot.register_next_step_handler.call_args
        assert args[0] == message
        assert callable(args[1])

    def test_register_with_args(self, handler, mock_bot):
        message = MagicMock()
        message.chat.id = 100
        fake_handler = MagicMock()
        handler.register_next_handler(message, fake_handler, "arg1", "arg2")
        mock_bot.register_next_step_handler.assert_called_once()
        args, _ = mock_bot.register_next_step_handler.call_args
        assert args[0] == message
        assert callable(args[1])


class TestHandleCancel:
    def test_cancel_sends_message(self, handler, mock_bot):
        result = handler.handle_cancel(100)
        assert result is True
        mock_bot.send_message.assert_called_once()
