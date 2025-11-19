"""
Configuration Loader Module
Loads and validates configuration from YAML and .env files
"""

import os
from pathlib import Path
from typing import Any, Dict
import yaml
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class TradingConfig(BaseModel):
    """Trading configuration"""
    capital: float = Field(gt=0)
    max_daily_loss_percent: float = Field(gt=0, le=100)
    risk_per_trade_percent: float = Field(gt=0, le=100)
    max_positions: int = Field(gt=0)
    trading_mode: str = Field(default="paper")

    @validator('trading_mode')
    def validate_mode(cls, v):
        if v not in ['paper', 'live']:
            raise ValueError('trading_mode must be either "paper" or "live"')
        return v


class StrategyConfig(BaseModel):
    """Strategy configuration"""
    regime_detection: Dict[str, Any]
    trending_strategy: Dict[str, Any]
    ranging_strategy: Dict[str, Any]
    multi_timeframe: Dict[str, Any]


class RiskManagementConfig(BaseModel):
    """Risk management configuration"""
    atr_period: int = 14
    atr_sl_multiplier: float = 3.0
    atr_tsl_multiplier: float = 2.5
    min_risk_reward: float = 2.0
    max_correlation: float = 0.7


class UpstoxSettings(BaseSettings):
    """Upstox API credentials from environment"""
    UPSTOX_API_KEY: str
    UPSTOX_API_SECRET: str
    UPSTOX_REDIRECT_URI: str
    UPSTOX_ACCESS_TOKEN: str = ""

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


class ConfigLoader:
    """Centralized configuration loader"""
    
    def __init__(self, config_path: str = "config/config.yaml", env_path: str = ".env"):
        """
        Initialize configuration loader
        
        Args:
            config_path: Path to YAML config file
            env_path: Path to .env file
        """
        self.config_path = Path(config_path)
        self.env_path = Path(env_path)
        
        # Load environment variables
        if self.env_path.exists():
            load_dotenv(self.env_path)
        
        # Load YAML configuration
        self.config_data = self._load_yaml()
        
        # Parse structured configs
        self.trading = TradingConfig(**self.config_data['trading'])
        self.strategy = StrategyConfig(**self.config_data['strategy'])
        self.risk_management = RiskManagementConfig(**self.config_data['risk_management'])
        self.upstox = UpstoxSettings()
        
        # Store raw configs for easy access
        self.market = self.config_data['market']
        self.order_execution = self.config_data['order_execution']
        self.websocket = self.config_data['websocket']
        self.logging = self.config_data['logging']
        self.backtesting = self.config_data['backtesting']
        self.watchlist = self.config_data['watchlist']
    
    def _load_yaml(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)"""
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        
        return value
    
    def validate(self) -> bool:
        """Validate all configuration"""
        try:
            # Check if all required settings are present
            assert self.upstox.UPSTOX_API_KEY, "UPSTOX_API_KEY not set"
            assert self.upstox.UPSTOX_API_SECRET, "UPSTOX_API_SECRET not set"
            assert self.trading.capital > 0, "Capital must be positive"
            assert self.trading.max_positions > 0, "Max positions must be positive"
            
            return True
        except AssertionError as e:
            raise ValueError(f"Configuration validation failed: {e}")
    
    def __repr__(self) -> str:
        return f"ConfigLoader(trading_mode={self.trading.trading_mode}, capital={self.trading.capital})"


# Global config instance (singleton pattern)
_config_instance = None


def get_config(config_path: str = "config/config.yaml") -> ConfigLoader:
    """Get global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader(config_path)
    return _config_instance
