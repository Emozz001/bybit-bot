"""
Core Constants for the Trading Bot.

Centralized constants for timeouts, limits, and default values.
"""

# API Timeouts
API_TIMEOUT = 30  # seconds
WS_RECONNECT_DELAY = 5  # seconds
WS_MAX_RECONNECT_ATTEMPTS = 5

# Rate Limits
RATE_LIMIT_DELAY = 0.08  # 80ms between requests
MAX_CONCURRENT_REQUESTS = 10

# Position Limits
MAX_POSITIONS = 5
MAX_LEVERAGE = 100
MIN_LEVERAGE = 1

# Risk Defaults
DEFAULT_RISK_PER_TRADE = 1.0  # percentage of account
DEFAULT_DAILY_LOSS_LIMIT = 5.0  # percentage
DEFAULT_WEEKLY_LOSS_LIMIT = 10.0  # percentage
DEFAULT_MONTHLY_LOSS_LIMIT = 20.0  # percentage
DEFAULT_MIN_RISK_REWARD = 2.0

# Trading Defaults
DEFAULT_OPPORTUNITY_THRESHOLD = 90  # score 0-100
DEFAULT_SCAN_INTERVAL = 5  # seconds
DEFAULT_MONITOR_INTERVAL = 2  # seconds

# Database Defaults
DB_PATH = "database/trading.db"
DB_TIMEOUT = 30  # seconds
DB_CACHE_SIZE_MB = 64

# Dashboard Defaults
DASHBOARD_REFRESH_RATE = 1.0  # seconds
TOP_OPPORTUNITIES_COUNT = 10

# Logging Defaults
LOG_LEVEL = "INFO"
LOG_ROTATION_SIZE_MB = 10
LOG_BACKUP_COUNT = 5

# Indicator Defaults
RSI_PERIOD = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ATR_PERIOD = 14
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2.0
EMA_PERIODS = [20, 50, 100, 200]
DEFAULT_TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]

# Cache TTL
CACHE_TTL_SECONDS = 5  # Market data cache expiration

# Scanner Defaults
SCANNER_MAX_CONCURRENT_REQUESTS = 20
