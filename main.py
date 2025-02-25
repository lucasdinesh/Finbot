from typing import Final
import telebot
from telebot import types
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
    buttons = [types.InlineKeyboardButton(text=str(i), callback_data=f"{valor_despesa};{name_despesa};{i}") for i in
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
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
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


bot.polling()
