"""
Bitcoin Kimchi Premium Arbitrage Strategy

This module implements the Bitcoin kimchi premium arbitrage strategy:
1. Short Bitcoin on Binance when kimchi premium < 0.3%
2. Buy Bitcoin on Upbit with limit orders (one tick below current price)
3. Close positions when kimchi premium > 1.3%
4. Sell Bitcoin on Upbit with limit orders (one tick above current price)
"""

import requests
import time
import logging
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import ccxt
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class BitcoinArbitrageConfig:
    """Configuration for Bitcoin arbitrage strategy"""
    entry_premium_threshold: float = -2.0  # Enter position when premium < -2.0% (negative kimchi premium)
    exit_profit_threshold: float = 2.0     # Exit position when profit > 2.0% (actual profit percentage)
    max_position_size_btc: float = 0.1     # Maximum BTC position size
    tick_offset: int = 1                   # Number of ticks for limit orders
    max_open_positions: int = 3            # Maximum simultaneous positions
    use_market_orders_binance: bool = True  # Use market orders on Binance
    min_order_size_btc: float = 0.001      # Minimum BTC order size

class BitcoinKimchiPremiumCalculator:
    """Calculate Bitcoin kimchi premium between Binance and Upbit"""
    
    def __init__(self):
        self.binance = ccxt.binance()
        self.upbit = ccxt.upbit()
        
        # Exchange rate API
        self.exchange_rate_api = "https://api.exchangerate-api.com/v4/latest/USD"
        
        # Cache for exchange rates
        self._exchange_rate_cache = {}
        self._cache_timestamp = 0
        self._cache_duration = 300  # 5 minutes
        
    def get_usd_krw_rate(self) -> Optional[float]:
        """Get current USD/KRW exchange rate"""
        current_time = time.time()
        
        # Check cache first
        if (current_time - self._cache_timestamp < self._cache_duration and 
            'USD_KRW' in self._exchange_rate_cache):
            return self._exchange_rate_cache['USD_KRW']
        
        try:
            response = requests.get(self.exchange_rate_api, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'rates' in data and 'KRW' in data['rates']:
                usd_krw_rate = data['rates']['KRW']
                
                # Update cache
                self._exchange_rate_cache['USD_KRW'] = usd_krw_rate
                self._cache_timestamp = current_time
                
                logger.info(f"Retrieved USD/KRW rate: {usd_krw_rate}")
                return usd_krw_rate
                
        except Exception as e:
            logger.warning(f"Failed to get USD/KRW rate: {e}")
            # Use fallback rate
            return 1350.0
    
    def get_binance_btc_usdt_price(self) -> Optional[float]:
        """Get BTC/USDT price from Binance"""
        try:
            ticker = self.binance.fetch_ticker('BTC/USDT')
            btc_usdt_price = float(ticker['last'])
            logger.info(f"Binance BTC/USDT price: {btc_usdt_price}")
            return btc_usdt_price
        except Exception as e:
            logger.error(f"Failed to get Binance BTC/USDT price: {e}")
            return None
    
    def get_upbit_btc_krw_price(self) -> Optional[float]:
        """Get BTC/KRW price from Upbit"""
        try:
            ticker = self.upbit.fetch_ticker('BTC/KRW')
            btc_krw_price = float(ticker['last'])
            logger.info(f"Upbit BTC/KRW price: {btc_krw_price}")
            return btc_krw_price
        except Exception as e:
            logger.error(f"Failed to get Upbit BTC/KRW price: {e}")
            return None
    
    def get_order_book(self, exchange: str, symbol: str) -> Optional[Dict]:
        """Get order book for a specific exchange and symbol"""
        try:
            if exchange.lower() == 'binance':
                order_book = self.binance.fetch_order_book(symbol)
            elif exchange.lower() == 'upbit':
                order_book = self.upbit.fetch_order_book(symbol)
            else:
                raise ValueError(f"Unknown exchange: {exchange}")
            
            return order_book
        except Exception as e:
            logger.error(f"Failed to get order book for {exchange} {symbol}: {e}")
            return None
    
    def calculate_bitcoin_kimchi_premium(self) -> Optional[Dict]:
        """Calculate Bitcoin kimchi premium percentage"""
        try:
            # Get prices
            binance_btc_usdt = self.get_binance_btc_usdt_price()
            upbit_btc_krw = self.get_upbit_btc_krw_price()
            usd_krw_rate = self.get_usd_krw_rate()
            
            if not all([binance_btc_usdt, upbit_btc_krw, usd_krw_rate]):
                logger.error("Failed to get required prices for kimchi premium calculation")
                return None
            
            # Convert Binance BTC price to KRW
            binance_btc_krw = binance_btc_usdt * usd_krw_rate
            
            # Calculate kimchi premium
            kimchi_premium = ((upbit_btc_krw - binance_btc_krw) / binance_btc_krw) * 100
            
            # Get order books for better execution prices
            upbit_order_book = self.get_order_book('upbit', 'BTC/KRW')
            binance_order_book = self.get_order_book('binance', 'BTC/USDT')
            
            result = {
                'kimchi_premium_percentage': kimchi_premium,
                'upbit_btc_krw': upbit_btc_krw,
                'binance_btc_usdt': binance_btc_usdt,
                'binance_btc_krw': binance_btc_krw,
                'usd_krw_rate': usd_krw_rate,
                'timestamp': datetime.now().isoformat(),
                'price_difference_krw': upbit_btc_krw - binance_btc_krw,
                'upbit_order_book': upbit_order_book,
                'binance_order_book': binance_order_book
            }
            
            logger.info(f"Bitcoin Kimchi Premium: {kimchi_premium:.2f}%")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating Bitcoin kimchi premium: {e}")
            return None

class BitcoinArbitrageStrategy:
    """Bitcoin Kimchi Premium Arbitrage Strategy with Shorting"""
    
    def __init__(self, config: BitcoinArbitrageConfig):
        self.config = config
        self.calculator = BitcoinKimchiPremiumCalculator()
        self.open_positions = []
        self.position_counter = 0
        
    def get_limit_price(self, order_book: Dict, side: str, tick_offset: int = 1) -> float:
        """Calculate limit order price based on order book"""
        try:
            if side == 'buy':
                # For buying, use bid price minus tick offset
                best_bid = order_book['bids'][0][0]
                # Get price at tick_offset level if available
                if len(order_book['bids']) > tick_offset:
                    return order_book['bids'][tick_offset][0]
                return best_bid
            else:  # sell
                # For selling, use ask price plus tick offset
                best_ask = order_book['asks'][0][0]
                # Get price at tick_offset level if available
                if len(order_book['asks']) > tick_offset:
                    return order_book['asks'][tick_offset][0]
                return best_ask
        except Exception as e:
            logger.error(f"Error calculating limit price: {e}")
            return None
    
    def calculate_position_size(self, available_balance: float, btc_price: float) -> float:
        """Calculate optimal position size"""
        max_size_by_balance = available_balance / btc_price
        position_size = min(self.config.max_position_size_btc, max_size_by_balance * 0.95)
        
        # Ensure minimum order size
        if position_size < self.config.min_order_size_btc:
            return 0.0
        
        return round(position_size, 8)  # Round to 8 decimal places for BTC
    
    def should_enter_position(self, premium_data: Dict) -> bool:
        """Check if we should enter a new arbitrage position"""
        if not premium_data:
            return False
        
        # Check if we have room for more positions
        if len(self.open_positions) >= self.config.max_open_positions:
            logger.info(f"Maximum positions reached: {len(self.open_positions)}")
            return False
        
        # Check kimchi premium threshold
        premium = premium_data['kimchi_premium_percentage']
        if premium < self.config.entry_premium_threshold:
            logger.info(f"Kimchi premium {premium:.2f}% < entry threshold {self.config.entry_premium_threshold}%")
            return True
        
        return False
    
    def should_exit_position(self, position: Dict, current_premium: float, current_upbit_price: float, current_binance_price: float) -> bool:
        """Check if we should exit an existing position"""
        # Calculate total arbitrage profit percentage (both Upbit and Binance)
        # Upbit: Buy low, sell high
        upbit_profit_pct = ((current_upbit_price - position['upbit_entry_price']) / position['upbit_entry_price']) * 100
        
        # Binance: Short high, buy low (inverse relationship)
        binance_profit_pct = ((position['binance_entry_price'] - current_binance_price) / position['binance_entry_price']) * 100
        
        # Total arbitrage profit (weighted average)
        total_profit_percentage = (upbit_profit_pct + binance_profit_pct) / 2
        
        # Exit if total profit exceeds threshold
        if total_profit_percentage > self.config.exit_profit_threshold:
            logger.info(f"Total arbitrage profit {total_profit_percentage:.2f}% > exit threshold {self.config.exit_profit_threshold}%")
            return True
        
        # Check position age (optional: add time-based exit)
        position_age = datetime.now() - position['entry_time']
        if position_age > timedelta(days=7):  # Exit after 7 days
            logger.info(f"Position {position['id']} aged out: {position_age}")
            return True
        
        return False
    
    def execute_entry(self, premium_data: Dict, available_krw: float, available_usdt: float) -> Optional[Dict]:
        """Execute entry into arbitrage position"""
        try:
            # Calculate position size based on available USDT for Binance short
            btc_price_usdt = premium_data['binance_btc_usdt']
            position_size = self.calculate_position_size(available_usdt, btc_price_usdt)
            
            if position_size == 0:
                return None
            
            # Get order books
            upbit_order_book = premium_data.get('upbit_order_book')
            
            # Calculate Upbit limit buy price (one tick below current)
            upbit_limit_price = None
            if upbit_order_book:
                upbit_limit_price = self.get_limit_price(upbit_order_book, 'buy', self.config.tick_offset)
            
            # Create position entry
            self.position_counter += 1
            position = {
                'id': f'ARB_{self.position_counter}',
                'entry_time': datetime.now(),
                'entry_premium': premium_data['kimchi_premium_percentage'],
                'size_btc': position_size,
                'upbit_entry_price': upbit_limit_price or premium_data['upbit_btc_krw'],
                'binance_entry_price': btc_price_usdt,
                'status': 'pending_upbit',  # Wait for Upbit fill first
                'upbit_order_type': 'limit' if upbit_limit_price else 'market',
                'binance_order_type': 'market'
            }
            
            logger.info(f"Entering arbitrage position: {position}")
            self.open_positions.append(position)
            
            return position
            
        except Exception as e:
            logger.error(f"Error executing entry: {e}")
            return None
    
    def execute_exit(self, position: Dict, premium_data: Dict) -> Optional[Dict]:
        """Execute exit from arbitrage position"""
        try:
            # Get order books
            upbit_order_book = premium_data.get('upbit_order_book')
            
            # Calculate Upbit limit sell price (one tick above current)
            upbit_limit_price = None
            if upbit_order_book:
                upbit_limit_price = self.get_limit_price(upbit_order_book, 'sell', self.config.tick_offset)
            
            exit_data = {
                'position_id': position['id'],
                'exit_time': datetime.now(),
                'exit_premium': premium_data['kimchi_premium_percentage'],
                'upbit_exit_price': upbit_limit_price or premium_data['upbit_btc_krw'],
                'binance_exit_price': premium_data['binance_btc_usdt'],
                'upbit_order_type': 'limit' if upbit_limit_price else 'market',
                'profit_krw': None,  # Calculate after execution
                'profit_usdt': None  # Calculate after execution
            }
            
            # Remove from open positions
            self.open_positions.remove(position)
            
            logger.info(f"Exiting arbitrage position: {exit_data}")
            return exit_data
            
        except Exception as e:
            logger.error(f"Error executing exit: {e}")
            return None
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status"""
        try:
            premium_data = self.calculator.calculate_bitcoin_kimchi_premium()
            
            return {
                'strategy_name': 'Bitcoin Kimchi Premium Arbitrage',
                'entry_threshold': self.config.entry_premium_threshold,
                'exit_profit_threshold': self.config.exit_profit_threshold,
                'current_premium': premium_data.get('kimchi_premium_percentage', 0) if premium_data else 0,
                'open_positions': len(self.open_positions),
                'max_positions': self.config.max_open_positions,
                'positions': self.open_positions,
                'last_update': datetime.now().isoformat(),
                'market_data': premium_data
            }
            
        except Exception as e:
            logger.error(f"Error getting strategy status: {e}")
            return {'error': str(e)} 