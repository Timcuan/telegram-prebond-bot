#!/usr/bin/env python3
"""
Solana Bonding Curve Monitor Bot
A Telegram bot for monitoring Solana token bonding curves using Bitquery API
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
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
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🎯 **Solana Bonding Curve Monitor Bot**

Welcome! This bot monitors Solana tokens' bonding curve progress and market cap using real-time data from Bitquery.

**Available Commands:**
• `/monitor <token_address>` - Start monitoring a token
• `/unmonitor <token_address>` - Stop monitoring a token
• `/status <token_address>` - Get current token status
• `/list` - Show your monitored tokens
• `/trending` - Show trending tokens by market cap
• `/graduating` - Show tokens about to graduate (95%+ bonding curve)
• `/help` - Show this help message

**Features:**
✅ Real-time bonding curve progress tracking
✅ Market cap monitoring with alerts
✅ Price alerts and notifications
✅ Graduation alerts (when tokens move to Raydium)
✅ Trending token discovery

Start monitoring with `/monitor <token_address>`

Example: `/monitor 2Z4FzKBcw48KBD2PaR4wtxo4sYGbS7QqTQCLoQnUpump`
        """
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await self.start_command(update, context)
    
    async def monitor_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /monitor command"""
        user_id = update.effective_user.id
        
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a token address.\n"
                "Usage: `/monitor <token_address>`\n\n"
                "Example: `/monitor 2Z4FzKBcw48KBD2PaR4wtxo4sYGbS7QqTQCLoQnUpump`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        token_address = context.args[0].strip()
        
        # Basic validation
        if len(token_address) < 32 or len(token_address) > 44:
            await update.message.reply_text(
                "❌ Invalid token address format. Please provide a valid Solana token address."
            )
            return
        
        # Initialize user data
        if user_id not in self.user_subscriptions:
            self.user_subscriptions[user_id] = set()
            self.user_alerts[user_id] = {}
        
        self.user_subscriptions[user_id].add(token_address)
        
        if token_address not in self.user_alerts[user_id]:
            self.user_alerts[user_id][token_address] = set()
        
        await update.message.reply_text(f"🔄 Starting to monitor token: `{token_address}`", parse_mode=ParseMode.MARKDOWN)
        
        # Start monitoring task if not already running
        if token_address not in self.monitoring_tasks:
            task = asyncio.create_task(self.monitor_token(token_address))
            self.monitoring_tasks[token_address] = task
        
        # Get initial status
        try:
            async with BitqueryClient() as client:
                token_data = await client.get_token_price(token_address)
                bonding_data = await client.get_bonding_curve_progress(token_address)
                
                if token_data or bonding_data:
                    status_message = self.format_token_status(token_address, token_data, bonding_data)
                    await update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text(
                        f"⚠️ Could not fetch data for token `{token_address}`.\n"
                        "Make sure it's a valid Pump.fun token address.",
                        parse_mode=ParseMode.MARKDOWN
                    )
        except Exception as e:
            logger.error(f"Error monitoring token {token_address}: {e}")
            await update.message.reply_text(
                f"❌ Error starting monitoring: {str(e)}"
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
        """Handle /trending command"""
        await update.message.reply_text("🔄 Fetching trending tokens...")
        
        try:
            async with BitqueryClient() as client:
                # Get tokens with market cap between 10K and 1M
                tokens = await client.get_tokens_by_market_cap_range(0.00001, 0.001)
                
                if not tokens:
                    await update.message.reply_text("📊 No trending tokens found at the moment.")
                    return
                
                message = "📈 **Trending Tokens (by Market Cap):**\n\n"
                
                # Sort by market cap
                sorted_tokens = sorted(tokens, key=lambda x: x.get('Trade', {}).get('PriceInUSD', 0), reverse=True)
                
                for i, token_data in enumerate(sorted_tokens[:10], 1):
                    trade = token_data.get('Trade', {})
                    currency = trade.get('Currency', {})
                    
                    name = currency.get('Name', 'Unknown')
                    symbol = currency.get('Symbol', 'Unknown')
                    mint_address = currency.get('MintAddress', '')
                    price_usd = trade.get('PriceInUSD', 0)
                    market_cap = price_usd * 1000000000
                    
                    message += f"{i}. **{name} ({symbol})**\n"
                    message += f"   🏷️ `{mint_address[:8]}...{mint_address[-8:]}`\n"
                    message += f"   💰 ${price_usd:.8f}\n"
                    message += f"   📊 ${market_cap:,.0f}\n\n"
                
                await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Error fetching trending tokens: {e}")
            await update.message.reply_text(f"❌ Error fetching trending tokens: {str(e)}")
    
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
                    balance = int(base.get('PostAmount', 0))
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
    
    async def monitor_token(self, token_address: str):
        """Monitor a token continuously"""
        logger.info(f"Starting monitoring for token: {token_address}")
        
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
                            balance = int(base.get('PostAmount', 0))
                            bonding_progress = client.calculate_bonding_curve_progress(balance)
                        
                        # Store data
                        self.token_data[token_address] = {
                            'price_usd': price_usd,
                            'bonding_progress': bonding_progress,
                            'last_update': datetime.now(),
                            'token_data': token_data,
                            'bonding_data': bonding_data
                        }
                        
                        # Check for alerts
                        await self.check_alerts(token_address, price_usd, bonding_progress)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                logger.info(f"Monitoring cancelled for token: {token_address}")
                break
            except Exception as e:
                logger.error(f"Error monitoring token {token_address}: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def check_alerts(self, token_address: str, price_usd: float, bonding_progress: float):
        """Check and send alerts for a token"""
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
            
            balance = int(base.get('PostAmount', 0))
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