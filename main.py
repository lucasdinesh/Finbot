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

import requests
import telebot
from telebot import types
from config import TOKEN, local_mode, DATABASE_URL, LLM_ENABLED, LLM_API_KEY, LLM_MODEL, LLM_BASE_URL
from database import IExpenseRepository
from local_repository import LocalRepository
from cloud_database import PostgresRepository
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


class ExpenseRepositorySingleton:
    """Singleton for expense repository."""
    _instance: IExpenseRepository = None

    @staticmethod
    def get_instance() -> IExpenseRepository:
        if ExpenseRepositorySingleton._instance is None:
            if local_mode:
                ExpenseRepositorySingleton._instance = LocalRepository()
            else:
                ExpenseRepositorySingleton._instance = PostgresRepository(DATABASE_URL)
        return ExpenseRepositorySingleton._instance


BOT_USERNAME: Final = "ufrgs_financialbot"


class ExceptionHandler:
    """Catch all unhandled handler exceptions so the bot doesn't crash."""

    def handle(self, exception: Exception) -> bool:
        logging.error("Unhandled handler error: %s: %s", type(exception).__name__, exception, exc_info=True)
        return True


bot = telebot.TeleBot(TOKEN, exception_handler=ExceptionHandler())

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
date_handler = DateHandler(bot, state_manager, expense_service)
receipt_handler = ReceiptHandler(bot, state_manager, expense_service, ocr_service)
category_handler = CategoryHandler(bot, state_manager, expense_service)
budget_handler = BudgetHandler(bot, state_manager, expense_service)
insight_handler = InsightHandler(bot, state_manager, expense_service)
recurring_handler = RecurringHandler(bot, state_manager, expense_service)
goal_handler = GoalHandler(bot, state_manager, expense_service)

# ============================================================================
# BOT COMMAND SETUP
# ============================================================================

def setup_bot_commands():
    """Set up available bot commands for Telegram."""
    commands = [
        # Geral
        types.BotCommand("inicio", "Mostra a mensagem de boas-vindas"),
        types.BotCommand("ajuda", "Mostra todos os comandos disponíveis"),

        # Despesas
        types.BotCommand("adicionar", "Adiciona uma nova despesa"),
        types.BotCommand("listar", "Lista todas as despesas"),
        types.BotCommand("buscar", "Busca despesas pelo nome"),
        types.BotCommand("buscar_por_data", "Busca despesas por intervalo de datas"),
        types.BotCommand("editar", "Edita uma despesa existente"),
        types.BotCommand("deletar", "Deleta uma despesa existente"),

        # Relatórios
        types.BotCommand("resumo_mensal", "Resumo detalhado do mês atual"),
        types.BotCommand("relatorio", "Relatório rápido comparando mês atual com anterior"),
        types.BotCommand("comparativo", "Comparativo de gastos mês a mês"),

        # Categorias e Orçamentos
        types.BotCommand("categorias", "Lista todas as categorias"),
        types.BotCommand("definir_orcamento", "Define orçamento mensal para uma categoria"),
        types.BotCommand("orcamentos", "Mostra orçamentos do mês"),

        # Despesas Recorrentes
        types.BotCommand("adicionar_recorrente", "Adiciona despesa recorrente"),
        types.BotCommand("recorrentes", "Lista despesas recorrentes"),
        types.BotCommand("remover_recorrente", "Remove despesa recorrente"),

        # Metas de Economia
        types.BotCommand("adicionar_meta", "Cria uma nova meta de economia"),
        types.BotCommand("metas", "Mostra metas de economia"),
        types.BotCommand("contribuir_meta", "Adiciona valor a uma meta"),

        # Comprovante
        types.BotCommand("foto", "Escanear comprovante com a câmera"),
    ]
    import time
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            scopes = [
                types.BotCommandScopeDefault(),
                types.BotCommandScopeAllPrivateChats(),
                types.BotCommandScopeAllGroupChats(),
                types.BotCommandScopeAllChatAdministrators(),
            ]
            for scope in scopes:
                bot.delete_my_commands(scope=scope)
                bot.set_my_commands(commands, scope=scope)
            logging.getLogger("financialbot").info(
                "Registered %d bot commands across all scopes", len(commands)
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

@bot.message_handler(commands=['inicio', 'start'])
def send_welcome(message):
    """Handle /inicio command."""
    first_name = message.from_user.first_name
    bot.send_message(message.chat.id, WELCOME_MESSAGE.format(first_name=first_name))
    
    commands = bot.get_my_commands()
    text = COMMANDS_HEADER
    for cmd in commands:
        text += f"/{cmd.command} – {cmd.description}\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=['ajuda'])
def send_help(message):
    """Handle /ajuda command."""
    commands = bot.get_my_commands()
    text = COMMANDS_HEADER
    for cmd in commands:
        text += f"/{cmd.command} – {cmd.description}\n"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=['adicionar'])
def add_expense_cmd(message):
    """Handle /adicionar command."""
    expense_handler.handle_add_command(message)


@bot.message_handler(commands=['resumo_mensal'])
def monthly_summary_cmd(message):
    """Handle /resumo_mensal command."""
    report_handler.handle_monthly_summary(message)


@bot.message_handler(commands=['relatorio'])
def quick_report_cmd(message):
    """Handle /relatorio command."""
    report_handler.handle_quick_report(message)


@bot.message_handler(commands=['listar'])
def get_all_expenses_cmd(message):
    """Handle /listar command."""
    report_handler.handle_get_all(message)


@bot.message_handler(commands=['buscar_por_data'])
def get_by_date_cmd(message):
    """Handle /buscar_por_data command."""
    date_handler.handle_getbydate(message)


@bot.message_handler(commands=['foto'])
def scan_receipt_cmd(message):
    """Handle /foto command."""
    receipt_handler.handle_scan_command(message)


@bot.message_handler(commands=['buscar'])
def search_expense_cmd(message):
    """Handle /buscar command."""
    expense_handler.handle_search_command(message)


@bot.message_handler(commands=['editar'])
def edit_expense_cmd(message):
    """Handle /editar command."""
    expense_handler.handle_edit_command(message)


@bot.message_handler(commands=['categorias'])
def categories_cmd(message):
    """Handle /categorias command."""
    category_handler.handle_list_categories(message)


@bot.message_handler(commands=['definir_orcamento'])
def set_budget_cmd(message):
    """Handle /definir_orcamento command."""
    budget_handler.handle_set_budget(message)


@bot.message_handler(commands=['orcamentos'])
def budgets_cmd(message):
    """Handle /orcamentos command."""
    budget_handler.handle_list_budgets(message)


@bot.message_handler(commands=['comparativo'])
def insights_cmd(message):
    """Handle /comparativo command."""
    insight_handler.handle_insights(message)


@bot.message_handler(commands=['adicionar_recorrente'])
def add_recurring_cmd(message):
    """Handle /adicionar_recorrente command."""
    recurring_handler.handle_add_recurring(message)


@bot.message_handler(commands=['recorrentes'])
def recurring_cmd(message):
    """Handle /recorrentes command."""
    recurring_handler.handle_list_recurring(message)


@bot.message_handler(commands=['remover_recorrente'])
def remove_recurring_cmd(message):
    """Handle /remover_recorrente command."""
    recurring_handler.handle_delete_recurring(message)


@bot.message_handler(commands=['adicionar_meta'])
def add_goal_cmd(message):
    """Handle /adicionar_meta command."""
    goal_handler.handle_add_goal(message)


@bot.message_handler(commands=['metas'])
def goals_cmd(message):
    """Handle /metas command."""
    goal_handler.handle_list_goals(message)


@bot.message_handler(commands=['contribuir_meta'])
def contribute_goal_cmd(message):
    """Handle /contribuir_meta command."""
    goal_handler.handle_contribute_start(message)


@bot.message_handler(content_types=['photo'])
def photo_message(message):
    """Handle any incoming photo message as a receipt scan attempt."""
    receipt_handler.handle_photo_message(message)


@bot.message_handler(commands=['deletar'])
def delete_expense_cmd(message):
    """Handle /Deletar command."""
    expense_handler.handle_delete_command(message)


# Register command handlers for cross-flow abort detection
from handlers.base_handler import BaseHandler
BaseHandler.register_commands({
    "inicio": send_welcome,
    "start": send_welcome,
    "ajuda": send_help,
    "adicionar": expense_handler.handle_add_command,
    "listar": report_handler.handle_get_all,
    "buscar": expense_handler.handle_search_command,
    "buscar_por_data": date_handler.handle_getbydate,
    "editar": expense_handler.handle_edit_command,
    "deletar": expense_handler.handle_delete_command,
    "resumo_mensal": report_handler.handle_monthly_summary,
    "relatorio": report_handler.handle_quick_report,
    "comparativo": insight_handler.handle_insights,
    "categorias": category_handler.handle_list_categories,
    "definir_orcamento": budget_handler.handle_set_budget,
    "orcamentos": budget_handler.handle_list_budgets,
    "adicionar_recorrente": recurring_handler.handle_add_recurring,
    "recorrentes": recurring_handler.handle_list_recurring,
    "remover_recorrente": recurring_handler.handle_delete_recurring,
    "adicionar_meta": goal_handler.handle_add_goal,
    "metas": goal_handler.handle_list_goals,
    "contribuir_meta": goal_handler.handle_contribute_start,
    "foto": receipt_handler.handle_scan_command,
})

# ============================================================================
# CALLBACK HANDLERS
# ============================================================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('START-DAY;') or call.data.startswith('END-DAY;'))
def handle_day_callback(call):
    """Handle day selection from calendar."""
    try:
        date_handler.handle_day_selection(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_day_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('START-PREV-MONTH;') or call.data.startswith('END-PREV-MONTH;') or call.data.startswith('START-NEXT-MONTH;') or call.data.startswith('END-NEXT-MONTH;'))
def handle_month_nav_callback(call):
    """Handle prev/next month navigation in calendar."""
    try:
        date_handler.handle_month_navigation(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_month_nav_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RECEIPT'))
def handle_receipt_callback(call):
    """Handle receipt confirmation / edit / cancel callbacks."""
    try:
        if call.data == 'RECEIPT_CONFIRM':
            receipt_handler.handle_confirm(call)
        elif call.data.startswith('RECEIPT_EDIT_FIELD') or call.data == 'RECEIPT_EDIT_DONE':
            receipt_handler.handle_edit_field(call)
        elif call.data == 'RECEIPT_EDIT':
            receipt_handler.handle_edit(call)
        elif call.data == 'RECEIPT_CANCEL':
            receipt_handler.handle_cancel_action(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_receipt_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RCPAYMENT_'))
def handle_receipt_payment_callback(call):
    """Handle payment method selection in receipt flow."""
    try:
        receipt_handler.handle_receipt_payment_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_receipt_payment_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RCINST_'))
def handle_receipt_installment_callback(call):
    """Handle installment selection in receipt flow."""
    try:
        receipt_handler.handle_receipt_installment_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_receipt_installment_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RCCAT_'))
def handle_receipt_category_callback(call):
    """Handle category selection in receipt flow."""
    try:
        receipt_handler.handle_receipt_category_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_receipt_category_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('PAYMENT'))
def handle_payment_callback(call):
    """Handle payment method selection."""
    try:
        expense_handler.handle_payment_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_payment_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('INST_'))
def handle_installment_callback(call):
    """Handle installment selection in expense flow."""
    try:
        expense_handler.handle_installment_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_installment_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('CATEGORY'))
def handle_category_callback(call):
    """Handle category selection."""
    try:
        expense_handler.handle_category_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_category_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('EDIT_'))
def handle_edit_field_callback(call):
    """Handle edit field selection."""
    try:
        expense_handler.handle_edit_field_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_edit_field_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data == 'CATEGORY_CREATE')
def handle_category_create_callback(call):
    """Handle create category from /categories."""
    try:
        category_handler.handle_create_category_start(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_category_create_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('BUDGET_CAT_'))
def handle_budget_category_callback(call):
    """Handle budget category selection."""
    try:
        budget_handler.handle_budget_category_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_budget_category_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RPAYMENT_'))
def handle_recurring_payment_callback(call):
    """Handle recurring expense payment method."""
    try:
        recurring_handler.handle_payment_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_recurring_payment_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RCAT_'))
def handle_recurring_category_callback(call):
    """Handle recurring expense category selection."""
    try:
        recurring_handler.handle_category_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_recurring_category_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('RDEL_'))
def handle_recurring_delete_callback(call):
    """Handle recurring expense deletion."""
    try:
        recurring_handler.handle_delete_callback(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_recurring_delete_callback crashed", exc_info=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('GOAL_CONT_'))
def handle_goal_contribute_callback(call):
    """Handle goal contribution selection."""
    try:
        goal_handler.handle_contribute_select(call)
    except Exception:
        logging.getLogger("financialbot").error("handle_goal_contribute_callback crashed", exc_info=True)


def generate_recurring_expenses():
    """Auto-generate expenses from recurring subscriptions."""
    logger = logging.getLogger("financialbot")
    try:
        due = expense_service.get_due_recurring_expenses()
        now = datetime.datetime.now()
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
    
    # Polling with retry logic for network errors only
    retry_delay = 5

    while True:
        try:
            bot.polling(non_stop=True, interval=0, timeout=60)
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user", flush=True)
            break
        except (ConnectionError, TimeoutError, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            logging.getLogger("financialbot").warning(
                "Polling network error: %s. Retrying in %ds...", e, retry_delay
            )
            import time
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)
        except Exception as e:
            print(f"❌ BOT CRASHED: {type(e).__name__}: {str(e)[:200]}", flush=True)
            logging.getLogger("financialbot").error("Unexpected polling error — restarting container", exc_info=True)
            raise

