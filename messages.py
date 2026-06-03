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
ADD_DATE_INVALID = "❌ Data inválida! Use o formato DD-MM-YYYY ou digite 'hoje'.\n_(Digite 'cancelar' para sair)_"
ADD_INSTALLMENTS_PROMPT = "Escolha uma parcela:"
ADD_SUCCESS = (
    "Despesa registrada com sucesso!\n"
    "Nome: {name}\n"
    "Valor: R$ {value:.2f}\n"
    "Data: {date}\n"
    "{installments_line}"
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
DATE_FUTURE_NOT_ALLOWED = "❌ Data no futuro não permitida! Escolha uma data até hoje."
DATE_PROCESSING_ERROR = "Erro ao processar a data."

# Date Range Query Messages
DATE_RANGE_HEADER = "📋 *Despesas de {start_date} até {end_date}*\n\n"
DATE_RANGE_EXPENSE_FORMAT = "• [#{local_id}] *{name}*\n  💵 R${amount:,.2f} | 📅 {date} | 📦 {installment}x\n\n"
DATE_RANGE_TOTAL = "*Total: R${total:,.2f}*"
DATE_RANGE_NO_RESULTS = "Nenhuma despesa encontrada entre {start_date} e {end_date}."

# Monthly Summary Messages
MONTHLY_SUMMARY_HEADER = "📊 *Resumo Mensal - {month_name} {year}*\n\n"
MONTHLY_SUMMARY_TOTAL = "💰 Total: R${total:,.2f}\n"
MONTHLY_SUMMARY_COUNT = "📝 Despesas registradas: {count}\n"
MONTHLY_SUMMARY_TOP = "🔝 *Top 5 Despesas:*\n"
MONTHLY_SUMMARY_CATEGORIES = "\n📂 *Por Categoria:*\n"
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

# Payment Method Messages
ADD_PAYMENT_PROMPT = "Qual a forma de pagamento?"
PAYMENT_PIX = "💳 Pix"
PAYMENT_DINHEIRO = "💰 Dinheiro"
PAYMENT_CREDITO = "💳 Crédito"

# Category Messages
ADD_CATEGORY_PROMPT = "Escolha a categoria da despesa:"
ADD_CATEGORY_CUSTOM_PROMPT = "✏️ Digite o nome da nova categoria:"
CATEGORY_OTHER = "📦 Outra"
CATEGORIES_HEADER = "📂 *Categorias Disponíveis:*\n\n"
NO_CATEGORIES = "Nenhuma categoria encontrada."

# Search Messages
SEARCH_PROMPT = "🔍 Digite o nome da despesa que deseja buscar:"
SEARCH_NO_RESULTS = "Nenhuma despesa encontrada com o nome *\"{query}\"*."
SEARCH_RESULT_FORMAT = "• [#{local_id}] *{name}*\n  💵 R${amount:,.2f} | 📅 {date} | 📦 {installment}x | 💳 {payment_method}"

# Edit Expense Messages
EDIT_PROMPT = "✏️ Digite o ID da despesa que deseja editar:"
EDIT_NOT_FOUND = "❌ Despesa com ID {id} não encontrada!"
EDIT_FIELD_PROMPT = "Escolha o campo que deseja editar:"
EDIT_FIELD_VALUE = "💵 Valor"
EDIT_FIELD_NAME = "🏷️ Nome"
EDIT_FIELD_DATE = "📅 Data"
EDIT_FIELD_INSTALLMENTS = "📦 Parcelas"
EDIT_FIELD_CATEGORY = "📂 Categoria"
EDIT_FIELD_PAYMENT = "💳 Forma de Pagamento"
EDIT_NEW_VALUE = "✏️ Digite o novo valor para *{field}*:"
EDIT_SUCCESS = "✅ Despesa editada com sucesso!"
EDIT_CANCELLED = "❌ Edição cancelada."

# Budget Messages
BUDGET_SET_PROMPT = "💰 Digite o valor do orçamento mensal para *{category}*:"
BUDGET_SET_SUCCESS = "✅ Orçamento de R$ {amount:.2f} definido para *{category}*!"
BUDGET_HEADER = "📊 *Orçamentos do Mês:*\n\n"
BUDGET_FORMAT = "• *{category}:* R$ {spent:.2f} / R$ {budget:.2f} ({percent:.0f}%)"
BUDGET_OVER = "⚠️ *Atenção:* Você já gastou R$ {total:.2f} em *{category}* — o orçamento era R$ {budget:.2f}!"
NO_BUDGETS = "Nenhum orçamento definido para este mês."
BUDGET_SELECT_CATEGORY = "Escolha a categoria para definir o orçamento:"

# Savings Goal Messages
GOAL_NAME_PROMPT = "🎯 Qual o nome da sua meta?"
GOAL_TARGET_PROMPT = "💰 Qual o valor alvo da meta?"
GOAL_DEADLINE_PROMPT = "📅 Qual o prazo? (DD-MM-YYYY) ou digite '0' se não tiver prazo:"
GOAL_ADD_SUCCESS = "✅ Meta *{name}* criada com sucesso!"
GOAL_HEADER = "🎯 *Suas Metas:*\n\n"
GOAL_FORMAT = "• {name}\n  R$ {current:,.2f} / R$ {target:,.2f} ({percent:.0f}%)\n  Prazo: {deadline}\n"
GOAL_NO_DEADLINE = "Sem prazo"
NO_GOALS = "Nenhuma meta cadastrada."
GOAL_CONTRIBUTE_PROMPT = "💰 Digite o valor que deseja adicionar à meta *{name}*:"
GOAL_CONTRIBUTE_SUCCESS = "✅ R$ {amount:.2f} adicionado à meta *{name}*!"
GOAL_SELECT_PROMPT = "Escolha a meta:"

# Recurring Expense Messages
RECURRING_NAME_PROMPT = "📋 Qual o nome da despesa recorrente?"
RECURRING_VALUE_PROMPT = "💰 Qual o valor?"
RECURRING_DAY_PROMPT = "📅 Qual o dia do vencimento? (1-31)"
RECURRING_ADD_SUCCESS = "✅ Despesa recorrente *{name}* cadastrada! Será gerada todo dia {day}."
RECURRING_HEADER = "🔄 *Despesas Recorrentes:*\n\n"
RECURRING_FORMAT = "• *{name}* — R$ {amount:.2f} — Dia {day} — {payment}\n"
NO_RECURRING = "Nenhuma despesa recorrente cadastrada."
RECURRING_DELETED = "✅ Despesa recorrente removida."
RECURRING_SELECT_DELETE = "Escolha a despesa recorrente para remover:"

# Insight Messages
INSIGHT_HEADER = "📈 *Insights - {month} vs {prev_month}*\n\n"
INSIGHT_TOTAL = "📊 Total: R$ {total:,.2f} ({change:+.1f}%)\n"
INSIGHT_COUNT = "📝 Despesas: {count} ({count_change:+d})\n\n"
INSIGHT_CATEGORY_LINE = "{category}: R$ {amount:,.2f} ({change} {arrow})\n"
INSIGHT_NO_DATA = "Sem dados suficientes para comparar."
INSIGHT_ARROW_UP = "↑"
INSIGHT_ARROW_DOWN = "↓"
INSIGHT_ARROW_SAME = "→"
INSIGHT_NEW = "NOVO"
INSIGHT_NONE = "-"

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

# OCR / Receipt Messages
SCAN_PROMPT = "📸 Envie a foto do comprovante que deseja escanear."
SCAN_PROCESSING = "⏳ Processando imagem... aguarde um momento."
SCAN_ERROR = "❌ Não foi possível processar a imagem. Tente novamente com uma foto mais nítida e com boa iluminação."
SCAN_NO_TEXT = "❌ Nenhum texto foi detectado na imagem. Certifique-se de que o comprovante está visível e tente novamente."
SCAN_CONFIRM = (
    "📋 *Dados encontrados:*\n\n"
    "🏪 Estabelecimento: {store_name}\n"
    "💰 Valor: R$ {amount:.2f}\n"
    "📅 Data: {date}\n\n"
    "Confirma o lançamento?"
)
SCAN_CONFIRM_LOW_CONFIDENCE = (
    "⚠️ *Confiança baixa* nos dados extraídos.\n\n"
    "📄 Texto reconhecido:\n```\n{raw_text}\n```\n\n"
    "Os dados acima estão corretos?"
)
SCAN_EDIT_VALUE = "✏️ Valor atual: *R$ {current:.2f}*\nDigite o valor correto:"
SCAN_EDIT_NAME = "✏️ Estabelecimento atual: *{current}*\nDigite o nome correto:"
SCAN_EDIT_DATE = "✏️ Data atual: *{current}*\nDigite a data correta (DD-MM-YYYY) ou 'hoje':"
SCAN_EDIT_INSTALLMENTS = "✏️ Parcelas atuais: *{current}*\nDigite 'Sim' ou escreva o número correto (1-1000):"
SCAN_NO_AMOUNT = "❌ Não foi possível identificar o valor no comprovante.\n\nDigite o valor manualmente:"

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
