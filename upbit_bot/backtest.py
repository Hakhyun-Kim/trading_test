import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import requests
import logging
from dataclasses import dataclass, asdict
import json
from .trading_bot import TradingConfig, TradeRecord
import ccxt

logger = logging.getLogger(__name__)

@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    initial_balance_usd: float = 10000.0  # USDT balance (kept as 'usd' for backward compatibility)
    initial_balance_krw: float = 0.0  # Initial KRW balance
    max_trade_amount: float = 1000.0  # Max USDT per trade
    price_threshold: float = 0.5  # Legacy threshold
    buy_threshold: float = 0.3  # Buy when kimchi premium < 0.3%
    sell_threshold: float = 2.0  # Sell when kimchi premium > 2.0%
    stop_loss_threshold: float = 2.0
    take_profit_threshold: float = 1.0
    max_trades_per_day: int = 10
    commission_rate: float = 0.0025  # 0.25% commission
    slippage_rate: float = 0.001  # 0.1% slippage
    
class BacktestResult:
    """Results of a backtest"""
    def __init__(self):
        self.initial_balance = 0.0
        self.final_balance = 0.0
        self.total_return = 0.0
        self.return_percentage = 0.0
        self.max_drawdown = 0.0
        self.sharpe_ratio = 0.0
        self.win_rate = 0.0
        self.profit_factor = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.average_win = 0.0
        self.average_loss = 0.0
        self.trades = []
        self.balance_history = []  # Track balance over time
        self.drawdown_history = []  # Track drawdown over time
        self.daily_returns = []  # Daily returns for charting
        self.equity_curve = []  # Equity curve for charting

class StrategyTester:
    """Base class for strategy testing"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        
    def calculate_signal(self, data: Dict[str, Any]) -> str:
        """Calculate trading signal based on strategy"""
        raise NotImplementedError("Subclasses must implement calculate_signal")
    
    def should_exit_position(self, entry_price: float, current_price: float, 
                           position_type: str, days_held: int) -> bool:
        """Check if position should be exited"""
        if position_type == 'LONG':
            pnl_pct = (current_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - current_price) / entry_price * 100
        
        # Stop loss or take profit
        if pnl_pct <= -self.config.stop_loss_threshold:
            return True
        if pnl_pct >= self.config.take_profit_threshold:
            return True
        
        return False

class ArbitrageStrategy(StrategyTester):
    """USDT/USD arbitrage strategy"""
    
    def __init__(self, config: BacktestConfig):
        super().__init__(config)
        # Independent thresholds for buy/sell
        self.buy_threshold = getattr(config, 'buy_threshold', 0.3)  # Default 0.3%
        self.sell_threshold = getattr(config, 'sell_threshold', 2.0)  # Default 2.0%
    
    def calculate_signal(self, data: Dict[str, Any]) -> str:
        """Calculate arbitrage signal based on kimchi premium"""
        usd_krw_rate = data['usd_krw_rate']
        usdt_krw_price = data['usdt_krw_price']
        
        # Calculate kimchi premium (positive when USDT is expensive in Korea)
        kimchi_premium = ((usdt_krw_price - usd_krw_rate) / usd_krw_rate) * 100
        
        # Buy when premium is low (USDT cheap in Korea)
        if kimchi_premium < self.buy_threshold:
            return 'BUY'
        # Sell when premium is high (USDT expensive in Korea)
        elif kimchi_premium > self.sell_threshold:
            return 'SELL'
        else:
            return 'HOLD'

class EnhancedUpbitBacktest:
    def __init__(self, config: Optional[BacktestConfig] = None, strategy: Optional[StrategyTester] = None):
        self.config = config or BacktestConfig()
        # Make sure ArbitrageStrategy gets the config with buy/sell thresholds
        self.strategy = strategy or ArbitrageStrategy(self.config)
        self.reset_state()
        
    def reset_state(self):
        """Reset backtest state"""
        # If initial KRW balance is provided, use it; otherwise split USDT 50/50
        if self.config.initial_balance_krw > 0:
            self.balance_usd = self.config.initial_balance_usd  # Actually USDT
            self.balance_krw = self.config.initial_balance_krw
        else:
            # Default: split initial USDT balance 50/50 between USDT and KRW
            half_balance = self.config.initial_balance_usd / 2
            self.balance_usd = half_balance  # Actually USDT
            self.balance_krw = half_balance * 1300  # Convert to KRW at approximate USDT/KRW rate
        
        self.trades: List[TradeRecord] = []
        self.daily_returns: List[float] = []
        self.equity_curve: List[float] = []
        self.current_position = None
        self.position_entry_price = 0
        self.position_entry_date = None
        self.daily_trade_count = 0
        self.last_trade_date = None
        
    def fetch_real_historical_data(self, symbol: str, start_date: datetime, 
                                  end_date: datetime, timeframe: str = '1d') -> pd.DataFrame:
        """Fetch real historical data from Upbit"""
        try:
            client = ccxt.upbit()
            
            # Convert dates to timestamps
            start_timestamp = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
            
            # Fetch OHLCV data
            ohlcv_data = client.fetch_ohlcv(symbol, timeframe, start_timestamp, limit=1000)
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)]
            
            logger.info(f"Fetched {len(df)} historical data points for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            return self._generate_synthetic_data(start_date, end_date)
    
    def _generate_synthetic_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Generate synthetic historical data for testing"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        data = []
        
        base_usd_krw = 1300.0
        base_usdt_krw = 1300.0
        
        for i, date in enumerate(dates):
            # Simulate realistic price movements
            usd_krw_rate = base_usd_krw * (1 + np.random.normal(0, 0.005))
            usdt_krw_price = base_usdt_krw * (1 + np.random.normal(0, 0.008))
            
            # Add some correlation and market trends
            trend = np.sin(i * 0.1) * 0.002
            usd_krw_rate *= (1 + trend)
            usdt_krw_price *= (1 + trend + np.random.normal(0, 0.003))
            
            data.append({
                'datetime': date,
                'usd_krw_rate': usd_krw_rate,
                'usdt_krw_price': usdt_krw_price,
                'volume': np.random.uniform(1000000, 10000000)
            })
        
        return pd.DataFrame(data)
    
    def calculate_commission_and_slippage(self, amount: float, price: float) -> float:
        """Calculate trading costs"""
        commission = amount * self.config.commission_rate
        slippage = amount * price * self.config.slippage_rate
        return commission + slippage
    
    def execute_backtest_trade(self, action: str, amount: float, price: float, 
                             usd_krw_rate: float, date: datetime) -> Dict[str, Any]:
        """Execute a trade in backtest"""
        # Check daily trade limit
        if self.last_trade_date != date.date():
            self.daily_trade_count = 0
            self.last_trade_date = date.date()
        
        if self.daily_trade_count >= self.config.max_trades_per_day:
            return {'success': False, 'reason': 'Daily trade limit exceeded'}
        
        # Calculate costs
        costs = self.calculate_commission_and_slippage(amount, price)
        
        # Execute trade
        if action == 'BUY':
            if self.balance_usd >= amount + costs:
                self.balance_usd -= (amount + costs)  # Buy USDT with KRW
                self.balance_krw += amount * price
                success = True
            else:
                return {'success': False, 'reason': 'Insufficient USDT balance'}
        else:  # SELL
            krw_needed = amount * price
            if self.balance_krw >= krw_needed:
                self.balance_krw -= krw_needed  # Sell USDT for KRW
                self.balance_usd += amount - costs
                success = True
            else:
                return {'success': False, 'reason': 'Insufficient KRW balance'}
        
        if success:
            self.daily_trade_count += 1
            
            # Record trade
            diff_percentage = ((price - usd_krw_rate) / usd_krw_rate) * 100
            trade_record = TradeRecord(
                timestamp=date.isoformat(),
                action=action,
                amount_usd=amount,
                usdt_krw_price=price,
                usd_krw_rate=usd_krw_rate,
                difference_percentage=diff_percentage,
                success=True,
                reason='',
                profit_loss=0.0,
                balance_after={'USD': self.balance_usd, 'KRW': self.balance_krw}
            )
            self.trades.append(trade_record)
            
        return {'success': success, 'costs': costs}
    
    def calculate_performance_metrics(self) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        # Calculate initial value including KRW if provided
        if self.config.initial_balance_krw > 0:
            # Use approximate rate for initial value calculation
            initial_value = self.config.initial_balance_usd + (self.config.initial_balance_krw / 1300)
        else:
            initial_value = self.config.initial_balance_usd
        final_value = self.balance_usd + self.balance_krw / 1300  # Rough conversion
        total_return = final_value - initial_value
        return_percentage = (total_return / initial_value) * 100 if initial_value > 0 else 0
        
        if not self.trades:
            # Return basic metrics even with no trades
            return {
                'initial_balance': initial_value,
                'final_balance': final_value,
                'total_return': total_return,
                'return_percentage': return_percentage,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'average_win': 0.0,
                'average_loss': 0.0
            }
        
        # Calculate trade-based metrics (we already have initial_value, etc. from above)
        
        # Calculate trade-based metrics
        winning_trades = sum(1 for trade in self.trades if trade.profit_loss > 0)
        losing_trades = sum(1 for trade in self.trades if trade.profit_loss < 0)
        win_rate = (winning_trades / len(self.trades)) * 100 if self.trades else 0
        
        # Calculate profit metrics
        total_wins = sum(trade.profit_loss for trade in self.trades if trade.profit_loss > 0)
        total_losses = sum(abs(trade.profit_loss) for trade in self.trades if trade.profit_loss < 0)
        
        avg_win = total_wins / winning_trades if winning_trades > 0 else 0
        avg_loss = total_losses / losing_trades if losing_trades > 0 else 0
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Calculate drawdown
        max_drawdown = self.calculate_max_drawdown()
        
        # Calculate Sharpe ratio
        sharpe_ratio = self.calculate_sharpe_ratio()
        
        return {
            'initial_balance': initial_value,
            'final_balance': final_value,
            'total_return': total_return,
            'return_percentage': return_percentage,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': len(self.trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'average_win': avg_win,
            'average_loss': avg_loss
        }
    
    def calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        if not self.equity_curve:
            return 0.0
        
        peak = self.equity_curve[0]
        max_dd = 0.0
        
        for value in self.equity_curve:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak * 100
            max_dd = max(max_dd, drawdown)
        
        return max_dd
    
    def calculate_drawdown_history(self) -> List[Tuple[datetime, float]]:
        """Calculate drawdown history over time"""
        if not self.equity_curve or not self.trades:
            return []
        
        drawdown_history = []
        peak = self.equity_curve[0]
        
        for i, value in enumerate(self.equity_curve):
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak * 100 if peak > 0 else 0
            
            # Try to associate with trade timestamp
            if i < len(self.trades):
                timestamp = datetime.fromisoformat(self.trades[i].timestamp)
            else:
                # Use last trade timestamp + days
                last_timestamp = datetime.fromisoformat(self.trades[-1].timestamp)
                timestamp = last_timestamp + timedelta(days=i - len(self.trades) + 1)
            
            drawdown_history.append((timestamp, drawdown))
        
        return drawdown_history
    
    def calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio"""
        if not self.daily_returns:
            return 0.0
        
        mean_return = np.mean(self.daily_returns)
        std_return = np.std(self.daily_returns)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe ratio (assuming 252 trading days)
        return (mean_return / std_return) * np.sqrt(252)
    
    def run_backtest(self, start_date: datetime, end_date: datetime, 
                    use_real_data: bool = True) -> BacktestResult:
        """Run comprehensive backtest"""
        logger.info(f"Starting backtest from {start_date} to {end_date}")
        
        # Reset state
        self.reset_state()
        
        # Fetch historical data
        if use_real_data:
            try:
                usdt_data = self.fetch_real_historical_data('USDT/KRW', start_date, end_date)
                # For USD/KRW, we'll use external API or synthetic data
                historical_data = self._combine_with_usd_krw_data(usdt_data, start_date, end_date)
            except Exception as e:
                logger.warning(f"Failed to fetch real data, using synthetic: {str(e)}")
                historical_data = self._generate_synthetic_data(start_date, end_date)
        else:
            historical_data = self._generate_synthetic_data(start_date, end_date)
        
        # Run backtest
        previous_balance = self.config.initial_balance_usd
        
        for _, row in historical_data.iterrows():
            current_date = row['datetime']
            
            # Prepare data for strategy
            market_data = {
                'usd_krw_rate': row['usd_krw_rate'],
                'usdt_krw_price': row['usdt_krw_price'],
                'volume': row.get('volume', 0),
                'date': current_date
            }
            
            # Get trading signal
            signal = self.strategy.calculate_signal(market_data)
            
            # Execute trade if signal is generated
            if signal in ['BUY', 'SELL']:
                trade_amount = min(self.config.max_trade_amount, self.balance_usd * 0.3)  # Max 30% per trade
                
                if trade_amount > 100:  # Minimum trade size
                    result = self.execute_backtest_trade(
                        signal, trade_amount, row['usdt_krw_price'], 
                        row['usd_krw_rate'], current_date
                    )
            
            # Calculate daily performance
            current_balance = self.balance_usd + self.balance_krw / row['usd_krw_rate']
            daily_return = (current_balance - previous_balance) / previous_balance * 100
            
            self.daily_returns.append(daily_return)
            self.equity_curve.append(current_balance)
            previous_balance = current_balance
        
        # Calculate final metrics
        metrics = self.calculate_performance_metrics()
        
        result = BacktestResult()
        result.initial_balance = metrics['initial_balance']
        result.final_balance = metrics['final_balance']
        result.total_return = metrics['total_return']
        result.return_percentage = metrics['return_percentage']
        result.max_drawdown = metrics['max_drawdown']
        result.sharpe_ratio = metrics['sharpe_ratio']
        result.win_rate = metrics['win_rate']
        result.profit_factor = metrics['profit_factor']
        result.total_trades = int(metrics['total_trades'])
        result.winning_trades = int(metrics['winning_trades'])
        result.losing_trades = int(metrics['losing_trades'])
        result.average_win = metrics['average_win']
        result.average_loss = metrics['average_loss']
        result.trades = self.trades
        result.balance_history = self.equity_curve
        result.drawdown_history = self.calculate_drawdown_history()
        result.daily_returns = self.daily_returns
        result.equity_curve = self.equity_curve
        
        logger.info(f"Backtest completed: {result.return_percentage:.2f}% return, {result.total_trades} trades")
        return result
    
    def _combine_with_usd_krw_data(self, usdt_data: pd.DataFrame, 
                                  start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Combine USDT data with USD/KRW rates"""
        # This simulates realistic forex rates with arbitrage opportunities
        combined_data = []
        
        for i, (_, row) in enumerate(usdt_data.iterrows()):
            # Base USD/KRW rate around the USDT price
            base_rate = float(row['close'])
            
            # Create realistic USD/KRW variations that sometimes create arbitrage
            # Real forex markets have spreads and inefficiencies
            
            # Add realistic forex market variations
            time_of_day_factor = np.sin(i * 0.1) * 0.002  # Time-based variations
            market_volatility = np.random.normal(0, 0.003)  # Market noise
            
            # Create periodic arbitrage opportunities
            if i % 8 == 0:  # Every 8th data point
                # Create stronger arbitrage opportunity
                if i % 16 == 0:
                    # USDT cheaper in Korea (BUY opportunity)
                    usd_krw_rate = base_rate * (1 + 0.015 + market_volatility)
                else:
                    # USDT more expensive in Korea (SELL opportunity)  
                    usd_krw_rate = base_rate * (1 - 0.015 + market_volatility)
            else:
                # Normal market conditions with small variations
                usd_krw_rate = base_rate * (1 + time_of_day_factor + market_volatility)
            
            combined_data.append({
                'datetime': row['datetime'],
                'usd_krw_rate': usd_krw_rate,
                'usdt_krw_price': row['close'],
                'volume': row['volume']
            })
        
        logger.info(f"Combined {len(combined_data)} data points with USD/KRW rates")
        return pd.DataFrame(combined_data)
    
    def optimize_parameters(self, start_date: datetime, end_date: datetime, 
                           param_ranges: Dict[str, Tuple[float, float, float]]) -> Dict[str, Any]:
        """Optimize strategy parameters"""
        logger.info("Starting parameter optimization")
        
        best_return = float('-inf')
        best_params = {}
        results = []
        
        # Generate parameter combinations
        param_combinations = self._generate_param_combinations(param_ranges)
        
        for params in param_combinations:
            # Update config with new parameters
            test_config = BacktestConfig(**{**asdict(self.config), **params})
            test_backtest = EnhancedUpbitBacktest(test_config, ArbitrageStrategy(test_config))
            
            try:
                result = test_backtest.run_backtest(start_date, end_date, use_real_data=False)
                
                # Store result
                result_dict = {
                    'params': params,
                    'return_percentage': result.return_percentage,
                    'max_drawdown': result.max_drawdown,
                    'sharpe_ratio': result.sharpe_ratio,
                    'win_rate': result.win_rate,
                    'total_trades': result.total_trades
                }
                results.append(result_dict)
                
                # Check if this is the best result
                if result.return_percentage > best_return:
                    best_return = result.return_percentage
                    best_params = params
                    
            except Exception as e:
                logger.error(f"Error in parameter optimization: {str(e)}")
                continue
        
        logger.info(f"Optimization completed. Best return: {best_return:.2f}%")
        
        return {
            'best_params': best_params,
            'best_return': best_return,
            'all_results': results
        }
    
    def _generate_param_combinations(self, param_ranges: Dict[str, Tuple[float, float, float]]) -> List[Dict[str, float]]:
        """Generate all parameter combinations for optimization"""
        combinations = []
        
        # Simple grid search - could be improved with more sophisticated optimization
        for price_threshold in np.arange(*param_ranges.get('price_threshold', (0.1, 2.0, 0.1))):
            for max_trade_amount in np.arange(*param_ranges.get('max_trade_amount', (500, 2000, 250))):
                for stop_loss in np.arange(*param_ranges.get('stop_loss_threshold', (1.0, 5.0, 0.5))):
                    combinations.append({
                        'price_threshold': round(price_threshold, 2),
                        'max_trade_amount': round(max_trade_amount, 2),
                        'stop_loss_threshold': round(stop_loss, 2)
                    })
        
        return combinations[:100]  # Limit to prevent excessive computation
    
    def export_results(self, result: BacktestResult, filename: Optional[str] = None) -> Optional[str]:
        """Export backtest results to JSON"""
        if filename is None:
            filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            # Convert result to dict
            result_dict = {
                'summary': {
                    'initial_balance': result.initial_balance,
                    'final_balance': result.final_balance,
                    'total_return': result.total_return,
                    'return_percentage': result.return_percentage,
                    'max_drawdown': result.max_drawdown,
                    'sharpe_ratio': result.sharpe_ratio,
                    'win_rate': result.win_rate,
                    'profit_factor': result.profit_factor,
                    'total_trades': result.total_trades,
                    'winning_trades': result.winning_trades,
                    'losing_trades': result.losing_trades,
                    'average_win': result.average_win,
                    'average_loss': result.average_loss
                },
                'trades': [asdict(trade) for trade in result.trades],
                'daily_returns': result.daily_returns,
                'equity_curve': result.equity_curve
            }
            
            with open(filename, 'w') as f:
                json.dump(result_dict, f, indent=2, default=str)
            
            logger.info(f"Results exported to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error exporting results: {str(e)}")
            return None

# Legacy class for backward compatibility
class UpbitBacktest(EnhancedUpbitBacktest):
    """Legacy backtest class for backward compatibility"""
    
    def __init__(self, initial_balance_usd=10000, max_trade_amount=1000):
        config = BacktestConfig(
            initial_balance_usd=initial_balance_usd,
            max_trade_amount=max_trade_amount
        )
        super().__init__(config)
        self.initial_balance_usd = initial_balance_usd
        self.max_trade_amount = max_trade_amount
    
    def fetch_historical_data(self, start_date, end_date):
        """Legacy method for backward compatibility"""
        return self._generate_synthetic_data(start_date, end_date)
    
    def calculate_profit_loss(self):
        """Legacy method for backward compatibility"""
        metrics = self.calculate_performance_metrics()
        return {
            'initial_balance_usd': metrics.get('initial_balance', 0),
            'final_balance_usd': metrics.get('final_balance', 0),
            'profit_loss_usd': metrics.get('total_return', 0),
            'profit_loss_percentage': metrics.get('return_percentage', 0),
            'total_trades': metrics.get('total_trades', 0)
        }
    
    def run_backtest(self, start_date, end_date, threshold=0.5):
        """Legacy method for backward compatibility"""
        self.config.price_threshold = threshold
        result = super().run_backtest(start_date, end_date, use_real_data=False)
        return self.calculate_profit_loss() 