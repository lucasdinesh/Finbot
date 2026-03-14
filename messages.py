"""
Centralized messages for the FinancialBot application.
This file contains all user-facing messages to make it easy to manage and update them.
"""

# Welcome and Help Messages
WELCOME_MESSAGE = "Olá {first_name}, como eu posso te ajudar?\n"
COMMANDS_HEADER = "👋 *Comandos Disponiveis:*\n\n"

# Add Expense Messages
ADD_VALUE_PROMPT = "Qual o valor da despesa?"
ADD_NAME_PROMPT = "Qual o nome da despesa?"
ADD_INSTALLMENTS_PROMPT = "Escolha uma parcela:"
ADD_SUCCESS = (
    "Despesa registrada com sucesso!\n"
    "Nome: {name}\n"
    "Valor: {value}\n"
    "Parcelas: {installments}"
)
ADD_CANCELLED = "❌ Operação cancelada."

# Value Validation Messages
VALUE_INVALID = "❌ Valor inválido! Por favor, insira um número válido.\n_(Digite 'cancelar' para sair)_"
VALUE_MUST_BE_POSITIVE = "❌ Valor deve ser maior que zero! Por favor, insira um valor válido.\n_(Digite 'cancelar' para sair)_"

# Name Validation Messages
NAME_EMPTY = "❌ Nome da despesa não pode estar vazio! Por favor, insira um nome válido.\n_(Digite 'cancelar' para sair)_"
NAME_TOO_LONG = "❌ Nome muito longo! Use no máximo 50 caracteres.\n_(Digite 'cancelar' para sair)_"
NAME_NOT_ALPHANUMERIC = "❌ Nome deve conter apenas letras e números! Por favor, insira um nome válido.\n_(Digite 'cancelar' para sair)_"

# Installments Validation Messages
ADD_INSTALLMENTS_PROMPT = "Quantas parcelas? (1-1000):"
INSTALLMENTS_INVALID = "❌ Número de parcelas inválido! Por favor, insira um número inteiro positivo.\n_(Digite 'cancelar' para sair)_"
INSTALLMENTS_TOO_LARGE = "❌ Número de parcelas não pode ser maior que 1000! Por favor, insira um valor válido.\n_(Digite 'cancelar' para sair)_"

# Date Selection Messages
DATE_SELECT_START = "Escolha uma data de inicio:"
DATE_SELECT_END = "Escolha uma data de fim:"
DATE_START_SELECTED = "Data de Início escolhida: {date}"
DATE_END_SELECTED = "Data de Fim escolhida: {date}"
DATE_ALREADY_SELECTED_START = "Data de início já escolhida!"
DATE_ALREADY_SELECTED_END = "Data de fim já escolhida!"
DATE_SELECTED_CONFIRMATION = "Data selecionada!"
DATE_PROCESSING_ERROR = "Erro ao processar a data."

# Date Range Query Messages
DATE_RANGE_HEADER = "📋 *Despesas de {start_date} até {end_date}*\n\n"
DATE_RANGE_EXPENSE_FORMAT = "• *{name}*\n  💵 R${amount:,.2f} | 📅 {date} | 📦 {installment}x\n\n"
DATE_RANGE_TOTAL = "*Total: R${total:,.2f}*"
DATE_RANGE_NO_RESULTS = "Nenhuma despesa encontrada entre {start_date} e {end_date}."

# Monthly Summary Messages
MONTHLY_SUMMARY_HEADER = "📊 *Resumo Mensal - {month_name} {year}*\n\n"
MONTHLY_SUMMARY_TOTAL = "💰 Total: R${total:,.2f}\n"
MONTHLY_SUMMARY_COUNT = "📝 Despesas registradas: {count}\n"
MONTHLY_SUMMARY_TOP = "🔝 *Top 5 Despesas:*\n"
MONTHLY_SUMMARY_ERROR = "Erro ao gerar resumo: {error}"

# Quick Report Messages
QUICK_REPORT_HEADER = "📈 *Relatório Rápido*\n\n"
QUICK_REPORT_CURRENT_MONTH = "*{month_name} (Atual):*\n"
QUICK_REPORT_CURRENT_TOTAL = "  💰 Total: R${total:,.2f}\n"
QUICK_REPORT_CURRENT_COUNT = "  📝 Despesas: {count}\n\n"
QUICK_REPORT_LAST_MONTH = "*{month_name} (Anterior):*\n"
QUICK_REPORT_LAST_TOTAL = "  💰 Total: R${total:,.2f}\n"
QUICK_REPORT_LAST_COUNT = "  📝 Despesas: {count}\n\n"
QUICK_REPORT_TREND_UP = "📈 +{percentage:.1f}% (Aumentou)"
QUICK_REPORT_TREND_DOWN = "📉 {percentage:.1f}% (Diminuiu)"
QUICK_REPORT_TREND_EQUAL = "➡️ 0% (Igual)"
QUICK_REPORT_TREND_LABEL = "*Variação mês a mês:* {trend}\n"
QUICK_REPORT_INSTALLMENTS = "*Parcelas ativas:* {count}\n"
QUICK_REPORT_TOP_3 = "🎯 *Top 3 Categorias:*\n"
QUICK_REPORT_ERROR = "Erro ao gerar relatório: {error}"

# Delete Expense Messages
DELETE_PROMPT = "Qual é o ID da despesa que deseja deletar? (ou 'cancelar' para sair)"
DELETE_ID_INVALID = "❌ ID inválido! Por favor, insira um número inteiro positivo.\n_(Digite 'cancelar' para sair)_"
DELETE_NOT_FOUND = "❌ Despesa com ID {id} não encontrada!"
DELETE_CONFIRM_PROMPT = "Tem certeza que deseja deletar esta despesa?\n_Nome: {name} | Valor: R${amount:.2f} | Parcelas: {installments}_\n\n(sim/não)"
DELETE_SUCCESS = "✅ Despesa deletada com sucesso!"
DELETE_CANCELLED = "❌ Deleção cancelada."

# Date Interval Validation
DATE_INTERVAL_TOO_LARGE = "❌ O intervalo entre as datas não pode exceder {max_months} meses!\nPor favor, escolha um intervalo menor."

# Get All Expenses Messages
GET_ALL_EXPENSES_FORMAT = "{name} - R${amount}"

# Month Names and Weekday Names (localization)
MONTH_NAMES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

# Localized month and weekday names for calendars
CALENDAR_MONTH_NAMES = {
    "en": ["January", "February", "March", "April", "May", "June", 
           "July", "August", "September", "October", "November", "December"],
    "pt": ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
           "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"],
}

CALENDAR_WEEKDAY_NAMES = {
    "en": ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
    "pt": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"],
}
