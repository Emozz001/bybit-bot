"""
Position Manager Module.

Manages open positions, monitors P&L, adjusts stop-losses,
and handles position exits.
"""

import asyncio
from datetime import datetime
from typing import Any


class PositionManager:
    """
    Manages trading positions.
    
    Monitors open positions, manages risk, and handles exits.
    """

    def __init__(self, config, exchange, db_manager):
        """
        Initialize position manager.
        
        Args:
            config: Configuration object
            exchange: BybitClient instance
            db_manager: DatabaseManager instance
        """
        self.config = config
        self.exchange = exchange
        self.db_manager = db_manager
        self.logger = None  # Will be set by main bot
        
        # Position state
        self._running = False
        self._monitor_interval = 2  # seconds
        self._positions: dict[str, dict] = {}
        
        # Risk tracking
        self._daily_pnl = 0.0
        self._daily_trades = 0

    async def run(self):
        """Main position management loop."""
        self._running = True
        
        if self.logger:
            self.logger.info("Position manager started")
        
        while self._running:
            try:
                await self._monitor_positions()
                await self._check_risk_limits()
                await asyncio.sleep(self._monitor_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Position manager error: {e}", exc_info=True)
                await asyncio.sleep(self._monitor_interval)

    async def stop(self):
        """Stop the position manager."""
        self._running = False
        if self.logger:
            self.logger.info("Position manager stopped")

    async def _monitor_positions(self):
        """Monitor all open positions with optimized batch processing."""
        try:
            # Get current positions from exchange
            positions = await self.exchange.get_positions()
            
            # Update internal state in one operation
            self._positions = {pos["symbol"]: pos for pos in positions}
            
            # Batch process positions for risk checks
            if positions:
                position_checks = []
                db_snapshots = []
                
                for pos in positions:
                    symbol = pos["symbol"]
                    position_checks.append(self._check_position(symbol, pos))
                    
                    # Prepare DB snapshot data
                    db_snapshots.append({
                        "symbol": symbol,
                        "side": pos.get("side", ""),
                        "size": float(pos.get("size", 0)),
                        "entry_price": float(pos.get("avgPrice", 0)),
                        "mark_price": float(pos.get("markPrice", 0)),
                        "unrealized_pnl": float(pos.get("unrealisedPnl", 0)),
                        "leverage": int(pos.get("leverage", 1)),
                        "liquidation_price": float(pos.get("liqPrice", 0)),
                    })
                
                # Execute all position checks in parallel
                if position_checks:
                    await asyncio.gather(*position_checks, return_exceptions=True)
                
                # Batch save to database (if supported)
                if db_snapshots and hasattr(self.db_manager, 'save_position_snapshots_batch'):
                    await self.db_manager.save_position_snapshots_batch(db_snapshots)
                else:
                    # Fallback to individual saves
                    for snapshot in db_snapshots:
                        await self.db_manager.save_position_snapshot(**snapshot)
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error monitoring positions: {e}")

    async def _check_position(self, symbol: str, pos: dict):
        """
        Check a single position for risk management actions.
        
        Args:
            symbol: Trading pair symbol
            pos: Position data dictionary
        """
        try:
            size = float(pos.get("size", 0))
            if size == 0:
                return
            
            side = pos.get("side", "")
            entry_price = float(pos.get("avgPrice", 0))
            mark_price = float(pos.get("markPrice", 0))
            unrealized_pnl = float(pos.get("unrealisedPnl", 0))
            
            # Calculate PnL percentage
            if entry_price > 0:
                if side == "Buy":
                    pnl_pct = ((mark_price - entry_price) / entry_price) * 100
                else:  # Sell
                    pnl_pct = ((entry_price - mark_price) / entry_price) * 100
            else:
                pnl_pct = 0
            
            # Check for trailing stop adjustment
            if self.config.execution.use_trailing_stop:
                await self._adjust_trailing_stop(symbol, side, entry_price, mark_price, pnl_pct)
            
            # Check for partial exit at take profit levels
            if self.config.execution.partial_exits:
                await self._check_partial_exit(symbol, side, pnl_pct)
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error checking position {symbol}: {e}")

    async def _adjust_trailing_stop(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        mark_price: float,
        pnl_pct: float
    ):
        """
        Adjust trailing stop based on price movement.
        
        Args:
            symbol: Trading pair symbol
            side: Position side (Buy/Sell)
            entry_price: Entry price
            mark_price: Current mark price
            pnl_pct: PnL percentage
        """
        try:
            # Move stop loss to breakeven when profitable
            if pnl_pct >= 2.0:  # 2% profit
                # Could implement dynamic stop loss adjustment here
                pass
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error adjusting trailing stop: {e}")

    async def _check_partial_exit(self, symbol: str, side: str, pnl_pct: float):
        """
        Check for partial exit conditions.
        
        Args:
            symbol: Trading pair symbol
            side: Position side
            pnl_pct: PnL percentage
        """
        try:
            # Example: Close 50% at 5% profit
            if pnl_pct >= 5.0:
                # Implementation would go here
                pass
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error checking partial exit: {e}")

    async def _check_risk_limits(self):
        """Check if any risk limits have been breached."""
        try:
            # Get current balance
            balance = await self.exchange.get_account_balance()
            if not balance:
                return
            
            # Calculate daily PnL
            coin_data = balance.get("coin", [])
            usdt_data = next((c for c in coin_data if c.get("coin") == "USDT"), {})
            
            equity = float(usdt_data.get("equity", 0))
            
            # Check daily loss limit
            if self._daily_pnl < -self.config.risk.daily_loss_limit:
                if self.logger:
                    self.logger.warning("Daily loss limit reached!")
                # Could trigger circuit breaker here
            
            # Check position count
            position_count = len(self._positions)
            if position_count >= self.config.trading.max_positions:
                if self.logger:
                    self.logger.debug(f"Max positions reached: {position_count}")
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error checking risk limits: {e}")

    async def get_positions(self) -> list[dict]:
        """
        Get all open positions.
        
        Returns:
            List of position dictionaries
        """
        return list(self._positions.values())

    async def get_statistics(self) -> dict[str, Any]:
        """
        Get trading statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            stats = await self.db_manager.get_trade_statistics()
            return stats
        except Exception:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "profit_factor": 0,
            }

    async def open_position(
        self,
        symbol: str,
        side: str,
        size: float,
        leverage: int = 10,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> bool:
        """
        Open a new position.
        
        Args:
            symbol: Trading pair symbol
            side: Buy or Sell
            size: Position size
            leverage: Leverage multiplier
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Set leverage
            await self.exchange.set_leverage(symbol, leverage)
            
            # Place order
            result = await self.exchange.place_order(
                symbol=symbol,
                side=side,
                qty=size,
                order_type="Market",
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
            
            if result and result.get("retCode") == 0:
                # Record trade in database
                await self.db_manager.add_trade(
                    symbol=symbol,
                    side=side,
                    size=size,
                    entry_price=result.get("result", {}).get("avgPrice", 0),
                    leverage=leverage,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    status="open",
                )
                
                if self.logger:
                    self.logger.info(f"Opened {side} position on {symbol}: {size}")
                
                return True
            
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to open position: {e}")
            return False

    async def close_position(self, symbol: str) -> bool:
        """
        Close an existing position.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            True if successful, False otherwise
        """
        try:
            pos = self._positions.get(symbol)
            if not pos:
                return False
            
            size = float(pos.get("size", 0))
            side = pos.get("side", "")
            
            if size == 0:
                return False
            
            # Close with opposite side
            close_side = "Sell" if side == "Buy" else "Buy"
            
            result = await self.exchange.place_order(
                symbol=symbol,
                side=close_side,
                qty=size,
                order_type="Market",
                reduce_only=True,
            )
            
            if result and result.get("retCode") == 0:
                # Update trade record
                await self.db_manager.update_trade(
                    symbol=symbol,
                    status="closed",
                    exit_time=datetime.utcnow(),
                )
                
                if self.logger:
                    self.logger.info(f"Closed position on {symbol}")
                
                return True
            
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to close position: {e}")
            return False

    async def close_all_positions(self) -> int:
        """
        Close all open positions.
        
        Returns:
            Number of positions closed
        """
        closed_count = 0
        
        for symbol in list(self._positions.keys()):
            if await self.close_position(symbol):
                closed_count += 1
        
        if self.logger:
            self.logger.info(f"Closed {closed_count} positions")
        
        return closed_count
