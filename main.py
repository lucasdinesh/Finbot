from typing import Final
import telebot
from config import TOKEN
from database import ExpenseRepository

BOT_USERNAME: Final = "financiallufe_bot"

bot = telebot.TeleBot(TOKEN)

@bot.setup_middleware()
def setup():
    context.bot_data['expense_repository'] = ExpenseRepository()
@
def add_expanse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repository = context.bot_data['expense_repository']
    context
    repository.add(name="Despesa", amount=100)
    await update.message.reply_text(f"Despesa adicionada!")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Olá {update.effective_user.first_name}! Vamos as finanças!")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Eu sou o Lufe! Adicione suas financias ")

async def custom_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Custom commands")


#Responses

def handle_responses(text: str) -> str:
    processed = text.lower()

    if "oi" in processed:
        return "Oi, vamos inicar as finanças ?"



async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    messageType: str = update.message.chat.type
    text: str = update.message.text


    print(f'UserId: {update.message.chat.id} - userFirstName {update.message.chat.first_name} - Message: {text}')

    if messageType == "group":
        return
    else:
        response: str = handle_responses(text)

    print(f'Response: {response}')

    await update.message.reply_text(response)


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f'Update {update} caused error {context.error}')

if __name__ == "__main__":
    print("Connecting Database on main")
    print("Bot started")
    app = Application.builder().token(TOKEN).build()
    #command section
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_expanse_command))

    # Messages

    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    #Erros
    app.add_error_handler(error)

    #Polls the bot
    print("Bot polling")
    app.run_polling(poll_interval=3)