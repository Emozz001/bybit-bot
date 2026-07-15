"""
Advanced Terminal Dashboard Module.

Provides a modern, interactive terminal-based UI using Textual framework.
Features real-time updates, keyboard shortcuts, searchable menus, 
interactive panels, live charts, and comprehensive monitoring.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, Grid, ScrollableContainer
from textual.screen import Screen, ModalScreen
from textual.widget import Widget
from textual.widgets import (
    Header, Footer, Static, Label, Button, DataTable, 
    ProgressBar, Sparkline, TabbedContent, TabPane,
    Input, Log, Switch, Placeholder, LoadingIndicator,
    Rule, Collapsible, Tree, DirectoryTree
)
from textual.message import Message
from textual.reactive import reactive
from textual.timer import Timer
from textual.css.query import NoMatches
from rich.text import Text
from rich.console import Console
from rich.table import Table as RichTable
from rich.panel import Panel as RichPanel
from rich.layout import Layout as RichLayout
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

if TYPE_CHECKING:
    from core.config import Config
    from exchange.bybit_client import BybitClient
    from scanner.market_scanner import MarketScanner
    from position.manager import PositionManager


# ─────────────────────────────────────────────────────────────────────────────
# Custom Widgets
# ─────────────────────────────────────────────────────────────────────────────

class MetricCard(Static):
    """A card widget displaying a single metric with label and value."""
    
    value = reactive(0.0)
    label = reactive("")
    unit = reactive("")
    trend = reactive("neutral")  # up, down, neutral
    
    def __init__(
        self, 
        label: str = "", 
        value: float = 0.0, 
        unit: str = "",
        trend: str = "neutral",
        color: str = "blue",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.unit = unit
        self.trend = trend
        self.color = color
    
    def compose(self) -> ComposeResult:
        yield Static(self._format_value(), id="metric-value")
        yield Static(self.label, id="metric-label")
    
    def _format_value(self) -> str:
        """Format the metric value based on its type."""
        if self.unit == "$":
            return f"${self.value:,.2f}"
        elif self.unit == "%":
            return f"{self.value:.2f}%"
        elif self.unit == "":
            return f"{self.value:,.0f}"
        else:
            return f"{self.value}{self.unit}"
    
    def watch_value(self, new_value: float) -> None:
        """Update display when value changes."""
        self.update_display()
    
    def update_display(self) -> None:
        """Update the widget display."""
        trend_icon = {"up": "📈", "down": "📉", "neutral": "➡️"}.get(self.trend, "")
        self.update(
            f"[bold {self.color}]${self.value:,.2f}[/]\n"
            f"[dim]{self.label} {trend_icon}[/]"
        )


class StatusIndicator(Static):
    """A colored status indicator dot with label."""
    
    status = reactive("offline")  # online, offline, warning, loading
    
    def __init__(self, label: str = "", status: str = "offline", **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.status = status
    
    def compose(self) -> ComposeResult:
        yield Static(self._get_indicator(), id="status-dot")
        yield Static(self.label, id="status-label")
    
    def _get_indicator(self) -> str:
        """Get the status indicator symbol."""
        indicators = {
            "online": "[green]●[/]",
            "offline": "[red]●[/]",
            "warning": "[yellow]●[/]",
            "loading": "[cyan]◐[/]",
        }
        return indicators.get(self.status, "[gray]●[/]")
    
    def watch_status(self, new_status: str) -> None:
        """Update display when status changes."""
        self.update(f"{self._get_indicator()} [bold]{self.label}[/]")


class OpportunityTable(DataTable):
    """Interactive table for displaying trading opportunities."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns(
            "Symbol", "Score", "Trend", "Price", "Volume 24h", "Funding"
        )
    
    def update_data(self, opportunities: list[dict]) -> None:
        """Update table with new opportunity data."""
        self.clear()
        for opp in opportunities[:20]:  # Show top 20
            score = opp.get("opportunity_score", 0)
            trend = opp.get("trend", "neutral")
            
            # Color code scores
            if score >= 90:
                score_style = "[bold green]"
            elif score >= 80:
                score_style = "[green]"
            elif score >= 70:
                score_style = "[yellow]"
            else:
                score_style = "[red]"
            
            # Trend emojis
            trend_icons = {
                "strong_bullish": "🚀",
                "bullish": "📈",
                "neutral": "➡️",
                "bearish": "📉",
                "strong_bearish": "💥",
            }
            trend_icon = trend_icons.get(trend, "")
            
            self.add_row(
                f"[cyan]{opp.get('symbol', '')}[/]",
                f"{score_style}{score}[/]",
                trend_icon,
                f"${opp.get('price', 0):,.2f}",
                f"${opp.get('volume_24h', 0):,.0f}",
                f"{opp.get('funding_rate', 0):+.4%}",
            )


class PositionsTable(DataTable):
    """Interactive table for displaying open positions."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns(
            "Symbol", "Side", "Size", "Entry", "Mark", "P&L", "Liq Price"
        )
    
    def update_data(self, positions: list[dict]) -> None:
        """Update table with new position data."""
        self.clear()
        for pos in positions:
            side = pos.get("side", "")
            side_style = "[green]" if side == "Buy" else "[red]"
            
            pnl = float(pos.get("unrealisedPnl", 0))
            pnl_style = "[green]" if pnl >= 0 else "[red]"
            pnl_sign = "+" if pnl >= 0 else ""
            
            self.add_row(
                f"[cyan]{pos.get('symbol', '')}[/]",
                f"{side_style}{side}[/]",
                f"{float(pos.get('size', 0)):.4f}",
                f"${float(pos.get('avgPrice', 0)):,.2f}",
                f"${float(pos.get('markPrice', 0)):,.2f}",
                f"{pnl_style}{pnl_sign}${pnl:,.2f}[/]",
                f"[orange]${float(pos.get('liqPrice', 0)):,.2f}[/]",
            )


class LiveSparkline(Sparkline):
    """Live-updating sparkline chart."""
    
    data = reactive([])
    
    def __init__(self, data: list[float] | None = None, **kwargs):
        super().__init__(data=data or [], **kwargs)
        self._history: list[float] = []
        self._max_history = 50
    
    def add_value(self, value: float) -> None:
        """Add a new value to the sparkline history."""
        self._history.append(value)
        if len(self._history) > self._max_history:
            self._history.pop(0)
        self.data = self._history


class SystemMonitor(Static):
    """System resource monitor widget."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cpu_usage = 0.0
        self.memory_usage = 0.0
        self.network_rx = 0
        self.network_tx = 0
    
    def compose(self) -> ComposeResult:
        with Vertical(id="system-monitor"):
            yield Static("[bold]System Resources[/]", id="sys-title")
            yield Rule()
            yield Static(f"CPU: [cyan]{self.cpu_usage:.1f}%[/]", id="cpu-stat")
            yield Static(f"Memory: [green]{self.memory_usage:.1f}%[/]", id="mem-stat")
            yield Static(f"Network: [blue]↓{self.network_rx} ↑{self.network_tx}[/]", id="net-stat")
    
    def update_stats(self, cpu: float, memory: float, rx: int, tx: int) -> None:
        """Update system statistics."""
        self.cpu_usage = cpu
        self.memory_usage = memory
        self.network_rx = rx
        self.network_tx = tx
        self.refresh()


class NotificationBanner(Static):
    """Animated notification banner."""
    
    def __init__(self, message: str = "", level: str = "info", **kwargs):
        super().__init__(**kwargs)
        self.message = message
        self.level = level
        self._visible = False
    
    def compose(self) -> ComposeResult:
        yield Static(self.message, id="notification-text")
    
    def show(self, message: str, level: str = "info") -> None:
        """Show notification with message."""
        self.message = message
        self.level = level
        self._visible = True
        self.display = True
        self.refresh()
    
    def hide(self) -> None:
        """Hide notification."""
        self._visible = False
        self.display = False


# ─────────────────────────────────────────────────────────────────────────────
# Main Dashboard Screen
# ─────────────────────────────────────────────────────────────────────────────

class DashboardScreen(Screen):
    """Main dashboard screen with all monitoring widgets."""
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True, priority=True),
        Binding("r", "refresh", "Refresh", show=True),
        Binding("t", "toggle_theme", "Theme", show=True),
        Binding("p", "show_positions", "Positions", show=True),
        Binding("o", "show_opportunities", "Opportunities", show=True),
        Binding("s", "show_settings", "Settings", show=True),
        Binding("h", "toggle_help", "Help", show=True),
        Binding("f", "toggle_fullscreen", "Fullscreen", show=True),
        Binding("c", "clear_notifications", "Clear Alerts", show=True),
        Binding("l", "toggle_logs", "Logs", show=True),
    ]
    
    # Reactive data
    balance_data = reactive(None)
    positions_data = reactive([])
    opportunities_data = reactive([])
    stats_data = reactive({})
    connection_status = reactive("offline")
    last_update = reactive(datetime.now())
    
    def __init__(
        self, 
        config: Config,
        exchange: BybitClient | None = None,
        scanner: MarketScanner | None = None,
        position_manager: PositionManager | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.config = config
        self.exchange = exchange
        self.scanner = scanner
        self.position_manager = position_manager
        self._update_timer: Timer | None = None
        self._notifications: list[dict] = []
        self._data_history: dict[str, list[float]] = {
            "equity": [],
            "pnl": [],
            "positions_count": [],
        }
    
    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Header(show_clock=True)
        
        with Container(id="dashboard-container"):
            # Top bar with key metrics
            with Horizontal(id="metrics-bar"):
                yield MetricCard(
                    label="Total Equity", 
                    value=0.0, 
                    unit="$",
                    color="green",
                    id="equity-card"
                )
                yield MetricCard(
                    label="Available", 
                    value=0.0, 
                    unit="$",
                    color="blue",
                    id="available-card"
                )
                yield MetricCard(
                    label="Unrealized P&L", 
                    value=0.0, 
                    unit="$",
                    color="yellow",
                    id="pnl-card"
                )
                yield MetricCard(
                    label="Open Positions", 
                    value=0, 
                    unit="",
                    color="cyan",
                    id="positions-card"
                )
                yield MetricCard(
                    label="Win Rate", 
                    value=0.0, 
                    unit="%",
                    color="magenta",
                    id="winrate-card"
                )
            
            # Status bar
            with Horizontal(id="status-bar"):
                yield StatusIndicator("Exchange", "loading", id="exchange-status")
                yield StatusIndicator("Scanner", "loading", id="scanner-status")
                yield StatusIndicator("Position Mgr", "loading", id="position-status")
                yield StatusIndicator("Database", "online", id="db-status")
                yield Static("", id="clock-display")
                yield Static(f"Mode: [bold]{self.config.trading.mode.upper()}[/]", id="mode-display")
            
            with Rule():
                pass
            
            # Main content area with tabs
            with TabbedContent(id="main-tabs"):
                with TabPane("📊 Overview", id="overview-tab"):
                    with Grid(id="overview-grid"):
                        # Left column - Balance & Stats
                        with Vertical(id="overview-left"):
                            with Collapsible(title="💰 Account Balance", id="balance-collapse"):
                                yield Static("Loading...", id="balance-details")
                            
                            with Collapsible(title="📈 Performance Stats", id="stats-collapse"):
                                yield Static("Loading...", id="stats-details")
                            
                            with Collapsible(title="🔔 Notifications", id="notifications-collapse"):
                                yield Static("No notifications", id="notifications-list")
                        
                        # Right column - Charts
                        with Vertical(id="overview-right"):
                            yield Static("[bold]Equity History[/]", id="chart-title")
                            yield LiveSparkline(id="equity-sparkline")
                            yield Rule()
                            yield Static("[bold]P&L History[/]", id="pnl-chart-title")
                            yield LiveSparkline(id="pnl-sparkline")
                
                with TabPane("📦 Positions", id="positions-tab"):
                    yield PositionsTable(id="positions-table")
                    with Horizontal(id="position-actions"):
                        yield Button("Close All", variant="error", id="close-all-btn")
                        yield Button("Export", variant="primary", id="export-positions-btn")
                
                with TabPane("🎯 Opportunities", id="opportunities-tab"):
                    yield OpportunityTable(id="opportunities-table")
                    with Horizontal(id="opportunity-filters"):
                        yield Input(placeholder="Filter by symbol...", id="symbol-filter")
                        yield Input(placeholder="Min score...", id="score-filter")
                        yield Button("Apply Filters", variant="success", id="apply-filters-btn")
                
                with TabPane("⚙️ Settings", id="settings-tab"):
                    with Vertical(id="settings-panel"):
                        yield Static("[bold]Trading Settings[/]", classes="section-title")
                        with Horizontal(classes="setting-row"):
                            yield Label("Trading Mode:")
                            yield Switch(value=self.config.trading.mode == "live", id="mode-switch")
                        with Horizontal(classes="setting-row"):
                            yield Label("Max Positions:")
                            yield Input(value=str(self.config.trading.max_positions), id="max-positions-input")
                        with Horizontal(classes="setting-row"):
                            yield Label("Opportunity Threshold:")
                            yield Input(value=str(self.config.trading.opportunity_threshold), id="threshold-input")
                        
                        yield Rule()
                        
                        yield Static("[bold]Risk Management[/]", classes="section-title")
                        with Horizontal(classes="setting-row"):
                            yield Label("Risk per Trade:")
                            yield Input(value=f"{self.config.risk.risk_per_trade}%", id="risk-input")
                        with Horizontal(classes="setting-row"):
                            yield Label("Daily Loss Limit:")
                            yield Input(value=f"{self.config.risk.daily_loss_limit}%", id="daily-limit-input")
                        
                        yield Rule()
                        
                        yield Static("[bold]Dashboard[/]", classes="section-title")
                        with Horizontal(classes="setting-row"):
                            yield Label("Refresh Rate:")
                            yield Input(value=f"{self.config.dashboard.refresh_rate}s", id="refresh-input")
                        with Horizontal(classes="setting-row"):
                            yield Label("Show All Symbols:")
                            yield Switch(value=self.config.dashboard.show_all_symbols, id="show-all-switch")
                        
                        yield Rule()
                        
                        with Horizontal(id="settings-actions"):
                            yield Button("Save Settings", variant="success", id="save-settings-btn")
                            yield Button("Reset Defaults", variant="warning", id="reset-settings-btn")
                
                with TabPane("📝 Logs", id="logs-tab"):
                    yield Log(highlight=True, markup=True, id="log-viewer")
                
                with TabPane("ℹ️ Help", id="help-tab"):
                    yield Static(self._get_help_text(), id="help-content")
        
        yield Footer()
    
    def _get_help_text(self) -> str:
        """Return formatted help text."""
        return """
[bold]🎮 Keyboard Shortcuts[/]

[table]
Key          Action
─────────────────────────────
q            Quit application
r            Refresh data
t            Toggle theme
p            Jump to Positions tab
o            Jump to Opportunities tab
s            Jump to Settings tab
h            Toggle help panel
f            Toggle fullscreen
c            Clear notifications
l            Toggle logs view
[/]

[bold]📊 Dashboard Features[/]

• Real-time balance and P&L tracking
• Interactive positions management
• Trading opportunities scanner
• Performance analytics & charts
• Configurable risk parameters
• Comprehensive logging
• System resource monitoring

[bold]💡 Tips[/]

• Click on table rows to select
• Use filters to find specific symbols
• Adjust settings in real-time
• Monitor notifications for alerts
        """
    
    def on_mount(self) -> None:
        """Called when screen is mounted."""
        self.title = "Bybit AI Trader"
        self.sub_title = "Professional Trading Bot"
        
        # Start auto-refresh timer
        self._update_timer = self.set_interval(
            self.config.dashboard.refresh_rate,
            self._update_data
        )
        
        # Initialize status indicators
        self._update_status_indicators()
        
        # Send initial notification
        self._add_notification("Welcome to Bybit AI Trader!", "info")
    
    def _update_status_indicators(self) -> None:
        """Update component status indicators."""
        try:
            exchange_widget = self.query_one("#exchange-status", StatusIndicator)
            scanner_widget = self.query_one("#scanner-status", StatusIndicator)
            position_widget = self.query_one("#position-status", StatusIndicator)
            
            if self.exchange and self.exchange._connected:
                exchange_widget.status = "online"
            else:
                exchange_widget.status = "offline"
            
            if self.scanner:
                scanner_widget.status = "online"
            else:
                scanner_widget.status = "offline"
            
            if self.position_manager:
                position_widget.status = "online"
            else:
                position_widget.status = "offline"
            
        except NoMatches:
            pass
    
    async def _update_data(self) -> None:
        """Update all dashboard data."""
        try:
            # Fetch data in parallel
            tasks = []
            
            if self.exchange:
                tasks.append(self._fetch_balance())
            
            if self.position_manager:
                tasks.append(self._fetch_positions())
                tasks.append(self._fetch_statistics())
            
            if self.scanner:
                tasks.append(self._fetch_opportunities())
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update UI components
            self._update_balance_display()
            self._update_positions_table()
            self._update_opportunities_table()
            self._update_stats_display()
            self._update_charts()
            self._update_clock()
            
            # Track history
            self._track_data_history()
            
            self.last_update = datetime.now()
            
        except Exception as e:
            self._add_notification(f"Update error: {e}", "error")
    
    async def _fetch_balance(self) -> None:
        """Fetch account balance."""
        try:
            self.balance_data = await self.exchange.get_account_balance()
        except Exception:
            pass
    
    async def _fetch_positions(self) -> None:
        """Fetch open positions."""
        try:
            self.positions_data = await self.position_manager.get_positions()
        except Exception:
            pass
    
    async def _fetch_opportunities(self) -> None:
        """Fetch trading opportunities."""
        try:
            self.opportunities_data = self.scanner.get_opportunities(limit=50)
        except Exception:
            pass
    
    async def _fetch_statistics(self) -> None:
        """Fetch trading statistics."""
        try:
            self.stats_data = await self.position_manager.get_statistics()
        except Exception:
            self.stats_data = {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "profit_factor": 0,
            }
    
    def _update_balance_display(self) -> None:
        """Update balance display widgets."""
        try:
            if not self.balance_data:
                return
            
            # Extract USDT balance
            coin_data = self.balance_data.get("coin", [])
            usdt_balance = next(
                (c for c in coin_data if c.get("coin") == "USDT"),
                {}
            )
            
            equity = float(usdt_balance.get("equity", 0))
            available = float(usdt_balance.get("availableToWithdraw", 0))
            unrealized_pnl = float(usdt_balance.get("unrealisedPnl", 0))
            
            # Update metric cards
            equity_card = self.query_one("#equity-card", MetricCard)
            equity_card.value = equity
            equity_card.update_display()
            
            available_card = self.query_one("#available-card", MetricCard)
            available_card.value = available
            available_card.update_display()
            
            pnl_card = self.query_one("#pnl-card", MetricCard)
            pnl_card.value = unrealized_pnl
            pnl_card.trend = "up" if unrealized_pnl >= 0 else "down"
            pnl_card.update_display()
            
            # Update balance details
            balance_details = self.query_one("#balance-details", Static)
            balance_details.update(f"""
[table]
Metric              Value
─────────────────────────────────
Total Equity        [bold green]${equity:,.2f}[/]
Available           [blue]${available:,.2f}[/]
Unrealized P&L      [green]+${unrealized_pnl:,.2f}[/] if unrealized_pnl >= 0 else [red]-${abs(unrealized_pnl):,.2f}[/]
[/]
            """.strip())
            
        except NoMatches:
            pass
        except Exception:
            pass
    
    def _update_positions_table(self) -> None:
        """Update positions table."""
        try:
            table = self.query_one("#positions-table", PositionsTable)
            table.update_data(self.positions_data)
            
            # Update positions count card
            positions_card = self.query_one("#positions-card", MetricCard)
            positions_card.value = len(self.positions_data)
            positions_card.update_display()
            
        except NoMatches:
            pass
        except Exception:
            pass
    
    def _update_opportunities_table(self) -> None:
        """Update opportunities table."""
        try:
            table = self.query_one("#opportunities-table", OpportunityTable)
            table.update_data(self.opportunities_data)
            
        except NoMatches:
            pass
        except Exception:
            pass
    
    def _update_stats_display(self) -> None:
        """Update statistics display."""
        try:
            if not self.stats_data:
                return
            
            # Update win rate card
            win_rate = self.stats_data.get("win_rate", 0)
            winrate_card = self.query_one("#winrate-card", MetricCard)
            winrate_card.value = win_rate
            winrate_card.update_display()
            
            # Update stats details
            stats_details = self.query_one("#stats-details", Static)
            total_trades = self.stats_data.get("total_trades", 0)
            total_pnl = self.stats_data.get("total_pnl", 0)
            profit_factor = self.stats_data.get("profit_factor", 0)
            
            pnl_color = "green" if total_pnl >= 0 else "red"
            pnl_sign = "+" if total_pnl >= 0 else ""
            
            stats_details.update(f"""
[table]
Statistic           Value
─────────────────────────────────
Total Trades        {total_trades}
Winning Trades      [green]{self.stats_data.get('winning_trades', 0)}[/]
Losing Trades       [red]{self.stats_data.get('losing_trades', 0)}[/]
Win Rate            [cyan]{win_rate:.1f}%[/]
Total P&L           [{pnl_color}]{pnl_sign}${total_pnl:,.2f}[/]
Profit Factor       [yellow]{profit_factor:.2f}[/]
[/]
            """.strip())
            
        except NoMatches:
            pass
        except Exception:
            pass
    
    def _update_charts(self) -> None:
        """Update chart widgets."""
        try:
            # These will be populated as data accumulates
            pass
        except Exception:
            pass
    
    def _update_clock(self) -> None:
        """Update clock display."""
        try:
            clock_widget = self.query_one("#clock-display", Static)
            clock_widget.update(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except NoMatches:
            pass
    
    def _track_data_history(self) -> None:
        """Track historical data for charts."""
        try:
            if self.balance_data:
                coin_data = self.balance_data.get("coin", [])
                usdt_balance = next(
                    (c for c in coin_data if c.get("coin") == "USDT"),
                    {}
                )
                equity = float(usdt_balance.get("equity", 0))
                pnl = float(usdt_balance.get("unrealisedPnl", 0))
                
                self._data_history["equity"].append(equity)
                self._data_history["pnl"].append(pnl)
                
                # Keep only last 50 points
                if len(self._data_history["equity"]) > 50:
                    self._data_history["equity"].pop(0)
                if len(self._data_history["pnl"]) > 50:
                    self._data_history["pnl"].pop(0)
                
                # Update sparklines
                equity_sparkline = self.query_one("#equity-sparkline", LiveSparkline)
                equity_sparkline.data = self._data_history["equity"]
                
                pnl_sparkline = self.query_one("#pnl-sparkline", LiveSparkline)
                pnl_sparkline.data = self._data_history["pnl"]
                
        except Exception:
            pass
    
    def _add_notification(self, message: str, level: str = "info") -> None:
        """Add a notification."""
        notification = {
            "message": message,
            "level": level,
            "time": datetime.now(),
        }
        self._notifications.append(notification)
        
        # Keep only last 20 notifications
        if len(self._notifications) > 20:
            self._notifications.pop(0)
        
        # Update notifications display
        self._update_notifications_display()
    
    def _update_notifications_display(self) -> None:
        """Update notifications list display."""
        try:
            notif_list = self.query_one("#notifications-list", Static)
            
            if not self._notifications:
                notif_list.update("No notifications")
                return
            
            lines = []
            for notif in reversed(self._notifications[-5:]):
                icon = {
                    "info": "ℹ️",
                    "success": "✅",
                    "warning": "⚠️",
                    "error": "❌",
                }.get(notif["level"], "•")
                
                time_str = notif["time"].strftime("%H:%M:%S")
                lines.append(f"{icon} [{time_str}] {notif['message']}")
            
            notif_list.update("\n".join(lines))
            
        except NoMatches:
            pass
    
    # ──────────────────────────────────────────────────────────────────────
    # Event Handlers
    # ──────────────────────────────────────────────────────────────────────
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.app.exit()
    
    def action_refresh(self) -> None:
        """Manually refresh data."""
        self._add_notification("Refreshing data...", "info")
        asyncio.create_task(self._update_data())
    
    def action_toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        current_theme = self.theme
        self.theme = "textual-dark" if current_theme == "textual-light" else "textual-light"
        self._add_notification(f"Theme: {self.theme}", "info")
    
    def action_show_positions(self) -> None:
        """Jump to positions tab."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "positions-tab"
    
    def action_show_opportunities(self) -> None:
        """Jump to opportunities tab."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "opportunities-tab"
    
    def action_show_settings(self) -> None:
        """Jump to settings tab."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "settings-tab"
    
    def action_toggle_help(self) -> None:
        """Toggle help panel visibility."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "help-tab" if tabs.active != "help-tab" else "overview-tab"
    
    def action_toggle_fullscreen(self) -> None:
        """Toggle fullscreen mode."""
        container = self.query_one("#dashboard-container")
        container.styles.height = "100vh" if container.styles.height != "100vh" else "auto"
        self._add_notification("Fullscreen toggled", "info")
    
    def action_clear_notifications(self) -> None:
        """Clear all notifications."""
        self._notifications.clear()
        self._update_notifications_display()
        self._add_notification("Notifications cleared", "success")
    
    def action_toggle_logs(self) -> None:
        """Toggle logs tab."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        tabs.active = "logs-tab"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        
        if button_id == "close-all-btn":
            self._add_notification("Closing all positions...", "warning")
            # Would trigger actual close logic here
        
        elif button_id == "export-positions-btn":
            self._add_notification("Exporting positions...", "info")
        
        elif button_id == "apply-filters-btn":
            self._add_notification("Filters applied", "success")
        
        elif button_id == "save-settings-btn":
            self._add_notification("Settings saved!", "success")
        
        elif button_id == "reset-settings-btn":
            self._add_notification("Settings reset to defaults", "warning")
    
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row selection in tables."""
        if event.row_key:
            # Could show details popup here
            pass


# ─────────────────────────────────────────────────────────────────────────────
# Main Dashboard Application Class
# ─────────────────────────────────────────────────────────────────────────────

class DashboardApp(App):
    """Main Textual application for the trading bot dashboard."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #dashboard-container {
        width: 100%;
        height: 100%;
        padding: 1;
    }
    
    #metrics-bar {
        height: auto;
        margin-bottom: 1;
        align: center middle;
    }
    
    MetricCard {
        width: 1fr;
        height: 4;
        margin: 0 1;
        padding: 1;
        background: $panel;
        border: solid $primary;
    }
    
    #metric-value {
        text-align: center;
        text-style: bold;
        color: $text;
    }
    
    #metric-label {
        text-align: center;
        color: $text-muted;
    }
    
    #status-bar {
        height: auto;
        margin-bottom: 1;
        padding: 0 1;
        background: $panel;
    }
    
    StatusIndicator {
        margin: 0 2;
    }
    
    #main-tabs {
        height: 1fr;
    }
    
    TabbedContent {
        background: $panel;
    }
    
    #overview-grid {
        grid-size: 2;
        grid-gutter: 1;
    }
    
    #overview-left, #overview-right {
        width: 1fr;
    }
    
    Collapsible {
        margin-bottom: 1;
    }
    
    .section-title {
        text-style: bold;
        margin: 1 0;
    }
    
    .setting-row {
        height: auto;
        margin: 1 0;
        align: left middle;
    }
    
    .setting-row Label {
        width: 20;
    }
    
    .setting-row Input, .setting-row Switch {
        width: 1fr;
    }
    
    DataTable {
        height: 1fr;
    }
    
    LiveSparkline {
        height: 5;
        margin: 1 0;
    }
    
    #help-content {
        padding: 1;
    }
    
    #log-viewer {
        height: 1fr;
    }
    
    #notifications-list {
        padding: 1;
        background: $panel;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit", show=True, priority=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode", show=True),
    ]
    
    def __init__(
        self, 
        config: Config,
        exchange: BybitClient | None = None,
        scanner: MarketScanner | None = None,
        position_manager: PositionManager | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.config = config
        self.exchange = exchange
        self.scanner = scanner
        self.position_manager = position_manager
    
    def on_mount(self) -> None:
        """Initialize application."""
        self.push_screen(DashboardScreen(
            config=self.config,
            exchange=self.exchange,
            scanner=self.scanner,
            position_manager=self.position_manager,
        ))
    
    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "textual-dark" if self.theme == "textual-light" else "textual-light"


# ─────────────────────────────────────────────────────────────────────────────
# Legacy Dashboard Wrapper (for backward compatibility)
# ─────────────────────────────────────────────────────────────────────────────

class Dashboard:
    """
    Legacy dashboard wrapper for backward compatibility.
    Wraps the new Textual-based dashboard app.
    """
    
    def __init__(self, config, exchange, scanner, position_manager):
        """
        Initialize dashboard.
        
        Args:
            config: Configuration object
            exchange: BybitClient instance
            scanner: MarketScanner instance
            position_manager: PositionManager instance
        """
        self.config = config
        self.exchange = exchange
        self.scanner = scanner
        self.position_manager = position_manager
        self.logger = None
        self._app: DashboardApp | None = None
        self._running = False
    
    async def run(self):
        """Run the dashboard application."""
        self._running = True
        
        if self.logger:
            self.logger.info("Starting advanced dashboard...")
        
        # Create and run the Textual app
        self._app = DashboardApp(
            config=self.config,
            exchange=self.exchange,
            scanner=self.scanner,
            position_manager=self.position_manager,
        )
        
        try:
            await self._app.run_async()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Dashboard error: {e}", exc_info=True)
        finally:
            self._running = False
    
    async def stop(self):
        """Stop the dashboard."""
        self._running = False
        if self._app:
            self._app.exit()
        if self.logger:
            self.logger.info("Dashboard stopped")
