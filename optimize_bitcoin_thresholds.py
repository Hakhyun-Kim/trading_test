"""
Optimize Bitcoin Arbitrage Thresholds

This script finds the best entry and exit premium thresholds
for the Bitcoin kimchi premium arbitrage strategy
"""

import logging
from datetime import datetime, timedelta
from upbit_bot.bitcoin_backtest import BitcoinBacktester, BitcoinBacktestConfig
import pandas as pd
import numpy as np
from itertools import product

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Set to WARNING to reduce output during optimization
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def run_single_backtest(entry_threshold: float, exit_threshold: float, 
                       start_date: str, end_date: str, silent: bool = True):
    """Run a single backtest with given thresholds"""
    try:
        # Create configuration
        config = BitcoinBacktestConfig(
            initial_balance_krw=13_500_000,
            initial_balance_usdt=10_000,
            initial_btc=0.0,
            entry_premium_threshold=entry_threshold,
            exit_premium_threshold=exit_threshold,
            max_position_size_btc=0.1,
            upbit_commission=0.0025,
            binance_commission=0.001,
            slippage_rate=0.001
        )
        
        # Create backtester
        backtester = BitcoinBacktester(config)
        
        # Run backtest
        results = backtester.run_backtest(start_date, end_date)
        
        if 'error' in results:
            return None
            
        return {
            'entry_threshold': entry_threshold,
            'exit_threshold': exit_threshold,
            'return_percentage': results['return_percentage'],
            'total_trades': results['total_trades'],
            'total_return_krw': results['total_return_krw'],
            'final_value_krw': results['final_value_krw']
        }
        
    except Exception as e:
        if not silent:
            print(f"Error with thresholds {entry_threshold}/{exit_threshold}: {e}")
        return None

def optimize_thresholds():
    """Find optimal entry and exit thresholds"""
    
    # Define parameter ranges
    entry_thresholds = [-0.5, -1.0, -1.5, -2.0, -2.5, -3.0, -3.5, -4.0]
    exit_thresholds = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    
    # Date range (1 year)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    print(f"\n{'='*60}")
    print("BITCOIN ARBITRAGE THRESHOLD OPTIMIZATION")
    print(f"{'='*60}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Entry thresholds to test: {entry_thresholds}")
    print(f"Exit thresholds to test: {exit_thresholds}")
    print(f"Total combinations: {len(entry_thresholds) * len(exit_thresholds)}")
    print(f"{'='*60}\n")
    
    # Test all combinations
    results = []
    total_combinations = len(entry_thresholds) * len(exit_thresholds)
    current = 0
    
    print("Running backtests...")
    for entry, exit in product(entry_thresholds, exit_thresholds):
        current += 1
        if current % 10 == 0:
            print(f"Progress: {current}/{total_combinations} ({current/total_combinations*100:.1f}%)")
        
        # Skip invalid combinations (entry should be negative, exit positive)
        if entry >= 0 or exit <= 0 or entry >= exit:
            continue
            
        result = run_single_backtest(entry, exit, start_date, end_date)
        if result:
            results.append(result)
    
    # Sort by return percentage
    results.sort(key=lambda x: x['return_percentage'], reverse=True)
    
    # Display results
    print(f"\n{'='*60}")
    print("TOP 10 PARAMETER COMBINATIONS")
    print(f"{'='*60}")
    print(f"{'Rank':<5} {'Entry':<8} {'Exit':<8} {'Return %':<10} {'Trades':<8} {'Total Return KRW':<20}")
    print(f"{'-'*5} {'-'*8} {'-'*8} {'-'*10} {'-'*8} {'-'*20}")
    
    for i, result in enumerate(results[:10], 1):
        print(f"{i:<5} {result['entry_threshold']:<8.1f} {result['exit_threshold']:<8.1f} "
              f"{result['return_percentage']:<10.2f} {result['total_trades']:<8} "
              f"₩{result['total_return_krw']:>18,.0f}")
    
    # Analyze best parameters
    best = results[0]
    print(f"\n{'='*60}")
    print("BEST PARAMETERS")
    print(f"{'='*60}")
    print(f"Entry Threshold: {best['entry_threshold']}%")
    print(f"Exit Threshold: {best['exit_threshold']}%")
    print(f"Annual Return: {best['return_percentage']:.2f}%")
    print(f"Total Trades: {best['total_trades']}")
    print(f"Total Return: ₩{best['total_return_krw']:,.0f}")
    
    # Group by characteristics
    print(f"\n{'='*60}")
    print("ANALYSIS BY THRESHOLD RANGE")
    print(f"{'='*60}")
    
    # Analyze by entry threshold
    entry_groups = {}
    for r in results:
        entry = r['entry_threshold']
        if entry not in entry_groups:
            entry_groups[entry] = []
        entry_groups[entry].append(r['return_percentage'])
    
    print("\nAverage Return by Entry Threshold:")
    for entry in sorted(entry_groups.keys(), reverse=True):
        avg_return = np.mean(entry_groups[entry])
        print(f"  Entry {entry}%: Avg Return {avg_return:.2f}%")
    
    # Analyze by exit threshold
    exit_groups = {}
    for r in results:
        exit = r['exit_threshold']
        if exit not in exit_groups:
            exit_groups[exit] = []
        exit_groups[exit].append(r['return_percentage'])
    
    print("\nAverage Return by Exit Threshold:")
    for exit in sorted(exit_groups.keys()):
        avg_return = np.mean(exit_groups[exit])
        print(f"  Exit {exit}%: Avg Return {avg_return:.2f}%")
    
    # Trade frequency analysis
    print(f"\n{'='*60}")
    print("TRADE FREQUENCY ANALYSIS")
    print(f"{'='*60}")
    
    # Group by number of trades
    trade_buckets = {
        '0-5 trades': [],
        '6-10 trades': [],
        '11-20 trades': [],
        '20+ trades': []
    }
    
    for r in results:
        trades = r['total_trades']
        if trades <= 5:
            trade_buckets['0-5 trades'].append(r)
        elif trades <= 10:
            trade_buckets['6-10 trades'].append(r)
        elif trades <= 20:
            trade_buckets['11-20 trades'].append(r)
        else:
            trade_buckets['20+ trades'].append(r)
    
    for bucket, items in trade_buckets.items():
        if items:
            avg_return = np.mean([r['return_percentage'] for r in items])
            best_in_bucket = max(items, key=lambda x: x['return_percentage'])
            print(f"\n{bucket}:")
            print(f"  Average Return: {avg_return:.2f}%")
            print(f"  Best: Entry {best_in_bucket['entry_threshold']}% / Exit {best_in_bucket['exit_threshold']}% = {best_in_bucket['return_percentage']:.2f}%")
    
    return results

if __name__ == "__main__":
    optimize_thresholds() 