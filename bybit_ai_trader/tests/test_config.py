"""Unit tests for configuration management."""

import pytest
from pathlib import Path
import tempfile
import yaml

from core.config import Config, TradingConfig, RiskConfig


class TestTradingConfig:
    """Tests for TradingConfig validation."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TradingConfig()
        assert config.mode == "paper"
        assert config.max_positions == 5
        assert config.max_leverage == 10
        assert config.opportunity_threshold == 90

    def test_valid_trading_mode(self):
        """Test valid trading modes."""
        config_paper = TradingConfig(mode="paper")
        assert config_paper.mode == "paper"
        
        config_live = TradingConfig(mode="live")
        assert config_live.mode == "live"

    def test_max_positions_validation(self):
        """Test max_positions validation."""
        # Valid values
        config = TradingConfig(max_positions=1)
        assert config.max_positions == 1
        
        config = TradingConfig(max_positions=10)
        assert config.max_positions == 10

    def test_max_leverage_validation(self):
        """Test max_leverage validation."""
        # Valid values
        config = TradingConfig(max_leverage=1)
        assert config.max_leverage == 1
        
        config = TradingConfig(max_leverage=100)
        assert config.max_leverage == 100

    def test_invalid_max_leverage(self):
        """Test invalid max_leverage raises error."""
        with pytest.raises(Exception):
            TradingConfig(max_leverage=101)
        
        with pytest.raises(Exception):
            TradingConfig(max_leverage=0)


class TestRiskConfig:
    """Tests for RiskConfig validation."""

    def test_default_values(self):
        """Test default risk configuration values."""
        config = RiskConfig()
        assert config.risk_per_trade == 1.0
        assert config.daily_loss_limit == 5.0
        assert config.weekly_loss_limit == 10.0
        assert config.monthly_loss_limit == 20.0
        assert config.min_risk_reward == 2.0

    def test_risk_per_trade_validation(self):
        """Test risk_per_trade validation."""
        config = RiskConfig(risk_per_trade=0.5)
        assert config.risk_per_trade == 0.5
        
        config = RiskConfig(risk_per_trade=5.0)
        assert config.risk_per_trade == 5.0

    def test_invalid_risk_per_trade(self):
        """Test invalid risk_per_trade raises error."""
        with pytest.raises(Exception):
            RiskConfig(risk_per_trade=0)
        
        with pytest.raises(Exception):
            RiskConfig(risk_per_trade=-1)


class TestConfigLoad:
    """Tests for Config.load() method."""

    def test_load_with_yaml_file(self):
        """Test loading configuration from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "settings.yaml"
            config_data = {
                "trading": {
                    "mode": "paper",
                    "max_positions": 3,
                },
                "risk": {
                    "risk_per_trade": 2.0,
                }
            }
            
            with open(yaml_path, 'w') as f:
                yaml.dump(config_data, f)
            
            config = Config.load(str(yaml_path))
            assert config.trading.max_positions == 3
            assert config.risk.risk_per_trade == 2.0

    def test_load_without_yaml_file(self):
        """Test loading configuration without YAML file (uses defaults)."""
        config = Config.load("nonexistent.yaml")
        assert config.trading.max_positions == 5
        assert config.risk.risk_per_trade == 1.0
