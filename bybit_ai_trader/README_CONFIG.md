# Configuration Management Guide

## Overview

The Bybit AI Trader now supports centralized configuration management through a `config.env` file that synchronizes settings across both `.env` and `config/settings.yaml` files.

## File Structure

```
bybit_ai_trader/
├── config.env          # Central configuration file (EDIT THIS)
├── .env                # Environment variables (auto-synced)
└── config/
    └── settings.yaml   # YAML settings (auto-synced)
```

## How It Works

1. **Edit `config.env`**: This is your single source of truth for all configuration
2. **Sync Configuration**: The script automatically syncs changes to:
   - `.env` - For environment variables used by Python
   - `config/settings.yaml` - For structured YAML configuration

## Usage via Menu

Run `./bybit_trader.sh` and select from these new options:

- **Option 6**: Edit Configuration (opens config.env in your text editor)
- **Option 7**: Set Individual Config Value (quick edit for common settings)
- **Option 8**: Sync Configuration Files (manually sync config.env to .env and settings.yaml)

## Configuration Options in config.env

### Environment Variables (.env)
- `BYBIT_API_KEY` - Your Bybit API key
- `BYBIT_API_SECRET` - Your Bybit API secret
- `BYBIT_TESTNET` - Use testnet (true/false)
- `TRADING_MODE` - paper or live
- `RISK_PER_TRADE` - Risk percentage per trade
- `MAX_LEVERAGE` - Maximum leverage
- `MAX_POSITIONS` - Maximum concurrent positions
- `DAILY_LOSS_LIMIT` - Daily loss limit percentage
- `WEEKLY_LOSS_LIMIT` - Weekly loss limit percentage
- `MONTHLY_LOSS_LIMIT` - Monthly loss limit percentage
- `OPPORTUNITY_THRESHOLD` - Minimum score for opportunities
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `TELEGRAM_CHAT_ID` - Telegram chat ID
- `DATABASE_PATH` - Path to SQLite database
- `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

### YAML Settings (settings.yaml)
- `YAML_TIMEFRAMES` - Comma-separated timeframes (e.g., "1m,3m,5m,15m")
- `YAML_EMA_PERIODS` - Comma-separated EMA periods (e.g., "20,50,100,200")
- `YAML_RSI_PERIOD` - RSI period
- `YAML_MACD_FAST` - MACD fast period
- `YAML_MACD_SLOW` - MACD slow period
- `YAML_MACD_SIGNAL` - MACD signal period
- `YAML_ATR_PERIOD` - ATR period
- `YAML_BOLLINGER_PERIOD` - Bollinger Bands period
- `YAML_BOLLINGER_STD` - Bollinger Bands standard deviation
- `YAML_DEFAULT_SL_TYPE` - Default stop-loss type
- `YAML_DEFAULT_TP_TYPE` - Default take-profit type
- `YAML_USE_TRAILING_STOP` - Enable trailing stops (true/false)
- `YAML_PARTIAL_EXITS` - Enable partial exits (true/false)
- `YAML_REFRESH_RATE` - Dashboard refresh rate in seconds
- `YAML_SHOW_ALL_SYMBOLS` - Show all symbols in dashboard (true/false)
- `YAML_TOP_OPPORTUNITIES_COUNT` - Number of top opportunities to display
- `YAML_SAVE_TO_FILE` - Save logs to file (true/false)
- `YAML_ROTATION_SIZE_MB` - Log rotation size in MB
- `YAML_BACKUP_COUNT` - Number of log backups to keep
- `YAML_TELEGRAM_ENABLED` - Enable Telegram notifications (true/false)
- `YAML_NOTIFY_ON_TRADE` - Notify on trade execution (true/false)
- `YAML_NOTIFY_ON_ERROR` - Notify on errors (true/false)
- `YAML_DAILY_SUMMARY` - Send daily summary (true/false)

## Quick Start

1. Run `./bybit_trader.sh`
2. Select option 6 to edit configuration
3. Modify the values you need
4. Save and exit the editor
5. When prompted, choose 'y' to sync configuration
6. Your changes are now applied to both `.env` and `config/settings.yaml`

## Manual Sync

If you edit `config.env` directly with a text editor, run option 8 to sync the changes.

## Example: Change Trading Mode

**Method 1: Using Menu Option 7**
```
Select option 7
Enter: 3 (TRADING_MODE)
Enter value: live
Sync now? y
```

**Method 2: Edit config.env Directly**
```bash
nano config.env
# Change: TRADING_MODE=paper → TRADING_MODE=live
# Save and exit
./bybit_trader.sh → Option 8 (Sync)
```

## Backup Configuration

Your original `.env` and `config/settings.yaml` files are preserved. The sync operation updates existing values or adds new ones without deleting custom configurations.
