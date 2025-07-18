#!/usr/bin/env python3
"""
Solana Bonding Curve Monitor Bot
A Telegram bot for monitoring Solana token bonding curves using Bitquery API
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

from bitquery_client import BitqueryClient
from config import TELEGRAM_BOT_TOKEN, BONDING_CURVE_ALERT_THRESHOLDS

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BondingCurveMonitorBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.user_subscriptions: Dict[int, Set[str]] = {}
        self.token_data: Dict[str, Dict] = {}
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self.user_alerts: Dict[int, Dict[str, Set[str]]] = {}
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup command handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("monitor", self.monitor_command))
        self.application.add_handler(CommandHandler("unmonitor", self.unmonitor_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("list", self.list_command))
        self.application.add_handler(CommandHandler("trending", self.trending_command))
        self.application.add_handler(CommandHandler("graduating", self.graduating_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🎯 **Solana Bonding Curve Monitor Bot**

Selamat datang! Bot ini memantau token Solana di letsbonk.fun dengan data real-time dari Bitquery.

**Pilih fungsi yang ingin Anda gunakan:**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Monitor Bonding Tokens", callback_data="monitor_help"),
                InlineKeyboardButton("📈 Trending PreBonding", callback_data="trending_help")
            ],
            [
                InlineKeyboardButton("📊 Status Token", callback_data="status_help"),
                InlineKeyboardButton("📝 List Token Saya", callback_data="list_help")
            ],
            [
                InlineKeyboardButton("🎓 Tokens Graduating", callback_data="graduating_help"),
                InlineKeyboardButton("❓ Help", callback_data="help_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await self.start_command(update, context)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "monitor_help":
            message = """
🔄 **Monitor Bonding Tokens**

Fungsi ini memantau token yang sudah bonding di letsbonk.fun secara real-time.

**Cara Penggunaan:**
• `/monitor <token_address>` - Mulai monitoring token
• `/unmonitor <token_address>` - Berhenti monitoring token

**Fitur:**
✅ Monitoring real-time token yang sudah bonding
✅ Alert ketika ada perubahan harga signifikan
✅ Notifikasi ketika mendekati graduation
✅ Update setiap 30 detik

**Contoh:**
`/monitor 2Z4FzKBcw48KBD2PaR4wtxo4sYGbS7QqTQCLoQnUpump`
            """
            
        elif query.data == "trending_help":
            message = """
📈 **Trending PreBonding (40-80% Market Cap)**

Fungsi ini menampilkan token yang sedang trending dalam fase prebonding dengan market cap 40-80%.

**Cara Penggunaan:**
• `/trending` - Lihat token prebonding yang trending

**Fitur:**
✅ Token dengan market cap 40-80% (fase prebonding)
✅ Update real-time setiap permintaan
✅ Informasi harga dan progress bonding curve
✅ Sortir berdasarkan volume dan aktivitas

**Target Market Cap:**
• Minimum: 40% bonding curve progress
• Maximum: 80% bonding curve progress
            """
            
        elif query.data == "status_help":
            message = """
📊 **Status Token**

Melihat status detail dari token tertentu.

**Cara Penggunaan:**
• `/status <token_address>` - Lihat status token

**Informasi yang Ditampilkan:**
• Harga saat ini (USD & SOL)
• Market cap
• Progress bonding curve
• Likuiditas SOL
• Status graduation
            """
            
        elif query.data == "list_help":
            message = """
📝 **List Token Saya**

Menampilkan semua token yang sedang Anda monitor.

**Cara Penggunaan:**
• `/list` - Lihat semua token yang dimonitor

**Informasi yang Ditampilkan:**
• Daftar token yang dimonitor
• Harga terakhir
• Market cap
• Progress bonding curve
            """
            
        elif query.data == "graduating_help":
            message = """
🎓 **Tokens Graduating**

Menampilkan token yang akan segera graduate (95%+ bonding curve).

**Cara Penggunaan:**
• `/graduating` - Lihat token yang akan graduate

**Kriteria:**
• Progress bonding curve 95% atau lebih
• Siap untuk pindah ke Raydium
• Potensi likuiditas tinggi
            """
            
        elif query.data == "help_menu":
            message = """
❓ **Menu Bantuan**

**Semua Command:**
• `/start` - Menu utama
• `/monitor <address>` - Monitor token bonding
• `/trending` - Token prebonding (40-80%)
• `/status <address>` - Status token
• `/list` - Token yang dimonitor
• `/graduating` - Token akan graduate
• `/help` - Bantuan

**Tips:**
• Gunakan address token yang valid
• Bot update setiap 30 detik
• Notifikasi otomatis untuk perubahan penting
            """
        
        await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /monitor command - Monitor bonding tokens real-time"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Masukkan alamat token yang ingin dimonitor.\n"
                "Penggunaan: `/monitor <token_address>`\n\n"
                "Contoh: `/monitor 2Z4FzKBcw48KBD2PaR4wtxo4sYGbS7QqTQCLoQnUpump`\n\n"
                "🔄 **Fungsi Monitor:** Memantau token yang sudah bonding di letsbonk.fun secara real-time",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        token_address = context.args[0].strip()
        
        # Basic validation
        if len(token_address) < 32 or len(token_address) > 44:
            await update.message.reply_text(
                "❌ Format alamat token tidak valid. Masukkan alamat token Solana yang valid."
            )
            return
        
        # Initialize user data
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
            self.user_alerts[user_id] = {}
        
        self.user_subscriptions[user_id].add(token_address)
        
        if token_address not in self.user_alerts[user_id]:
            self.user_alerts[user_id][token_address] = set()
        
        await update.message.reply_text(f"🔄 Memulai monitoring real-time untuk token: `{token_address}`", parse_mode=ParseMode.MARKDOWN)
        
        # Start monitoring task if not already running
        if token_address not in self.monitoring_tasks:
            task = asyncio.create_task(self.monitor_bonding_token(token_address))
            self.monitoring_tasks[token_address] = task
        
        # Get initial status
        try:
            async with BitqueryClient() as client:
                token_data = await client.get_token_price(token_address)
                bonding_data = await client.get_bonding_curve_progress(token_address)
                
                if token_data or bonding_data:
                    # Check if token is already bonding
                    if bonding_data:
                        pool = bonding_data.get('Pool', {})
                        base = pool.get('Base', {})
                        balance = base.get('PostAmount', 0)
                        bonding_progress = client.calculate_bonding_curve_progress(balance)
                        
                        if bonding_progress >= 80:
                            status_message = self.format_bonding_token_status(token_address, token_data, bonding_data)
                            await update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN)
                        else:
                            await update.message.reply_text(
                                f"⚠️ Token `{token_address}` masih dalam fase prebonding ({bonding_progress:.1f}%).\n"
                                "Fungsi monitor khusus untuk token yang sudah bonding (80%+).\n"
                                "Gunakan `/trending` untuk melihat token prebonding.",
                                parse_mode=ParseMode.MARKDOWN
                            )
                    else:
                        await update.message.reply_text(
                            f"⚠️ Tidak dapat mengambil data bonding curve untuk token `{token_address}`.\n"
                            "Pastikan ini adalah alamat token letsbonk.fun yang valid.",
                            parse_mode=ParseMode.MARKDOWN
                        )
                else:
                    await update.message.reply_text(
                        f"⚠️ Tidak dapat mengambil data untuk token `{token_address}`.\n"
                        "Pastikan ini adalah alamat token letsbonk.fun yang valid.",
                        parse_mode=ParseMode.MARKDOWN
                    )
        except Exception as e:
            logger.error(f"Error monitoring token {token_address}: {e}")
            await update.message.reply_text(
                f"❌ Error memulai monitoring: {str(e)}"
            )
    
    async def unmonitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unmonitor command"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a token address.\n"
                "Usage: `/unmonitor <token_address>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        token_address = context.args[0].strip()
        
        if user_id in self.user_subscriptions and token_address in self.user_subscriptions[user_id]:
            self.user_subscriptions[user_id].discard(token_address)
            
            if token_address in self.user_alerts.get(user_id, {}):
                del self.user_alerts[user_id][token_address]
            
            # Stop monitoring if no users are subscribed
            if not any(token_address in subs for subs in self.user_subscriptions.values()):
                if token_address in self.monitoring_tasks:
                    self.monitoring_tasks[token_address].cancel()
                    del self.monitoring_tasks[token_address]
            
            await update.message.reply_text(
                f"✅ Stopped monitoring token: `{token_address}`",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                f"❌ You are not monitoring token: `{token_address}`",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a token address.\n"
                "Usage: `/status <token_address>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        token_address = context.args[0].strip()
        await update.message.reply_text(f"🔄 Fetching status for `{token_address}`...", parse_mode=ParseMode.MARKDOWN)
        
        try:
            async with BitqueryClient() as client:
                token_data = await client.get_token_price(token_address)
                bonding_data = await client.get_bonding_curve_progress(token_address)
                
                if token_data or bonding_data:
                    status_message = self.format_token_status(token_address, token_data, bonding_data)
                    await update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text(
                        f"❌ Could not fetch data for token `{token_address}`.\n"
                        "Make sure it's a valid Pump.fun token address.",
                        parse_mode=ParseMode.MARKDOWN
                    )
        except Exception as e:
            logger.error(f"Error fetching status for {token_address}: {e}")
            await update.message.reply_text(f"❌ Error fetching status: {str(e)}")
    
    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list command"""
        user_id = update.effective_user.id
        
        if user_id not in self.user_subscriptions or not self.user_subscriptions[user_id]:
            await update.message.reply_text("📝 You are not monitoring any tokens.")
            return
        
        tokens = list(self.user_subscriptions[user_id])
        message = "📝 **Your Monitored Tokens:**\n\n"
        
        for i, token in enumerate(tokens, 1):
            latest_data = self.token_data.get(token, {})
            
            if latest_data:
                price = latest_data.get('price_usd', 0)
                bonding_progress = latest_data.get('bonding_progress', 0)
                market_cap = price * 1000000000
                
                message += f"{i}. `{token[:8]}...{token[-8:]}`\n"
                message += f"   💰 Price: ${price:.8f}\n"
                message += f"   📊 Market Cap: ${market_cap:,.0f}\n"
                message += f"   📈 Bonding: {bonding_progress:.1f}%\n\n"
            else:
                message += f"{i}. `{token[:8]}...{token[-8:]}`\n"
                message += f"   ⏳ Loading data...\n\n"
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def trending_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trending command - Show prebonding tokens (40-80% bonding curve)"""
        await update.message.reply_text("🔄 Mengambil data token prebonding (40-80% bonding curve)...")
        
        try:
            async with BitqueryClient() as client:
                # Get all tokens and filter for prebonding range
                tokens = await client.get_tokens_by_market_cap_range(0.00001, 0.01)
                
                if not tokens:
                    await update.message.reply_text("📊 Tidak ada token prebonding yang ditemukan saat ini.")
                    return
                
                prebonding_tokens = []
                
                for token_data in tokens:
                    try:
                        trade = token_data.get('Trade', {})
                        currency = trade.get('Currency', {})
                        mint_address = currency.get('MintAddress', '')
                        
                        if mint_address:
                            # Get bonding curve data
                            bonding_data = await client.get_bonding_curve_progress(mint_address)
                            if bonding_data:
                                pool = bonding_data.get('Pool', {})
                                base = pool.get('Base', {})
                                balance = base.get('PostAmount', 0)
                                bonding_progress = client.calculate_bonding_curve_progress(balance)
                                
                                # Filter for prebonding range (40-80%)
                                if 40 <= bonding_progress <= 80:
                                    token_data['bonding_progress'] = bonding_progress
                                    prebonding_tokens.append(token_data)
                    except Exception as e:
                        logger.error(f"Error processing token {mint_address}: {e}")
                        continue
                
                if not prebonding_tokens:
                    await update.message.reply_text("📊 Tidak ada token dalam fase prebonding (40-80%) saat ini.")
                    return
                
                message = "📈 **Trending PreBonding Tokens (40-80% Bonding Curve):**\n\n"
                
                # Sort by bonding progress (descending)
                sorted_tokens = sorted(prebonding_tokens, key=lambda x: x.get('bonding_progress', 0), reverse=True)
                
                for i, token_data in enumerate(sorted_tokens[:10], 1):
                    trade = token_data.get('Trade', {})
                    currency = trade.get('Currency', {})
                    
                    name = currency.get('Name', 'Unknown')
                    symbol = currency.get('Symbol', 'Unknown')
                    mint_address = currency.get('MintAddress', '')
                    price_usd = trade.get('PriceInUSD', 0)
                    market_cap = price_usd * 1000000000
                    bonding_progress = token_data.get('bonding_progress', 0)
                    
                    message += f"{i}. **{name} ({symbol})**\n"
                    message += f"   🏷️ `{mint_address[:8]}...{mint_address[-8:]}`\n"
                    message += f"   💰 ${price_usd:.8f}\n"
                    message += f"   📊 ${market_cap:,.0f}\n"
                    message += f"   📈 Bonding: {bonding_progress:.1f}%\n"
                    
                    # Add status indicator
                    if bonding_progress >= 70:
                        message += f"   🔥 **Mendekati Bonding Phase!**\n\n"
                    elif bonding_progress >= 60:
                        message += f"   ⚡ **Hot PreBonding**\n\n"
                    else:
                        message += f"   🌱 **Early PreBonding**\n\n"
                
                message += "💡 **Tips:** Token ini dalam fase prebonding yang ideal untuk entry sebelum bonding phase!"
                
                await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error fetching prebonding tokens: {e}")
            await update.message.reply_text(f"❌ Error mengambil data token prebonding: {str(e)}")
    
    async def graduating_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /graduating command"""
        await update.message.reply_text("🔄 Fetching tokens about to graduate...")
        
        try:
            async with BitqueryClient() as client:
                # Get tokens above 95% bonding curve progress
                tokens = await client.get_tokens_above_bonding_curve_threshold(95.0)
                
                if not tokens:
                    await update.message.reply_text("🎓 No tokens about to graduate found at the moment.")
                    return
                
                message = "🎓 **Tokens About to Graduate (95%+ Bonding Curve):**\n\n"
                
                for i, pool_data in enumerate(tokens[:10], 1):
                    pool = pool_data.get('Pool', {})
                    market = pool.get('Market', {})
                    base_currency = market.get('BaseCurrency', {})
                    base = pool.get('Base', {})
                    quote = pool.get('Quote', {})
                    
                    name = base_currency.get('Name', 'Unknown')
                    symbol = base_currency.get('Symbol', 'Unknown')
                    mint_address = base_currency.get('MintAddress', '')
                    balance = base.get('PostAmount', 0)
                    price_usd = quote.get('PriceInUSD', 0)
                    
                    # Calculate bonding curve progress
                    bonding_progress = client.calculate_bonding_curve_progress(balance)
                    market_cap = price_usd * 1000000000
                    
                    message += f"{i}. **{name} ({symbol})**\n"
                    message += f"   🏷️ `{mint_address[:8]}...{mint_address[-8:]}`\n"
                    message += f"   📈 Bonding: {bonding_progress:.1f}%\n"
                    message += f"   💰 ${price_usd:.8f}\n"
                    message += f"   📊 ${market_cap:,.0f}\n\n"
                
                await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error fetching graduating tokens: {e}")
            await update.message.reply_text(f"❌ Error fetching graduating tokens: {str(e)}")
    
    async def monitor_bonding_token(self, token_address: str):
        """Monitor a bonding token continuously (real-time for bonding tokens)"""
        logger.info(f"Starting real-time monitoring for bonding token: {token_address}")
        
        while True:
            try:
                async with BitqueryClient() as client:
                    token_data = await client.get_token_price(token_address)
                    bonding_data = await client.get_bonding_curve_progress(token_address)
                    
                    if token_data or bonding_data:
                        price_usd = 0
                        bonding_progress = 0
                        
                        if token_data:
                            trade = token_data.get('Trade', {})
                            price_usd = trade.get('PriceInUSD', 0)
                        
                        if bonding_data:
                            pool = bonding_data.get('Pool', {})
                            base = pool.get('Base', {})
                            balance = base.get('PostAmount', 0)
                            bonding_progress = client.calculate_bonding_curve_progress(balance)
                        
                        # Only monitor if token is in bonding phase (80%+)
                        if bonding_progress >= 80:
                            # Store data
                            self.token_data[token_address] = {
                                'price_usd': price_usd,
                                'bonding_progress': bonding_progress,
                                'last_update': datetime.now(),
                                'token_data': token_data,
                                'bonding_data': bonding_data
                            }
                            
                            # Check for alerts (more frequent for bonding tokens)
                            await self.check_bonding_alerts(token_address, price_usd, bonding_progress)
                        else:
                            # Token moved out of bonding phase, stop monitoring
                            logger.info(f"Token {token_address} is no longer in bonding phase ({bonding_progress:.1f}%)")
                            break
                
                await asyncio.sleep(15)  # Check every 15 seconds for bonding tokens
                
            except asyncio.CancelledError:
                logger.info(f"Monitoring cancelled for bonding token: {token_address}")
                break
            except Exception as e:
                logger.error(f"Error monitoring bonding token {token_address}: {e}")
                await asyncio.sleep(30)  # Wait shorter on error for bonding tokens
    
    async def check_bonding_alerts(self, token_address: str, price_usd: float, bonding_progress: float):
        """Check and send alerts for bonding tokens (more sensitive)"""
        market_cap = price_usd * 1000000000
        
        for user_id, subscriptions in self.user_subscriptions.items():
            if token_address not in subscriptions:
                continue
            
            user_alerts = self.user_alerts.get(user_id, {}).get(token_address, set())
            
            # Check bonding curve thresholds (more sensitive for bonding tokens)
            bonding_thresholds = [85, 90, 95, 98, 99, 99.5]
            
            for threshold in bonding_thresholds:
                alert_key = f"bonding_{threshold}"
                
                if bonding_progress >= threshold and alert_key not in user_alerts:
                    user_alerts.add(alert_key)
                    
                    # Different alert messages based on threshold
                    if threshold >= 99.5:
                        message = f"🔥 **GRADUATION IMMINENT!**\n\n"
                        message += f"Token: `{token_address}`\n"
                        message += f"📈 Bonding Progress: **{bonding_progress:.1f}%**\n"
                        message += f"💰 Price: ${price_usd:.8f}\n"
                        message += f"📊 Market Cap: ${market_cap:,.0f}\n"
                        message += f"🚨 **Token akan segera graduate ke Raydium!**"
                    elif threshold >= 95:
                        message = f"⚡ **HIGH BONDING ALERT!**\n\n"
                        message += f"Token: `{token_address}`\n"
                        message += f"📈 Bonding Progress: **{bonding_progress:.1f}%**\n"
                        message += f"💰 Price: ${price_usd:.8f}\n"
                        message += f"📊 Market Cap: ${market_cap:,.0f}\n"
                        message += f"🎯 **Mendekati graduation!**"
                    else:
                        message = f"📊 **Bonding Progress Update**\n\n"
                        message += f"Token: `{token_address}`\n"
                        message += f"📈 Bonding Progress: **{bonding_progress:.1f}%**\n"
                        message += f"💰 Price: ${price_usd:.8f}\n"
                        message += f"📊 Market Cap: ${market_cap:,.0f}\n"
                    
                    message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    try:
                        await self.application.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.error(f"Error sending bonding alert to user {user_id}: {e}")
    
    async def check_alerts(self, token_address: str, price_usd: float, bonding_progress: float):
        """Check and send alerts for regular tokens"""
        market_cap = price_usd * 1000000000
        
        for user_id, subscriptions in self.user_subscriptions.items():
            if token_address not in subscriptions:
                continue
            
            user_alerts = self.user_alerts.get(user_id, {}).get(token_address, set())
            
            # Check bonding curve thresholds
            for threshold in BONDING_CURVE_ALERT_THRESHOLDS:
                alert_key = f"bonding_{threshold}"
                
                if bonding_progress >= threshold and alert_key not in user_alerts:
                    user_alerts.add(alert_key)
                    
                    message = f"🚨 **Bonding Curve Alert!**\n\n"
                    message += f"Token: `{token_address}`\n"
                    message += f"📈 Bonding Progress: **{bonding_progress:.1f}%**\n"
                    message += f"💰 Price: ${price_usd:.8f}\n"
                    message += f"📊 Market Cap: ${market_cap:,.0f}\n"
                    message += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    try:
                        await self.application.bot.send_message(
                            chat_id=user_id,
                            text=message,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.error(f"Error sending alert to user {user_id}: {e}")
    
    def format_bonding_token_status(self, token_address: str, token_data: Optional[Dict], bonding_data: Optional[Dict]) -> str:
        """Format bonding token status message with real-time info"""
        message = f"🔄 **Real-Time Bonding Token Status**\n\n"
        message += f"🏷️ Address: `{token_address}`\n\n"
        
        if token_data:
            trade = token_data.get('Trade', {})
            currency = trade.get('Currency', {})
            
            name = currency.get('Name', 'Unknown')
            symbol = currency.get('Symbol', 'Unknown')
            price_usd = trade.get('PriceInUSD', 0)
            price_sol = trade.get('Price', 0)
            market_cap = price_usd * 1000000000
            
            message += f"📛 **{name} ({symbol})**\n"
            message += f"💰 Price: ${price_usd:.8f}\n"
            message += f"🪙 Price (SOL): {price_sol:.8f}\n"
            message += f"📊 Market Cap: ${market_cap:,.0f}\n\n"
        
        if bonding_data:
            pool = bonding_data.get('Pool', {})
            base = pool.get('Base', {})
            quote = pool.get('Quote', {})
            
            balance = base.get('PostAmount', 0)
            quote_amount = float(quote.get('PostAmount', 0))
            
            # Calculate bonding curve progress
            client = BitqueryClient()
            bonding_progress = client.calculate_bonding_curve_progress(balance)
            
            message += f"🔥 **BONDING PHASE ACTIVE**\n"
            message += f"📈 **Bonding Progress: {bonding_progress:.1f}%**\n"
            message += f"🏦 Token Balance: {balance:,}\n"
            message += f"💧 SOL Liquidity: {quote_amount:.2f}\n"
            
            # Progress bar
            filled = int(bonding_progress / 5)  # 20 segments
            empty = 20 - filled
            progress_bar = "█" * filled + "░" * empty
            message += f"▓{progress_bar}▓ {bonding_progress:.1f}%\n\n"
            
            # Status indicators
            if bonding_progress >= 99.5:
                message += "🚨 **GRADUATION IMMINENT!**\n"
                message += "⚡ Token akan segera graduate ke Raydium!\n"
            elif bonding_progress >= 95:
                message += "🎯 **MENDEKATI GRADUATION!**\n"
                message += "🔥 Dalam fase bonding tinggi!\n"
            elif bonding_progress >= 90:
                message += "⚡ **HIGH BONDING PHASE!**\n"
                message += "📈 Momentum bonding kuat!\n"
            else:
                message += "🔄 **ACTIVE BONDING PHASE**\n"
                message += "📊 Dalam fase bonding aktif!\n"
        
        if not token_data and not bonding_data:
            message += "❌ Tidak ada data tersedia untuk token ini.\n"
            message += "Pastikan ini adalah alamat token letsbonk.fun yang valid."
        
        message += f"\n⏰ Real-time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        message += f"\n🔄 Update setiap 15 detik"
        
        return message
    
    def format_token_status(self, token_address: str, token_data: Optional[Dict], bonding_data: Optional[Dict]) -> str:
        """Format token status message"""
        message = f"📊 **Token Status**\n\n"
        message += f"🏷️ Address: `{token_address}`\n\n"
        
        if token_data:
            trade = token_data.get('Trade', {})
            currency = trade.get('Currency', {})
            
            name = currency.get('Name', 'Unknown')
            symbol = currency.get('Symbol', 'Unknown')
            price_usd = trade.get('PriceInUSD', 0)
            price_sol = trade.get('Price', 0)
            market_cap = price_usd * 1000000000
            
            message += f"📛 **{name} ({symbol})**\n"
            message += f"💰 Price: ${price_usd:.8f}\n"
            message += f"🪙 Price (SOL): {price_sol:.8f}\n"
            message += f"📊 Market Cap: ${market_cap:,.0f}\n\n"
        
        if bonding_data:
            pool = bonding_data.get('Pool', {})
            base = pool.get('Base', {})
            quote = pool.get('Quote', {})
            
            balance = base.get('PostAmount', 0)
            quote_amount = float(quote.get('PostAmount', 0))
            
            # Calculate bonding curve progress
            client = BitqueryClient()
            bonding_progress = client.calculate_bonding_curve_progress(balance)
            
            message += f"📈 **Bonding Curve Progress: {bonding_progress:.1f}%**\n"
            message += f"🏦 Token Balance: {balance:,}\n"
            message += f"💧 SOL Liquidity: {quote_amount:.2f}\n"
            
            # Progress bar
            filled = int(bonding_progress / 5)  # 20 segments
            empty = 20 - filled
            progress_bar = "█" * filled + "░" * empty
            message += f"▓{progress_bar}▓ {bonding_progress:.1f}%\n\n"
            
            if bonding_progress >= 100:
                message += "🎓 **Token has graduated to Raydium!**\n"
            elif bonding_progress >= 95:
                message += "🚨 **Token is about to graduate!**\n"
        
        if not token_data and not bonding_data:
            message += "❌ No data available for this token.\n"
            message += "Make sure it's a valid Pump.fun token address."
        
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return message
    
    async def run(self):
        """Run the bot"""
        logger.info("Starting Bonding Curve Monitor Bot...")
        
        # Start the bot
        await self.application.run_polling()

if __name__ == "__main__":
    bot = BondingCurveMonitorBot()
    bot.application.run_polling()