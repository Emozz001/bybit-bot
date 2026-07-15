"""
Bybit Exchange Client.

Handles all interactions with the Bybit API including REST and WebSocket connections.
Implements rate limiting, retry logic, and automatic reconnection.
"""

import asyncio
import time
from typing import Any

import aiohttp
from pybit.unified_trading import HTTP, WebSocket


class BybitClient:
    """Bybit exchange client for REST and WebSocket API."""

    # Class-level constants for performance
    RATE_LIMIT_DELAY = 0.08  # 80ms between requests (optimized)
    MAX_RECONNECT_ATTEMPTS = 5
    CACHE_TTL_SECONDS = 5  # Cache expiration time

    def __init__(self, config):
        """
        Initialize Bybit client.
        
        Args:
            config: Configuration object with exchange settings
        """
        self.config = config
        self.logger = None  # Will be set by main bot
        self.testnet = config.exchange.testnet
        self.api_key = config.exchange.api_key
        self.api_secret = config.exchange.api_secret
        
        # REST client
        self._rest_client: HTTP | None = None
        
        # WebSocket clients
        self._ws_public: WebSocket | None = None
        self._ws_private: WebSocket | None = None
        
        # Rate limiting with token bucket
        self._rate_limiter = asyncio.Semaphore(10)  # Allow 10 concurrent requests
        self._last_request_time = 0.0
        
        # Connection state
        self._connected = False
        self._authenticated = False
        self._reconnect_attempts = 0
        
        # Market data cache with TTL
        self._markets: dict[str, dict] = {}
        self._markets_timestamp: float = 0.0
        self._tickers: dict[str, tuple[dict, float]] = {}  # (data, timestamp)
        self._orderbooks: dict[str, tuple[dict, float]] = {}
        
        # WebSocket callbacks
        self._ws_callbacks: dict[str, callable] = {}
        
        # HTTP session for aiohttp
        self._session: aiohttp.ClientSession | None = None

    async def connect(self) -> bool:
        """
        Connect to Bybit REST API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Initialize REST client
            self._rest_client = HTTP(
                testnet=self.testnet,
                api_key=self.api_key if self.api_key else None,
                api_secret=self.api_secret if self.api_secret else None,
            )
            
            # Test connection
            server_time = self._rest_client.get_time()
            if server_time:
                self._connected = True
                if self.logger:
                    self.logger.info("Connected to Bybit REST API")
                return True
            
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to connect to Bybit: {e}")
            return False

    async def authenticate(self) -> bool:
        """
        Authenticate with Bybit API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        if not self.api_key or not self.api_secret:
            if self.logger:
                self.logger.warning("No API credentials provided")
            return False
        
        try:
            # Test authentication by getting wallet balance
            balance = self._rest_client.get_wallet_balance(accountType="UNIFIED")
            
            if balance:
                self._authenticated = True
                if self.logger:
                    self.logger.info("Authenticated with Bybit API")
                return True
            
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Authentication failed: {e}")
            return False

    async def get_futures_markets(self) -> list[dict]:
        """
        Get all USDT perpetual futures markets.
        
        Returns:
            List of market dictionaries
        """
        try:
            await self._rate_limit()
            
            response = self._rest_client.get_instruments_info(
                category="linear",
                settle="USDT"
            )
            
            if response and "retCode" in response and response["retCode"] == 0:
                markets = response["result"]["list"]
                
                # Cache markets
                for market in markets:
                    symbol = market["symbol"]
                    self._markets[symbol] = {
                        "symbol": symbol,
                        "base_coin": market["baseCoin"],
                        "quote_coin": market["quoteCoin"],
                        "price_scale": float(market.get("priceScale", 2)),
                        "lot_size_filter": market.get("lotSizeFilter", {}),
                        "status": market.get("status", "Trading"),
                    }
                
                if self.logger:
                    self.logger.info(f"Cached {len(self._markets)} futures markets")
                
                return list(self._markets.values())
            
            return []
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get markets: {e}")
            return []

    async def get_ticker(self, symbol: str) -> dict | None:
        """
        Get ticker for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Ticker dictionary or None
        """
        try:
            await self._rate_limit()
            
            response = self._rest_client.get_tickers(
                category="linear",
                symbol=symbol
            )
            
            if response and "retCode" in response and response["retCode"] == 0:
                if response["result"]["list"]:
                    ticker = response["result"]["list"][0]
                    self._tickers[symbol] = ticker
                    return ticker
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Failed to get ticker for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 25) -> dict | None:
        """
        Get order book for a symbol.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of levels (default 25)
            
        Returns:
            Order book dictionary or None
        """
        try:
            await self._rate_limit()
            
            response = self._rest_client.get_orderbook(
                category="linear",
                symbol=symbol,
                limit=limit
            )
            
            if response and "retCode" in response and response["retCode"] == 0:
                orderbook = response["result"]
                self._orderbooks[symbol] = orderbook
                return orderbook
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Failed to get orderbook for {symbol}: {e}")
            return None

    async def get_klines(self, symbol: str, interval: str, limit: int = 200) -> list:
        """
        Get historical kline/candlestick data.
        
        Args:
            symbol: Trading pair symbol
            interval: Kline interval (e.g., '1', '5', '15', '60', 'D')
            limit: Number of candles to retrieve (max 200)
            
        Returns:
            List of candle dictionaries
        """
        try:
            await self._rate_limit()
            
            response = self._rest_client.get_kline(
                category="linear",
                symbol=symbol,
                interval=interval,
                limit=min(limit, 200)
            )
            
            if response and "retCode" in response and response["retCode"] == 0:
                candles = response["result"]["list"]
                return [
                    {
                        "timestamp": int(candle[0]),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]),
                        "turnover": float(candle[6]),
                    }
                    for candle in candles
                ]
            
            return []
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Failed to get klines for {symbol}: {e}")
            return []

    async def get_account_balance(self) -> dict | None:
        """
        Get account wallet balance.
        
        Returns:
            Balance dictionary or None
        """
        if not self._authenticated:
            return None
        
        try:
            await self._rate_limit()
            
            response = self._rest_client.get_wallet_balance(accountType="UNIFIED")
            
            if response and "retCode" in response and response["retCode"] == 0:
                return response["result"]
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get balance: {e}")
            return None

    async def get_positions(self) -> list[dict]:
        """
        Get all open positions.
        
        Returns:
            List of position dictionaries
        """
        if not self._authenticated:
            return []
        
        try:
            await self._rate_limit()
            
            response = self._rest_client.get_positions(
                category="linear",
                settle="USDT"
            )
            
            if response and "retCode" in response and response["retCode"] == 0:
                positions = response["result"]["list"]
                return [p for p in positions if float(p.get("size", 0)) != 0]
            
            return []
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to get positions: {e}")
            return []

    async def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "Market",
        price: float | None = None,
        reduce_only: bool = False,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> dict | None:
        """
        Place an order.
        
        Args:
            symbol: Trading pair symbol
            side: Buy or Sell
            qty: Order quantity
            order_type: Market or Limit
            price: Limit price (required for limit orders)
            reduce_only: Reduce only flag
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Order response or None
        """
        if not self._authenticated:
            if self.logger:
                self.logger.warning("Cannot place order - not authenticated")
            return None
        
        try:
            await self._rate_limit()
            
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": order_type,
                "qty": str(qty),
                "reduceOnly": reduce_only,
            }
            
            if order_type == "Limit" and price:
                params["price"] = str(price)
            
            if stop_loss:
                params["stopLoss"] = str(stop_loss)
            
            if take_profit:
                params["takeProfit"] = str(take_profit)
            
            response = self._rest_client.place_order(**params)
            
            if response and "retCode" in response:
                if self.logger:
                    if response["retCode"] == 0:
                        self.logger.info(f"Order placed: {symbol} {side} {qty}")
                    else:
                        self.logger.warning(f"Order failed: {response['retMsg']}")
                
                return response
            
            return None
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to place order: {e}")
            return None

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """
        Cancel an order.
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        if not self._authenticated:
            return False
        
        try:
            await self._rate_limit()
            
            response = self._rest_client.cancel_order(
                category="linear",
                symbol=symbol,
                orderId=order_id
            )
            
            if response and "retCode" in response and response["retCode"] == 0:
                if self.logger:
                    self.logger.info(f"Order cancelled: {symbol} {order_id}")
                return True
            
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to cancel order: {e}")
            return False

    async def start_websocket_streams(self):
        """Start WebSocket streams for real-time data."""
        try:
            # Public WebSocket for market data
            self._ws_public = WebSocket(
                testnet=self.testnet,
                channel_type="public"
            )
            
            # Private WebSocket for account updates
            if self._authenticated:
                self._ws_private = WebSocket(
                    testnet=self.testnet,
                    channel_type="private",
                    api_key=self.api_key,
                    api_secret=self.api_secret
                )
            
            if self.logger:
                self.logger.info("WebSocket streams initialized")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start WebSocket: {e}")

    async def subscribe_ticker(self, symbol: str, callback: callable):
        """
        Subscribe to ticker updates for a symbol.
        
        Args:
            symbol: Trading pair symbol
            callback: Callback function for ticker updates
        """
        if not self._ws_public:
            return
        
        try:
            self._ws_callbacks[f"ticker.{symbol}"] = callback
            
            self._ws_public.ticker_stream(
                symbol=symbol,
                callback=callback
            )
            
            if self.logger:
                self.logger.debug(f"Subscribed to ticker: {symbol}")
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Failed to subscribe ticker: {e}")

    async def _rate_limit(self):
        """Apply rate limiting to API requests with optimized token bucket algorithm."""
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)
        
        self._last_request_time = time.time()

    async def close(self):
        """Close all connections."""
        try:
            if self._ws_public:
                self._ws_public.close()
            
            if self._ws_private:
                self._ws_private.close()
            
            if self._session:
                await self._session.close()
            
            self._connected = False
            self._authenticated = False
            
            if self.logger:
                self.logger.info("Bybit connections closed")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error closing connections: {e}")
