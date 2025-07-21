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
    initial_balance_krw: float = 13_500_000  # 10,000 USD in KRW
    initial_balance_usdt: float = 10_000     # USDT for Binance
    initial_btc: float = 0.0                 # Starting BTC
    entry_premium_threshold: float = 0.3     # Entry threshold
    exit_premium_threshold: float = 1.3      # Exit threshold
    max_position_size_btc: float = 0.1       # Max BTC per position
    upbit_commission: float = 0.0025         # 0.25% Upbit fee
    binance_commission: float = 0.001        # 0.1% Binance fee
    slippage_rate: float = 0.001             # 0.1% slippage

class BitcoinBacktester:
    """Backtest Bitcoin arbitrage strategy"""
    
    def __init__(self, config: BitcoinBacktestConfig):
        self.config = config
        self.binance = ccxt.binance()
        self.upbit = ccxt.upbit()
        
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
        """Simulate trades based on historical data"""
        # Initialize balances
        balance_krw = self.config.initial_balance_krw
        balance_usdt = self.config.initial_balance_usdt
        balance_btc = self.config.initial_btc
        
        # Track trades and positions
        trades = []
        open_positions = []
        balance_history = []
        
        # Strategy configuration
        arb_config = BitcoinArbitrageConfig(
            entry_premium_threshold=self.config.entry_premium_threshold,
            exit_premium_threshold=self.config.exit_premium_threshold,
            max_position_size_btc=self.config.max_position_size_btc
        )
        
        for idx, row in df.iterrows():
            current_premium = row['kimchi_premium']
            btc_price_krw = row['upbit_close']
            btc_price_usdt = row['binance_close']
            
            # Check for entry signals
            if current_premium < arb_config.entry_premium_threshold and len(open_positions) < 3:
                # Calculate position size
                max_btc_by_usdt = balance_usdt / btc_price_usdt * 0.95
                max_btc_by_krw = balance_krw / btc_price_krw * 0.95
                position_size = min(arb_config.max_position_size_btc, max_btc_by_usdt, max_btc_by_krw)
                
                if position_size >= 0.001:  # Minimum order size
                    # Execute entry
                    upbit_cost = position_size * btc_price_krw * (1 + self.config.upbit_commission)
                    binance_proceeds = position_size * btc_price_usdt * (1 - self.config.binance_commission)
                    
                    if balance_krw >= upbit_cost and balance_usdt >= binance_proceeds:
                        # Buy on Upbit
                        balance_krw -= upbit_cost
                        balance_btc += position_size
                        
                        # Short on Binance (simplified: just track USDT)
                        balance_usdt += binance_proceeds
                        
                        position = {
                            'entry_time': idx,
                            'entry_premium': current_premium,
                            'size': position_size,
                            'upbit_entry_price': btc_price_krw,
                            'binance_entry_price': btc_price_usdt,
                            'upbit_cost_krw': upbit_cost,
                            'binance_proceeds_usdt': binance_proceeds
                        }
                        
                        open_positions.append(position)
                        
                        trades.append({
                            'time': idx,
                            'type': 'ENTRY',
                            'premium': current_premium,
                            'size': position_size,
                            'upbit_price': btc_price_krw,
                            'binance_price': btc_price_usdt
                        })
            
            # Check for exit signals
            positions_to_close = []
            for i, pos in enumerate(open_positions):
                if current_premium > arb_config.exit_premium_threshold:
                    positions_to_close.append(i)
            
            # Close positions
            for i in reversed(positions_to_close):
                pos = open_positions.pop(i)
                
                # Sell on Upbit
                upbit_proceeds = pos['size'] * btc_price_krw * (1 - self.config.upbit_commission)
                balance_krw += upbit_proceeds
                balance_btc -= pos['size']
                
                # Close short on Binance
                binance_cost = pos['size'] * btc_price_usdt * (1 + self.config.binance_commission)
                balance_usdt -= binance_cost
                
                # Calculate P&L
                upbit_pnl_krw = upbit_proceeds - pos['upbit_cost_krw']
                binance_pnl_usdt = pos['binance_proceeds_usdt'] - binance_cost
                
                trades.append({
                    'time': idx,
                    'type': 'EXIT',
                    'premium': current_premium,
                    'size': pos['size'],
                    'upbit_price': btc_price_krw,
                    'binance_price': btc_price_usdt,
                    'upbit_pnl_krw': upbit_pnl_krw,
                    'binance_pnl_usdt': binance_pnl_usdt,
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