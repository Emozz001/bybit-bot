"""
Database manager for the trading bot.

Handles SQLite database operations using SQLAlchemy with async support.
Stores trades, orders, positions, historical data, and statistics.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    func,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Trade(Base):
    """Trade record model."""
    
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float)
    pnl = Column(Float)
    pnl_percentage = Column(Float)
    leverage = Column(Integer)
    strategy = Column(String(50))
    confidence_score = Column(Integer)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    entry_time = Column(DateTime, default=datetime.utcnow, index=True)
    exit_time = Column(DateTime)
    status = Column(String(20), default="open")  # open, closed, cancelled
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Order(Base):
    """Order record model."""
    
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    order_id = Column(String(50), unique=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)
    type = Column(String(20))
    size = Column(Float, nullable=False)
    price = Column(Float)
    filled_size = Column(Float, default=0)
    status = Column(String(20), default="new")  # new, filled, cancelled, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Position(Base):
    """Position snapshot model."""
    
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10))
    size = Column(Float, default=0)
    entry_price = Column(Float)
    mark_price = Column(Float)
    unrealized_pnl = Column(Float)
    leverage = Column(Integer)
    liquidation_price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class Candle(Base):
    """Historical candlestick data model."""
    
    __tablename__ = "candles"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(Integer, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    turnover = Column(Float)
    
    __table_args__ = (
        # Unique constraint to prevent duplicates
        {"sqlite_autoincrement": True},
    )


class ScannerResult(Base):
    """Market scanner result model."""
    
    __tablename__ = "scanner_results"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    price = Column(Float)
    volume_24h = Column(Float)
    funding_rate = Column(Float)
    open_interest = Column(Float)
    atr = Column(Float)
    volatility = Column(Float)
    trend = Column(String(20))
    opportunity_score = Column(Integer)
    indicators = Column(Text)  # JSON string


class Statistics(Base):
    """Trading statistics model."""
    
    __tablename__ = "statistics"
    
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    total_pnl = Column(Float, default=0)
    win_rate = Column(Float, default=0)
    profit_factor = Column(Float, default=0)
    max_drawdown = Column(Float, default=0)
    sharpe_ratio = Column(Float)


class DatabaseManager:
    """Database manager for all database operations."""

    def __init__(self, config):
        """
        Initialize database manager.
        
        Args:
            config: Configuration object with database settings
        """
        self.config = config
        self.db_path = Path(config.database.path)
        self.engine = None
        self.SessionLocal = None
        self.session = None
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize database connection and create tables with optimized settings."""
        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create engine with optimized settings for SQLite
            db_url = f"sqlite:///{self.db_path}"
            self.engine = create_engine(
                db_url,
                connect_args={
                    "check_same_thread": False,
                    "timeout": 30,  # Increased timeout for concurrent access
                },
                echo=False,
                pool_pre_ping=True,  # Enable connection health checks
            )
            
            # Optimize SQLite for performance
            with self.engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))  # Write-Ahead Logging for better concurrency
                conn.execute(text("PRAGMA synchronous=NORMAL"))  # Faster than FULL, safer than OFF
                conn.execute(text("PRAGMA cache_size=-64000"))  # 64MB cache
                conn.execute(text("PRAGMA temp_store=MEMORY"))  # Store temp tables in memory
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            
            # Create session factory with optimized settings
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
                expire_on_commit=False,  # Prevent object expiration
            )
            
            # Get initial session
            self.session = self.SessionLocal()
            
        except Exception as e:
            raise RuntimeError(f"Failed to initialize database: {e}")

    def _get_session(self):
        """Get a database session."""
        if self.session is None:
            self.session = self.SessionLocal()
        return self.session

    async def add_trade(self, **kwargs) -> Trade:
        """Add a trade record."""
        async with self._lock:
            session = self._get_session()
            try:
                trade = Trade(**kwargs)
                session.add(trade)
                session.commit()
                session.refresh(trade)
                return trade
            except Exception as e:
                session.rollback()
                raise e

    async def update_trade(self, trade_id: int, **kwargs) -> bool:
        """Update a trade record."""
        async with self._lock:
            session = self._get_session()
            try:
                trade = session.query(Trade).filter(Trade.id == trade_id).first()
                if trade:
                    for key, value in kwargs.items():
                        setattr(trade, key, value)
                    session.commit()
                    return True
                return False
            except Exception as e:
                session.rollback()
                raise e

    async def get_open_trades(self) -> list[Trade]:
        """Get all open trades."""
        session = self._get_session()
        return session.query(Trade).filter(Trade.status == "open").all()

    async def get_closed_trades(self, limit: int = 100) -> list[Trade]:
        """Get closed trades."""
        session = self._get_session()
        return (
            session.query(Trade)
            .filter(Trade.status == "closed")
            .order_by(Trade.exit_time.desc())
            .limit(limit)
            .all()
        )

    async def add_order(self, **kwargs) -> Order:
        """Add an order record."""
        async with self._lock:
            session = self._get_session()
            try:
                order = Order(**kwargs)
                session.add(order)
                session.commit()
                session.refresh(order)
                return order
            except Exception as e:
                session.rollback()
                raise e

    async def update_order(self, order_id: str, **kwargs) -> bool:
        """Update an order record."""
        async with self._lock:
            session = self._get_session()
            try:
                order = session.query(Order).filter(Order.order_id == order_id).first()
                if order:
                    for key, value in kwargs.items():
                        setattr(order, key, value)
                    session.commit()
                    return True
                return False
            except Exception as e:
                session.rollback()
                raise e

    async def save_position_snapshot(self, **kwargs) -> Position:
        """Save a position snapshot."""
        async with self._lock:
            session = self._get_session()
            try:
                position = Position(**kwargs)
                session.add(position)
                session.commit()
                session.refresh(position)
                return position
            except Exception as e:
                session.rollback()
                raise e

    async def save_candle(self, **kwargs) -> Candle:
        """Save a candlestick record."""
        async with self._lock:
            session = self._get_session()
            try:
                # Check if candle already exists
                existing = (
                    session.query(Candle)
                    .filter(
                        Candle.symbol == kwargs["symbol"],
                        Candle.timeframe == kwargs["timeframe"],
                        Candle.timestamp == kwargs["timestamp"],
                    )
                    .first()
                )
                
                if existing:
                    # Update existing candle
                    for key, value in kwargs.items():
                        setattr(existing, key, value)
                    session.commit()
                    return existing
                else:
                    # Insert new candle
                    candle = Candle(**kwargs)
                    session.add(candle)
                    session.commit()
                    session.refresh(candle)
                    return candle
            except Exception as e:
                session.rollback()
                raise e

    async def save_candles_batch(self, candles: list[dict]) -> int:
        """Save multiple candles in a batch."""
        async with self._lock:
            session = self._get_session()
            try:
                count = 0
                for candle_data in candles:
                    existing = (
                        session.query(Candle)
                        .filter(
                            Candle.symbol == candle_data["symbol"],
                            Candle.timeframe == candle_data["timeframe"],
                            Candle.timestamp == candle_data["timestamp"],
                        )
                        .first()
                    )
                    
                    if existing:
                        for key, value in candle_data.items():
                            setattr(existing, key, value)
                    else:
                        candle = Candle(**candle_data)
                        session.add(candle)
                    
                    count += 1
                
                session.commit()
                return count
            except Exception as e:
                session.rollback()
                raise e

    async def get_candles(
        self, symbol: str, timeframe: str, limit: int = 200
    ) -> list[Candle]:
        """Get historical candles."""
        session = self._get_session()
        return (
            session.query(Candle)
            .filter(
                Candle.symbol == symbol,
                Candle.timeframe == timeframe,
            )
            .order_by(Candle.timestamp.desc())
            .limit(limit)
            .all()
        )

    async def save_scanner_result(self, **kwargs) -> ScannerResult:
        """Save a scanner result."""
        async with self._lock:
            session = self._get_session()
            try:
                result = ScannerResult(**kwargs)
                session.add(result)
                session.commit()
                session.refresh(result)
                return result
            except Exception as e:
                session.rollback()
                raise e

    async def get_latest_scanner_results(
        self, symbol: str | None = None, limit: int = 100
    ) -> list[ScannerResult]:
        """Get latest scanner results."""
        session = self._get_session()
        query = session.query(ScannerResult)
        
        if symbol:
            query = query.filter(ScannerResult.symbol == symbol)
        
        return query.order_by(ScannerResult.timestamp.desc()).limit(limit).all()

    async def save_statistics(self, **kwargs) -> Statistics:
        """Save trading statistics."""
        async with self._lock:
            session = self._get_session()
            try:
                stats = Statistics(**kwargs)
                session.add(stats)
                session.commit()
                session.refresh(stats)
                return stats
            except Exception as e:
                session.rollback()
                raise e

    async def get_statistics(self, days: int = 30) -> list[Statistics]:
        """Get trading statistics for the specified period."""
        from datetime import timedelta
        
        session = self._get_session()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return (
            session.query(Statistics)
            .filter(Statistics.date >= cutoff_date)
            .order_by(Statistics.date.desc())
            .all()
        )

    async def get_trade_statistics(self) -> dict[str, Any]:
        """Get aggregated trade statistics."""
        session = self._get_session()
        
        # Total trades
        total = session.query(func.count(Trade.id)).filter(
            Trade.status == "closed"
        ).scalar()
        
        # Winning trades
        wins = session.query(func.count(Trade.id)).filter(
            Trade.status == "closed",
            Trade.pnl > 0
        ).scalar()
        
        # Losing trades
        losses = session.query(func.count(Trade.id)).filter(
            Trade.status == "closed",
            Trade.pnl < 0
        ).scalar()
        
        # Total PnL
        total_pnl = session.query(func.sum(Trade.pnl)).filter(
            Trade.status == "closed"
        ).scalar() or 0
        
        # Average win
        avg_win = session.query(func.avg(Trade.pnl)).filter(
            Trade.status == "closed",
            Trade.pnl > 0
        ).scalar() or 0
        
        # Average loss
        avg_loss = session.query(func.avg(Trade.pnl)).filter(
            Trade.status == "closed",
            Trade.pnl < 0
        ).scalar() or 0
        
        win_rate = (wins / total * 100) if total > 0 else 0
        profit_factor = (abs(avg_win * wins) / abs(avg_loss * losses)) if losses > 0 else 0
        
        return {
            "total_trades": total,
            "winning_trades": wins,
            "losing_trades": losses,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
        }

    async def close(self):
        """Close database connection."""
        try:
            if self.session:
                self.session.close()
            
            if self.engine:
                self.engine.dispose()
            
        except Exception as e:
            pass
