import json
from typing import Final
import telebot
from telebot import types
import inline_calendar
import datetime
from config import TOKEN
from database import ExpenseRepository


class ExpenseRepositorySingleton:
    _instance = None

    @staticmethod
    def get_instance():
        if ExpenseRepositorySingleton._instance is None:
            ExpenseRepositorySingleton._instance = ExpenseRepository()
        return ExpenseRepositorySingleton._instance


BOT_USERNAME: Final = "financiallufe_bot"
current_shown_dates={}
user_date_status = {}
bot = telebot.TeleBot(TOKEN)


# Step 1: Start the interaction and ask for the expense value
@bot.message_handler(commands=['add'])
def add_expanse_command(message):
    print(message)
    bot.send_message(message.chat.id, "Qual o valor da despesa?")
    bot.register_next_step_handler(message, process_value)


# Step 2: Capture the value of the expense
def process_value(message):
    valor_despesa = message.text.strip()  # Get the value of the expense
    bot.send_message(message.chat.id, "Qual o nome da despesa?")
    bot.register_next_step_handler(message, process_name, valor_despesa)


# Step 3: Capture the name of the expense
def process_name(message, valor_despesa):
    name_despesa = message.text.strip()  # Get the name of the expense
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
        "Escolha uma parcela:",
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
        f"Despesa registrada com sucesso!\n"
        f"Nome: {name_despesa}\n"
        f"Valor: {valor_despesa}\n"
        f"Parcelas: {parcelas}",
    )


@bot.message_handler(commands=['get'])
def add_expanse_command(message):
    expense_repository = ExpenseRepositorySingleton.get_instance()
    expenses = expense_repository.get_all()
    for expense in expenses:
        bot.send_message(message.chat.id, f"{expense.name} - {expense.amount}")


@bot.message_handler(commands=['get_by_date'])
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
    bot.send_message(chat_id, "Escolha uma data de inicio:", reply_markup=start_markup)
    bot.send_message(chat_id, "Escolha uma data de fim:", reply_markup=end_markup)

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
                bot.answer_callback_query(call.id, text="Data de início já escolhida!")
                return
        elif "END-" in call.data:
            calendar_type = "end"
            if user_date_status[chat_id]["end_selected"]:
                bot.answer_callback_query(call.id, text="Data de fim já escolhida!")
                return
        else:
            calendar_type = "unknown"  # Fallback, optional

        day = int(call.data[last_sep:])
        date = datetime.datetime(int(saved_date[0]), int(saved_date[1]), day, 0, 0, 0).date().strftime("%d-%m-%Y")
        if calendar_type == "start":
            user_date_status[chat_id]["start_date"] = date
            user_date_status[chat_id]["start_selected"] = True  # Mark as selected
            bot.send_message(chat_id=chat_id, text=f"Data de Início escolhida: {date}")
        elif calendar_type == "end":
            user_date_status[chat_id]["end_date"] = date
            user_date_status[chat_id]["end_selected"] = True  # Mark as selected
            bot.send_message(chat_id=chat_id, text=f"Data de Fim escolhida: {date}")

        # Remove the calendar after selection
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=None
        )

        bot.answer_callback_query(call.id, text="Data selecionada!")

        # Perform action if both dates are selected
        if user_date_status[chat_id]["start_selected"] and user_date_status[chat_id]["end_selected"]:
            start_date = user_date_status[chat_id]["start_date"]
            end_date = user_date_status[chat_id]["end_date"]

            # Call repository or perform an action with the selected dates
            expense_repository = ExpenseRepositorySingleton.get_instance()
            expenses = expense_repository.get_by_date_interval(start_date, end_date)

            if expenses:
                for expense in expenses:
                    bot.send_message(chat_id, f"{expense.name} - {expense.amount} - {expense.date}")
            else:
                bot.send_message(chat_id, "Nenhuma despesa encontrada para o intervalo selecionado.")
    else:
        # Handle error when no saved date
        bot.answer_callback_query(call.id, text="Erro ao processar a data.")


@bot.callback_query_handler(func=lambda call: 'MONTH' in call.data)
def handle_month_query(call):
    info = call.data.split(';')
    month_opt = info[0].split('-')[0]  # 'PREV' or 'NEXT'
    prefix = info[0].split('-')[1]  # 'START' or 'END'
    year, month = int(info[1]), int(info[2])
    chat_id = call.message.chat.id

    if month_opt == "PREV":
        month -= 1
    elif month_opt == "NEXT":
        month += 1

    if month < 1:
        month = 12
        year -= 1
    if month > 12:
        month = 1
        year += 1

    date = (year, month)
    current_shown_dates[chat_id] = date

    # Recreate the calendar with the same prefix
    markup = json.loads(inline_calendar.create_calendar(year, month, prefix=f"{prefix}-"))
    bot.edit_message_text(
        "Escolha uma data:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
    )

    # expense_repository = ExpenseRepositorySingleton.get_instance()
    # expenses = expense_repository.get_by_date_interval(message.text.split()[1], message.text.split()[2])
    # for expense in expenses:
    #     bot.send_message(message.chat.id, f"{expense.name} - {expense.amount} - {expense.date}")


bot.polling()
