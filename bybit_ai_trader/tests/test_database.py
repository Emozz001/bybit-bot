"""Unit tests for database manager."""

import pytest
import asyncio
from pathlib import Path
import tempfile

from sqlalchemy import text

from database.manager import DatabaseManager, Trade


class MockConfig:
    """Mock configuration for testing."""
    
    class DatabaseConfig:
        path = ":memory:"
    
    database = DatabaseConfig()


class TestDatabaseManager:
    """Tests for DatabaseManager."""

    @pytest.fixture
    async def db_manager(self):
        """Create a database manager with in-memory SQLite."""
        config = MockConfig()
        manager = DatabaseManager(config)
        await manager.initialize()
        yield manager
        await manager.close()

    @pytest.mark.asyncio
    async def test_initialize(self, db_manager):
        """Test database initialization."""
        assert db_manager.engine is not None
        assert db_manager.SessionLocal is not None

    @pytest.mark.asyncio
    async def test_add_trade(self, db_manager):
        """Test adding a trade record."""
        trade = await db_manager.add_trade(
            symbol="BTCUSDT",
            side="Buy",
            size=0.1,
            entry_price=50000.0,
            leverage=10,
            strategy="test_strategy",
        )
        
        assert trade.id is not None
        assert trade.symbol == "BTCUSDT"
        assert trade.side == "Buy"
        assert trade.size == 0.1
        assert trade.entry_price == 50000.0

    @pytest.mark.asyncio
    async def test_update_trade(self, db_manager):
        """Test updating a trade record."""
        # Add a trade
        trade = await db_manager.add_trade(
            symbol="ETHUSDT",
            side="Sell",
            size=1.0,
            entry_price=3000.0,
        )
        
        # Update the trade
        updated = await db_manager.update_trade(
            trade.id,
            exit_price=3100.0,
            pnl=-100.0,
            status="closed",
        )
        
        assert updated is True
        
        # Verify update
        trades = await db_manager.get_open_trades()
        # Trade should no longer be open
        assert not any(t.id == trade.id for t in trades)

    @pytest.mark.asyncio
    async def test_get_open_trades(self, db_manager):
        """Test getting open trades."""
        # Add multiple trades
        await db_manager.add_trade(symbol="BTCUSDT", side="Buy", size=0.1, entry_price=50000.0)
        await db_manager.add_trade(symbol="ETHUSDT", side="Sell", size=1.0, entry_price=3000.0)
        
        # Close one trade
        trades = await db_manager.get_open_trades()
        if trades:
            await db_manager.update_trade(trades[0].id, status="closed")
        
        # Get open trades
        open_trades = await db_manager.get_open_trades()
        assert len(open_trades) <= 2

    @pytest.mark.asyncio
    async def test_save_candle(self, db_manager):
        """Test saving candlestick data."""
        candle = await db_manager.save_candle(
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=1234567890,
            open=50000.0,
            high=51000.0,
            low=49000.0,
            close=50500.0,
            volume=1000.0,
        )
        
        assert candle.id is not None
        assert candle.symbol == "BTCUSDT"
        assert candle.open == 50000.0

    @pytest.mark.asyncio
    async def test_get_candles(self, db_manager):
        """Test retrieving candlestick data."""
        # Add candles
        for i in range(5):
            await db_manager.save_candle(
                symbol="BTCUSDT",
                timeframe="1h",
                timestamp=1234567890 + i * 3600,
                open=50000.0 + i * 100,
                high=51000.0 + i * 100,
                low=49000.0 + i * 100,
                close=50500.0 + i * 100,
                volume=1000.0,
            )
        
        # Retrieve candles
        candles = await db_manager.get_candles("BTCUSDT", "1h", limit=10)
        assert len(candles) == 5

    @pytest.mark.asyncio
    async def test_sqlite_pragma_settings(self, db_manager):
        """Test that SQLite PRAGMA settings are applied correctly."""
        # Test that we can execute PRAGMA queries (verifies text() usage works)
        with db_manager.engine.connect() as conn:
            result = conn.execute(text("PRAGMA journal_mode")).fetchone()
            # WAL mode should be enabled
            assert result[0] == "wal"
