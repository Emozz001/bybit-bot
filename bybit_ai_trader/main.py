"""
Bybit AI Futures Trading Bot

A professional, production-quality cryptocurrency futures trading bot for Bybit USDT Perpetual Futures.
Runs locally on MacBook Air 2017 with modular architecture and comprehensive risk management.

Author: AI Assistant
Version: 1.0.0
"""

import asyncio
import signal
import sys
from pathlib import Path

from core.config import Config
from core.logger import setup_logging
from database.manager import DatabaseManager
from exchange.bybit_client import BybitClient
from scanner.market_scanner import MarketScanner
from dashboard.terminal import Dashboard
from position.manager import PositionManager


class TradingBot:
    """Main trading bot orchestrator."""

    def __init__(self):
        self.config = Config.load()
        self.logger = setup_logging(self.config)
        self.db_manager: DatabaseManager | None = None
        self.exchange: BybitClient | None = None
        self.scanner: MarketScanner | None = None
        self.dashboard: Dashboard | None = None
        self.position_manager: PositionManager | None = None
        self._shutdown_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []

    async def initialize(self) -> bool:
        """Initialize all components."""
        try:
            self.logger.info("Initializing trading bot...")
            
            # Initialize database
            self.db_manager = DatabaseManager(self.config)
            await self.db_manager.initialize()
            self.logger.info("Database initialized")
            
            # Initialize exchange connection
            self.exchange = BybitClient(self.config)
            connected = await self.exchange.connect()
            if not connected:
                self.logger.error("Failed to connect to Bybit API")
                return False
            self.logger.info("Connected to Bybit API")
            
            # Authenticate
            authenticated = await self.exchange.authenticate()
            if not authenticated:
                self.logger.warning("Authentication failed - running in read-only mode")
            
            # Load markets
            markets = await self.exchange.get_futures_markets()
            self.logger.info(f"Loaded {len(markets)} futures markets")
            
            # Initialize scanner
            self.scanner = MarketScanner(self.config, self.exchange, self.db_manager)
            self.logger.info("Market scanner initialized")
            
            # Initialize position manager
            self.position_manager = PositionManager(self.config, self.exchange, self.db_manager)
            self.logger.info("Position manager initialized")
            
            # Initialize dashboard
            self.dashboard = Dashboard(self.config, self.exchange, self.scanner, self.position_manager)
            self.logger.info("Dashboard initialized")
            
            self.logger.info("Initialization complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}", exc_info=True)
            return False

    async def start(self):
        """Start the trading bot."""
        try:
            # Start WebSocket streams
            ws_task = asyncio.create_task(
                self.exchange.start_websocket_streams(),
                name="websocket_streams"
            )
            self._tasks.append(ws_task)
            
            # Start market scanner
            scanner_task = asyncio.create_task(
                self.scanner.run(),
                name="market_scanner"
            )
            self._tasks.append(scanner_task)
            
            # Start position manager
            position_task = asyncio.create_task(
                self.position_manager.run(),
                name="position_manager"
            )
            self._tasks.append(position_task)
            
            # Start dashboard
            dashboard_task = asyncio.create_task(
                self.dashboard.run(),
                name="dashboard"
            )
            self._tasks.append(dashboard_task)
            
            self.logger.info("All components started")
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)
            raise

    async def shutdown(self):
        """Gracefully shutdown all components."""
        self.logger.info("Shutting down...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Close connections
        if self.exchange:
            await self.exchange.close()
        
        if self.db_manager:
            await self.db_manager.close()
        
        if self.dashboard:
            await self.dashboard.stop()
        
        self.logger.info("Shutdown complete")

    def handle_signal(self, sig):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {sig}")
        asyncio.create_task(self.shutdown())


async def main():
    """Main entry point."""
    bot = TradingBot()
    
    # Setup signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: bot.handle_signal(s))
    
    try:
        # Initialize
        if not await bot.initialize():
            sys.exit(1)
        
        # Start
        await bot.start()
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        bot.logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await bot.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
