"""
Run Bitcoin Arbitrage Backtest with 14-day Moving Average Strategy

This script runs backtesting for the enhanced strategy that combines:
- Kimchi premium arbitrage (-2% to 2% base thresholds)
- 14-day moving average trend filter
- Dynamic threshold adjustments based on trend
- Position sizing based on trend strength
"""

import asyncio
import logging
from datetime import datetime, timedelta
from upbit_bot.bitcoin_backtest import BitcoinBacktester, BitcoinBacktestConfig
from upbit_bot.bitcoin_kimchi_strategy_ma import BitcoinKimchiStrategyMA, create_ma_strategy_config
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedBitcoinBacktester(BitcoinBacktester):
    """Extended backtester with MA strategy support"""
    
    def __init__(self, config: BitcoinBacktestConfig):
        super().__init__(config)
        self.ma_strategy = BitcoinKimchiStrategyMA(create_ma_strategy_config())
        
    def simulate_trades_with_ma(self, df: pd.DataFrame) -> dict:
        """Simulate trades using MA-enhanced strategy"""
        # Initialize balances
        balance_krw = self.config.initial_balance_krw
        balance_usdt = self.config.initial_balance_usdt
        balance_btc = self.config.initial_btc
        
        # Track trades and positions
        trades = []
        open_positions = []
        balance_history = []
        ma_signals = []
        
        # Calculate 14-day MA on the data
        df['ma_14'] = df['binance_close'].rolling(window=14*24).mean()  # 14 days in hours
        
        for idx, row in df.iterrows():
            current_premium = row['kimchi_premium']
            btc_price_krw = row['upbit_close']
            btc_price_usdt = row['binance_close']
            
            # Get MA signal
            if not pd.isna(df.loc[idx, 'ma_14']):
                # Calculate trend
                ma_value = df.loc[idx, 'ma_14']
                position_pct = (btc_price_usdt - ma_value) / ma_value
                
                if position_pct > 0.02:
                    trend = 'strong_uptrend'
                    strength = min(position_pct / 0.02, 2.0)
                elif position_pct > 0:
                    trend = 'uptrend'
                    strength = position_pct / 0.02
                elif position_pct < -0.02:
                    trend = 'strong_downtrend'
                    strength = min(abs(position_pct) / 0.02, 2.0)
                elif position_pct < 0:
                    trend = 'downtrend'
                    strength = abs(position_pct) / 0.02
                else:
                    trend = 'neutral'
                    strength = 0
                
                # Adjust thresholds based on trend
                entry_threshold = -2.0  # Base
                exit_threshold = 2.0    # Base
                
                if 'uptrend' in trend:
                    entry_threshold = entry_threshold - (0.5 * strength)  # More aggressive
                    exit_threshold = exit_threshold - (0.25 * strength)   # Quicker exit
                elif 'downtrend' in trend:
                    entry_threshold = entry_threshold + (0.5 * strength)  # More conservative
                    exit_threshold = exit_threshold + (0.25 * strength)   # Hold longer
                
                # Ensure bounds
                entry_threshold = max(entry_threshold, -5.0)
                entry_threshold = min(entry_threshold, -0.5)
                exit_threshold = max(exit_threshold, 1.0)
                exit_threshold = min(exit_threshold, 5.0)
                
                ma_signals.append({
                    'time': idx,
                    'trend': trend,
                    'strength': strength,
                    'ma_value': ma_value,
                    'position_pct': position_pct,
                    'entry_threshold': entry_threshold,
                    'exit_threshold': exit_threshold
                })
            else:
                entry_threshold = -2.0
                exit_threshold = 2.0
                trend = 'unknown'
                strength = 0
            
            # Check for entry signals
            if current_premium < entry_threshold and len(open_positions) < 3:
                # Calculate position size (larger in strong trends)
                base_size = self.config.max_position_size_btc
                if 'strong' in trend:
                    position_size = min(base_size * 1.5, self.config.max_position_size_btc)
                else:
                    position_size = base_size * 0.8
                
                # Check available balance
                max_btc_by_usdt = balance_usdt / btc_price_usdt * 0.95
                max_btc_by_krw = balance_krw / btc_price_krw * 0.95
                position_size = min(position_size, max_btc_by_usdt, max_btc_by_krw)
                
                if position_size >= 0.001:
                    # Execute entry
                    upbit_cost = position_size * btc_price_krw * (1 + self.config.upbit_commission)
                    binance_proceeds = position_size * btc_price_usdt * (1 - self.config.binance_commission)
                    
                    if balance_krw >= upbit_cost and balance_usdt >= binance_proceeds:
                        # Buy on Upbit
                        balance_krw -= upbit_cost
                        balance_btc += position_size
                        
                        # Short on Binance
                        balance_usdt += binance_proceeds
                        
                        position = {
                            'entry_time': idx,
                            'entry_premium': current_premium,
                            'size': position_size,
                            'upbit_entry_price': btc_price_krw,
                            'binance_entry_price': btc_price_usdt,
                            'upbit_cost_krw': upbit_cost,
                            'binance_proceeds_usdt': binance_proceeds,
                            'entry_trend': trend,
                            'entry_threshold': entry_threshold
                        }
                        
                        open_positions.append(position)
                        
                        trades.append({
                            'time': idx,
                            'type': 'ENTRY',
                            'premium': current_premium,
                            'size': position_size,
                            'upbit_price': btc_price_krw,
                            'binance_price': btc_price_usdt,
                            'trend': trend,
                            'threshold': entry_threshold
                        })
            
            # Check for exit signals
            positions_to_close = []
            for i, pos in enumerate(open_positions):
                # Premium-based exit
                should_exit_premium = current_premium > exit_threshold
                
                # MA-based exit (if price crosses below MA after being above)
                should_exit_ma = False
                if not pd.isna(df.loc[idx, 'ma_14']):
                    if pos['binance_entry_price'] > df.loc[idx, 'ma_14'] and btc_price_usdt < df.loc[idx, 'ma_14']:
                        should_exit_ma = True
                
                # Stop loss check
                pnl_pct = ((btc_price_usdt - pos['binance_entry_price']) / pos['binance_entry_price']) * 100
                should_exit_stop = pnl_pct < -5.0
                
                if should_exit_premium or should_exit_ma or should_exit_stop:
                    positions_to_close.append((i, 'premium' if should_exit_premium else ('ma_cross' if should_exit_ma else 'stop_loss')))
            
            # Close positions
            for i, exit_reason in reversed(positions_to_close):
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
                    'total_pnl_krw': upbit_pnl_krw + (binance_pnl_usdt * row['usd_krw_rate']),
                    'exit_reason': exit_reason,
                    'trend': trend,
                    'threshold': exit_threshold
                })
            
            # Record balance
            total_value_krw = balance_krw + (balance_usdt * row['usd_krw_rate']) + (balance_btc * btc_price_krw)
            balance_history.append({
                'time': idx,
                'balance_krw': balance_krw,
                'balance_usdt': balance_usdt,
                'balance_btc': balance_btc,
                'total_value_krw': total_value_krw,
                'premium': current_premium,
                'trend': trend if 'trend' in locals() else 'unknown'
            })
        
        # Calculate final results
        final_value_krw = balance_krw + (balance_usdt * df.iloc[-1]['usd_krw_rate']) + (balance_btc * df.iloc[-1]['upbit_close'])
        initial_value_krw = self.config.initial_balance_krw + (self.config.initial_balance_usdt * df.iloc[0]['usd_krw_rate'])
        
        return {
            'trades': trades,
            'balance_history': balance_history,
            'ma_signals': ma_signals,
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

def main():
    """Run Bitcoin arbitrage backtest with MA strategy"""
    
    # Create backtest configuration
    config = BitcoinBacktestConfig(
        initial_balance_krw=13_500_000,  # ~10,000 USD
        initial_balance_usdt=10_000,     # USDT for Binance
        initial_btc=0.0,
        entry_premium_threshold=-2.0,    # Base (will be adjusted by MA)
        exit_premium_threshold=2.0,      # Base (will be adjusted by MA)
        max_position_size_btc=0.1,       # Max 0.1 BTC per position
        upbit_commission=0.0025,         # 0.25%
        binance_commission=0.001,        # 0.1%
        slippage_rate=0.001              # 0.1%
    )
    
    # Create enhanced backtester
    backtester = EnhancedBitcoinBacktester(config)
    
    # Set date range (last 365 days - one year)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    print(f"\n{'='*60}")
    print("BITCOIN ARBITRAGE BACKTEST WITH 14-DAY MA STRATEGY")
    print(f"{'='*60}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial KRW Balance: ₩{config.initial_balance_krw:,.0f}")
    print(f"Initial USDT Balance: ${config.initial_balance_usdt:,.0f}")
    print(f"Base Entry Threshold: {config.entry_premium_threshold}% (adjusted by trend)")
    print(f"Base Exit Threshold: {config.exit_premium_threshold}% (adjusted by trend)")
    print(f"MA Period: 14 days")
    print(f"{'='*60}\n")
    
    # Fetch data
    df = backtester.fetch_historical_data(start_date, end_date)
    
    if df.empty:
        print("Error: No historical data available")
        return
    
    # Run enhanced backtest
    results = backtester.simulate_trades_with_ma(df)
    
    # Display results
    print(f"\n{'='*60}")
    print("BACKTEST RESULTS")
    print(f"{'='*60}")
    print(f"Total Trades: {results['total_trades']}")
    print(f"Open Positions: {results['open_positions']}")
    print(f"\nFinal Balances:")
    print(f"  KRW: ₩{results['final_balance_krw']:,.0f}")
    print(f"  USDT: ${results['final_balance_usdt']:,.2f}")
    print(f"  BTC: {results['final_balance_btc']:.6f}")
    print(f"\nPerformance:")
    print(f"  Initial Value (KRW): ₩{results['initial_value_krw']:,.0f}")
    print(f"  Final Value (KRW): ₩{results['final_value_krw']:,.0f}")
    print(f"  Total Return (KRW): ₩{results['total_return_krw']:,.0f}")
    print(f"  Return %: {results['return_percentage']:.2f}%")
    print(f"{'='*60}\n")
    
    # Show trade breakdown by exit reason
    exit_reasons = {}
    for trade in results['trades']:
        if trade['type'] == 'EXIT':
            reason = trade.get('exit_reason', 'unknown')
            exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
    
    print("Exit Reasons:")
    for reason, count in exit_reasons.items():
        print(f"  {reason}: {count} trades")
    
    # Show sample trades
    if results['trades']:
        print(f"\nRecent Trades (last 10):")
        print(f"{'='*60}")
        for trade in results['trades'][-10:]:
            if trade['type'] == 'ENTRY':
                print(f"[ENTRY] {trade['time']} - Premium: {trade['premium']:.2f}%, Size: {trade['size']:.6f} BTC")
                print(f"        Trend: {trade['trend']}, Threshold: {trade['threshold']:.2f}%")
            else:
                print(f"[EXIT] {trade['time']} - Premium: {trade['premium']:.2f}%, P&L: ₩{trade.get('total_pnl_krw', 0):,.0f}")
                print(f"       Reason: {trade.get('exit_reason', 'premium')}, Trend: {trade['trend']}")

if __name__ == "__main__":
    main() 