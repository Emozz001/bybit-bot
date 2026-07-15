"""Advanced Trading Strategies Module.

Implements multiple trading strategies for ensemble approach:
- Trend Following
- Mean Reversion
- Breakout
- Momentum
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class StrategyType(Enum):
    """Available strategy types."""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    MOMENTUM = "momentum"


@dataclass
class StrategySignal:
    """Trading signal from a strategy."""
    
    strategy_type: StrategyType
    symbol: str
    side: Optional[str]  # Buy, Sell, or None
    strength: float  # 0-100 confidence score
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timeframe: str = "15m"
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(self, config):
        """Initialize strategy with configuration."""
        self.config = config
        self.name = self.__class__.__name__
        
    @abstractmethod
    def generate_signal(self, market_data: dict) -> Optional[StrategySignal]:
        """Generate trading signal based on market data.
        
        Args:
            market_data: Dictionary containing OHLCV data and indicators
            
        Returns:
            StrategySignal if conditions met, None otherwise
        """
        pass
    
    @abstractmethod
    def calculate_confidence(self, market_data: dict) -> float:
        """Calculate confidence score for the strategy signal.
        
        Args:
            market_data: Dictionary containing market data
            
        Returns:
            Confidence score between 0-100
        """
        pass


class TrendFollowingStrategy(BaseStrategy):
    """Trend following strategy using moving averages and ADX."""
    
    def __init__(self, config):
        super().__init__(config)
        self.ema_fast = 20
        self.ema_slow = 50
        self.adx_threshold = 25
        
    def generate_signal(self, market_data: dict) -> Optional[StrategySignal]:
        """Generate trend following signal."""
        if not self._has_required_data(market_data):
            return None
        
        ema_fast = market_data.get('ema_fast', [])
        ema_slow = market_data.get('ema_slow', [])
        adx = market_data.get('adx', 0)
        close_prices = market_data.get('close', [])
        
        if len(ema_fast) < 2 or len(ema_slow) < 2:
            return None
        
        # Check for trend direction
        bullish_crossover = ema_fast[-1] > ema_slow[-1] and ema_fast[-2] <= ema_slow[-2]
        bearish_crossover = ema_fast[-1] < ema_slow[-1] and ema_fast[-2] >= ema_slow[-2]
        
        # Confirm with ADX
        if adx < self.adx_threshold:
            return None
        
        current_price = close_prices[-1] if close_prices else 0
        
        if bullish_crossover:
            atr = market_data.get('atr', 0)
            stop_loss = current_price - (2.5 * atr) if atr > 0 else current_price * 0.98
            take_profit = current_price + (3 * abs(current_price - stop_loss))
            
            return StrategySignal(
                strategy_type=StrategyType.TREND_FOLLOWING,
                symbol=market_data.get('symbol', 'UNKNOWN'),
                side='Buy',
                strength=self.calculate_confidence(market_data),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=market_data.get('timeframe', '15m')
            )
        
        elif bearish_crossover:
            atr = market_data.get('atr', 0)
            stop_loss = current_price + (2.5 * atr) if atr > 0 else current_price * 1.02
            take_profit = current_price - (3 * abs(stop_loss - current_price))
            
            return StrategySignal(
                strategy_type=StrategyType.TREND_FOLLOWING,
                symbol=market_data.get('symbol', 'UNKNOWN'),
                side='Sell',
                strength=self.calculate_confidence(market_data),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=market_data.get('timeframe', '15m')
            )
        
        return None
    
    def calculate_confidence(self, market_data: dict) -> float:
        """Calculate confidence based on trend strength."""
        adx = market_data.get('adx', 0)
        
        # Higher ADX = stronger trend = higher confidence
        if adx > 40:
            adx_score = 40
        elif adx > 25:
            adx_score = adx
        else:
            adx_score = 0
        
        # Check volume confirmation
        volume = market_data.get('volume', [])
        avg_volume = sum(volume[-10:-1]) / 9 if len(volume) > 10 else 0
        current_volume = volume[-1] if volume else 0
        
        volume_score = min(30, (current_volume / avg_volume) * 15) if avg_volume > 0 else 15
        
        # Multi-timeframe alignment bonus
        mt_alignment = market_data.get('mtf_aligned', False)
        mtf_score = 30 if mt_alignment else 15
        
        return min(100, adx_score + volume_score + mtf_score)
    
    def _has_required_data(self, market_data: dict) -> bool:
        """Check if required data is available."""
        required = ['ema_fast', 'ema_slow', 'adx', 'close']
        return all(key in market_data for key in required)


class MeanReversionStrategy(BaseStrategy):
    """Mean reversion strategy using Bollinger Bands and RSI."""
    
    def __init__(self, config):
        super().__init__(config)
        self.bb_std_dev = 2.0
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        
    def generate_signal(self, market_data: dict) -> Optional[StrategySignal]:
        """Generate mean reversion signal."""
        if not self._has_required_data(market_data):
            return None
        
        close_prices = market_data.get('close', [])
        bb_upper = market_data.get('bb_upper', [])
        bb_lower = market_data.get('bb_lower', [])
        bb_middle = market_data.get('bb_middle', [])
        rsi = market_data.get('rsi', 50)
        
        if not all([close_prices, bb_upper, bb_lower, bb_middle]):
            return None
        
        current_price = close_prices[-1]
        
        # Oversold condition: price below lower BB and RSI oversold
        if current_price < bb_lower[-1] and rsi < self.rsi_oversold:
            atr = market_data.get('atr', 0)
            stop_loss = current_price - (2 * atr) if atr > 0 else bb_lower[-1] * 0.98
            take_profit = bb_middle[-1]  # Target is the mean
            
            return StrategySignal(
                strategy_type=StrategyType.MEAN_REVERSION,
                symbol=market_data.get('symbol', 'UNKNOWN'),
                side='Buy',
                strength=self.calculate_confidence(market_data),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=market_data.get('timeframe', '15m')
            )
        
        # Overbought condition: price above upper BB and RSI overbought
        elif current_price > bb_upper[-1] and rsi > self.rsi_overbought:
            atr = market_data.get('atr', 0)
            stop_loss = current_price + (2 * atr) if atr > 0 else bb_upper[-1] * 1.02
            take_profit = bb_middle[-1]  # Target is the mean
            
            return StrategySignal(
                strategy_type=StrategyType.MEAN_REVERSION,
                symbol=market_data.get('symbol', 'UNKNOWN'),
                side='Sell',
                strength=self.calculate_confidence(market_data),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=market_data.get('timeframe', '15m')
            )
        
        return None
    
    def calculate_confidence(self, market_data: dict) -> float:
        """Calculate confidence based on mean reversion signals."""
        close_prices = market_data.get('close', [])
        bb_upper = market_data.get('bb_upper', [])
        bb_lower = market_data.get('bb_lower', [])
        rsi = market_data.get('rsi', 50)
        
        if not all([close_prices, bb_upper, bb_lower]):
            return 0
        
        current_price = close_prices[-1]
        bb_width = (bb_upper[-1] - bb_lower[-1]) / bb_upper[-1] if bb_upper[-1] > 0 else 0
        
        # Price deviation from bands
        if current_price < bb_lower[-1]:
            deviation = (bb_lower[-1] - current_price) / bb_lower[-1]
        elif current_price > bb_upper[-1]:
            deviation = (current_price - bb_upper[-1]) / bb_upper[-1]
        else:
            deviation = 0
        
        deviation_score = min(40, deviation * 1000)
        
        # RSI extremity
        if rsi < 20 or rsi > 80:
            rsi_score = 40
        elif rsi < 30 or rsi > 70:
            rsi_score = 30
        else:
            rsi_score = 15
        
        # Band width (wider bands = better mean reversion opportunity)
        width_score = min(20, bb_width * 200)
        
        return min(100, deviation_score + rsi_score + width_score)
    
    def _has_required_data(self, market_data: dict) -> bool:
        """Check if required data is available."""
        required = ['close', 'bb_upper', 'bb_lower', 'bb_middle', 'rsi']
        return all(key in market_data for key in required)


class BreakoutStrategy(BaseStrategy):
    """Breakout strategy using support/resistance levels."""
    
    def __init__(self, config):
        super().__init__(config)
        self.lookback_period = 20
        self.volume_multiplier = 1.5
        
    def generate_signal(self, market_data: dict) -> Optional[StrategySignal]:
        """Generate breakout signal."""
        if not self._has_required_data(market_data):
            return None
        
        high_prices = market_data.get('high', [])
        low_prices = market_data.get('low', [])
        close_prices = market_data.get('close', [])
        volume = market_data.get('volume', [])
        
        if len(high_prices) < self.lookback_period:
            return None
        
        # Calculate resistance and support
        resistance = max(high_prices[-self.lookback_period:-1])
        support = min(low_prices[-self.lookback_period:-1])
        
        current_price = close_prices[-1]
        current_volume = volume[-1] if volume else 0
        avg_volume = sum(volume[-self.lookback_period:-1]) / self.lookback_period
        
        # Bullish breakout
        if current_price > resistance and current_volume > (avg_volume * self.volume_multiplier):
            range_size = resistance - support
            atr = market_data.get('atr', 0)
            stop_loss = resistance - (atr * 2) if atr > 0 else support
            take_profit = current_price + (range_size * 0.8)
            
            return StrategySignal(
                strategy_type=StrategyType.BREAKOUT,
                symbol=market_data.get('symbol', 'UNKNOWN'),
                side='Buy',
                strength=self.calculate_confidence(market_data),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=market_data.get('timeframe', '15m')
            )
        
        # Bearish breakout
        elif current_price < support and current_volume > (avg_volume * self.volume_multiplier):
            range_size = resistance - support
            atr = market_data.get('atr', 0)
            stop_loss = support + (atr * 2) if atr > 0 else resistance
            take_profit = current_price - (range_size * 0.8)
            
            return StrategySignal(
                strategy_type=StrategyType.BREAKOUT,
                symbol=market_data.get('symbol', 'UNKNOWN'),
                side='Sell',
                strength=self.calculate_confidence(market_data),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=market_data.get('timeframe', '15m')
            )
        
        return None
    
    def calculate_confidence(self, market_data: dict) -> float:
        """Calculate confidence based on breakout quality."""
        volume = market_data.get('volume', [])
        high_prices = market_data.get('high', [])
        low_prices = market_data.get('low', [])
        
        if len(volume) < self.lookback_period:
            return 0
        
        current_volume = volume[-1]
        avg_volume = sum(volume[-self.lookback_period:-1]) / self.lookback_period
        
        # Volume surge
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        volume_score = min(50, volume_ratio * 20)
        
        # Range compression before breakout
        recent_range = max(high_prices[-5:]) - min(low_prices[-5:])
        prior_range = max(high_prices[-10:-5]) - min(low_prices[-10:-5])
        
        if prior_range > 0 and recent_range < prior_range * 0.5:
            compression_score = 30  # Compression before breakout is bullish
        else:
            compression_score = 15
        
        # Time of day liquidity
        hour_score = 20  # Default
        
        return min(100, volume_score + compression_score + hour_score)
    
    def _has_required_data(self, market_data: dict) -> bool:
        """Check if required data is available."""
        required = ['high', 'low', 'close', 'volume']
        return all(key in market_data for key in required)


class MomentumStrategy(BaseStrategy):
    """Momentum strategy using rate of change and MACD."""
    
    def __init__(self, config):
        super().__init__(config)
        self.roc_period = 10
        
    def generate_signal(self, market_data: dict) -> Optional[StrategySignal]:
        """Generate momentum signal."""
        if not self._has_required_data(market_data):
            return None
        
        close_prices = market_data.get('close', [])
        macd_line = market_data.get('macd_line', [])
        signal_line = market_data.get('signal_line', [])
        
        if len(close_prices) < self.roc_period + 1:
            return None
        
        # Calculate Rate of Change
        roc = ((close_prices[-1] - close_prices[-self.roc_period]) / 
               close_prices[-self.roc_period]) * 100
        
        # MACD crossover
        macd_bullish = (len(macd_line) >= 2 and len(signal_line) >= 2 and
                       macd_line[-1] > signal_line[-1] and 
                       macd_line[-2] <= signal_line[-2])
        
        macd_bearish = (len(macd_line) >= 2 and len(signal_line) >= 2 and
                       macd_line[-1] < signal_line[-1] and 
                       macd_line[-2] >= signal_line[-2])
        
        current_price = close_prices[-1]
        
        # Strong bullish momentum
        if roc > 2 and macd_bullish:
            atr = market_data.get('atr', 0)
            stop_loss = current_price - (2.5 * atr) if atr > 0 else current_price * 0.97
            take_profit = current_price * (1 + roc * 1.5 / 100)
            
            return StrategySignal(
                strategy_type=StrategyType.MOMENTUM,
                symbol=market_data.get('symbol', 'UNKNOWN'),
                side='Buy',
                strength=self.calculate_confidence(market_data),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=market_data.get('timeframe', '15m')
            )
        
        # Strong bearish momentum
        elif roc < -2 and macd_bearish:
            atr = market_data.get('atr', 0)
            stop_loss = current_price + (2.5 * atr) if atr > 0 else current_price * 1.03
            take_profit = current_price * (1 - abs(roc) * 1.5 / 100)
            
            return StrategySignal(
                strategy_type=StrategyType.MOMENTUM,
                symbol=market_data.get('symbol', 'UNKNOWN'),
                side='Sell',
                strength=self.calculate_confidence(market_data),
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timeframe=market_data.get('timeframe', '15m')
            )
        
        return None
    
    def calculate_confidence(self, market_data: dict) -> float:
        """Calculate confidence based on momentum strength."""
        close_prices = market_data.get('close', [])
        
        if len(close_prices) < self.roc_period + 1:
            return 0
        
        # Rate of Change magnitude
        roc = ((close_prices[-1] - close_prices[-self.roc_period]) / 
               close_prices[-self.roc_period]) * 100
        
        roc_score = min(40, abs(roc) * 10)
        
        # Momentum consistency
        up_days = sum(1 for i in range(-5, 0) if close_prices[i] > close_prices[i-1])
        consistency_score = up_days * 6 if roc > 0 else (5 - up_days) * 6
        
        # Volume confirmation
        volume = market_data.get('volume', [])
        if len(volume) >= 5:
            avg_volume = sum(volume[-5:-1]) / 4
            current_volume = volume[-1]
            volume_score = min(20, (current_volume / avg_volume) * 10) if avg_volume > 0 else 10
        else:
            volume_score = 10
        
        return min(100, roc_score + consistency_score + volume_score)
    
    def _has_required_data(self, market_data: dict) -> bool:
        """Check if required data is available."""
        required = ['close', 'macd_line', 'signal_line']
        return all(key in market_data for key in required)


class EnsembleStrategyManager:
    """Manages ensemble of multiple strategies."""
    
    def __init__(self, config):
        """Initialize ensemble manager with all strategies."""
        self.config = config
        self.strategies = {
            StrategyType.TREND_FOLLOWING: TrendFollowingStrategy(config),
            StrategyType.MEAN_REVERSION: MeanReversionStrategy(config),
            StrategyType.BREAKOUT: BreakoutStrategy(config),
            StrategyType.MOMENTUM: MomentumStrategy(config),
        }
        
        # Strategy weights from config
        weights_str = getattr(config, 'strategy_weights', '0.4,0.3,0.2,0.1')
        self.weights = [float(w) for w in weights_str.split(',')]
        
        self.min_confluence = getattr(config, 'min_confluence_score', 75)
    
    def generate_signals(self, market_data: dict) -> list[StrategySignal]:
        """Generate signals from all strategies."""
        signals = []
        
        for strategy_type, strategy in self.strategies.items():
            signal = strategy.generate_signal(market_data)
            if signal:
                signals.append(signal)
        
        return signals
    
    def get_ensemble_decision(self, market_data: dict) -> Optional[StrategySignal]:
        """Get combined decision from all strategies using weighted voting."""
        signals = self.generate_signals(market_data)
        
        if not signals:
            return None
        
        # Group signals by side
        buy_signals = [s for s in signals if s.side == 'Buy']
        sell_signals = [s for s in signals if s.side == 'Sell']
        
        # Calculate weighted scores
        buy_score = self._calculate_weighted_score(buy_signals)
        sell_score = self._calculate_weighted_score(sell_signals)
        
        # Determine dominant side
        if buy_score >= self.min_confluence and buy_score > sell_score:
            return self._create_ensemble_signal(buy_signals, 'Buy', market_data)
        elif sell_score >= self.min_confluence and sell_score > buy_score:
            return self._create_ensemble_signal(sell_signals, 'Sell', market_data)
        
        return None
    
    def _calculate_weighted_score(self, signals: list[StrategySignal]) -> float:
        """Calculate weighted score for a set of signals."""
        if not signals:
            return 0
        
        total_weight = 0
        weighted_strength = 0
        
        for signal in signals:
            weight_idx = list(self.strategies.keys()).index(signal.strategy_type)
            weight = self.weights[weight_idx] if weight_idx < len(self.weights) else 0.25
            
            total_weight += weight
            weighted_strength += signal.strength * weight
        
        return weighted_strength / total_weight if total_weight > 0 else 0
    
    def _create_ensemble_signal(self, signals: list[StrategySignal], side: str, 
                                market_data: dict) -> StrategySignal:
        """Create consolidated ensemble signal."""
        # Average entry prices
        entries = [s.entry_price for s in signals if s.entry_price]
        avg_entry = sum(entries) / len(entries) if entries else 0
        
        # Conservative stop loss (closest to entry)
        if side == 'Buy':
            stops = [s.stop_loss for s in signals if s.stop_loss and s.stop_loss < avg_entry]
            stop_loss = max(stops) if stops else avg_entry * 0.98
            
            takes = [s.take_profit for s in signals if s.take_profit and s.take_profit > avg_entry]
            take_profit = min(takes) if takes else avg_entry * 1.03
        else:
            stops = [s.stop_loss for s in signals if s.stop_loss and s.stop_loss > avg_entry]
            stop_loss = min(stops) if stops else avg_entry * 1.02
            
            takes = [s.take_profit for s in signals if s.take_profit and s.take_profit < avg_entry]
            take_profit = max(takes) if takes else avg_entry * 0.97
        
        # Average strength
        avg_strength = sum(s.strength for s in signals) / len(signals)
        
        return StrategySignal(
            strategy_type=StrategyType.TREND_FOLLOWING,  # Primary strategy
            symbol=market_data.get('symbol', 'UNKNOWN'),
            side=side,
            strength=avg_strength,
            entry_price=avg_entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            timeframe=market_data.get('timeframe', '15m'),
            metadata={'ensemble': True, 'num_signals': len(signals)}
        )
