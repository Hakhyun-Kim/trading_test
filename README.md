# Enhanced Upbit Trading Bot 🚀

An advanced cryptocurrency arbitrage trading bot for Upbit exchange that leverages USDT/USD price differences against KRW rates. This enhanced version includes comprehensive risk management, real-time monitoring, strategy optimization, and a modern web interface.

## ✨ Features

### Core Trading Features
- **Arbitrage Strategy**: Automatically trades USDT based on price differences with USD/KRW rates
- **Bitcoin Arbitrage Strategy**: Advanced BTC arbitrage between Binance and Upbit with shorting
- **Risk Management**: Advanced position sizing, stop-loss, take-profit, and daily loss limits
- **Virtual Trading**: Test strategies with virtual money before going live
- **Real-time Monitoring**: Live market data and performance tracking
- **Emergency Stop**: Automatic trading halt on significant losses

### Strategy & Analysis
- **Enhanced Backtesting**: Comprehensive historical performance analysis
- **Parameter Optimization**: Automated strategy parameter tuning
- **Performance Metrics**: Sharpe ratio, max drawdown, win rate, profit factor
- **Commission & Slippage**: Realistic trading cost simulation
- **Multiple Strategies**: Extensible strategy framework including USDT and Bitcoin arbitrage

### Web Interface
- **Modern Dashboard**: Real-time trading dashboard with charts
- **Session Management**: Multiple trading sessions with individual configurations
- **API Integration**: RESTful API for programmatic access
- **WebSocket Support**: Live updates and real-time trading
- **Export Features**: JSON export of results and trade history

### Risk Management
- **Position Sizing**: Intelligent position sizing based on account balance
- **Daily Limits**: Maximum trades per day and daily loss limits
- **Cooldown Periods**: Prevents overtrading with configurable cooldowns
- **Emergency Stops**: Automatic shutdown on excessive losses
- **Balance Monitoring**: Real-time balance tracking and alerts

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Upbit API keys (for live trading)

### Quick Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/upbit-trading-bot.git
cd upbit-trading-bot

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (optional for virtual trading)
cp .env.example .env
# Edit .env with your Upbit API keys
```

### Environment Variables
Create a `.env` file in the root directory:
```env
UPBIT_API_KEY=your_upbit_api_key
UPBIT_SECRET_KEY=your_upbit_secret_key
```

## 🚀 Usage

### Command Line Interface

#### Web Interface (Recommended)
```bash
# Start the web interface
python main.py web

# Custom host and port
python main.py web --host 0.0.0.0 --port 8080 --debug
```

#### Virtual Trading Bot
```bash
# Run virtual trading bot
python main.py bot --virtual --initial-balance 10000

# With custom parameters
python main.py bot --virtual \
  --initial-balance 50000 \
  --max-trade-amount 2000 \
  --price-threshold 0.3 \
  --max-daily-loss 1000
```

#### Live Trading Bot
```bash
# Run live trading bot (requires API keys)
python main.py bot \
  --api-key YOUR_API_KEY \
  --secret-key YOUR_SECRET_KEY \
  --max-trade-amount 1000
```

#### Backtesting
```bash
# Run backtest
python main.py backtest \
  --start-date 2023-01-01 \
  --end-date 2023-12-31 \
  --initial-balance 10000 \
  --export

# Use real historical data
python main.py backtest \
  --start-date 2023-01-01 \
  --end-date 2023-06-30 \
  --use-real-data
```

#### Parameter Optimization
```bash
# Optimize strategy parameters
python main.py optimize \
  --start-date 2023-01-01 \
  --end-date 2023-06-30

# Custom parameter ranges
python main.py optimize \
  --start-date 2023-01-01 \
  --end-date 2023-06-30 \
  --param-ranges '{"price_threshold": [0.1, 2.0, 0.1], "max_trade_amount": [500, 2000, 250]}'
```

### Web Interface Features

#### Dashboard
- Real-time market data and arbitrage opportunities
- Live balance tracking and performance metrics
- Active trading sessions management

#### Trading Pages
- **Virtual Trading**: Practice with virtual money
- **Live Trading**: Real money trading with API keys
- **Analytics**: Detailed performance analysis and charts

#### API Endpoints
- `GET /api/health` - Health check
- `POST /api/backtest` - Run backtest via API
- `GET /api/market-data` - Current market data
- `POST /api/sessions` - Create trading session
- `DELETE /api/sessions/{id}` - Stop trading session
- `GET /api/optimize` - Parameter optimization

## 📊 Strategy Details

### Arbitrage Logic
The bot identifies arbitrage opportunities by comparing:
- **USD/KRW exchange rate** (from forex APIs)
- **USDT/KRW price** (from Upbit)

When USDT is trading at a discount to the USD/KRW rate, the bot buys USDT. When at a premium, it sells USDT.

### Bitcoin Arbitrage Strategy

The advanced Bitcoin arbitrage strategy exploits price differences between Binance and Upbit:

1. **Entry (Kimchi Premium < 0.3%)**:
   - Buy Bitcoin on Upbit with limit orders
   - Short Bitcoin on Binance with market orders

2. **Exit (Kimchi Premium > 1.3%)**:
   - Sell Bitcoin on Upbit with limit orders
   - Close short position on Binance

**Key Features**:
- Simultaneous trading on two exchanges
- Smart order execution (limit orders on Upbit, market on Binance)
- Multiple position tracking
- Configurable premium thresholds via UI

See [BITCOIN_ARBITRAGE_README.md](BITCOIN_ARBITRAGE_README.md) for detailed documentation.

### Risk Management
- **Position Sizing**: Maximum 30% of balance per trade
- **Stop Loss**: 2% default stop loss per position
- **Take Profit**: 1% default take profit per position
- **Daily Limits**: Maximum 10 trades per day, 500 USD daily loss limit
- **Emergency Stop**: 5% total account loss triggers shutdown

### Performance Metrics
- **Sharpe Ratio**: Risk-adjusted return measurement
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Ratio of total wins to total losses
- **Average Win/Loss**: Average profit per winning/losing trade

## 🔧 Configuration

### Trading Configuration
```python
from upbit_bot.trading_bot import TradingConfig

config = TradingConfig(
    max_trade_amount=1000.0,      # Maximum trade size in USD
    max_daily_loss=500.0,         # Maximum daily loss in USD
    max_position_size=0.3,        # Maximum position size (30% of balance)
    price_threshold=0.5,          # Minimum price difference % to trade
    stop_loss_threshold=2.0,      # Stop loss at 2% loss
    take_profit_threshold=1.0,    # Take profit at 1% gain
    max_trades_per_day=10,        # Maximum trades per day
    cooldown_period=300,          # 5 minutes cooldown between trades
    emergency_stop_loss=5.0       # Emergency stop at 5% total loss
)
```

### Backtest Configuration
```python
from upbit_bot.backtest import BacktestConfig

config = BacktestConfig(
    initial_balance_usd=10000.0,  # Starting balance
    max_trade_amount=1000.0,      # Maximum trade size
    price_threshold=0.5,          # Price difference threshold
    stop_loss_threshold=2.0,      # Stop loss percentage
    take_profit_threshold=1.0,    # Take profit percentage
    max_trades_per_day=10,        # Daily trade limit
    commission_rate=0.0025,       # 0.25% commission
    slippage_rate=0.001          # 0.1% slippage
)
```

## 📈 Sample Results

### Backtest Example
```
====================================================================
BACKTEST RESULTS
====================================================================
Period: 2023-01-01 to 2023-12-31
Initial Balance: $10,000.00
Final Balance: $12,847.50
Total Return: $2,847.50
Return %: 28.48%
Max Drawdown: 5.23%
Sharpe Ratio: 1.85
Win Rate: 67.50%
Profit Factor: 2.34
Total Trades: 847
Winning Trades: 572
Losing Trades: 275
Average Win: $12.45
Average Loss: $8.90
====================================================================
```

## 🚨 Risk Disclaimer

⚠️ **Important**: Cryptocurrency trading involves significant risk. This bot is for educational purposes and should not be used with money you cannot afford to lose. Always:

- Test thoroughly in virtual mode first
- Start with small amounts
- Monitor the bot regularly
- Understand the risks involved
- Use proper risk management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the code comments and docstrings
- **Issues**: Open an issue on GitHub for bugs or feature requests
- **Discussions**: Use GitHub Discussions for questions and ideas

## 🔗 Links

- [Upbit API Documentation](https://docs.upbit.com/)
- [CCXT Library](https://github.com/ccxt/ccxt)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Made with ❤️ for the crypto community** 