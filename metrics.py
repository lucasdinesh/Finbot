"""Prometheus metrics collection for Financial Bot."""
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from datetime import datetime

# Command execution metrics
command_executions = Counter(
    'bot_command_executions_total',
    'Total number of command executions',
    ['command', 'user_id', 'status']
)

# User activity metrics
active_users = Gauge(
    'bot_active_users',
    'Number of active users',
)

# Request latency
request_duration = Histogram(
    'bot_request_duration_seconds',
    'Request duration in seconds',
    ['command']
)

# Expense operations
expenses_added = Counter(
    'bot_expenses_added_total',
    'Total expenses added',
    ['user_id']
)

expenses_deleted = Counter(
    'bot_expenses_deleted_total',
    'Total expenses deleted',
    ['user_id']
)

# Query metrics
queries_executed = Counter(
    'bot_queries_executed_total',
    'Total database queries executed',
    ['query_type', 'user_id', 'status']
)

# Message metrics
messages_received = Counter(
    'bot_messages_received_total',
    'Total messages received',
    ['message_type', 'user_id']
)

# Error metrics
errors_occurred = Counter(
    'bot_errors_total',
    'Total errors occurred',
    ['error_type', 'command', 'user_id']
)

# Bot state
bot_running = Gauge(
    'bot_running',
    'Bot running status (1 = running, 0 = stopped)',
)

# Concurrent users
concurrent_conversations = Gauge(
    'bot_concurrent_conversations',
    'Number of concurrent conversations',
)

# Cache metrics
user_state_cache_size = Gauge(
    'bot_user_state_cache_size',
    'Size of user state cache (number of users)',
)


def record_command(command: str, user_id: int, status: str = 'success'):
    """Record command execution."""
    command_executions.labels(command=command, user_id=str(user_id), status=status).inc()


def record_expense_added(user_id: int):
    """Record expense addition."""
    expenses_added.labels(user_id=str(user_id)).inc()


def record_expense_deleted(user_id: int):
    """Record expense deletion."""
    expenses_deleted.labels(user_id=str(user_id)).inc()


def record_query(query_type: str, user_id: int, status: str = 'success'):
    """Record database query."""
    queries_executed.labels(query_type=query_type, user_id=str(user_id), status=status).inc()


def record_message(message_type: str, user_id: int):
    """Record incoming message."""
    messages_received.labels(message_type=message_type, user_id=str(user_id)).inc()


def record_error(error_type: str, command: str, user_id: int):
    """Record error occurrence."""
    errors_occurred.labels(error_type=error_type, command=command, user_id=str(user_id)).inc()


def set_active_users(count: int):
    """Set count of active users."""
    active_users.set(count)


def set_concurrent_conversations(count: int):
    """Set number of concurrent conversations."""
    concurrent_conversations.set(count)


def set_user_state_cache_size(count: int):
    """Set size of user state cache."""
    user_state_cache_size.set(count)


def set_bot_running(running: bool):
    """Set bot running status."""
    bot_running.set(1 if running else 0)
