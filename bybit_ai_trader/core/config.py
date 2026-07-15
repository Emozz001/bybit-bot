"""
Configuration management for the trading bot.

Loads configuration from .env and config/settings.yaml files.
Uses Pydantic for validation and type safety.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


class TradingConfig(BaseModel):
    """Trading configuration."""
    
    mode: str = Field(default="paper", description="Trading mode: paper or live")
    symbols: str | list[str] = Field(default="all", description="Symbols to trade")
    opportunity_threshold: int = Field(default=90, ge=0, le=100)
    max_positions: int = Field(default=5, ge=1)
    max_leverage: int = Field(default=10, ge=1, le=100)


class RiskConfig(BaseModel):
    """Risk management configuration."""
    
    risk_per_trade: float = Field(default=1.0, gt=0, le=100)
    daily_loss_limit: float = Field(default=5.0, gt=0)
    weekly_loss_limit: float = Field(default=10.0, gt=0)
    monthly_loss_limit: float = Field(default=20.0, gt=0)
    min_risk_reward: float = Field(default=2.0, gt=0)


class IndicatorConfig(BaseModel):
    """Technical indicator configuration."""
    
    timeframes: list[str] = Field(
        default=["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]
    )
    ema_periods: list[int] = Field(default=[20, 50, 100, 200])
    rsi_period: int = Field(default=14, gt=0)
    macd_fast: int = Field(default=12, gt=0)
    macd_slow: int = Field(default=26, gt=0)
    macd_signal: int = Field(default=9, gt=0)
    atr_period: int = Field(default=14, gt=0)
    bollinger_period: int = Field(default=20, gt=0)
    bollinger_std: float = Field(default=2.0, gt=0)


class ExecutionConfig(BaseModel):
    """Order execution configuration."""
    
    default_sl_type: str = Field(default="stop_loss")
    default_tp_type: str = Field(default="take_profit")
    use_trailing_stop: bool = Field(default=True)
    partial_exits: bool = Field(default=True)


class DashboardConfig(BaseModel):
    """Dashboard configuration."""
    
    refresh_rate: float = Field(default=1.0, gt=0)
    show_all_symbols: bool = Field(default=False)
    top_opportunities_count: int = Field(default=10, gt=0)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO")
    save_to_file: bool = Field(default=True)
    rotation_size_mb: int = Field(default=10, gt=0)
    backup_count: int = Field(default=5, gt=0)


class TelegramConfig(BaseModel):
    """Telegram notification configuration."""
    
    enabled: bool = Field(default=False)
    notify_on_trade: bool = Field(default=True)
    notify_on_error: bool = Field(default=True)
    daily_summary: bool = Field(default=True)
    bot_token: str = Field(default="")
    chat_id: str = Field(default="")


class ExchangeConfig(BaseModel):
    """Exchange API configuration."""
    
    api_key: str = Field(default="")
    api_secret: str = Field(default="")
    testnet: bool = Field(default=True)


class DatabaseConfig(BaseModel):
    """Database configuration."""
    
    path: str = Field(default="database/trading.db")


class Config(BaseModel):
    """Main configuration class."""
    
    trading: TradingConfig = Field(default_factory=TradingConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    indicators: IndicatorConfig = Field(default_factory=IndicatorConfig)
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    exchange: ExchangeConfig = Field(default_factory=ExchangeConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    @classmethod
    def load(cls, config_path: str = "config/settings.yaml") -> "Config":
        """Load configuration from files and environment variables."""
        
        # Load environment variables
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)
        
        # Load YAML config
        config_data: dict[str, Any] = {}
        yaml_path = Path(config_path)
        if yaml_path.exists():
            with open(yaml_path, "r") as f:
                config_data = yaml.safe_load(f) or {}
        
        # Build configuration from environment and YAML
        exchange_config = {
            "api_key": os.getenv("BYBIT_API_KEY", ""),
            "api_secret": os.getenv("BYBIT_API_SECRET", ""),
            "testnet": os.getenv("BYBIT_TESTNET", "true").lower() == "true",
        }
        
        telegram_config = {
            "enabled": os.getenv("TELEGRAM_BOT_TOKEN") is not None,
            "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
            "chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
        }
        
        database_config = {
            "path": os.getenv("DATABASE_PATH", "database/trading.db"),
        }
        
        # Merge with YAML data
        if "trading" in config_data:
            trading_data = config_data["trading"]
        else:
            trading_data = {}
        
        if "risk" in config_data:
            risk_data = config_data["risk"]
        else:
            risk_data = {}
        
        if "indicators" in config_data:
            indicator_data = config_data["indicators"]
        else:
            indicator_data = {}
        
        if "execution" in config_data:
            execution_data = config_data["execution"]
        else:
            execution_data = {}
        
        if "dashboard" in config_data:
            dashboard_data = config_data["dashboard"]
        else:
            dashboard_data = {}
        
        if "logging" in config_data:
            logging_data = config_data["logging"]
        else:
            logging_data = {}
        
        if "telegram" in config_data:
            telegram_data = {**telegram_config, **config_data["telegram"]}
        else:
            telegram_data = telegram_config
        
        if "database" in config_data:
            database_data = {**database_config, **config_data["database"]}
        else:
            database_data = database_config
        
        return cls(
            trading=TradingConfig(**trading_data),
            risk=RiskConfig(**risk_data),
            indicators=IndicatorConfig(**indicator_data),
            execution=ExecutionConfig(**execution_data),
            dashboard=DashboardConfig(**dashboard_data),
            logging=LoggingConfig(**logging_data),
            telegram=TelegramConfig(**telegram_data),
            exchange=ExchangeConfig(**exchange_config),
            database=DatabaseConfig(**database_data),
        )
