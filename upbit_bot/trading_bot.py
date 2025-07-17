import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from dotenv import load_dotenv
import ccxt
import json
import threading
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TradingConfig:
    """Configuration for trading strategy"""
    max_trade_amount: float = 1000.0
    max_daily_loss: float = 500.0
    max_position_size: float = 0.3  # 30% of balance
    price_threshold: float = 0.5  # Minimum price difference %
    stop_loss_threshold: float = 2.0  # Stop loss at 2% loss
    take_profit_threshold: float = 1.0  # Take profit at 1% gain
    max_trades_per_day: int = 10
    cooldown_period: int = 300  # 5 minutes cooldown between trades
    emergency_stop_loss: float = 5.0  # Emergency stop at 5% total loss

@dataclass
class TradeRecord:
    """Record of a trade execution"""
    timestamp: str
    action: str
    amount_usd: float  # Amount in USDT (kept as 'usd' for backward compatibility)
    usdt_krw_price: float
    usd_krw_rate: float
    difference_percentage: float
    success: bool
    reason: str = ""
    profit_loss: float = 0.0
    balance_after: Optional[Dict[str, float]] = None

class RiskManager:
    """Risk management system for trading bot"""
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.daily_trades = 0
        self.daily_loss = 0.0
        self.last_trade_time = 0
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.total_invested = 0.0
        
    def reset_daily_counters(self):
        """Reset daily counters if new day"""
        now = datetime.now()
        if now >= self.daily_reset_time + timedelta(days=1):
            self.daily_trades = 0
            self.daily_loss = 0.0
            self.daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            logger.info("Daily counters reset")
    
    def can_trade(self, action: str, amount: float, current_balance: Dict[str, float]) -> Tuple[bool, str]:
        """Check if trade is allowed based on risk parameters"""
        self.reset_daily_counters()
        
        # Check daily trade limit
        if self.daily_trades >= self.config.max_trades_per_day:
            return False, "Daily trade limit exceeded"
        
        # Check daily loss limit
        if self.daily_loss >= self.config.max_daily_loss:
            return False, "Daily loss limit exceeded"
        
        # Check cooldown period
        if time.time() - self.last_trade_time < self.config.cooldown_period:
            return False, "Cooldown period active"
        
        # Check position size
        total_balance = current_balance.get('USD', 0) + current_balance.get('KRW', 0) / 1300  # Rough conversion
        if amount > total_balance * self.config.max_position_size:
            return False, "Position size too large"
        
        # Check sufficient balance
        if action == 'BUY' and current_balance.get('USD', 0) < amount:
            return False, "Insufficient USD balance"
        elif action == 'SELL' and current_balance.get('KRW', 0) < amount * 1300:  # Rough conversion
            return False, "Insufficient KRW balance"
        
        return True, "Trade allowed"
    
    def record_trade(self, trade_result: TradeRecord):
        """Record trade for risk tracking"""
        self.daily_trades += 1
        self.last_trade_time = time.time()
        
        if trade_result.profit_loss < 0:
            self.daily_loss += abs(trade_result.profit_loss)
        
        logger.info(f"Trade recorded: {trade_result.action} ${trade_result.amount_usd:.2f}")

class UpbitTradingBot:
    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, 
                 initial_balance_usd: float = 10000, config: Optional[TradingConfig] = None, 
                 virtual_mode: bool = True):
        """
        Initialize the Enhanced Upbit Trading Bot
        """
        load_dotenv()
        self.virtual_mode = virtual_mode
        self.config = config or TradingConfig()
        self.risk_manager = RiskManager(self.config)
        
        # Initialize API client
        if not virtual_mode:
            self.api_key = api_key or os.getenv('UPBIT_API_KEY')
            self.secret_key = secret_key or os.getenv('UPBIT_SECRET_KEY')
            if not self.api_key or not self.secret_key:
                raise ValueError("API keys required for live trading mode")
            
            try:
                self.client = ccxt.upbit({
                    'apiKey': self.api_key,
                    'secret': self.secret_key,
                    'sandbox': False,
                    'rateLimit': 1000,  # Rate limiting
                })
                logger.info("Connected to Upbit API")
            except Exception as e:
                logger.error(f"Failed to connect to Upbit API: {str(e)}")
                raise
        else:
            self.client = ccxt.upbit()  # Public API only
            
        # Initialize balances
        self.virtual_balance_usd = initial_balance_usd
        self.virtual_balance_krw = 0
        self.initial_balance = initial_balance_usd
        
        # Trading state
        self.trade_history: List[TradeRecord] = []
        self.is_running = False
        self.last_market_data = {}
        
        # Performance tracking
        self.performance_metrics = {
            'total_trades': 0,
            'successful_trades': 0,
            'total_profit_loss': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0
        }
        
        logger.info(f"Bot initialized in {'virtual' if virtual_mode else 'live'} mode")

    def get_exchange_rate(self) -> float:
        """Get current USD/KRW exchange rate with error handling"""
        try:
            url = "https://api.exchangerate-api.com/v4/latest/USD"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            rate = data['rates']['KRW']
            logger.debug(f"USD/KRW rate: {rate}")
            return rate
        except Exception as e:
            logger.error(f"Failed to get exchange rate: {str(e)}")
            # Return cached rate if available
            if 'usd_krw_rate' in self.last_market_data:
                return self.last_market_data['usd_krw_rate']
            return 1300.0  # Fallback rate

    def get_usdt_krw_price(self) -> float:
        """Get current USDT/KRW price from Upbit with error handling"""
        try:
            ticker = self.client.fetch_ticker('USDT/KRW')
            price = float(ticker['last'])
            logger.debug(f"USDT/KRW price: {price}")
            return price
        except Exception as e:
            logger.error(f"Failed to get USDT/KRW price: {str(e)}")
            # Return cached price if available
            if 'usdt_krw_price' in self.last_market_data:
                return self.last_market_data['usdt_krw_price']
            return 1300.0  # Fallback price

    def calculate_arbitrage_opportunity(self) -> Dict:
        """Calculate arbitrage opportunity with enhanced analysis"""
        try:
            usd_krw_rate = self.get_exchange_rate()
            usdt_krw_price = self.get_usdt_krw_price()
            
            # Calculate the difference percentage
            diff_percentage = ((usdt_krw_price - usd_krw_rate) / usd_krw_rate) * 100
            
            # Determine action based on threshold
            action = 'HOLD'
            if diff_percentage < -self.config.price_threshold:
                action = 'BUY'
            elif diff_percentage > self.config.price_threshold:
                action = 'SELL'
            
            # Cache market data
            self.last_market_data = {
                'usd_krw_rate': usd_krw_rate,
                'usdt_krw_price': usdt_krw_price
            }
            
            opportunity = {
                'timestamp': datetime.now().isoformat(),
                'usd_krw_rate': usd_krw_rate,
                'usdt_krw_price': usdt_krw_price,
                'difference_percentage': diff_percentage,
                'action': action,
                'profitable': abs(diff_percentage) > self.config.price_threshold,
                'confidence': min(abs(diff_percentage), 5.0) / 5.0  # Confidence score 0-1
            }
            
            logger.debug(f"Arbitrage opportunity: {opportunity}")
            return opportunity
            
        except Exception as e:
            logger.error(f"Error calculating arbitrage opportunity: {str(e)}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'action': 'HOLD',
                'profitable': False
            }

    def execute_trade(self, action: str, amount: float) -> Dict:
        """Execute trade with enhanced error handling and risk management"""
        try:
            # Get current balance
            current_balance = self.get_current_balance()
            
            # Check risk management
            can_trade, reason = self.risk_manager.can_trade(action, amount, current_balance)
            if not can_trade:
                logger.warning(f"Trade rejected: {reason}")
                return {'success': False, 'reason': reason}
            
            # Limit trade amount
            amount = min(amount, self.config.max_trade_amount)
            
            # Get current market data
            usdt_krw_price = self.get_usdt_krw_price()
            usd_krw_rate = self.get_exchange_rate()
            
            # Calculate expected profit/loss
            diff_percentage = ((usdt_krw_price - usd_krw_rate) / usd_krw_rate) * 100
            
            # Execute trade
            trade_result = self._execute_trade_internal(action, amount, usdt_krw_price)
            
            # Record trade
            trade_record = TradeRecord(
                timestamp=datetime.now().isoformat(),
                action=action,
                amount_usd=amount,
                usdt_krw_price=usdt_krw_price,
                usd_krw_rate=usd_krw_rate,
                difference_percentage=diff_percentage,
                success=trade_result.get('success', False),
                reason=trade_result.get('reason', ''),
                profit_loss=trade_result.get('profit_loss', 0.0),
                balance_after=self.get_current_balance()
            )
            
            self.trade_history.append(trade_record)
            self.risk_manager.record_trade(trade_record)
            self._update_performance_metrics(trade_record)
            
            logger.info(f"Trade executed: {action} ${amount:.2f} - Success: {trade_result.get('success', False)}")
            return trade_result
            
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return {'success': False, 'reason': f'Execution error: {str(e)}'}

    def _execute_trade_internal(self, action: str, amount: float, price: float) -> Dict:
        """Internal trade execution logic"""
        if self.virtual_mode:
            return self._execute_virtual_trade(action, amount, price)
        else:
            return self._execute_real_trade(action, amount)

    def _execute_virtual_trade(self, action: str, amount: float, price: float) -> Dict:
        """Execute virtual trade"""
        krw_amount = amount * price
        
        if action == 'BUY' and self.virtual_balance_usd >= amount:
            self.virtual_balance_usd -= amount
            self.virtual_balance_krw += krw_amount
            return {'success': True, 'profit_loss': 0.0}
        elif action == 'SELL' and self.virtual_balance_krw >= krw_amount:
            self.virtual_balance_krw -= krw_amount
            self.virtual_balance_usd += amount
            return {'success': True, 'profit_loss': 0.0}
        else:
            return {'success': False, 'reason': 'Insufficient balance'}

    def _execute_real_trade(self, action: str, amount: float) -> Dict:
        """Execute real trade through Upbit API"""
        try:
            if action == 'BUY':
                order = self.client.create_market_buy_order('USDT/KRW', amount)
            else:
                order = self.client.create_market_sell_order('USDT/KRW', amount)
            
            return {
                'success': True,
                'order_id': order['id'],
                'profit_loss': 0.0  # Will be calculated later
            }
        except Exception as e:
            logger.error(f"Real trade execution failed: {str(e)}")
            return {'success': False, 'reason': str(e)}

    def get_current_balance(self) -> Dict[str, float]:
        """Get current balance with error handling"""
        try:
            if self.virtual_mode:
                return {
                    'USD': self.virtual_balance_usd,
                    'KRW': self.virtual_balance_krw
                }
            else:
                balance = self.client.fetch_balance()
                return {
                    'USD': balance.get('USDT', {}).get('free', 0),
                    'KRW': balance.get('KRW', {}).get('free', 0)
                }
        except Exception as e:
            logger.error(f"Error getting balance: {str(e)}")
            return {'USD': 0, 'KRW': 0}

    def _update_performance_metrics(self, trade: TradeRecord):
        """Update performance tracking metrics"""
        self.performance_metrics['total_trades'] += 1
        if trade.success:
            self.performance_metrics['successful_trades'] += 1
        
        self.performance_metrics['total_profit_loss'] += trade.profit_loss
        self.performance_metrics['win_rate'] = (
            self.performance_metrics['successful_trades'] / 
            self.performance_metrics['total_trades'] * 100
        )

    def get_performance_summary(self) -> Dict:
        """Get performance summary"""
        current_balance = self.get_current_balance()
        total_value = current_balance['USD'] + current_balance['KRW'] / 1300
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': total_value,
            'total_return': total_value - self.initial_balance,
            'return_percentage': ((total_value - self.initial_balance) / self.initial_balance) * 100,
            'metrics': self.performance_metrics,
            'trade_count': len(self.trade_history)
        }

    def run_bot(self, check_interval: int = 60):
        """Run the trading bot with enhanced monitoring"""
        logger.info("Starting enhanced trading bot...")
        self.is_running = True
        
        try:
            while self.is_running:
                # Check for emergency stop
                performance = self.get_performance_summary()
                if performance['return_percentage'] < -self.config.emergency_stop_loss:
                    logger.critical("Emergency stop triggered!")
                    self.is_running = False
                    break
                
                # Calculate opportunity
                opportunity = self.calculate_arbitrage_opportunity()
                
                if opportunity.get('profitable', False):
                    result = self.execute_trade(
                        opportunity['action'], 
                        self.config.max_trade_amount
                    )
                    
                    if result['success']:
                        logger.info(f"Trade successful: {opportunity['action']}")
                    else:
                        logger.warning(f"Trade failed: {result.get('reason', 'Unknown')}")
                
                # Log current status
                if len(self.trade_history) % 10 == 0:  # Every 10th cycle
                    logger.info(f"Performance: {performance}")
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {str(e)}")
        finally:
            self.is_running = False
            logger.info("Bot stopped")

    def stop_bot(self):
        """Stop the trading bot"""
        self.is_running = False
        logger.info("Bot stop requested")

    def export_trade_history(self, filename: Optional[str] = None) -> Optional[str]:
        """Export trade history to JSON file"""
        if filename is None:
            filename = f"trade_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump([asdict(trade) for trade in self.trade_history], f, indent=2)
            logger.info(f"Trade history exported to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error exporting trade history: {str(e)}")
            return None 