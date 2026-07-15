"""
Terminal Dashboard Module.

Provides a responsive terminal-based UI using Rich and Textual.
Displays account info, positions, opportunities, and system status.
"""

import asyncio
import logging
from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class Dashboard:
    """
    Terminal dashboard for monitoring trading bot status.
    
    Uses Rich library for beautiful terminal output.
    """

    def __init__(self, config, exchange, scanner, position_manager, logger=None):
        """
        Initialize dashboard.
        
        Args:
            config: Configuration object
            exchange: BybitClient instance
            scanner: MarketScanner instance
            position_manager: PositionManager instance
            logger: Logger instance for logging messages
        """
        self.config = config
        self.exchange = exchange
        self.scanner = scanner
        self.position_manager = position_manager
        self.logger = logger or logging.getLogger("bybit_trader.dashboard")
        
        # Dashboard state
        self._running = False
        self._refresh_rate = config.dashboard.refresh_rate
        self._console = Console()
        
        # Cached data
        self._balance_data: dict | None = None
        self._positions_data: list[dict] = []
        self._opportunities_data: list[dict] = []
        self._stats_data: dict | None = None

    async def run(self):
        """Main dashboard loop with optimized rendering."""
        self._running = True
        
        if self.logger:
            self.logger.info("Dashboard started")
        
        # Clear screen once at startup
        self._console.clear()
        
        while self._running:
            try:
                # Update data first, then render (proper sequencing)
                await self._update_data()
                self._render()
                
                # Sleep for refresh interval
                await asyncio.sleep(self._refresh_rate)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Dashboard error: {e}", exc_info=True)
                await asyncio.sleep(self._refresh_rate)

    async def stop(self):
        """Stop the dashboard."""
        self._running = False
        self._console.clear()
        if self.logger:
            self.logger.info("Dashboard stopped")

    async def _update_data(self):
        """Update dashboard data with parallel fetching."""
        try:
            # Fetch all data in parallel
            tasks = []
            
            if self.exchange:
                tasks.append(self._fetch_balance())
            
            if self.position_manager:
                tasks.append(self._fetch_positions())
                tasks.append(self._fetch_statistics())
            
            if self.scanner:
                tasks.append(self._fetch_opportunities())
            
            # Execute all fetches concurrently
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error updating dashboard data: {e}")

    async def _fetch_balance(self):
        """Fetch balance data."""
        try:
            self._balance_data = await self.exchange.get_account_balance()
        except Exception:
            pass

    async def _fetch_positions(self):
        """Fetch positions data."""
        try:
            self._positions_data = await self.position_manager.get_positions()
        except Exception:
            pass

    async def _fetch_opportunities(self):
        """Fetch opportunities data."""
        try:
            self._opportunities_data = self.scanner.get_opportunities(
                limit=self.config.dashboard.top_opportunities_count
            )
        except Exception:
            pass

    async def _fetch_statistics(self):
        """Fetch statistics data."""
        try:
            self._stats_data = await self.position_manager.get_statistics()
        except Exception:
            pass

    def _render(self):
        """Render the dashboard."""
        try:
            # Create layout
            layout = Layout()
            
            # Split into header, body, footer
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="body"),
                Layout(name="footer", size=10),
            )
            
            # Split body into left and right
            layout["body"].split_row(
                Layout(name="left", ratio=2),
                Layout(name="right", ratio=1),
            )
            
            # Split left into balance and positions
            layout["left"].split_column(
                Layout(name="balance", size=8),
                Layout(name="positions"),
            )
            
            # Render components
            layout["header"].update(self._render_header())
            layout["balance"].update(self._render_balance())
            layout["positions"].update(self._render_positions())
            layout["right"].update(self._render_opportunities())
            layout["footer"].update(self._render_footer())
            
            # Print to console
            self._console.print(layout)
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error rendering dashboard: {e}")

    def _render_header(self) -> Panel:
        """Render dashboard header."""
        title = Text("🚀 Bybit AI Trader", style="bold blue")
        subtitle = Text(f"Mode: {self.config.trading.mode.upper()}", style="dim")
        
        return Panel(
            title,
            subtitle=subtitle,
            border_style="blue",
        )

    def _render_balance(self) -> Panel:
        """Render account balance panel."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="dim")
        table.add_column("Value", justify="right")
        
        if self._balance_data:
            # Extract USDT balance
            coin_data = self._balance_data.get("coin", [])
            usdt_balance = next(
                (c for c in coin_data if c.get("coin") == "USDT"),
                {}
            )
            
            equity = float(usdt_balance.get("equity", 0))
            available = float(usdt_balance.get("availableToWithdraw", 0))
            unrealized_pnl = float(usdt_balance.get("unrealisedPnl", 0))
            
            table.add_row("Total Equity:", f"${equity:,.2f}")
            table.add_row("Available:", f"${available:,.2f}")
            
            pnl_style = "green" if unrealized_pnl >= 0 else "red"
            pnl_sign = "+" if unrealized_pnl >= 0 else ""
            table.add_row("Unrealized P&L:", f"{pnl_sign}${unrealized_pnl:,.2f}", style=pnl_style)
        else:
            table.add_row("Balance:", "Loading...")
        
        return Panel(table, title="💰 Account Balance", border_style="green")

    def _render_positions(self) -> Panel:
        """Render open positions panel."""
        table = Table(box=None, padding=(0, 1))
        table.add_column("Symbol", style="cyan")
        table.add_column("Side", justify="center")
        table.add_column("Size", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("Mark", justify="right")
        table.add_column("P&L", justify="right")
        
        if self._positions_data:
            for pos in self._positions_data[:5]:  # Show max 5 positions
                symbol = pos.get("symbol", "")
                side = pos.get("side", "")
                size = float(pos.get("size", 0))
                entry_price = float(pos.get("avgPrice", 0))
                mark_price = float(pos.get("markPrice", 0))
                unrealized_pnl = float(pos.get("unrealisedPnl", 0))
                
                side_style = "green" if side == "Buy" else "red"
                pnl_style = "green" if unrealized_pnl >= 0 else "red"
                pnl_sign = "+" if unrealized_pnl >= 0 else ""
                
                table.add_row(
                    symbol,
                    Text(side, style=side_style),
                    f"{size:.4f}",
                    f"${entry_price:,.2f}",
                    f"${mark_price:,.2f}",
                    Text(f"{pnl_sign}${unrealized_pnl:,.2f}", style=pnl_style),
                )
        else:
            table.add_row("", "", "", "", "", "No open positions")
        
        return Panel(table, title="📊 Open Positions", border_style="yellow")

    def _render_opportunities(self) -> Panel:
        """Render top opportunities panel."""
        table = Table(box=None, padding=(0, 1))
        table.add_column("Symbol", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Trend", justify="center")
        table.add_column("Price", justify="right")
        
        if self._opportunities_data:
            for opp in self._opportunities_data[:8]:  # Show max 8 opportunities
                symbol = opp.get("symbol", "")
                score = opp.get("opportunity_score", 0)
                trend = opp.get("trend", "")
                price = opp.get("price", 0)
                
                # Score color
                if score >= 90:
                    score_style = "bold green"
                elif score >= 80:
                    score_style = "green"
                elif score >= 70:
                    score_style = "yellow"
                else:
                    score_style = "red"
                
                # Trend emoji
                trend_emoji = {
                    "strong_bullish": "🚀",
                    "bullish": "📈",
                    "neutral": "➡️",
                    "bearish": "📉",
                    "strong_bearish": "💥",
                }.get(trend, "")
                
                table.add_row(
                    symbol,
                    Text(f"{score}", style=score_style),
                    trend_emoji,
                    f"${price:,.2f}",
                )
        else:
            table.add_row("", "", "Scanning...", "")
        
        return Panel(table, title="🎯 Top Opportunities", border_style="magenta")

    def _render_footer(self) -> Panel:
        """Render dashboard footer with stats."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Stat", style="dim")
        table.add_column("Value")
        
        if self._stats_data:
            total_trades = self._stats_data.get("total_trades", 0)
            win_rate = self._stats_data.get("win_rate", 0)
            total_pnl = self._stats_data.get("total_pnl", 0)
            profit_factor = self._stats_data.get("profit_factor", 0)
            
            pnl_style = "green" if total_pnl >= 0 else "red"
            pnl_sign = "+" if total_pnl >= 0 else ""
            
            table.add_row("Total Trades:", str(total_trades))
            table.add_row("Win Rate:", f"{win_rate:.1f}%")
            table.add_row("Total P&L:", Text(f"{pnl_sign}${total_pnl:,.2f}", style=pnl_style))
            table.add_row("Profit Factor:", f"{profit_factor:.2f}")
        else:
            table.add_row("Status:", "Collecting data...")
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        table.add_row("", f"Updated: {timestamp}", style="dim")
        
        return Panel(table, title="📈 Statistics", border_style="cyan")
