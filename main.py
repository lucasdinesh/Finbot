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
from config import TOKEN, local_mode, DATABASE_URL, LLM_ENABLED, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL
from database import IExpenseRepository
from local_repository import LocalRepository
from cloud_database import NeonPostgresRepository
from messages import WELCOME_MESSAGE, COMMANDS_HEADER, SEARCH_PROMPT, EDIT_PROMPT

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
from handlers.category_handler import CategoryHandler
from handlers.budget_handler import BudgetHandler
from handlers.insight_handler import InsightHandler
from handlers.recurring_handler import RecurringHandler
from handlers.goal_handler import GoalHandler
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
                ExpenseRepositorySingleton._instance = NeonPostgresRepository(DATABASE_URL)
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
category_handler = CategoryHandler(bot, state_manager, expense_service)
budget_handler = BudgetHandler(bot, state_manager, expense_service)
insight_handler = InsightHandler(bot, state_manager, expense_service)
recurring_handler = RecurringHandler(bot, state_manager, expense_service)
goal_handler = GoalHandler(bot, state_manager, expense_service)

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
        types.BotCommand("search", "Busca despesas pelo nome"),
        types.BotCommand("edit", "Edita uma despesa existente"),
        types.BotCommand("categories", "Lista todas as categorias"),
        types.BotCommand("setbudget", "Define orçamento mensal para uma categoria"),
        types.BotCommand("budgets", "Mostra orçamentos do mês"),
        types.BotCommand("insights", "Comparativo de gastos mês a mês"),
        types.BotCommand("addrecurring", "Adiciona despesa recorrente"),
        types.BotCommand("recurring", "Lista despesas recorrentes"),
        types.BotCommand("removerecurring", "Remove despesa recorrente"),
        types.BotCommand("addgoal", "Cria uma nova meta de economia"),
        types.BotCommand("goals", "Mostra metas de economia"),
        types.BotCommand("contributetogoal", "Adiciona valor a uma meta"),
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


@bot.message_handler(commands=['search'])
def search_expense_cmd(message):
    """Handle /search command."""
    expense_handler.handle_search_command(message)


@bot.message_handler(commands=['edit'])
def edit_expense_cmd(message):
    """Handle /edit command."""
    expense_handler.handle_edit_command(message)


@bot.message_handler(commands=['categories'])
def categories_cmd(message):
    """Handle /categories command."""
    category_handler.handle_list_categories(message)


@bot.message_handler(commands=['setbudget'])
def set_budget_cmd(message):
    """Handle /setbudget command."""
    budget_handler.handle_set_budget(message)


@bot.message_handler(commands=['budgets'])
def budgets_cmd(message):
    """Handle /budgets command."""
    budget_handler.handle_list_budgets(message)


@bot.message_handler(commands=['insights'])
def insights_cmd(message):
    """Handle /insights command."""
    insight_handler.handle_insights(message)


@bot.message_handler(commands=['addrecurring'])
def add_recurring_cmd(message):
    """Handle /addrecurring command."""
    recurring_handler.handle_add_recurring(message)


@bot.message_handler(commands=['recurring'])
def recurring_cmd(message):
    """Handle /recurring command."""
    recurring_handler.handle_list_recurring(message)


@bot.message_handler(commands=['removerecurring'])
def remove_recurring_cmd(message):
    """Handle /removerecurring command."""
    recurring_handler.handle_delete_recurring(message)


@bot.message_handler(commands=['addgoal'])
def add_goal_cmd(message):
    """Handle /addgoal command."""
    goal_handler.handle_add_goal(message)


@bot.message_handler(commands=['goals'])
def goals_cmd(message):
    """Handle /goals command."""
    goal_handler.handle_list_goals(message)


@bot.message_handler(commands=['contributetogoal'])
def contribute_goal_cmd(message):
    """Handle /contributetogoal command."""
    goal_handler.handle_contribute_start(message)


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


@bot.callback_query_handler(func=lambda call: call.data.startswith('RCPAYMENT_'))
def handle_receipt_payment_callback(call):
    """Handle payment method selection in receipt flow."""
    receipt_handler.handle_receipt_payment_callback(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RCCAT_'))
def handle_receipt_category_callback(call):
    """Handle category selection in receipt flow."""
    receipt_handler.handle_receipt_category_callback(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('PAYMENT'))
def handle_payment_callback(call):
    """Handle payment method selection."""
    expense_handler.handle_payment_callback(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('CATEGORY'))
def handle_category_callback(call):
    """Handle category selection."""
    expense_handler.handle_category_callback(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('EDIT_'))
def handle_edit_field_callback(call):
    """Handle edit field selection."""
    expense_handler.handle_edit_field_callback(call)


@bot.callback_query_handler(func=lambda call: call.data == 'CATEGORY_CREATE')
def handle_category_create_callback(call):
    """Handle create category from /categories."""
    category_handler.handle_create_category_start(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('BUDGET_CAT_'))
def handle_budget_category_callback(call):
    """Handle budget category selection."""
    budget_handler.handle_budget_category_callback(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RPAYMENT_'))
def handle_recurring_payment_callback(call):
    """Handle recurring expense payment method."""
    recurring_handler.handle_payment_callback(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RCAT_'))
def handle_recurring_category_callback(call):
    """Handle recurring expense category selection."""
    recurring_handler.handle_category_callback(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RDEL_'))
def handle_recurring_delete_callback(call):
    """Handle recurring expense deletion."""
    recurring_handler.handle_delete_callback(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('GOAL_CONT_'))
def handle_goal_contribute_callback(call):
    """Handle goal contribution selection."""
    goal_handler.handle_contribute_select(call)


def generate_recurring_expenses():
    """Auto-generate expenses from recurring subscriptions."""
    try:
        due = expense_service.get_due_recurring_expenses()
        from datetime import datetime
        now = datetime.now()
        today = now.strftime("%d-%m-%Y")
        for r in due:
            day = r["day_of_month"]
            day = min(day, 28)
            expense_date = f"{day:02d}-{now.month:02d}-{now.year}"
            expense_service.create_expense(
                user_id=r["user_id"],
                name=r["name"],
                amount=r["amount"],
                installments=1,
                date=expense_date,
                category_id=r["category_id"],
                payment_method=r["payment_method"],
            )
            expense_service.mark_recurring_generated(r["id"], today)
            logger.info("Auto-generated recurring expense: %s for user %d", r["name"], r["user_id"])
        if due:
            logger.info("Generated %d recurring expenses", len(due))
    except Exception as e:
        logger.error("Failed to generate recurring expenses: %s", e)


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

    # Generate due recurring expenses
    generate_recurring_expenses()

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

