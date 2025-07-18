import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BITQUERY_API_KEY = os.getenv('BITQUERY_API_KEY')

# API Endpoints
BITQUERY_GRAPHQL_URL = "https://streaming.bitquery.io/eap"
BITQUERY_WEBSOCKET_URL = "wss://streaming.bitquery.io/eap"

# Solana Program Addresses
PUMP_FUN_PROGRAM_ADDRESS = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
RAYDIUM_PROGRAM_ADDRESS = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

# Bonding Curve Constants
PUMP_FUN_TOTAL_SUPPLY = 1000000000  # 1 Billion tokens
PUMP_FUN_RESERVED_TOKENS = 206900000  # Reserved tokens
PUMP_FUN_INITIAL_REAL_TOKEN_RESERVES = 793100000  # Initial real token reserves

# Monitoring thresholds
BONDING_CURVE_ALERT_THRESHOLDS = [50, 75, 90, 95, 99]  # Percentage thresholds
MARKET_CAP_ALERT_THRESHOLDS = [10000, 50000, 100000, 500000, 1000000]  # USD thresholds

# Update intervals (in seconds)
PRICE_UPDATE_INTERVAL = 10
BONDING_CURVE_UPDATE_INTERVAL = 30
MARKET_CAP_UPDATE_INTERVAL = 60