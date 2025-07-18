import os
import requests
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Ambil token dan config dari environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BITQUERY_API_KEY = os.getenv('BITQUERY_API_KEY')
CHAT_ID = int(os.getenv('CHAT_ID'))  # pastikan ini angka

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BITQUERY_API_URL = "https://graphql.bitquery.io/"

# Fungsi ambil data prebond dan filter whale
def fetch_prebond_whale_tokens(whale_threshold=100000):
    query = """
    query ($network: String!) {
      solana(network: $network) {
        transfers(
          options: {desc: "amount", limit: 50}
          amount: {gt: 1000}
        ) {
          currency {
            symbol
            address
          }
          amount
          sender {
            address
          }
          receiver {
            address
          }
          transaction {
            hash
            timestamp {
              time
            }
          }
        }
      }
    }
    """
    headers = {
        "X-API-KEY": BITQUERY_API_KEY
    }
    variables = {"network": "solana"}
    response = requests.post(BITQUERY_API_URL, json={'query': query, 'variables': variables}, headers=headers)
    data = response.json()

    tokens = []
    for tx in data.get('data', {}).get('solana', {}).get('transfers', []):
        amount = float(tx['amount'])
        if amount >= whale_threshold:
            tokens.append(tx)
    return tokens

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot prebond sniper siap jalan! Ketik /whale untuk cek whale terbaru.")

async def whale(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tokens = fetch_prebond_whale_tokens()
    if not tokens:
        await update.message.reply_text("🤷‍♂️ Belum ada whale prebond besar hari ini.")
        return

    msg = "🐋 *Whale Alert Prebond Tokens:*\n\n"
    for tx in tokens[:5]:  # batasi 5 token terbaru
        symbol = tx['currency']['symbol']
        amount = tx['amount']
        sender = tx['sender']['address']
        receiver = tx['receiver']['address']
        tx_hash = tx['transaction']['hash']
        time = tx['transaction']['timestamp']['time']
        msg += f"Token: {symbol}\nAmount: {amount}\nFrom: {sender}\nTo: {receiver}\nTx: https://solscan.io/tx/{tx_hash}\nTime: {time}\n\n"

    await update.message.reply_markdown(msg)

async def whale_alert_job(context: ContextTypes.DEFAULT_TYPE):
    tokens = fetch_prebond_whale_tokens()
    if not tokens:
        return
    for tx in tokens:
        message = (
            f"🐋 Whale Alert!\n"
            f"Token: {tx['currency']['symbol']}\n"
            f"Amount: {tx['amount']}\n"
            f"From: {tx['sender']['address']}\n"
            f"Tx: https://solscan.io/tx/{tx['transaction']['hash']}"
        )
        await context.bot.send_message(chat_id=CHAT_ID, text=message)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("whale", whale))

    # Jalankan job whale alert setiap 5 menit
    job_queue = app.job_queue
    job_queue.run_repeating(whale_alert_job, interval=300, first=10)

    app.run_polling()
