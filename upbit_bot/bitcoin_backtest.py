"""
Bitcoin Arbitrage Backtesting Module

Backtests the Bitcoin kimchi premium arbitrage strategy using historical data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
import json
import ccxt
from dataclasses import dataclass, asdict
from .bitcoin_kimchi_strategy import BitcoinArbitrageConfig, BitcoinArbitrageStrategy

logger = logging.getLogger(__name__)

@dataclass 
class BitcoinBacktestConfig:
    """Configuration for Bitcoin arbitrage backtesting"""
    initial_balance_krw: float = 13_500_000  # 10,000 USD in KRW (1x leverage for Upbit)
    initial_balance_usdt: float = 5_000      # USDT for Binance (2x leverage for shorting)
    initial_btc: float = 0.0                 # Starting BTC
    entry_premium_threshold: float = -2.0    # Entry threshold (negative kimchi premium)
    exit_profit_threshold: float = 2.0       # Exit threshold (actual profit percentage)
    max_position_size_btc: float = 0.1       # Max BTC per position
    leverage_multiplier: float = 2.0         # Leverage for Binance futures (2x)
    upbit_commission: float = 0.0025         # 0.25% Upbit fee
    binance_commission: float = 0.001        # 0.1% Binance fee
    binance_funding_rate: float = 0.0001     # 0.01% Binance funding fee (8h)
    upbit_krw_fee: float = 0.02              # 2% Upbit KRW fee
    slippage_rate: float = 0.001             # 0.1% slippage
    use_scaled_strategy: bool = True         # Use scaled entry/exit strategy
    position_portion: float = 0.25           # 25% of capital per position

class BitcoinBacktester:
    """Backtest Bitcoin arbitrage strategy"""
    
    def __init__(self, config: BitcoinBacktestConfig):
        self.config = config
        self.binance = ccxt.binance()
        self.upbit = ccxt.upbit()
        
    def calculate_funding_income(self, position_size: float, position_value_usdt: float, 
                               hours_held: int) -> float:
        """Calculate Binance funding income for short positions"""
        # Funding income is received every 8 hours for short positions
        funding_periods = hours_held / 8
        funding_income = position_value_usdt * self.config.binance_funding_rate * funding_periods
        return funding_income
    
    def fetch_historical_data(self, start_date: str, end_date: str, 
                            timeframe: str = '1h') -> pd.DataFrame:
        """Fetch historical data from exchanges"""
        try:
            logger.info(f"Fetching historical data from {start_date} to {end_date}")
            
            # Convert dates to timestamps
            start_ts = int(pd.Timestamp(start_date).timestamp() * 1000)
            end_ts = int(pd.Timestamp(end_date).timestamp() * 1000)
            
            # Fetch Binance BTC/USDT data
            binance_data = []
            current_ts = start_ts
            
            while current_ts < end_ts:
                ohlcv = self.binance.fetch_ohlcv(
                    'BTC/USDT', 
                    timeframe=timeframe,
                    since=current_ts,
                    limit=1000
                )
                
                if not ohlcv:
                    break
                    
                binance_data.extend(ohlcv)
                current_ts = ohlcv[-1][0] + 1
                
                # Avoid rate limits
                import time
                time.sleep(0.5)
            
            # Convert to DataFrame
            binance_df = pd.DataFrame(
                binance_data,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            binance_df['timestamp'] = pd.to_datetime(binance_df['timestamp'], unit='ms')
            binance_df.set_index('timestamp', inplace=True)
            binance_df.columns = [f'binance_{col}' for col in binance_df.columns]
            
            # Fetch Upbit BTC/KRW data
            upbit_data = []
            current_ts = start_ts
            
            while current_ts < end_ts:
                ohlcv = self.upbit.fetch_ohlcv(
                    'BTC/KRW',
                    timeframe=timeframe,
                    since=current_ts,
                    limit=200  # Upbit has lower limits
                )
                
                if not ohlcv:
                    break
                    
                upbit_data.extend(ohlcv)
                current_ts = ohlcv[-1][0] + 1
                
                # Avoid rate limits
                time.sleep(0.5)
            
            # Convert to DataFrame
            upbit_df = pd.DataFrame(
                upbit_data,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            upbit_df['timestamp'] = pd.to_datetime(upbit_df['timestamp'], unit='ms')
            upbit_df.set_index('timestamp', inplace=True)
            upbit_df.columns = [f'upbit_{col}' for col in upbit_df.columns]
            
            # Merge data
            df = pd.merge(binance_df, upbit_df, left_index=True, right_index=True, how='inner')
            
            # Add USD/KRW rate (simplified - in production use real forex data)
            df['usd_krw_rate'] = 1350.0  # Placeholder
            
            # Calculate kimchi premium
            df['binance_btc_krw'] = df['binance_close'] * df['usd_krw_rate']
            df['kimchi_premium'] = ((df['upbit_close'] - df['binance_btc_krw']) / df['binance_btc_krw']) * 100
            
            logger.info(f"Fetched {len(df)} data points")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def simulate_trades(self, df: pd.DataFrame) -> Dict:
        """Simulate trades based on historical data with scaled entry/exit strategy"""
        # Initialize balances
        balance_krw = self.config.initial_balance_krw
        balance_usdt = self.config.initial_balance_usdt
        balance_btc = self.config.initial_btc
        
        # Track trades and positions
        trades = []
        open_positions = []
        balance_history = []
        
        # Scaled strategy configuration
        if self.config.use_scaled_strategy:
            # Entry levels: 0%, -0.5%, -1.0%, -1.5%, -2.0%, -2.5%, -3.0%, -3.5%, -4.0%
            entry_levels = [0.0, -0.5, -1.0, -1.5, -2.0, -2.5, -3.0, -3.5, -4.0]
            # Exit levels: 0.5%, 1.0%, 1.5%, 2.0%, 2.5%, etc.
            exit_levels = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
            
            # Track which entry/exit levels have been used
            used_entry_levels = set()
            used_exit_levels = set()
        else:
            # Fallback to original strategy
            entry_levels = [self.config.entry_premium_threshold]
            exit_levels = [self.config.exit_profit_threshold]
            used_entry_levels = set()
            used_exit_levels = set()
        
        for idx, row in df.iterrows():
            current_premium = row['kimchi_premium']
            btc_price_krw = row['upbit_close']
            btc_price_usdt = row['binance_close']
            
            # SCALED ENTRY STRATEGY
            if self.config.use_scaled_strategy:
                for entry_level in entry_levels:
                    # Check if we should enter at this level
                    if (current_premium < entry_level and 
                        entry_level not in used_entry_levels and
                        len(open_positions) < len(entry_levels)):  # Max 8 positions
                        
                        # Calculate position size (25% of initial total capital)
                        initial_total_krw = self.config.initial_balance_krw + (self.config.initial_balance_usdt * 1300)  # Approximate KRW equivalent
                        available_krw = initial_total_krw * self.config.position_portion
                        available_usdt = self.config.initial_balance_usdt * self.config.position_portion
                        
                        # Calculate max BTC we can buy with available KRW
                        max_btc_by_krw = available_krw / btc_price_krw * 0.95
                        # Calculate max BTC we can short with available USDT (2x leverage)
                        max_btc_by_usdt = (available_usdt * self.config.leverage_multiplier) / btc_price_usdt * 0.95
                        
                        position_size = min(self.config.max_position_size_btc, max_btc_by_krw, max_btc_by_usdt)
                        
                        if position_size >= 0.001:  # Minimum order size
                            # Execute entry with income
                            upbit_cost = position_size * btc_price_krw * (1 + self.config.upbit_commission)
                            # Add KRW deposit income for Upbit (2% bonus)
                            krw_deposit_income = upbit_cost * self.config.upbit_krw_fee
                            total_upbit_cost = upbit_cost - krw_deposit_income  # Income reduces cost
                            
                            binance_margin_required = (position_size * btc_price_usdt) / self.config.leverage_multiplier
                            binance_proceeds = position_size * btc_price_usdt * (1 - self.config.binance_commission)
                            
                            if balance_krw >= total_upbit_cost and balance_usdt >= binance_margin_required:
                                # Buy on Upbit
                                balance_krw -= total_upbit_cost
                                balance_btc += position_size
                                
                                # Short on Binance with leverage
                                balance_usdt -= binance_margin_required
                                
                                position = {
                                    'entry_time': idx,
                                    'entry_premium': current_premium,
                                    'entry_level': entry_level,
                                    'size': position_size,
                                    'upbit_entry_price': btc_price_krw,
                                    'binance_entry_price': btc_price_usdt,
                                    'upbit_cost_krw': total_upbit_cost,
                                    'binance_margin_usdt': binance_margin_required,
                                    'binance_proceeds_usdt': binance_proceeds,
                                    'leverage': self.config.leverage_multiplier
                                }
                                
                                open_positions.append(position)
                                used_entry_levels.add(entry_level)
                                
                                trades.append({
                                    'time': idx,
                                    'type': 'ENTRY',
                                    'premium': current_premium,
                                    'entry_level': entry_level,
                                    'size': position_size,
                                    'upbit_price': btc_price_krw,
                                    'binance_price': btc_price_usdt,
                                    'leverage': self.config.leverage_multiplier
                                })
                                break  # Only enter one position per iteration
            else:
                # Original strategy
                if current_premium < self.config.entry_premium_threshold and len(open_positions) < 3:
                    max_btc_by_usdt = (balance_usdt * self.config.leverage_multiplier) / btc_price_usdt * 0.95
                    max_btc_by_krw = balance_krw / btc_price_krw * 0.95
                    position_size = min(self.config.max_position_size_btc, max_btc_by_usdt, max_btc_by_krw)
                    
                    if position_size >= 0.001:
                        upbit_cost = position_size * btc_price_krw * (1 + self.config.upbit_commission)
                        binance_margin_required = (position_size * btc_price_usdt) / self.config.leverage_multiplier
                        binance_proceeds = position_size * btc_price_usdt * (1 - self.config.binance_commission)
                        
                        if balance_krw >= upbit_cost and balance_usdt >= binance_margin_required:
                            balance_krw -= upbit_cost
                            balance_btc += position_size
                            balance_usdt -= binance_margin_required
                            
                            position = {
                                'entry_time': idx,
                                'entry_premium': current_premium,
                                'size': position_size,
                                'upbit_entry_price': btc_price_krw,
                                'binance_entry_price': btc_price_usdt,
                                'upbit_cost_krw': upbit_cost,
                                'binance_margin_usdt': binance_margin_required,
                                'binance_proceeds_usdt': binance_proceeds,
                                'leverage': self.config.leverage_multiplier
                            }
                            
                            open_positions.append(position)
                            
                            trades.append({
                                'time': idx,
                                'type': 'ENTRY',
                                'premium': current_premium,
                                'size': position_size,
                                'upbit_price': btc_price_krw,
                                'binance_price': btc_price_usdt,
                                'leverage': self.config.leverage_multiplier
                            })
            
            # SCALED EXIT STRATEGY
            positions_to_close = []
            
            for i, pos in enumerate(open_positions):
                # Calculate total arbitrage profit percentage
                upbit_profit_pct = ((btc_price_krw - pos['upbit_entry_price']) / pos['upbit_entry_price']) * 100
                binance_profit_pct = ((pos['binance_entry_price'] - btc_price_usdt) / pos['binance_entry_price']) * 100
                total_profit_percentage = (upbit_profit_pct + binance_profit_pct) / 2
                
                if self.config.use_scaled_strategy:
                    # Check each exit level
                    for exit_level in exit_levels:
                        if (total_profit_percentage > exit_level and 
                            exit_level not in used_exit_levels and
                            pos.get('entry_level', 0) <= -0.5):  # Only exit positions entered at premium < -0.5%
                            
                            positions_to_close.append((i, exit_level))
                            used_exit_levels.add(exit_level)
                            break
                else:
                    # Original exit strategy
                    if total_profit_percentage > self.config.exit_profit_threshold:
                        positions_to_close.append((i, self.config.exit_profit_threshold))
            
            # Close positions
            for i, exit_level in reversed(positions_to_close):
                pos = open_positions.pop(i)
                
                # Calculate position duration for funding income
                position_duration = (idx - pos['entry_time']).total_seconds() / 3600  # hours
                position_value_usdt = pos['size'] * pos['binance_entry_price']
                funding_income = self.calculate_funding_income(pos['size'], position_value_usdt, position_duration)
                
                # Sell on Upbit
                upbit_proceeds = pos['size'] * btc_price_krw * (1 - self.config.upbit_commission)
                # Add KRW withdrawal income for Upbit (2% bonus)
                krw_withdrawal_income = upbit_proceeds * self.config.upbit_krw_fee
                net_upbit_proceeds = upbit_proceeds + krw_withdrawal_income  # Income increases proceeds
                balance_krw += net_upbit_proceeds
                balance_btc -= pos['size']
                
                # Close short on Binance
                binance_cost = pos['size'] * btc_price_usdt * (1 + self.config.binance_commission)
                balance_usdt += pos['binance_margin_usdt']
                
                # Calculate P&L with income
                upbit_pnl_krw = net_upbit_proceeds - pos['upbit_cost_krw']
                binance_pnl_usdt = pos['binance_proceeds_usdt'] - binance_cost + funding_income
                
                trades.append({
                    'time': idx,
                    'type': 'EXIT',
                    'premium': current_premium,
                    'exit_level': exit_level,
                    'size': pos['size'],
                    'upbit_price': btc_price_krw,
                    'binance_price': btc_price_usdt,
                    'upbit_pnl_krw': upbit_pnl_krw,
                    'binance_pnl_usdt': binance_pnl_usdt,
                    'funding_income_usdt': funding_income,
                    'total_pnl_krw': upbit_pnl_krw + (binance_pnl_usdt * row['usd_krw_rate'])
                })
            
            # Record balance
            total_value_krw = balance_krw + (balance_usdt * row['usd_krw_rate']) + (balance_btc * btc_price_krw)
            balance_history.append({
                'time': idx,
                'balance_krw': balance_krw,
                'balance_usdt': balance_usdt,
                'balance_btc': balance_btc,
                'total_value_krw': total_value_krw,
                'premium': current_premium
            })
        
        # Calculate final results
        final_value_krw = balance_krw + (balance_usdt * df.iloc[-1]['usd_krw_rate']) + (balance_btc * df.iloc[-1]['upbit_close'])
        initial_value_krw = self.config.initial_balance_krw + (self.config.initial_balance_usdt * df.iloc[0]['usd_krw_rate'])
        
        return {
            'trades': trades,
            'balance_history': balance_history,
            'final_balance_krw': balance_krw,
            'final_balance_usdt': balance_usdt,
            'final_balance_btc': balance_btc,
            'final_value_krw': final_value_krw,
            'initial_value_krw': initial_value_krw,
            'total_return_krw': final_value_krw - initial_value_krw,
            'return_percentage': ((final_value_krw - initial_value_krw) / initial_value_krw) * 100,
            'total_trades': len([t for t in trades if t['type'] == 'ENTRY']),
            'open_positions': len(open_positions)
        }
    
    def run_backtest(self, start_date: str, end_date: str) -> Dict:
        """Run complete backtest"""
        try:
            # Fetch historical data
            df = self.fetch_historical_data(start_date, end_date)
            
            if df.empty:
                return {'error': 'No historical data available'}
            
            # Run simulation
            results = self.simulate_trades(df)
            
            # Add metadata
            results['start_date'] = start_date
            results['end_date'] = end_date
            results['config'] = asdict(self.config)
            results['data_points'] = len(df)
            
            return results
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {'error': str(e)} 