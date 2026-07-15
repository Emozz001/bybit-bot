"""Risk Management Module.

Provides risk calculation, position sizing, and circuit breaker functionality.
"""

import logging
from dataclasses import dataclass
from typing import Any


@dataclass
class RiskMetrics:
    """Risk metrics for a potential trade."""
    
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


class RiskManager:
    """
    Risk management engine.
    
    Calculates position sizes, validates trades against risk limits,
    and monitors portfolio exposure.
    """

    def __init__(self, config, logger=None):
        """
        Initialize risk manager.
        
        Args:
            config: Configuration object with risk settings
            logger: Logger instance for logging messages
        """
        self.config = config
        self.logger = logger or logging.getLogger("bybit_trader.risk")
        
        # Risk state
        self._daily_pnl = 0.0
        self._weekly_pnl = 0.0
        self._monthly_pnl = 0.0
        self._current_exposure = 0.0
        self._open_positions_count = 0

    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss_price: float,
        risk_percentage: float | None = None,
        atr: float = 0,
    ) -> float:
        """
        Calculate optimal position size based on risk parameters.
        
        Args:
            account_balance: Total account balance in USDT
            entry_price: Entry price
            stop_loss_price: Stop loss price
            risk_percentage: Risk per trade as percentage (default from config)
            atr: Average True Range for volatility adjustment
            
        Returns:
            Position size in base currency
        """
        if risk_percentage is None:
            risk_percentage = self.config.risk.risk_per_trade
        
        # Calculate risk amount in USDT
        risk_amount = account_balance * (risk_percentage / 100)
        
        # Calculate stop loss distance
        if stop_loss_price > 0 and entry_price > 0:
            sl_distance_pct = abs(entry_price - stop_loss_price) / entry_price
            
            if sl_distance_pct > 0:
                # Position size = Risk Amount / SL Distance
                position_size_usdt = risk_amount / sl_distance_pct
                
                # Convert to base currency
                position_size = position_size_usdt / entry_price
                
                return position_size
        
        # Fallback: use ATR-based sizing
        if atr > 0:
            position_size_usdt = risk_amount / (atr * 2)  # 2x ATR
            return position_size_usdt / entry_price
        
        return 0

    def validate_trade(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        position_size: float,
        account_balance: float,
    ) -> tuple[bool, str]:
        """
        Validate a trade against risk rules.
        
        Args:
            symbol: Trading pair symbol
            side: Buy or Sell
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            position_size: Position size
            account_balance: Account balance
            
        Returns:
            Tuple of (is_valid, reason)
        """
        # Check daily loss limit
        if self._daily_pnl < -self.config.risk.daily_loss_limit:
            return False, "Daily loss limit reached"
        
        # Check weekly loss limit
        if self._weekly_pnl < -self.config.risk.weekly_loss_limit:
            return False, "Weekly loss limit reached"
        
        # Check monthly loss limit
        if self._monthly_pnl < -self.config.risk.monthly_loss_limit:
            return False, "Monthly loss limit reached"
        
        # Check maximum positions
        if self._open_positions_count >= self.config.trading.max_positions:
            return False, f"Maximum positions ({self.config.trading.max_positions}) reached"
        
        # Calculate risk/reward ratio
        if entry_price > 0 and stop_loss > 0 and take_profit > 0:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            
            if risk > 0:
                rr_ratio = reward / risk
                
                if rr_ratio < self.config.risk.min_risk_reward:
                    return False, f"Risk/Reward ratio {rr_ratio:.2f} below minimum {self.config.risk.min_risk_reward}"
        
        # Check leverage
        # (Leverage check would go here)
        
        return True, "Trade validated"

    def calculate_risk_metrics(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        position_size: float,
        leverage: int,
        account_balance: float,
    ) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics for a trade.
        
        Args:
            symbol: Trading pair symbol
            side: Buy or Sell
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            position_size: Position size
            leverage: Leverage multiplier
            account_balance: Account balance
            
        Returns:
            RiskMetrics dataclass
        """
        # Calculate risk amount
        if side == "Buy":
            risk_amount = (entry_price - stop_loss) * position_size
        else:
            risk_amount = (stop_loss - entry_price) * position_size
        
        # Calculate reward amount
        if side == "Buy":
            reward_amount = (take_profit - entry_price) * position_size
        else:
            reward_amount = (entry_price - take_profit) * position_size
        
        # Calculate risk/reward ratio
        if risk_amount > 0:
            rr_ratio = reward_amount / risk_amount
        else:
            rr_ratio = 0
        
        # Estimate liquidation price
        if leverage > 0:
            if side == "Buy":
                liquidation_price = entry_price * (1 - 1/leverage + 0.005)  # 0.5% buffer
            else:
                liquidation_price = entry_price * (1 + 1/leverage - 0.005)
        else:
            liquidation_price = 0
        
        return RiskMetrics(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            risk_amount=risk_amount,
            risk_reward_ratio=rr_ratio,
            leverage=leverage,
            liquidation_price=liquidation_price,
        )

    def update_daily_pnl(self, pnl: float):
        """Update daily PnL tracking."""
        self._daily_pnl += pnl

    def reset_daily_pnl(self):
        """Reset daily PnL (call at start of new day)."""
        self._daily_pnl = 0.0

    def increment_positions(self):
        """Increment open positions count."""
        self._open_positions_count += 1

    def decrement_positions(self):
        """Decrement open positions count."""
        if self._open_positions_count > 0:
            self._open_positions_count -= 1

    def get_current_exposure(self) -> float:
        """Get current total exposure."""
        return self._current_exposure

    def should_halt_trading(self) -> bool:
        """
        Check if trading should be halted due to risk limits.
        
        Returns:
            True if trading should stop, False otherwise
        """
        if self._daily_pnl < -self.config.risk.daily_loss_limit:
            return True
        
        if self._weekly_pnl < -self.config.risk.weekly_loss_limit:
            return True
        
        if self._monthly_pnl < -self.config.risk.monthly_loss_limit:
            return True
        
        return False
