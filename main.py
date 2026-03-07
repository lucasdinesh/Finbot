import datetime
import json
from typing import Final

import telebot
from telebot import types

import inline_calendar
from config import TOKEN, local_mode, connection_string_neon_demo
from database import IExpenseRepository, ExpenseRepository
from cloud_database import NeonPostgresRepository
from reports import ReportGenerator
from messages import *


class ExpenseRepositorySingleton:
    _instance: IExpenseRepository = None

    @staticmethod
    def get_instance() -> IExpenseRepository:
        if ExpenseRepositorySingleton._instance is None:
            if local_mode:
                ExpenseRepositorySingleton._instance = ExpenseRepository()
            else:
                ExpenseRepositorySingleton._instance = NeonPostgresRepository(connection_string_neon_demo)
        return ExpenseRepositorySingleton._instance


BOT_USERNAME: Final = "ufrgs_financialbot"
current_shown_dates={}
user_date_status = {}
bot = telebot.TeleBot(TOKEN)

# Register bot commands
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
    ]
    bot.set_my_commands(commands)

setup_bot_commands()


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    first_name = message.from_user.first_name
    bot.send_message(message.chat.id, WELCOME_MESSAGE.format(first_name=first_name))
    commands = bot.get_my_commands()  # ← get commands dynamically
    text = COMMANDS_HEADER

    for cmd in commands:
        text += f"/{cmd.command} – {cmd.description}\n"

    bot.send_message(message.chat.id, text, parse_mode="Markdown")



# Step 1: Start the interaction and ask for the expense value
@bot.message_handler(commands=['add'])
def add_expanse_command(message):
    print(message)
    bot.send_message(message.chat.id, ADD_VALUE_PROMPT)
    bot.register_next_step_handler(message, process_value)


# Step 2: Capture the value of the expense
def process_value(message):
    valor_despesa = message.text.strip()  # Get the value of the expense
    
    # Allow user to cancel
    if valor_despesa.lower() == 'cancelar':
        bot.send_message(message.chat.id, ADD_CANCELLED)
        return
    
    # Validate if input is a valid number and positive
    try:
        value = float(valor_despesa)
        if value <= 0:
            bot.send_message(message.chat.id, VALUE_MUST_BE_POSITIVE, parse_mode="Markdown")
            bot.register_next_step_handler(message, process_value)
            return
    except ValueError:
        bot.send_message(message.chat.id, VALUE_INVALID, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_value)
        return
    
    bot.send_message(message.chat.id, ADD_NAME_PROMPT)
    bot.register_next_step_handler(message, process_name, valor_despesa)


# Step 3: Capture the name of the expense
def process_name(message, valor_despesa):
    name_despesa = message.text.strip()  # Get the name of the expense
    
    # Allow user to cancel
    if name_despesa.lower() == 'cancelar':
        bot.send_message(message.chat.id, ADD_CANCELLED)
        return
    
    # Validate if name is not empty and reasonable length
    if not name_despesa:
        bot.send_message(message.chat.id, NAME_EMPTY, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_name, valor_despesa)
        return
    
    if len(name_despesa) > 50:
        bot.send_message(message.chat.id, NAME_TOO_LONG, parse_mode="Markdown")
        bot.register_next_step_handler(message, process_name, valor_despesa)
        return
    
    ask_installments(message, valor_despesa, name_despesa)


# Step 4: Ask the user to choose the number of installments
def ask_installments(message, valor_despesa, name_despesa):
    # Create an inline keyboard markup
    markup = types.InlineKeyboardMarkup(row_width=3)

    # Create buttons using InlineKeyboardButton
    buttons = [types.InlineKeyboardButton(text=str(i), callback_data=f"{valor_despesa};{name_despesa};{i};ADD") for i in
               range(1, 13)]

    # Add buttons to the keyboard layout
    markup.add(*buttons)

    # Send the message with the inline keyboard markup
    bot.send_message(
        message.chat.id,
        ADD_INSTALLMENTS_PROMPT,
        reply_markup=markup,
    )


# Step 5: Handle the callback when a button is clicked and post to the repository
@bot.callback_query_handler(func=lambda call: 'ADD' in call.data)
def handle_callback(call):
    print(call)
    # Extract the data from the callback
    data = call.data.split(";")  # Splitting the callback data into its components
    valor_despesa = data[0]
    name_despesa = data[1]
    parcelas = data[2]

    # Save the expense data into the repository
    expense_repository = ExpenseRepositorySingleton.get_instance()
    expense_repository.add(name=name_despesa, amount=valor_despesa, installment=parcelas, user_id=call.from_user.id)

    # Send confirmation to the user
    bot.send_message(
        call.message.chat.id,
        ADD_SUCCESS.format(name=name_despesa, value=valor_despesa, installments=parcelas),
    )


@bot.message_handler(commands=['get'])
def add_expanse_command(message):
    expense_repository = ExpenseRepositorySingleton.get_instance()
    expenses = expense_repository.get_all()
    for expense in expenses:
        bot.send_message(message.chat.id, GET_ALL_EXPENSES_FORMAT.format(name=expense.name, amount=expense.amount))


@bot.message_handler(commands=['getbydate'])
def get_by_date(message):
    now = datetime.datetime.now()
    chat_id = message.chat.id

    # Reset user status for date selection
    user_date_status[chat_id] = {"start_selected": False, "end_selected": False, "start_date": None, "end_date": None}
    date = (now.year, now.month)
    current_shown_dates[chat_id] = date

    # Create two different calendars for start and end dates
    start_calendar_json = inline_calendar.create_calendar(now.year, now.month, prefix="START-")
    end_calendar_json = inline_calendar.create_calendar(now.year, now.month, prefix="END-")

    # Convert JSON to InlineKeyboardMarkup
    start_markup = types.InlineKeyboardMarkup()
    end_markup = types.InlineKeyboardMarkup()

    # Assuming `create_calendar` returns JSON with a proper inline keyboard structure
    start_keyboard = json.loads(start_calendar_json)['inline_keyboard']
    end_keyboard = json.loads(end_calendar_json)['inline_keyboard']

    # Add the parsed keyboard rows to the markup
    for row in start_keyboard:
        start_markup.row(
            *[types.InlineKeyboardButton(text=btn['text'], callback_data=btn['callback_data']) for btn in row])

    for row in end_keyboard:
        end_markup.row(
            *[types.InlineKeyboardButton(text=btn['text'], callback_data=btn['callback_data']) for btn in row])

    # Send messages with the properly formatted InlineKeyboardMarkup
    bot.send_message(chat_id, DATE_SELECT_START, reply_markup=start_markup)
    bot.send_message(chat_id, DATE_SELECT_END, reply_markup=end_markup)

@bot.callback_query_handler(func=lambda call: 'DAY' in call.data)
def handle_day_query(call):
    chat_id = call.message.chat.id
    saved_date = current_shown_dates.get(chat_id)
    last_sep = call.data.rfind(';') + 1

    # Initialize the user's status if not already set
    if chat_id not in user_date_status:
        user_date_status[chat_id] = {"start_selected": False, "end_selected": False, "start_date": None,
                                     "end_date": None}

    if saved_date is not None:
        # Identify calendar context using the callback prefix
        if "START-" in call.data:
            calendar_type = "start"
            if user_date_status[chat_id]["start_selected"]:
                bot.answer_callback_query(call.id, text=DATE_ALREADY_SELECTED_START)
                return
        elif "END-" in call.data:
            calendar_type = "end"
            if user_date_status[chat_id]["end_selected"]:
                bot.answer_callback_query(call.id, text=DATE_ALREADY_SELECTED_END)
                return
        else:
            calendar_type = "unknown"  # Fallback, optional

        day = int(call.data[last_sep:])
        date = datetime.datetime(int(saved_date[0]), int(saved_date[1]), day, 0, 0, 0).date().strftime("%d-%m-%Y")
        if calendar_type == "start":
            user_date_status[chat_id]["start_date"] = date
            user_date_status[chat_id]["start_selected"] = True  # Mark as selected
            bot.send_message(chat_id=chat_id, text=DATE_START_SELECTED.format(date=date))
        elif calendar_type == "end":
            user_date_status[chat_id]["end_date"] = date
            user_date_status[chat_id]["end_selected"] = True  # Mark as selected
            bot.send_message(chat_id=chat_id, text=DATE_END_SELECTED.format(date=date))

        # Remove the calendar after selection
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )

        bot.answer_callback_query(call.id, text=DATE_SELECTED_CONFIRMATION)

        # Perform action if both dates are selected
        if user_date_status[chat_id]["start_selected"] and user_date_status[chat_id]["end_selected"]:
            start_date = user_date_status[chat_id]["start_date"]
            end_date = user_date_status[chat_id]["end_date"]

            # Call repository or perform an action with the selected dates
            expense_repository = ExpenseRepositorySingleton.get_instance()
            expenses = expense_repository.get_by_date_interval(start_date, end_date)

            if expenses:
                # Format the report nicely
                text = DATE_RANGE_HEADER.format(start_date=start_date, end_date=end_date)
                total_amount = 0
                
                for expense in expenses:
                    text += DATE_RANGE_EXPENSE_FORMAT.format(
                        name=expense.name,
                        amount=float(expense.amount),
                        date=expense.date,
                        installment=expense.installment
                    )
                    total_amount += float(expense.amount)
                
                text += DATE_RANGE_TOTAL.format(total=total_amount)
                bot.send_message(chat_id, text, parse_mode="Markdown")
            else:
                bot.send_message(chat_id, DATE_RANGE_NO_RESULTS.format(start_date=start_date, end_date=end_date))
        else:
            bot.answer_callback_query(call.id, text=DATE_PROCESSING_ERROR)


@bot.message_handler(commands=['monthlysummary'])
def monthly_summary(message):
    print(f"Generating monthly summary for user_id={message.from_user.id}")
    """Generate a detailed monthly summary for the current month."""
    try:
        now = datetime.datetime.now()
        expense_repository = ExpenseRepositorySingleton.get_instance()
        report_generator = ReportGenerator(expense_repository)

        # Get summary for current month
        summary = report_generator.get_monthly_summary(message.from_user.id, now.year, now.month)
        formatted_report = report_generator.format_monthly_summary(summary)

        bot.send_message(message.chat.id, formatted_report, parse_mode="Markdown")
    except Exception as e:
        import traceback
        print(f"Error in monthly_summary: {e}")
        traceback.print_exc()
        bot.send_message(message.chat.id, f"Erro ao gerar resumo: {str(e)}")


@bot.message_handler(commands=['quickreport'])
def quick_report(message):
    print(f"Generating quick report for user_id={message.from_user.id}")
    """Generate a quick report comparing current and previous month."""
    try:
        expense_repository = ExpenseRepositorySingleton.get_instance()
        report_generator = ReportGenerator(expense_repository)

        # Get quick report
        report = report_generator.get_quick_report(message.from_user.id)
        formatted_report = report_generator.format_quick_report(report)

        bot.send_message(message.chat.id, formatted_report, parse_mode="Markdown")
    except Exception as e:
        import traceback
        print(f"Error in quick_report: {e}")
        traceback.print_exc()
        bot.send_message(message.chat.id, f"Erro ao gerar relatório: {str(e)}")


bot.polling()
