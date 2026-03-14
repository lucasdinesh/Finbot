"""Routes and handles callback queries from inline keyboards."""
from typing import Callable, Dict


class CallbackRouter:
    """Routes callback queries to appropriate handlers."""

    def __init__(self):
        """Initialize callback router."""
        self._routes: Dict[str, Callable] = {}

    def register(self, pattern: str, handler: Callable) -> None:
        """
        Register a callback handler.
        
        Args:
            pattern: Callback data pattern to match (e.g., 'ADD', 'DAY')
            handler: Handler function/method
        """
        self._routes[pattern] = handler

    def get_handler(self, callback_data: str) -> Callable:
        """
        Get handler for callback data.
        
        Args:
            callback_data: Callback data from button
            
        Returns:
            Handler function or None
        """
        for pattern, handler in self._routes.items():
            if pattern in callback_data:
                return handler
        return None

    def route(self, callback):
        """
        Route a callback to appropriate handler.
        
        Args:
            callback: Callback query object
            
        Returns:
            True if routed successfully, False otherwise
        """
        handler = self.get_handler(callback.data)
        if handler:
            handler(callback)
            return True
        return False
