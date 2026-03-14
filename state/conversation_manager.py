"""Manages conversation state across user interactions."""
from threading import Lock
from typing import Any, Dict


class ConversationManager:
    """Centralized state management for user conversations."""

    def __init__(self):
        """Initialize state storage."""
        self._user_states: Dict[int, Dict[str, Any]] = {}
        self._date_selection_states: Dict[int, Dict[str, Any]] = {}
        self._shown_dates: Dict[int, tuple] = {}
        self._lock = Lock()

    def set_user_state(self, user_id: int, state_data: Dict[str, Any]) -> None:
        """
        Set complete state for a user.
        
        Args:
            user_id: Telegram user ID
            state_data: Dictionary containing state information
        """
        with self._lock:
            self._user_states[user_id] = state_data

    def get_user_state(self, user_id: int) -> Dict[str, Any]:
        """
        Get state for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            State dictionary or empty dict if not found
        """
        with self._lock:
            return self._user_states.get(user_id, {})

    def update_user_state(self, user_id: int, key: str, value: Any) -> None:
        """
        Update a specific state value for a user.
        
        Args:
            user_id: Telegram user ID
            key: State key
            value: State value
        """
        with self._lock:
            if user_id not in self._user_states:
                self._user_states[user_id] = {}
            self._user_states[user_id][key] = value

    def clear_user_state(self, user_id: int) -> None:
        """Clear all state for a user."""
        with self._lock:
            if user_id in self._user_states:
                del self._user_states[user_id]

    # Date selection state management
    def init_date_selection(self, chat_id: int, year: int, month: int) -> None:
        """
        Initialize date selection state.
        
        Args:
            chat_id: Chat ID
            year: Current year
            month: Current month
        """
        with self._lock:
            self._date_selection_states[chat_id] = {
                "start_selected": False,
                "end_selected": False,
                "start_date": None,
                "end_date": None
            }
            self._shown_dates[chat_id] = (year, month)

    def get_date_selection_state(self, chat_id: int) -> Dict[str, Any]:
        """Get date selection state for a chat."""
        with self._lock:
            return self._date_selection_states.get(chat_id, {})

    def update_date_selection_state(self, chat_id: int, key: str, value: Any) -> None:
        """Update a date selection state value."""
        with self._lock:
            if chat_id not in self._date_selection_states:
                self._date_selection_states[chat_id] = {}
            self._date_selection_states[chat_id][key] = value

    def get_shown_date(self, chat_id: int) -> tuple:
        """Get currently shown date (year, month)."""
        with self._lock:
            return self._shown_dates.get(chat_id, (2026, 3))

    def set_shown_date(self, chat_id: int, year: int, month: int) -> None:
        """Set currently shown date."""
        with self._lock:
            self._shown_dates[chat_id] = (year, month)

    def clear_date_selection(self, chat_id: int) -> None:
        """Clear date selection state."""
        with self._lock:
            if chat_id in self._date_selection_states:
                del self._date_selection_states[chat_id]
            if chat_id in self._shown_dates:
                del self._shown_dates[chat_id]
