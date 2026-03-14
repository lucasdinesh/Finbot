"""Base handler with shared functionality."""
import telebot
from state.conversation_manager import ConversationManager
from messages import ADD_CANCELLED
import time


class BaseHandler:
    """Base class for all handlers with shared functionality."""

    def __init__(self, bot: telebot.TeleBot, state_manager: ConversationManager):
        """
        Initialize base handler.
        
        Args:
            bot: TeleBot instance
            state_manager: ConversationManager instance
        """
        self.bot = bot
        self.state = state_manager

    def _send_message_with_retry(self, chat_id: int, message: str, parse_mode: str = "Markdown", max_retries: int = 3) -> bool:
        """
        Send message with retry logic for network failures.
        
        Args:
            chat_id: Chat ID to send to
            message: Message text
            parse_mode: Markdown or HTML
            max_retries: Number of retries on timeout
            
        Returns:
            True if sent successfully, False if all retries failed
        """
        for attempt in range(max_retries):
            try:
                self.bot.send_message(chat_id, message, parse_mode=parse_mode)
                return True
            except (TimeoutError, ConnectionError) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    time.sleep(wait_time)
                else:
                    print(f"⚠️  Failed to send message after {max_retries} attempts: {type(e).__name__}")
                    return False
            except Exception as e:
                # For other errors, don't retry
                print(f"❌ Error sending message: {type(e).__name__}: {str(e)[:100]}")
                return False
        return False

    def send_error(self, chat_id: int, message: str) -> None:
        """Send error message to user."""
        self._send_message_with_retry(chat_id, message)

    def send_success(self, chat_id: int, message: str) -> None:
        """Send success message to user."""
        self._send_message_with_retry(chat_id, message)

    def send_info(self, chat_id: int, message: str) -> None:
        """Send informational message to user."""
        self._send_message_with_retry(chat_id, message)

    def send_warning(self, chat_id: int, message: str) -> None:
        """Send warning message to user."""
        self._send_message_with_retry(chat_id, message)

    def register_next_handler(self, message, handler, *args) -> None:
        """Register next step handler for multi-step conversations."""
        self.bot.register_next_step_handler(message, handler, *args)

    def is_cancel_command(self, text: str) -> bool:
        """Check if user wants to cancel."""
        return text.lower() == 'cancelar'

    def handle_cancel(self, chat_id: int) -> bool:
        """
        Handle cancel request.
        
        Returns:
            True if cancelled, False otherwise
        """
        self.send_error(chat_id, ADD_CANCELLED)
        return True
