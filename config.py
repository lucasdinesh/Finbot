import os
from typing import Final

from dotenv import load_dotenv
load_dotenv()

TOKEN: Final = os.getenv("TELEGRAM_TOKEN", "")
OLD_TOKEN: Final = os.getenv("TELEGRAM_OLD_TOKEN", "")
DATABASE: Final = os.getenv("DATABASE_LOCAL_PATH", "finance.db")
DATABASE_URL: Final = os.getenv("DATABASE_URL", "")
local_mode: Final = os.getenv("LOCAL_MODE", "true").lower() == "true"
MAX_DATE_INTERVAL: Final = int(os.getenv("MAX_DATE_INTERVAL", "6"))

LLM_ENABLED: Final = os.getenv("LLM_ENABLED", "true").lower() == "true"
LLM_API_KEY: Final = os.getenv("LLM_API_KEY", "")
LLM_MODEL: Final = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_BASE_URL: Final = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")

DEFAULT_CATEGORIES: Final[list[str]] = [
    "Alimentação", "Transporte", "Moradia", "Saúde", "Educação",
    "Lazer", "Vestuário", "Assinaturas", "Salário", "Outros",
]

LLM_SYSTEM_PROMPT: Final = os.getenv("LLM_SYSTEM_PROMPT") or (
    "Você é um assistente que extrai dados de comprovantes de compra."
)
LLM_USER_PROMPT: Final = os.getenv("LLM_USER_PROMPT") or (
    "Extraia as seguintes informações do texto de um comprovante "
    "de compra abaixo.\n\n"
    "1. Valor total pago (apenas o número, use . para "
    "casas decimais, exemplo: 123.45).\n"
    "   Se houver um valor com R$, use esse.\n"
    "   Caso não tenha um valor com R$, pegue o que possua ponto "
    "flutuante e que esteja próximo ou após palavras como "
    "VALOR, VENDA, TOTAL, VALOR FINAL, VALOR A PAGAR, "
    "TOTAL DO PEDIDO, TOTAL A PAGAR.\n"
    "   Se ainda assim não achar nenhum, mande 0.00 como default.\n"
    "   Ignore subtotais e valores parciais.\n\n"
    "2. Data da compra (formato DD-MM-YYYY).\n\n"
    "3. Nome do estabelecimento.\n"
    "   - Geralmente está nas primeiras linhas do texto.\n"
    "   - Se o OCR tiver erros (ex: 'carhes' = 'carnes', "
    "'azehhe' = 'azenha'), corrija baseado no contexto.\n"
    "   - Mantenha capitalização correta (Shopping, não ShoppING).\n"
    "   - Remova caracteres estranhos como _, *, etc.\n"
    "   - Se o texto mencionar um aplicativo de delivery "
    "(iFood, Uber Eats, Rappi, 99Food, etc.), "
    "combine o aplicativo com o estabelecimento no formato "
    "'APLICATIVO - Estabelecimento'.\n"
    "   - Se NÃO encontrar um nome de estabelecimento válido "
    "após analisar todo o texto, use 'Não especificado'.\n"
    "   Exemplo: 'iFood - Burger King', "
    "'Shopping de Carnes Azenha'.\n\n"
    "Texto do comprovante:\n{ocr_text}\n\n"
    "Responda APENAS com um JSON válido no formato:\n"
    '{"amount": 123.45, "date": "31-12-2024", '
    '"store_name": "Nome do Estabelecimento"}'
)
