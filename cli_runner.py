#!/usr/bin/env python3
"""
Simple Command Line Interface for Upbit Trading Bot
"""

import argparse
import sys
from datetime import datetime, timedelta
from upbit_bot.trading_bot import UpbitTradingBot, TradingConfig
from upbit_bot.backtest import EnhancedUpbitBacktest, BacktestConfig

def quick_backtest():
    """Run a quick backtest with default parameters"""
    print("🚀 Running Quick Backtest...")
    
    # Default parameters
    start_date = datetime.now() - timedelta(days=30)  # Last 30 days
    end_date = datetime.now()
    
    config = BacktestConfig(
        initial_balance_usd=10000,
        max_trade_amount=1000,
        price_threshold=0.5,
        stop_loss_threshold=2.0,
        take_profit_threshold=1.0,
        max_trades_per_day=10
    )
    
    try:
        backtest = EnhancedUpbitBacktest(config)
        result = backtest.run_backtest(start_date, end_date, use_real_data=False)
        
        print("\n" + "="*60)
        print("🎯 QUICK BACKTEST RESULTS")
        print("="*60)
        print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        print(f"💰 Initial Balance: ${result.initial_balance:,.2f}")
        print(f"💵 Final Balance: ${result.final_balance:,.2f}")
        print(f"📈 Total Return: ${result.total_return:,.2f}")
        print(f"📊 Return %: {result.return_percentage:.2f}%")
        print(f"📉 Max Drawdown: {result.max_drawdown:.2f}%")
        print(f"⚡ Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"🎯 Win Rate: {result.win_rate:.2f}%")
        print(f"🔄 Total Trades: {result.total_trades}")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error: {e}")

def virtual_trading():
    """Start virtual trading with default parameters"""
    print("🎮 Starting Virtual Trading...")
    
    config = TradingConfig(
        max_trade_amount=1000,
        price_threshold=0.5,
        stop_loss_threshold=2.0,
        take_profit_threshold=1.0,
        max_trades_per_day=10,
        max_daily_loss=500,
        emergency_stop_loss=5.0
    )
    
    try:
        bot = UpbitTradingBot(
            virtual_mode=True,
            initial_balance_usd=10000,
            config=config
        )
        
        print("🚀 Virtual trading started! Press Ctrl+C to stop.")
        bot.run_bot(check_interval=60)
        
    except KeyboardInterrupt:
        print("\n⏹️  Virtual trading stopped.")
    except Exception as e:
        print(f"❌ Error: {e}")

def market_status():
    """Check current market status"""
    print("📊 Checking Market Status...")
    
    try:
        bot = UpbitTradingBot(virtual_mode=True)
        opportunity = bot.calculate_arbitrage_opportunity()
        
        print("\n" + "="*50)
        print("📈 CURRENT MARKET STATUS")
        print("="*50)
        
        if opportunity:
            print(f"💱 USDT/KRW Price: {opportunity.get('usdt_krw_price', 'N/A')}")
            print(f"💵 USD/KRW Rate: {opportunity.get('usd_krw_rate', 'N/A')}")
            print(f"📊 Difference: {opportunity.get('difference_percentage', 'N/A'):.2f}%")
            print(f"🎯 Recommendation: {opportunity.get('recommendation', 'N/A')}")
        else:
            print("❌ Unable to fetch market data")
            
        print("="*50)
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main CLI interface"""
    print("🤖 Upbit Trading Bot CLI")
    print("=" * 40)
    print("1. Quick Backtest (Last 30 days)")
    print("2. Virtual Trading")
    print("3. Market Status")
    print("4. Desktop GUI")
    print("5. Exit")
    print("=" * 40)
    
    while True:
        try:
            choice = input("\n👉 Select option (1-5): ").strip()
            
            if choice == '1':
                quick_backtest()
            elif choice == '2':
                virtual_trading()
            elif choice == '3':
                market_status()
            elif choice == '4':
                print("🖥️  Starting Desktop GUI...")
                import subprocess
                subprocess.Popen([sys.executable, "run_desktop.py"])
                print("✅ Desktop GUI started!")
            elif choice == '5':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid option. Please choose 1-5.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 