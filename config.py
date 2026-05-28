import os
from typing import Final

TOKEN: Final = "8203008574:AAEYkBFbatyB2gi6teM7a1oaqlzXiTXDM_c"
OLD_TOKEN: Final = "7644417713:AAFm1bOgYnV7nBAYHYTSM3oBHhj92vVKV4o"
DATABASE: Final = "finance.db"
connection_string_neon_demo: Final = "postgresql://neondb_owner:npg_f7xrNmZs3oaU@ep-frosty-resonance-ach1uf29-pooler.sa-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
local_mode: Final = True
MAX_DATE_INTERVAL: Final = 6  # Maximum number of months allowed for date range queries

# LLM receipt extraction (Groq API — free tier, no credit card: https://console.groq.com)
LLM_ENABLED: Final = True
LLM_API_KEY: Final = os.getenv("LLM_API_KEY", "")  # Set env var or edit here
LLM_MODEL: Final = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_BASE_URL: Final = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
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
    "   Se o texto mencionar um aplicativo de delivery "
    "(iFood, Uber Eats, Rappi, 99Food, etc.), "
    "combine o aplicativo com o estabelecimento no formato "
    "'APLICATIVO - Estabelecimento'.\n"
    "   Exemplo: 'iFood - Delícias da Maria', "
    "'Uber Eats - Burger King'.\n\n"
    "Texto do comprovante:\n{ocr_text}\n\n"
    "Responda APENAS com um JSON válido no formato:\n"
    '{"amount": 123.45, "date": "31-12-2024", '
    '"store_name": "iFood - Nome da Loja"}'
)