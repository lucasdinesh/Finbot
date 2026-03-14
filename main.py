"""
Main entry point for the Financial Couple Telegram Bot.
Orchestrates handlers, services, and state management.
"""
import datetime
import os
import threading
from typing import Final

import telebot
from telebot import types
from prometheus_client import start_http_server

from config import TOKEN, local_mode, connection_string_neon_demo
from database import IExpenseRepository
from local_repository import LocalRepository
from cloud_database import NeonPostgresRepository
from messages import WELCOME_MESSAGE, COMMANDS_HEADER
from metrics import (
    set_bot_running, record_command, record_expense_added, record_expense_deleted,
    record_message, record_error, set_concurrent_conversations, set_user_state_cache_size
)

# Import layers
from state.conversation_manager import ConversationManager
from services.expense_service import ExpenseService
from services.report_service import ReportService
from handlers.expense_handler import ExpenseHandler
from handlers.report_handler import ReportHandler
from handlers.date_handler import DateHandler
from callbacks.callback_router import CallbackRouter


class ExpenseRepositorySingleton:
    """Singleton for expense repository."""
    _instance: IExpenseRepository = None

    @staticmethod
    def get_instance() -> IExpenseRepository:
        if ExpenseRepositorySingleton._instance is None:
            if local_mode:
                ExpenseRepositorySingleton._instance = LocalRepository()
            else:
                ExpenseRepositorySingleton._instance = NeonPostgresRepository(connection_string_neon_demo)
        return ExpenseRepositorySingleton._instance


BOT_USERNAME: Final = "ufrgs_financialbot"
bot = telebot.TeleBot(TOKEN)

# Initialize dependency injection
state_manager = ConversationManager()
expense_repo = ExpenseRepositorySingleton.get_instance()
expense_service = ExpenseService(expense_repo)
report_service = ReportService(expense_repo)

# Initialize handlers
expense_handler = ExpenseHandler(bot, state_manager, expense_service)
report_handler = ReportHandler(bot, state_manager, report_service)
date_handler = DateHandler(bot, state_manager)

# Initialize callback router
callback_router = CallbackRouter()
callback_router.register("ADD", lambda call: None)  # Placeholder for backward compat
callback_router.register("DAY", date_handler.handle_day_selection)


# ============================================================================
# BOT COMMAND SETUP
# ============================================================================

def setup_bot_commands():
    """Set up available bot commands for Telegram."""
    commands = [
        types.BotCommand("start", "Mostra a mensagem de boas-vindas"),
        types.BotCommand("help", "Mostra todos os comandos disponíveis"),
        types.BotCommand("add", "Adiciona uma nova despesa"),
        types.BotCommand("get", "Lista todas as despesas"),
        types.BotCommand("getbydate", "Busca despesas por intervalo de datas"),
        types.BotCommand("monthlysummary", "Resumo detalhado do mês atual"),
        types.BotCommand("quickreport", "Relatório rápido comparando mês atual com anterior"),
        types.BotCommand("delete", "Deleta uma despesa existente"),
    ]
    bot.set_my_commands(commands)


setup_bot_commands()


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Handle /start and /help commands."""
    record_command('help', message.from_user.id)
    record_message('command', message.from_user.id)
    
    first_name = message.from_user.first_name
    bot.send_message(message.chat.id, WELCOME_MESSAGE.format(first_name=first_name))
    
    commands = bot.get_my_commands()
    text = COMMANDS_HEADER
    for cmd in commands:
        text += f"/{cmd.command} – {cmd.description}\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=['add'])
def add_expense_cmd(message):
    """Handle /add command."""
    record_command('add', message.from_user.id)
    record_message('command', message.from_user.id)
    expense_handler.handle_add_command(message)


@bot.message_handler(commands=['monthlysummary'])
def monthly_summary_cmd(message):
    """Handle /monthlysummary command."""
    record_command('monthlysummary', message.from_user.id)
    record_message('command', message.from_user.id)
    report_handler.handle_monthly_summary(message)


@bot.message_handler(commands=['quickreport'])
def quick_report_cmd(message):
    """Handle /quickreport command."""
    record_command('quickreport', message.from_user.id)
    record_message('command', message.from_user.id)
    report_handler.handle_quick_report(message)


@bot.message_handler(commands=['get'])
def get_all_expenses_cmd(message):
    """Handle /get command."""
    record_command('get', message.from_user.id)
    record_message('command', message.from_user.id)
    report_handler.handle_get_all(message)


@bot.message_handler(commands=['getbydate'])
def get_by_date_cmd(message):
    """Handle /getbydate command."""
    record_command('getbydate', message.from_user.id)
    record_message('command', message.from_user.id)
    date_handler.handle_getbydate(message)


@bot.message_handler(commands=['delete'])
def delete_expense_cmd(message):
    """Handle /delete command."""
    record_command('delete', message.from_user.id)
    record_message('command', message.from_user.id)
    expense_handler.handle_delete_command(message)


# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

@bot.callback_query_handler(func=lambda call: 'DAY' in call.data)
def handle_day_callback(call):
    """Handle day selection from calendar."""
    date_handler.handle_day_selection(call)


if __name__ == "__main__":
    # Start Prometheus metrics server in a separate thread
    metrics_port = int(os.getenv('PROMETHEUS_PORT', '8000'))
    try:
        start_http_server(metrics_port)
        print(f"📊 Prometheus metrics server started on port {metrics_port}")
    except Exception as e:
        print(f"⚠️ Failed to start metrics server: {e}")
    
    # Mark bot as running
    set_bot_running(True)
    print("🤖 Financial Bot started! Polling for messages...")
    
    # Polling with retry logic for network errors
    max_retries = 5
    retry_count = 0
    retry_delay = 5  # seconds
    
    while True:
        try:
            bot.polling(non_stop=True, interval=0, timeout=60)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            set_bot_running(False)
            break
        except (ConnectionError, TimeoutError) as e:
            retry_count += 1
            if retry_count > max_retries:
                print(f"❌ Max retries ({max_retries}) exceeded. Stopping bot.")
                set_bot_running(False)
                raise
            print(f"⚠️  Network error (attempt {retry_count}/{max_retries}): {type(e).__name__}")
            print(f"   Retrying in {retry_delay} seconds...")
            import time
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # Exponential backoff, max 60s
        except Exception as e:
            print(f"❌ Unexpected bot error: {type(e).__name__}: {str(e)[:100]}")
            retry_count += 1
            if retry_count > max_retries:
                print(f"❌ Max retries ({max_retries}) exceeded. Stopping bot.")
                set_bot_running(False)
                raise
            print(f"   Retrying in {retry_delay} seconds...")
            import time
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

