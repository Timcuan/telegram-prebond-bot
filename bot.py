import os
import logging
import requests
import asyncio
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load env dari file .env
load_dotenv()

# Setup log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BITQUERY_API_KEY = os.getenv("BITQUERY_API_KEY")
BITQUERY_URL = "https://graphql.bitquery.io/"

# Query untuk LetsBonk.fun prebond token
GRAPHQL_QUERY = '''
query ($limit: Int!) {
  solana(network: solana) {
    dexTrades(
      options: {limit: $limit, desc: "quoteAmount"},
      exchangeName: {in: ["LetsBonk.fun"]},
      tradeAmountUsd: {gt: 0.0}
    ) {
      token: baseCurrency {
        symbol
        address
      }
      trade: trades: count
      quoteAmount
    }
  }
}
'''

# Penyimpanan token yang sudah dilaporkan
known_tokens = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot tracking prebond memecoin aktif!\nTunggu notifikasi token baru...")
    context.job_queue.run_repeating(fetch_and_report, interval=300, first=5, data=context.bot)

async def fetch_and_report(context: ContextTypes.DEFAULT_TYPE):
    headers = {
        'X-API-KEY': BITQUERY_API_KEY,
        'Content-Type': 'application/json'
    }
    payload = {
        'query': GRAPHQL_QUERY,
        'variables': {'limit': 50}
    }

    try:
        response = requests.post(BITQUERY_URL, json=payload, headers=headers)
        data = response.json()['data']['solana']['dexTrades']
    except Exception as e:
        logger.error(f"Gagal fetch dari Bitquery: {e}")
        return

    bot: Bot = context.job.data
    new_tokens = []

    for item in data:
        symbol = item['token']['symbol']
        address = item['token']['address']
        volume = float(item['quoteAmount'])

        if address not in known_tokens:
            known_tokens.add(address)
            new_tokens.append((symbol, address, volume))

    for symbol, address, volume in new_tokens:
        message = f"🧪 *New Prebond Token!*\n\n🔸 Symbol: `{symbol}`\n🔹 Volume: ${volume:.2f}\n📦 Address: `{address}`\n🔍 https://explorer.solana.com/address/{address}?cluster=mainnet"
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')

if __name__ == '__main__':
    if not TELEGRAM_BOT_TOKEN or not CHAT_ID or not BITQUERY_API_KEY:
        logger.error("❌ API keys belum lengkap. Cek file .env")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    logger.info("✅ Bot siap. Jalankan /start di Telegram.")
    app.run_polling()
