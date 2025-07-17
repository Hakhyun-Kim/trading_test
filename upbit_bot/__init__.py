"""
Enhanced Upbit Trading Bot Package

This package provides:
- Trading bot with arbitrage strategies
- Comprehensive backtesting framework  
- Web interface for monitoring and control
- Parameter optimization tools
"""

__version__ = "2.0.0"
__author__ = "Upbit Trading Bot Team"

from .trading_bot import UpbitTradingBot, TradingConfig
from .backtest import EnhancedUpbitBacktest, BacktestConfig
from .web_app import app
from .kimchi_premium import KimchiPremiumCalculator, KimchiPremiumStrategy

__all__ = [
    'UpbitTradingBot',
    'TradingConfig', 
    'EnhancedUpbitBacktest',
    'BacktestConfig',
    'app',
    'KimchiPremiumCalculator',
    'KimchiPremiumStrategy'
] 