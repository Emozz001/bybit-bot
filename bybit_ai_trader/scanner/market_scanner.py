"""
Market Scanner Module.

Continuously scans all available USDT perpetual contracts,
collects market data, and identifies trading opportunities.
"""

import asyncio
from datetime import datetime
from typing import Any

import pandas as pd


class MarketScanner:
    """
    Market scanner for identifying trading opportunities.
    
    Scans all futures markets, calculates indicators,
    and assigns opportunity scores.
    """

    def __init__(self, config, exchange, db_manager):
        """
        Initialize market scanner.
        
        Args:
            config: Configuration object
            exchange: BybitClient instance
            db_manager: DatabaseManager instance
        """
        self.config = config
        self.exchange = exchange
        self.db_manager = db_manager
        self.logger = None  # Will be set by main bot
        
        # Scanner state
        self._running = False
        self._scan_interval = 5  # seconds
        self._markets: list[dict] = []
        self._opportunities: list[dict] = []
        self._market_data: dict[str, dict] = {}
        
        # Indicator cache
        self._indicator_cache: dict[str, dict] = {}

    async def run(self):
        """Main scanner loop."""
        self._running = True
        
        if self.logger:
            self.logger.info("Market scanner started")
        
        while self._running:
            try:
                await self._scan_markets()
                await asyncio.sleep(self._scan_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Scanner error: {e}", exc_info=True)
                await asyncio.sleep(self._scan_interval)

    async def stop(self):
        """Stop the scanner."""
        self._running = False
        if self.logger:
            self.logger.info("Market scanner stopped")

    async def _scan_markets(self):
        """Scan all markets and update opportunities."""
        try:
            # Get all markets from exchange
            if not self._markets:
                self._markets = await self.exchange.get_futures_markets()
            
            # Filter active markets
            active_markets = [
                m for m in self._markets
                if m.get("status") == "Trading"
            ]
            
            if self.logger:
                self.logger.debug(f"Scanning {len(active_markets)} markets")
            
            # Scan each market
            tasks = []
            for market in active_markets:
                symbol = market["symbol"]
                tasks.append(self._scan_symbol(symbol))
            
            # Wait for all scans to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Sort opportunities by score
            self._opportunities.sort(
                key=lambda x: x.get("opportunity_score", 0),
                reverse=True
            )
            
            # Keep only top opportunities
            max_opportunities = 100
            self._opportunities = self._opportunities[:max_opportunities]
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error scanning markets: {e}")

    async def _scan_symbol(self, symbol: str):
        """
        Scan a single symbol and calculate opportunity score.
        
        Args:
            symbol: Trading pair symbol
        """
        try:
            # Get ticker data
            ticker = await self.exchange.get_ticker(symbol)
            if not ticker:
                return
            
            # Get recent candles for analysis
            candles_1h = await self.exchange.get_klines(symbol, "60", limit=100)
            if not candles_1h:
                return
            
            # Convert to DataFrame
            df = pd.DataFrame(candles_1h)
            if len(df) < 50:
                return
            
            # Calculate basic metrics
            price = float(ticker.get("lastPrice", 0))
            volume_24h = float(ticker.get("volume24h", 0))
            funding_rate = float(ticker.get("fundingRate", 0))
            
            # Calculate ATR
            atr = self._calculate_atr(df, period=14)
            
            # Calculate volatility
            volatility = self._calculate_volatility(df)
            
            # Determine trend
            trend = self._determine_trend(df)
            
            # Calculate opportunity score
            score = self._calculate_opportunity_score(
                df=df,
                price=price,
                volume_24h=volume_24h,
                funding_rate=funding_rate,
                atr=atr,
                volatility=volatility,
                trend=trend
            )
            
            # Store market data
            self._market_data[symbol] = {
                "symbol": symbol,
                "price": price,
                "volume_24h": volume_24h,
                "funding_rate": funding_rate,
                "atr": atr,
                "volatility": volatility,
                "trend": trend,
                "opportunity_score": score,
                "timestamp": datetime.utcnow(),
            }
            
            # Save to database
            await self.db_manager.save_scanner_result(
                symbol=symbol,
                price=price,
                volume_24h=volume_24h,
                funding_rate=funding_rate,
                atr=atr,
                volatility=volatility,
                trend=trend,
                opportunity_score=score,
                indicators="{}",
            )
            
            # Add to opportunities if score is high enough
            threshold = self.config.trading.opportunity_threshold
            if score >= threshold:
                self._update_opportunity(symbol, score, trend)
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error scanning {symbol}: {e}")

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"].shift(1)
            
            tr1 = high - low
            tr2 = abs(high - close)
            tr3 = abs(low - close)
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=period).mean().iloc[-1]
            
            return float(atr) if not pd.isna(atr) else 0.0
            
        except Exception:
            return 0.0

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate price volatility (standard deviation of returns)."""
        try:
            returns = df["close"].pct_change()
            volatility = returns.std()
            return float(volatility) if not pd.isna(volatility) else 0.0
            
        except Exception:
            return 0.0

    def _determine_trend(self, df: pd.DataFrame) -> str:
        """
        Determine market trend based on EMA alignment.
        
        Returns:
            Trend string: strong_bullish, bullish, neutral, bearish, strong_bearish
        """
        try:
            close = df["close"]
            
            # Calculate EMAs
            ema20 = close.ewm(span=20, adjust=False).mean()
            ema50 = close.ewm(span=50, adjust=False).mean()
            ema200 = close.ewm(span=200, adjust=False).mean()
            
            current_price = close.iloc[-1]
            ema20_val = ema20.iloc[-1]
            ema50_val = ema50.iloc[-1]
            ema200_val = ema200.iloc[-1]
            
            # Bullish conditions
            if current_price > ema20_val > ema50_val > ema200_val:
                return "strong_bullish"
            elif current_price > ema200_val:
                return "bullish"
            
            # Bearish conditions
            elif current_price < ema20_val < ema50_val < ema200_val:
                return "strong_bearish"
            elif current_price < ema200_val:
                return "bearish"
            
            # Neutral
            else:
                return "neutral"
                
        except Exception:
            return "neutral"

    def _calculate_opportunity_score(
        self,
        df: pd.DataFrame,
        price: float,
        volume_24h: float,
        funding_rate: float,
        atr: float,
        volatility: float,
        trend: str
    ) -> int:
        """
        Calculate opportunity score (0-100).
        
        Args:
            df: Price DataFrame
            price: Current price
            volume_24h: 24h volume
            funding_rate: Current funding rate
            atr: Average True Range
            volatility: Price volatility
            trend: Market trend
            
        Returns:
            Opportunity score (0-100)
        """
        score = 50  # Base score
        
        # Trend score (up to ±20 points)
        trend_scores = {
            "strong_bullish": 20,
            "bullish": 10,
            "neutral": 0,
            "bearish": -10,
            "strong_bearish": -20,
        }
        score += trend_scores.get(trend, 0)
        
        # Volume score (up to +15 points)
        if volume_24h > 100_000_000:  # High volume
            score += 15
        elif volume_24h > 50_000_000:
            score += 10
        elif volume_24h > 10_000_000:
            score += 5
        
        # Funding rate score (up to ±10 points)
        # Prefer slightly negative funding for longs, positive for shorts
        if -0.0005 <= funding_rate <= 0.0005:
            score += 5  # Neutral funding is good
        elif funding_rate < -0.001:
            score += 10  # Very negative - potential long opportunity
        elif funding_rate > 0.001:
            score -= 10  # Very positive - avoid longs
        
        # Volatility score (up to +10 points)
        # Moderate volatility is preferred
        if 0.01 <= volatility <= 0.05:
            score += 10
        elif 0.005 <= volatility < 0.01 or 0.05 < volatility <= 0.1:
            score += 5
        elif volatility > 0.1:
            score -= 5  # Too volatile
        
        # ATR score (up to +10 points)
        if atr > 0 and price > 0:
            atr_pct = (atr / price) * 100
            if 0.5 <= atr_pct <= 2.0:
                score += 10
            elif 0.2 <= atr_pct < 0.5 or 2.0 < atr_pct <= 3.0:
                score += 5
        
        # Momentum score (up to ±15 points)
        try:
            close = df["close"]
            rsi = self._calculate_rsi(close, period=14)
            
            if 40 <= rsi <= 60:
                score += 0  # Neutral
            elif 30 <= rsi < 40 or 60 < rsi <= 70:
                score += 5
            elif rsi < 30:
                score += 15  # Oversold - potential long
            elif rsi > 70:
                score -= 15  # Overbought - avoid long
        except Exception:
            pass
        
        # Clamp score to 0-100
        score = max(0, min(100, int(score)))
        
        return score

    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> float:
        """Calculate RSI."""
        try:
            delta = series.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
            
        except Exception:
            return 50.0

    def _update_opportunity(self, symbol: str, score: int, trend: str):
        """Update or add an opportunity."""
        # Remove existing entry for this symbol
        self._opportunities = [
            opp for opp in self._opportunities
            if opp["symbol"] != symbol
        ]
        
        # Add new opportunity
        market_data = self._market_data.get(symbol, {})
        self._opportunities.append({
            "symbol": symbol,
            "opportunity_score": score,
            "trend": trend,
            "price": market_data.get("price", 0),
            "volume_24h": market_data.get("volume_24h", 0),
            "timestamp": datetime.utcnow(),
        })

    def get_opportunities(self, limit: int = 10) -> list[dict]:
        """
        Get top trading opportunities.
        
        Args:
            limit: Maximum number of opportunities to return
            
        Returns:
            List of opportunity dictionaries
        """
        return self._opportunities[:limit]

    def get_market_data(self, symbol: str | None = None) -> dict | None:
        """
        Get cached market data.
        
        Args:
            symbol: Specific symbol or None for all
            
        Returns:
            Market data dictionary or None
        """
        if symbol:
            return self._market_data.get(symbol)
        return self._market_data

    def get_all_markets(self) -> list[dict]:
        """Get all scanned markets."""
        return self._markets
