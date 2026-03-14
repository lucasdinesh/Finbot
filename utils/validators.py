"""Validation logic for expense data."""


class ExpenseValidator:
    """Validates expense inputs before processing."""

    @staticmethod
    def validate_value(valor_str: str) -> tuple[bool, float, str]:
        """
        Validate expense value input.
        
        Returns:
            (is_valid, value, error_message)
        """
        try:
            value = float(valor_str)
            if value <= 0:
                return False, 0.0, "VALUE_MUST_BE_POSITIVE"
            return True, value, ""
        except ValueError:
            return False, 0.0, "VALUE_INVALID"

    @staticmethod
    def validate_name(name: str) -> tuple[bool, str]:
        """
        Validate expense name.
        - Must not be empty
        - Must be <= 50 characters
        - Must be alphanumeric (letters, numbers, spaces only)
        
        Returns:
            (is_valid, error_message)
        """
        if not name:
            return False, "NAME_EMPTY"
        
        if len(name) > 50:
            return False, "NAME_TOO_LONG"
        
        # Allow alphanumeric and spaces only
        if not name.replace(" ", "").isalnum():
            return False, "NAME_NOT_ALPHANUMERIC"
        
        return True, ""

    @staticmethod
    def validate_installments(parcelas_str: str) -> tuple[bool, int, str]:
        """
        Validate number of installments.
        - Must be a positive integer
        - Must be between 1 and 1000
        
        Returns:
            (is_valid, value, error_message)
        """
        try:
            parcelas = int(parcelas_str)
            if parcelas <= 0:
                return False, 0, "INSTALLMENTS_INVALID"
            if parcelas > 1000:
                return False, 0, "INSTALLMENTS_TOO_LARGE"
            return True, parcelas, ""
        except ValueError:
            return False, 0, "INSTALLMENTS_INVALID"
