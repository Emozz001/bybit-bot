"""Advanced Execution Module for Scale-In/Scale-Out."""

from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ScaleLevel:
    """Represents a scale-in or scale-out level."""
    level: int
    percentage: float
    price_offset: float
    trigger_price: Optional[float] = None
    executed: bool = False
    execution_price: Optional[float] = None


class ScaleManager:
    """Manages scale-in and scale-out execution strategies."""
    
    def __init__(self, config):
        self.config = config
        self.scale_in_enabled = getattr(config, 'scale_in_enabled', True)
        self.scale_in_tranches = getattr(config, 'scale_in_tranches', 3)
        self.scale_in_increment = getattr(config, 'scale_in_increment', 0.5)
        self.scale_out_enabled = getattr(config, 'scale_out_enabled', True)
        self.scale_out_levels = getattr(config, 'scale_out_levels', 3)
        
        percentages_str = getattr(config, 'scale_out_percentages', '30,30,40')
        self.scale_out_percentages = [float(p) for p in percentages_str.split(',')]
        
        targets_str = getattr(config, 'scale_out_targets', '1.0,2.0,3.0')
        self.scale_out_targets = [float(t) for t in targets_str.split(',')]
        
        self.trailing_stop_activation = getattr(config, 'trailing_stop_activation', 1.5)
        self.trailing_stop_distance = getattr(config, 'trailing_stop_distance', 0.5)
        self.max_slippage = getattr(config, 'max_slippage', 0.1)
        self.active_positions = {}
    
    def generate_scale_in_orders(self, symbol, side, base_entry_price, total_position_size, atr=0.0):
        """Generate scale-in order levels."""
        if not self.scale_in_enabled:
            return [ScaleLevel(level=1, percentage=100.0, price_offset=0.0, trigger_price=base_entry_price)]
        
        orders = []
        for i in range(self.scale_in_tranches):
            percentage = 100.0 / self.scale_in_tranches
            if i == 0:
                offset = 0.0
            else:
                offset = -self.scale_in_increment * i if side == 'Buy' else self.scale_in_increment * i
            
            trigger_price = base_entry_price * (1 + offset / 100) if side == 'Buy' else base_entry_price * (1 - offset / 100)
            orders.append(ScaleLevel(level=i+1, percentage=percentage, price_offset=offset, trigger_price=trigger_price))
        return orders
    
    def generate_scale_out_orders(self, symbol, side, entry_price, position_size):
        """Generate scale-out order levels."""
        if not self.scale_out_enabled:
            return []
        
        orders = []
        num_levels = min(len(self.scale_out_percentages), len(self.scale_out_targets), self.scale_out_levels)
        
        for i in range(num_levels):
            percentage = self.scale_out_percentages[i]
            target_pct = self.scale_out_targets[i]
            trigger_price = entry_price * (1 + target_pct / 100) if side == 'Buy' else entry_price * (1 - target_pct / 100)
            orders.append(ScaleLevel(level=i+1, percentage=percentage, price_offset=target_pct, trigger_price=trigger_price))
        return orders
    
    def calculate_trailing_stop(self, side, entry_price, current_price, highest_price, lowest_price, atr=0.0):
        """Calculate trailing stop price."""
        if side == 'Buy':
            profit_pct = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_pct = ((entry_price - current_price) / entry_price) * 100
        
        if profit_pct < self.trailing_stop_activation:
            return None
        
        if side == 'Buy':
            stop_price = highest_price * (1 - self.trailing_stop_distance / 100)
        else:
            stop_price = lowest_price * (1 + self.trailing_stop_distance / 100)
        return stop_price
    
    def check_slippage(self, expected_price, actual_price, side):
        """Check if slippage exceeds maximum allowed."""
        if expected_price > 0:
            if side == 'Buy':
                slippage = ((actual_price - expected_price) / expected_price) * 100
            else:
                slippage = ((expected_price - actual_price) / expected_price) * 100
        else:
            slippage = 0.0
        return abs(slippage) <= self.max_slippage, slippage
