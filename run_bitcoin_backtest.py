"""
Run Bitcoin Arbitrage Backtest

This script runs the Bitcoin kimchi premium arbitrage backtesting
"""

import asyncio
import logging
from datetime import datetime, timedelta
from upbit_bot.bitcoin_backtest import BitcoinBacktester, BitcoinBacktestConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Run Bitcoin arbitrage backtest"""
    
    # Create backtest configuration
    config = BitcoinBacktestConfig(
        initial_balance_krw=13_500_000,  # ~10,000 USD (1x leverage for Upbit)
        initial_balance_usdt=5_000,      # USDT for Binance (2x leverage for shorting)
        initial_btc=0.0,
        entry_premium_threshold=-2.0,    # Enter when premium < -2% (simple and effective)
        exit_profit_threshold=2.0,       # Exit when total arbitrage profit > 2%
        max_position_size_btc=0.1,       # Max 0.1 BTC per position
        leverage_multiplier=2.0,         # 2x leverage for Binance futures
        upbit_commission=0.0025,         # 0.25%
        binance_commission=0.001,        # 0.1%
        slippage_rate=0.001,             # 0.1%
        use_scaled_strategy=True,        # Use scaled entry/exit strategy
        position_portion=0.25            # 25% of capital per position
    )
    
    # Create backtester
    backtester = BitcoinBacktester(config)
    
    # Set date range (last 365 days - one year)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    print(f"\n{'='*60}")
    print("BITCOIN ARBITRAGE BACKTEST - SCALED STRATEGY")
    print(f"{'='*60}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial KRW Balance: ₩{config.initial_balance_krw:,.0f}")
    print(f"Initial USDT Balance: ${config.initial_balance_usdt:,.0f}")
    print(f"Strategy: Scaled Entry/Exit (25% of total capital per position)")
    print(f"Entry Levels: 0%, -0.5%, -1.0%, -1.5%, -2.0%, -2.5%, -3.0%, -3.5%, -4.0%")
    print(f"Exit Levels: 0.5%, 1.0%, 1.5%, 2.0%, 2.5%, 3.0%, 3.5%, 4.0%")
    print(f"Leverage: {config.leverage_multiplier}x on Binance")
    print(f"Income: Binance 0.01% funding (8h) + Upbit 2% KRW bonus")
    print(f"{'='*60}\n")
    
    # Run backtest
    results = backtester.run_backtest(start_date, end_date)
    
    if 'error' in results:
        print(f"Error: {results['error']}")
        return
    
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
    
    # Calculate annualized return
    days_in_period = 365
    annualized_return = results['return_percentage']
    print(f"  Annualized Return: {annualized_return:.2f}%")
    print(f"{'='*60}\n")
    
    # Show sample trades
    if results['trades']:
        print(f"\nRecent Trades (last 10):")
        print(f"{'='*60}")
        for trade in results['trades'][-10:]:
            if trade['type'] == 'ENTRY':
                leverage = trade.get('leverage', 1)
                entry_level = trade.get('entry_level', 'N/A')
                print(f"[ENTRY] {trade['time']} - Premium: {trade['premium']:.2f}% (Level: {entry_level}%), Size: {trade['size']:.6f} BTC, {leverage}x")
            else:  # EXIT
                pnl = trade.get('total_pnl_krw', 0)
                exit_level = trade.get('exit_level', 'N/A')
                pnl_color = "🟢" if pnl > 0 else "🔴"
                print(f"[EXIT] {trade['time']} - Premium: {trade['premium']:.2f}% (Level: {exit_level}%), P&L: {pnl_color} ₩{pnl:,.0f}")
        
        # Show detailed analysis of losing trades
        losing_trades = [t for t in results['trades'] if t['type'] in ['PARTIAL_EXIT', 'FULL_EXIT'] and t.get('total_pnl_krw', 0) < 0]
        if losing_trades:
            print(f"\n🔴 Losing Trades Analysis:")
            print(f"{'='*60}")
            for trade in losing_trades:
                print(f"{trade['type']}: {trade['time']} - Premium: {trade['premium']:.2f}%, Loss: ₩{trade.get('total_pnl_krw', 0):,.0f}")
                print(f"  Upbit P&L: ₩{trade.get('upbit_pnl_krw', 0):,.0f}")
                print(f"  Binance P&L: ${trade.get('binance_pnl_usdt', 0):,.2f}")
                print()

if __name__ == "__main__":
    main() 