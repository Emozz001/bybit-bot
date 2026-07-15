"""Bybit AI Futures Trading Bot

A professional, production-quality cryptocurrency futures trading bot for Bybit USDT Perpetual Futures.

## Features

- **Market Scanner**: Continuously scans all USDT perpetual contracts
- **Multi-Timeframe Analysis**: Analyzes 1m to 1D timeframes
- **Technical Indicators**: EMA, RSI, MACD, ATR, Bollinger Bands, and more
- **Opportunity Scoring**: AI-powered scoring system (0-100)
- **Risk Management**: Configurable risk per trade, loss limits, position limits
- **Position Management**: Trailing stops, partial exits, dynamic stop-loss
- **Terminal Dashboard**: Beautiful real-time UI using Rich
- **Trade Journal**: Complete trade history with analytics
- **Paper Trading**: Test strategies without risking real capital
- **Telegram Integration**: Receive notifications and control the bot

## Requirements

- Python 3.12+
- macOS Monterey or later (optimized for MacBook Air 2017)
- Bybit API credentials (testnet recommended for testing)

## Installation

1. Clone the repository:
```bash
cd bybit_ai_trader
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the bot:
```bash
cp .env.example .env
# Edit .env with your API credentials
```

5. Run the bot:
```bash
python main.py
```

## Configuration

Edit `config/settings.yaml` to customize:

- Trading mode (paper/live)
- Risk parameters
- Indicator settings
- Dashboard refresh rate
- Telegram notifications

## Project Structure

```
bybit_ai_trader/
├── main.py              # Main entry point
├── requirements.txt     # Python dependencies
├── config/
│   └── settings.yaml    # Configuration file
├── core/                # Core utilities (config, logging)
├── exchange/            # Bybit API integration
├── scanner/             # Market scanning engine
├── indicators/          # Technical indicators
├── strategy/            # Trading strategies
├── execution/           # Order execution
├── risk/                # Risk management
├── position/            # Position management
├── portfolio/           # Portfolio analytics
├── analytics/           # Performance analytics
├── ai/                  # AI/ML components
├── backtest/            # Backtesting engine
├── dashboard/           # Terminal UI
├── database/            # SQLite database
└── logs/                # Log files
```

## Safety Features

- **Paper Trading Mode**: Test without real money (enabled by default)
- **Daily Loss Limits**: Automatic circuit breaker
- **Position Limits**: Maximum concurrent positions
- **API Key Security**: Keys stored in .env file
- **Graceful Shutdown**: Clean exit on signals

## Important Disclaimer

This trading bot is designed to identify high-quality trading opportunities and manage risk responsibly. 

**NO TRADING STRATEGY CAN GUARANTEE PROFITS.** 

Past performance does not indicate future results. Always:
- Start with paper trading
- Test thoroughly before live deployment
- Only risk capital you can afford to lose
- Monitor the bot regularly
- Keep software updated

## License

MIT License - See LICENSE file for details

## Support

For issues and feature requests, please open an issue on GitHub.

---

**Version**: 1.0.0  
**Author**: AI Assistant  
**Last Updated**: 2024