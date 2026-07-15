"""Advanced Risk Management Module."""

import math
from dataclasses import dataclass
from typing import Optional


@dataclass
class AdvancedRiskMetrics:
    """Comprehensive risk metrics for a trade."""
    symbol: str
    side: str
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    risk_amount: float
    risk_reward_ratio: float
    leverage: int
    liquidation_price: float
    kelly_fraction: float
    var_95: float
    correlation_risk: float
    volatility_adjusted_size: float


class AdvancedRiskManager:
    """Advanced risk management with Kelly Criterion, VaR, and correlation control."""
    
    def __init__(self, config):
        self.config = config
        self.kelly_multiplier = getattr(config, 'kelly_multiplier', 0.5)
        self.max_portfolio_exposure = getattr(config, 'max_portfolio_exposure', 1.5)
        self.max_correlation = getattr(config, 'max_correlation', 0.7)
        self.var_confidence = getattr(config, 'var_confidence_level', 0.95)
        self.max_var_limit = getattr(config, 'max_var_limit', 3.0)
        self.max_drawdown = getattr(config, 'max_drawdown', 5.0)
        self._daily_pnl = 0.0
        self._current_exposure = 0.0
        self._open_positions_count = 0
        self._consecutive_losses = 0
        self._peak_equity = 0.0
        self._current_drawdown = 0.0
    
    def calculate_kelly_position_size(self, win_rate, avg_win, avg_loss, account_balance, entry_price, stop_loss):
        if win_rate <= 0 or avg_loss <= 0:
            return account_balance * 0.01 / abs(entry_price - stop_loss)
        p = win_rate
        q = 1 - win_rate
        b = avg_win / avg_loss if avg_loss > 0 else 0
        kelly_fraction = (p * b - q) / b if b > 0 else 0
        kelly_fraction *= self.kelly_multiplier
        kelly_fraction = max(0.0025, min(0.05, kelly_fraction))
        risk_amount = account_balance * kelly_fraction
        sl_distance = abs(entry_price - stop_loss)
        if sl_distance > 0 and entry_price > 0:
            position_size_usdt = risk_amount / (sl_distance / entry_price)
            return position_size_usdt / entry_price
        return 0
    
    def calculate_var(self, position_value, volatility, holding_period=1):
        daily_volatility = volatility / math.sqrt(252)
        period_volatility = daily_volatility * math.sqrt(holding_period)
        z_scores = {0.95: 1.645, 0.99: 2.326, 0.90: 1.282}
        z_score = z_scores.get(self.var_confidence, 1.645)
        return position_value * z_score * period_volatility
    
    def get_risk_summary(self, account_balance):
        return {
            'daily_pnl': self._daily_pnl,
            'current_exposure': self._current_exposure,
            'exposure_pct': (self._current_exposure / account_balance) * 100 if account_balance > 0 else 0,
            'open_positions': self._open_positions_count,
            'consecutive_losses': self._consecutive_losses,
            'current_drawdown': self._current_drawdown,
        }
