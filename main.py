import argparse
import asyncio
import sys
import os
from typing import Optional
import uvicorn
from upbit_bot.trading_bot import UpbitTradingBot, TradingConfig
from upbit_bot.backtest import EnhancedUpbitBacktest, BacktestConfig
from upbit_bot.web_app import app
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_bot(api_key: Optional[str] = None, secret_key: Optional[str] = None, 
           initial_balance: float = 10000, max_trade_amount: float = 1000, 
           price_threshold: float = 0.5, check_interval: int = 60,
           virtual_mode: bool = True, max_daily_loss: float = 500):
    """Run the enhanced trading bot"""
    try:
        # Create trading configuration
        config = TradingConfig(
            max_trade_amount=max_trade_amount,
            price_threshold=price_threshold,
            max_daily_loss=max_daily_loss,
            emergency_stop_loss=5.0,
            max_trades_per_day=20
        )
        
        # Create and run bot
        bot = UpbitTradingBot(
            api_key=api_key,
            secret_key=secret_key,
            initial_balance_usd=initial_balance,
            config=config,
            virtual_mode=virtual_mode
        )
        
        logger.info(f"Starting bot in {'virtual' if virtual_mode else 'live'} mode")
        logger.info(f"Configuration: {config}")
        
        bot.run_bot(check_interval)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        sys.exit(1)

def run_backtest(start_date: str, end_date: str, initial_balance: float = 10000,
                max_trade_amount: float = 1000, price_threshold: float = 0.5,
                use_real_data: bool = False, export_results: bool = False):
    """Run enhanced backtest"""
    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Create backtest configuration
        config = BacktestConfig(
            initial_balance_usd=initial_balance,
            max_trade_amount=max_trade_amount,
            price_threshold=price_threshold,
            commission_rate=0.0025,
            slippage_rate=0.001
        )
        
        # Run backtest
        backtest = EnhancedUpbitBacktest(config)
        result = backtest.run_backtest(start_dt, end_dt, use_real_data=use_real_data)
        
        # Print results
        print("\n" + "="*60)
        print("BACKTEST RESULTS")
        print("="*60)
        print(f"Period: {start_date} to {end_date}")
        print(f"Initial Balance: ${result.initial_balance:,.2f}")
        print(f"Final Balance: ${result.final_balance:,.2f}")
        print(f"Total Return: ${result.total_return:,.2f}")
        print(f"Return %: {result.return_percentage:.2f}%")
        print(f"Max Drawdown: {result.max_drawdown:.2f}%")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Win Rate: {result.win_rate:.2f}%")
        print(f"Profit Factor: {result.profit_factor:.2f}")
        print(f"Total Trades: {result.total_trades}")
        print(f"Winning Trades: {result.winning_trades}")
        print(f"Losing Trades: {result.losing_trades}")
        print(f"Average Win: ${result.average_win:.2f}")
        print(f"Average Loss: ${result.average_loss:.2f}")
        print("="*60)
        
        # Export results if requested
        if export_results:
            filename = backtest.export_results(result)
            if filename:
                print(f"Results exported to: {filename}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error running backtest: {str(e)}")
        sys.exit(1)

def run_optimization(start_date: str, end_date: str, 
                    param_ranges: Optional[str] = None):
    """Run parameter optimization"""
    try:
        # Parse dates
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Parse parameter ranges if provided
        if param_ranges:
            import json
            ranges = json.loads(param_ranges)
        else:
            ranges = {
                'price_threshold': (0.1, 2.0, 0.2),
                'max_trade_amount': (500, 2000, 500),
                'stop_loss_threshold': (1.0, 5.0, 1.0)
            }
        
        # Run optimization
        backtest = EnhancedUpbitBacktest()
        result = backtest.optimize_parameters(start_dt, end_dt, ranges)
        
        print("\n" + "="*60)
        print("OPTIMIZATION RESULTS")
        print("="*60)
        print(f"Best Parameters: {result['best_params']}")
        print(f"Best Return: {result['best_return']:.2f}%")
        print(f"Total Combinations Tested: {len(result['all_results'])}")
        print("="*60)
        
        # Show top 5 results
        sorted_results = sorted(result['all_results'], 
                              key=lambda x: x['return_percentage'], 
                              reverse=True)
        
        print("\nTop 5 Parameter Combinations:")
        for i, res in enumerate(sorted_results[:5], 1):
            print(f"{i}. Params: {res['params']}")
            print(f"   Return: {res['return_percentage']:.2f}%")
            print(f"   Drawdown: {res['max_drawdown']:.2f}%")
            print(f"   Win Rate: {res['win_rate']:.2f}%")
            print(f"   Trades: {res['total_trades']}")
            print()
        
        return result
        
    except Exception as e:
        logger.error(f"Error running optimization: {str(e)}")
        sys.exit(1)

def run_web(host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
    """Run the enhanced web interface"""
    try:
        logger.info(f"Starting web server on {host}:{port}")
        uvicorn.run(
            app, 
            host=host, 
            port=port, 
            log_level="info" if not debug else "debug",
            reload=debug
        )
    except Exception as e:
        logger.error(f"Error running web server: {str(e)}")
        sys.exit(1)

def main():
    """Main entry point with enhanced CLI"""
    parser = argparse.ArgumentParser(
        description="Enhanced Upbit Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run web interface
  python main.py web
  
  # Run virtual trading bot
  python main.py bot --virtual --initial-balance 10000
  
  # Run live trading bot
  python main.py bot --api-key YOUR_KEY --secret-key YOUR_SECRET
  
  # Run backtest
  python main.py backtest --start-date 2023-01-01 --end-date 2023-12-31
  
  # Run optimization
  python main.py optimize --start-date 2023-01-01 --end-date 2023-06-30
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Web command
    web_parser = subparsers.add_parser('web', help='Run web interface')
    web_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    web_parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    web_parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    # Bot command
    bot_parser = subparsers.add_parser('bot', help='Run trading bot')
    bot_parser.add_argument('--api-key', help='Upbit API key')
    bot_parser.add_argument('--secret-key', help='Upbit Secret key')
    bot_parser.add_argument('--initial-balance', type=float, default=10000,
                          help='Initial balance in USD for virtual trading')
    bot_parser.add_argument('--max-trade-amount', type=float, default=1000,
                          help='Maximum trade amount in USD')
    bot_parser.add_argument('--price-threshold', type=float, default=0.5,
                          help='Price difference threshold for trading')
    bot_parser.add_argument('--check-interval', type=int, default=60,
                          help='Check interval in seconds')
    bot_parser.add_argument('--virtual', action='store_true',
                          help='Run in virtual mode (default if no API keys)')
    bot_parser.add_argument('--max-daily-loss', type=float, default=500,
                          help='Maximum daily loss limit in USD')
    
    # Backtest command
    backtest_parser = subparsers.add_parser('backtest', help='Run backtest')
    backtest_parser.add_argument('--start-date', required=True,
                               help='Start date (YYYY-MM-DD)')
    backtest_parser.add_argument('--end-date', required=True,
                               help='End date (YYYY-MM-DD)')
    backtest_parser.add_argument('--initial-balance', type=float, default=10000,
                               help='Initial balance in USD')
    backtest_parser.add_argument('--max-trade-amount', type=float, default=1000,
                               help='Maximum trade amount in USD')
    backtest_parser.add_argument('--price-threshold', type=float, default=0.5,
                               help='Price difference threshold for trading')
    backtest_parser.add_argument('--use-real-data', action='store_true',
                               help='Use real historical data from Upbit')
    backtest_parser.add_argument('--export', action='store_true',
                               help='Export results to JSON file')
    
    # Optimize command
    optimize_parser = subparsers.add_parser('optimize', help='Optimize parameters')
    optimize_parser.add_argument('--start-date', required=True,
                               help='Start date (YYYY-MM-DD)')
    optimize_parser.add_argument('--end-date', required=True,
                               help='End date (YYYY-MM-DD)')
    optimize_parser.add_argument('--param-ranges', 
                               help='Parameter ranges as JSON string')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Default to web if no command specified
    if not args.command:
        args.command = 'web'
        args.host = '0.0.0.0'
        args.port = 8000
        args.debug = False
    
    # Execute command
    if args.command == 'web':
        run_web(args.host, args.port, args.debug)
    elif args.command == 'bot':
        # Determine if virtual mode
        virtual_mode = args.virtual or not (args.api_key and args.secret_key)
        
        run_bot(
            api_key=args.api_key,
            secret_key=args.secret_key,
            initial_balance=args.initial_balance,
            max_trade_amount=args.max_trade_amount,
            price_threshold=args.price_threshold,
            check_interval=args.check_interval,
            virtual_mode=virtual_mode,
            max_daily_loss=args.max_daily_loss
        )
    elif args.command == 'backtest':
        run_backtest(
            start_date=args.start_date,
            end_date=args.end_date,
            initial_balance=args.initial_balance,
            max_trade_amount=args.max_trade_amount,
            price_threshold=args.price_threshold,
            use_real_data=args.use_real_data,
            export_results=args.export
        )
    elif args.command == 'optimize':
        run_optimization(
            start_date=args.start_date,
            end_date=args.end_date,
            param_ranges=args.param_ranges
        )

if __name__ == "__main__":
    main() 