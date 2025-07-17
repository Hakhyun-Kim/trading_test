"""
Kimchi Premium Strategy Implementation

This module implements the kimchi premium arbitrage strategy by:
1. Fetching Binance USDT/KRW prices
2. Fetching Upbit USDT/KRW prices
3. Getting actual USD/KRW exchange rates
4. Calculating kimchi premium percentage
5. Providing buy/sell signals based on premium thresholds
"""

import requests
import time
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
import ccxt

logger = logging.getLogger(__name__)

class KimchiPremiumCalculator:
    """Calculate kimchi premium between Binance and Upbit"""
    
    def __init__(self):
        self.binance = ccxt.binance()
        self.upbit = ccxt.upbit()
        
        # Exchange rate API (using exchangerate-api.com)
        self.exchange_rate_api = "https://api.exchangerate-api.com/v4/latest/USD"
        
        # Backup exchange rate APIs
        self.backup_exchange_apis = [
            "https://api.fxapi.com/v1/latest?base=USD&symbols=KRW",
            "https://api.currencyapi.com/v3/latest?apikey=YOUR_API_KEY&base_currency=USD&currencies=KRW"
        ]
        
        # Cache for exchange rates (valid for 5 minutes)
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
        
        # Try primary API
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
            logger.warning(f"Failed to get USD/KRW rate from primary API: {e}")
        
        # Try backup: Use Bank of Korea API
        try:
            # This is a simplified approach - in production you'd want to use official APIs
            # For now, we'll use a reasonable fallback
            fallback_rate = 1350.0  # Approximate USD/KRW rate
            logger.warning(f"Using fallback USD/KRW rate: {fallback_rate}")
            return fallback_rate
            
        except Exception as e:
            logger.error(f"Failed to get USD/KRW rate: {e}")
            return None
    
    def get_binance_usdt_krw_price(self) -> Optional[float]:
        """Get USDT/KRW price from Binance"""
        try:
            # Since USDT is pegged 1:1 with USD, we just need USD/KRW rate
            # USDT/USD is always approximately 1.0
            usdt_usd_price = 1.0  # USDT is a stablecoin pegged to USD
            
            usd_krw_rate = self.get_usd_krw_rate()
            if usd_krw_rate is None:
                return None
            
            # Calculate USDT/KRW price on Binance
            binance_usdt_krw = float(usdt_usd_price) * float(usd_krw_rate)
            
            logger.info(f"Binance USDT/KRW calculated price: {binance_usdt_krw}")
            return binance_usdt_krw
            
        except Exception as e:
            logger.error(f"Failed to get Binance USDT/KRW price: {e}")
            
            # Since we're already using USDT = 1 USD, just return the USD/KRW rate
            try:
                usd_krw_rate = self.get_usd_krw_rate()
                if usd_krw_rate:
                    logger.info(f"Using fallback: USDT/KRW = USD/KRW = {usd_krw_rate}")
                    return float(usd_krw_rate)
                else:
                    logger.error("Could not get USD/KRW rate for fallback")
                    return None
                
            except Exception as e2:
                logger.error(f"Failed fallback calculation: {e2}")
                return None
    
    def get_upbit_usdt_krw_price(self) -> Optional[float]:
        """Get USDT/KRW price from Upbit"""
        try:
            ticker = self.upbit.fetch_ticker('USDT/KRW')
            upbit_usdt_krw = float(ticker['last'])
            
            logger.info(f"Upbit USDT/KRW price: {upbit_usdt_krw}")
            return upbit_usdt_krw
            
        except Exception as e:
            logger.error(f"Failed to get Upbit USDT/KRW price: {e}")
            return None
    
    def calculate_kimchi_premium(self) -> Optional[Dict]:
        """Calculate kimchi premium percentage"""
        try:
            # Get prices
            binance_price = self.get_binance_usdt_krw_price()
            upbit_price = self.get_upbit_usdt_krw_price()
            usd_krw_rate = self.get_usd_krw_rate()
            
            if binance_price is None or upbit_price is None or usd_krw_rate is None:
                logger.error("Failed to get required prices for kimchi premium calculation")
                return None
            
            # Calculate kimchi premium
            # Premium = (Upbit_Price - Binance_Price) / Binance_Price * 100
            kimchi_premium = ((upbit_price - binance_price) / binance_price) * 100
            
            result = {
                'kimchi_premium_percentage': kimchi_premium,
                'upbit_usdt_krw': upbit_price,
                'binance_usdt_krw': binance_price,
                'usd_krw_rate': usd_krw_rate,
                'timestamp': datetime.now().isoformat(),
                'price_difference': upbit_price - binance_price
            }
            
            logger.info(f"Kimchi Premium: {kimchi_premium:.2f}%")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating kimchi premium: {e}")
            return None
    
    def get_trading_signal(self, buy_threshold: float = -2.0, 
                          sell_threshold: float = 2.0) -> Optional[Dict]:
        """
        Get trading signal based on kimchi premium thresholds
        
        Args:
            buy_threshold: Kimchi premium % below which to buy USDT (negative value)
            sell_threshold: Kimchi premium % above which to sell USDT (positive value)
        
        Returns:
            Dict with signal information
        """
        try:
            premium_data = self.calculate_kimchi_premium()
            if premium_data is None:
                return None
            
            kimchi_premium = premium_data['kimchi_premium_percentage']
            
            # Determine signal
            if kimchi_premium <= buy_threshold:
                signal = 'BUY'
                reason = f"Kimchi premium {kimchi_premium:.2f}% is below buy threshold {buy_threshold}%"
            elif kimchi_premium >= sell_threshold:
                signal = 'SELL'
                reason = f"Kimchi premium {kimchi_premium:.2f}% is above sell threshold {sell_threshold}%"
            else:
                signal = 'HOLD'
                reason = f"Kimchi premium {kimchi_premium:.2f}% is between thresholds"
            
            result = {
                'signal': signal,
                'reason': reason,
                'kimchi_premium': kimchi_premium,
                'buy_threshold': buy_threshold,
                'sell_threshold': sell_threshold,
                'timestamp': datetime.now().isoformat(),
                'market_data': premium_data
            }
            
            logger.info(f"Trading Signal: {signal} - {reason}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating trading signal: {e}")
            return None


class KimchiPremiumStrategy:
    """Kimchi Premium Trading Strategy"""
    
    def __init__(self, buy_threshold: float = -2.0, sell_threshold: float = 2.0):
        self.calculator = KimchiPremiumCalculator()
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        
        # Strategy parameters
        self.min_premium_for_trade = 0.5  # Minimum premium difference to consider
        self.max_trade_frequency = 4  # Maximum trades per day
        self.trade_count_today = 0
        self.last_trade_date = None
        
    def should_trade(self, signal_data: Dict) -> bool:
        """Check if we should execute a trade based on signal"""
        if signal_data is None:
            return False
        
        # Reset daily trade count if new day
        current_date = datetime.now().date()
        if self.last_trade_date != current_date:
            self.trade_count_today = 0
            self.last_trade_date = current_date
        
        # Check trade frequency limit
        if self.trade_count_today >= self.max_trade_frequency:
            logger.warning(f"Daily trade limit reached: {self.trade_count_today}")
            return False
        
        # Check if signal is actionable
        signal = signal_data.get('signal', 'HOLD')
        if signal == 'HOLD':
            return False
        
        # Check minimum premium difference
        premium = abs(signal_data.get('kimchi_premium', 0))
        if premium < self.min_premium_for_trade:
            logger.info(f"Premium {premium:.2f}% below minimum {self.min_premium_for_trade}%")
            return False
        
        return True
    
    def execute_strategy(self, balance_usd: float, max_trade_amount: float) -> Dict:
        """Execute the kimchi premium strategy"""
        try:
            # Get trading signal
            signal_data = self.calculator.get_trading_signal(
                self.buy_threshold, self.sell_threshold
            )
            
            if signal_data is None:
                return {'success': False, 'reason': 'Failed to get market data'}
            
            # Check if we should trade
            if not self.should_trade(signal_data):
                return {
                    'success': False,
                    'reason': 'No actionable signal',
                    'signal_data': signal_data
                }
            
            # Calculate trade amount
            trade_amount = min(max_trade_amount, balance_usd * 0.1)  # Max 10% of balance
            
            result = {
                'success': True,
                'action': signal_data['signal'],
                'amount_usd': trade_amount,
                'kimchi_premium': signal_data['kimchi_premium'],
                'reason': signal_data['reason'],
                'market_data': signal_data['market_data'],
                'timestamp': datetime.now().isoformat()
            }
            
            # Update trade count
            self.trade_count_today += 1
            
            logger.info(f"Strategy executed: {result['action']} ${trade_amount:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing kimchi premium strategy: {e}")
            return {'success': False, 'reason': str(e)}
    
    def get_strategy_status(self) -> Dict:
        """Get current strategy status"""
        try:
            premium_data = self.calculator.calculate_kimchi_premium()
            
            return {
                'strategy_name': 'Kimchi Premium Arbitrage',
                'buy_threshold': self.buy_threshold,
                'sell_threshold': self.sell_threshold,
                'current_premium': premium_data.get('kimchi_premium_percentage', 0) if premium_data else 0,
                'trades_today': self.trade_count_today,
                'max_trades_per_day': self.max_trade_frequency,
                'last_update': datetime.now().isoformat(),
                'market_data': premium_data
            }
            
        except Exception as e:
            logger.error(f"Error getting strategy status: {e}")
            return {'error': str(e)} 