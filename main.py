"""
Main entry point for the Financial Couple Telegram Bot.
Orchestrates handlers, services, and state management.
"""
import datetime
import logging
import os
import sys
import threading
from typing import Final

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    stream=sys.stdout,
    force=True,
)
logging.info("Application started — logging ready")

import telebot
from telebot import types
from config import TOKEN, local_mode, connection_string_neon_demo, LLM_ENABLED, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL
from database import IExpenseRepository
from local_repository import LocalRepository
from cloud_database import NeonPostgresRepository
from messages import WELCOME_MESSAGE, COMMANDS_HEADER

# Import layers
from state.conversation_manager import ConversationManager
from services.expense_service import ExpenseService
from services.report_service import ReportService
from services.ocr_service import OcrService
from services.llm_service import LlamaService
from handlers.expense_handler import ExpenseHandler
from handlers.report_handler import ReportHandler
from handlers.date_handler import DateHandler
from handlers.receipt_handler import ReceiptHandler
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

# Initialize services
ocr_service = OcrService()
llm_service = LlamaService(
    api_key=LLM_API_KEY,
    model=LLM_MODEL,
    base_url=LLM_BASE_URL,
    enabled=LLM_ENABLED,
)
ocr_service.llm_service = llm_service

# Initialize handlers
expense_handler = ExpenseHandler(bot, state_manager, expense_service)
report_handler = ReportHandler(bot, state_manager, report_service)
date_handler = DateHandler(bot, state_manager)
receipt_handler = ReceiptHandler(bot, state_manager, expense_service, ocr_service)

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
        types.BotCommand("foto", "Escanear comprovante com a câmera"),
    ]
    import time
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            bot.set_my_commands(commands)
            logging.getLogger("financialbot").info(
                "Registered %d bot commands via Telegram API", len(commands)
            )
            return
        except Exception as exc:
            logging.getLogger("financialbot").warning(
                "Failed to register bot commands (attempt %d/%d): %s",
                attempt, max_retries, exc,
            )
            if attempt < max_retries:
                time.sleep(2 ** attempt)


setup_bot_commands()


# ============================================================================
# COMMAND HANDLERS
# ============================================================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle /start command."""
    first_name = message.from_user.first_name
    bot.send_message(message.chat.id, WELCOME_MESSAGE.format(first_name=first_name))
    
    commands = bot.get_my_commands()
    text = COMMANDS_HEADER
    for cmd in commands:
        text += f"/{cmd.command} – {cmd.description}\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=['help'])
def send_help(message):
    """Handle /help command."""
    commands = bot.get_my_commands()
    text = COMMANDS_HEADER
    for cmd in commands:
        text += f"/{cmd.command} – {cmd.description}\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=['add'])
def add_expense_cmd(message):
    """Handle /add command."""
    expense_handler.handle_add_command(message)


@bot.message_handler(commands=['monthlysummary'])
def monthly_summary_cmd(message):
    """Handle /monthlysummary command."""
    report_handler.handle_monthly_summary(message)


@bot.message_handler(commands=['quickreport'])
def quick_report_cmd(message):
    """Handle /quickreport command."""
    report_handler.handle_quick_report(message)


@bot.message_handler(commands=['get'])
def get_all_expenses_cmd(message):
    """Handle /get command."""
    report_handler.handle_get_all(message)


@bot.message_handler(commands=['getbydate'])
def get_by_date_cmd(message):
    """Handle /getbydate command."""
    date_handler.handle_getbydate(message)


@bot.message_handler(commands=['foto'])
def scan_receipt_cmd(message):
    """Handle /foto command."""
    receipt_handler.handle_scan_command(message)


@bot.message_handler(content_types=['photo'])
def photo_message(message):
    """Handle any incoming photo message as a receipt scan attempt."""
    receipt_handler.handle_photo_message(message)


@bot.message_handler(commands=['delete'])
def delete_expense_cmd(message):
    """Handle /delete command."""
    expense_handler.handle_delete_command(message)


# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

@bot.callback_query_handler(func=lambda call: 'DAY' in call.data)
def handle_day_callback(call):
    """Handle day selection from calendar."""
    date_handler.handle_day_selection(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RECEIPT'))
def handle_receipt_callback(call):
    """Handle receipt confirmation / edit / cancel callbacks."""
    if 'CONFIRM' in call.data:
        receipt_handler.handle_confirm(call)
    elif 'EDIT' in call.data:
        receipt_handler.handle_edit(call)
    elif 'CANCEL' in call.data:
        receipt_handler.handle_cancel_action(call)


if __name__ == "__main__":
    # Pre-download OCR models at startup (non-blocking — runs in background)
    import threading
    def _warm_ocr():
        try:
            ocr_service._get_ocr()
            logging.getLogger("financialbot").info("OCR warm-up complete")
        except Exception as exc:
            logging.getLogger("financialbot").warning("OCR warm-up failed: %s", exc)
    threading.Thread(target=_warm_ocr, daemon=True).start()

    llm_service.warm_up()

    # Logging test
    print("[PRINT] Bot starting up — stdout works", flush=True)
    logging.getLogger("financialbot").info("[LOGGER] Bot starting up — logging works")
    sys.stdout.flush()

    print("🤖 Financial Bot started! Polling for messages...", flush=True)
    sys.stdout.flush()
    
    # Polling with retry logic for network errors
    max_retries = 5
    retry_count = 0
    retry_delay = 5  # seconds
    
    while True:
        try:
            bot.polling(non_stop=True, interval=0, timeout=60)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user", flush=True)
            break
        except (ConnectionError, TimeoutError) as e:
            retry_count += 1
            if retry_count > max_retries:
                print(f"❌ Max retries ({max_retries}) exceeded. Stopping bot.", flush=True)
                # bot stopped
                raise
            print(f"⚠️  Network error (attempt {retry_count}/{max_retries}): {type(e).__name__}", flush=True)
            print(f"   Retrying in {retry_delay} seconds...", flush=True)
            import time
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)  # Exponential backoff, max 60s
        except Exception as e:
            print(f"❌ Unexpected bot error: {type(e).__name__}: {str(e)[:100]}", flush=True)
            retry_count += 1
            if retry_count > max_retries:
                print(f"❌ Max retries ({max_retries}) exceeded. Stopping bot.", flush=True)
                # bot stopped
                raise
            print(f"   Retrying in {retry_delay} seconds...", flush=True)
            import time
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)

