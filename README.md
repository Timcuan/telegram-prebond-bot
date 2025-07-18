# Solana Bonding Curve Monitor Bot

A Telegram bot that monitors Solana token bonding curves in real-time using the Bitquery API. This bot tracks Pump.fun tokens and provides alerts when bonding curve progress reaches specified thresholds.

## Features

- 🔄 **Real-time monitoring** of Solana token bonding curves
- 📈 **Bonding curve progress tracking** with visual progress bars
- 💰 **Price and market cap monitoring** with USD and SOL values
- 🚨 **Customizable alerts** for bonding curve thresholds (50%, 75%, 90%, 95%, 99%)
- 🎓 **Graduation alerts** when tokens move from Pump.fun to Raydium
- 📊 **Trending tokens** discovery by market cap
- 🏆 **About to graduate** tokens (95%+ bonding curve progress)
- 👥 **Multi-user support** with individual subscriptions
- 📱 **Simple Telegram interface** with easy-to-use commands

## Prerequisites

- Python 3.8 or higher
- Telegram Bot Token (from @BotFather)
- Bitquery API Key (from https://bitquery.io/)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd solana-bonding-curve-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file and add your API keys:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   BITQUERY_API_KEY=your_bitquery_api_key_here
   ```

## Getting API Keys

### Telegram Bot Token

1. Open Telegram and search for @BotFather
2. Start a chat and send `/newbot`
3. Follow the instructions to create your bot
4. Copy the bot token provided

### Bitquery API Key

1. Go to https://bitquery.io/
2. Sign up for a free account
3. Navigate to your dashboard
4. Generate an API key
5. Copy the API key

## Usage

### Starting the Bot

```bash
python main.py
```

### Bot Commands

- `/start` - Welcome message and bot introduction
- `/help` - Show help message with available commands
- `/monitor <token_address>` - Start monitoring a specific token
- `/unmonitor <token_address>` - Stop monitoring a token
- `/status <token_address>` - Get current status of a token
- `/list` - Show all your monitored tokens
- `/trending` - Show trending tokens by market cap
- `/graduating` - Show tokens about to graduate (95%+ bonding curve)

### Example Usage

```
/monitor 2Z4FzKBcw48KBD2PaR4wtxo4sYGbS7QqTQCLoQnUpump
/status 2Z4FzKBcw48KBD2PaR4wtxo4sYGbS7QqTQCLoQnUpump
/list
/trending
/graduating
```

## How It Works

### Bonding Curve Monitoring

The bot uses the Bitquery API to monitor Pump.fun tokens and calculates bonding curve progress using the formula:

```
BondingCurveProgress = 100 - (((balance - 206900000) * 100) / 793100000)
```

Where:
- `balance` = Token balance at the market address
- `206900000` = Reserved tokens for Pump.fun
- `793100000` = Initial real token reserves

### Alert System

The bot sends alerts when tokens reach these bonding curve thresholds:
- 50% - Early stage alert
- 75% - Mid-stage alert  
- 90% - Late stage alert
- 95% - About to graduate alert
- 99% - Almost graduated alert

### Market Cap Calculation

Market cap is calculated as:
```
Market Cap = Token Price (USD) × 1,000,000,000 (total supply)
```

## Configuration

You can modify the following settings in `config.py`:

- `BONDING_CURVE_ALERT_THRESHOLDS` - Alert thresholds for bonding curve progress
- `MARKET_CAP_ALERT_THRESHOLDS` - Alert thresholds for market cap
- `BONDING_CURVE_UPDATE_INTERVAL` - How often to check bonding curve progress (seconds)
- `PRICE_UPDATE_INTERVAL` - How often to check price updates (seconds)

## File Structure

```
solana-bonding-curve-bot/
├── main.py                 # Main bot application
├── bitquery_client.py      # Bitquery API client
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables example
├── .env                  # Your environment variables (create this)
└── README.md            # This file
```

## API Endpoints Used

The bot uses the following Bitquery GraphQL endpoints:

1. **Token Price Monitoring:**
   - `DEXTradeByTokens` - Get latest token prices
   
2. **Bonding Curve Progress:**
   - `DEXPools` - Get pool liquidity data for bonding curve calculation
   
3. **Trending Tokens:**
   - `DEXTradeByTokens` with market cap filters
   
4. **Graduating Tokens:**
   - `DEXPools` with bonding curve progress filters

## Troubleshooting

### Common Issues

1. **"Could not fetch token data"**
   - Make sure the token address is valid
   - Verify the token is a Pump.fun token
   - Check your Bitquery API key

2. **Bot not responding**
   - Verify your Telegram bot token
   - Check if the bot is running
   - Check the logs for error messages

3. **API rate limits**
   - Bitquery has rate limits on free plans
   - Consider upgrading your Bitquery plan for higher limits

### Logs

The bot logs important events and errors. Check the console output for:
- Token monitoring start/stop events
- API errors
- Alert sending status

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Disclaimer

This bot is for educational and informational purposes only. It is not financial advice. Always do your own research before making investment decisions.

## Support

If you encounter any issues or have questions:

1. Check the troubleshooting section
2. Review the logs for error messages
3. Open an issue on GitHub
4. Contact the maintainers

## Acknowledgments

- [Bitquery](https://bitquery.io/) for providing the Solana blockchain data API
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) library
- Solana and Pump.fun communities for documentation and support