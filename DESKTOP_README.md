# 🤖 Upbit Trading Bot - Desktop Edition

## 🚀 Quick Start

### Desktop GUI Application
```bash
py run_desktop.py
```

### Command Line Interface
```bash
py cli_runner.py
```

## 🖥️ Desktop GUI Features

### 📋 Configuration Tab
- **API Keys**: Enter your Upbit API credentials
- **Trading Parameters**: Set initial balance, max trade amount, price threshold
- **Risk Management**: Configure stop-loss, take-profit, max trades per day
- **Save/Load**: Save configurations to file for easy reuse

### 📊 Backtest Tab
- **Date Range**: Select start and end dates for historical testing
- **Real Data**: Option to use real Upbit historical data
- **Results Display**: View comprehensive backtest results with metrics
- **Export**: Export results to JSON files

### 🎯 Live Trading Tab
- **Virtual Mode**: Test strategies without real money
- **Live Mode**: Trade with real Upbit API (requires API keys)
- **Real-time Status**: Monitor trading activity and performance
- **Quick Controls**: Start/stop trading with single click

### 📈 Charts & Analysis Tab
- **Equity Curve**: Visualize portfolio performance over time
- **Trade Distribution**: Analyze winning vs losing trades
- **Performance Metrics**: View detailed trading statistics

## 🛠️ Command Line Interface

### Quick Options:
1. **Quick Backtest**: Run 30-day backtest with default parameters
2. **Virtual Trading**: Start virtual trading session
3. **Market Status**: Check current USDT/KRW arbitrage opportunity
4. **Desktop GUI**: Launch the desktop application
5. **Exit**: Close the CLI

## 📝 Usage Examples

### Basic Backtest
```bash
py main.py backtest --start-date 2024-01-01 --end-date 2024-12-31
```

### Virtual Trading
```bash
py main.py bot --virtual --initial-balance 10000 --max-trade-amount 1000
```

### Live Trading (requires API keys)
```bash
py main.py bot --api-key YOUR_KEY --secret-key YOUR_SECRET
```

## 🔧 Configuration

### API Keys
1. Get your Upbit API keys from [Upbit Pro](https://upbit.com/service_center/open_api_guide)
2. Enter them in the Desktop GUI Configuration tab
3. Test connection before live trading

### Trading Parameters
- **Initial Balance**: Starting amount in USD (for virtual trading)
- **Max Trade Amount**: Maximum amount per trade
- **Price Threshold**: Minimum difference % to trigger trade
- **Stop Loss**: Maximum loss % before selling
- **Take Profit**: Target profit % for selling
- **Max Trades/Day**: Daily trade limit for risk management

## 🛡️ Safety Features

- **Virtual Mode**: Test strategies without real money
- **Emergency Stop**: Automatic stop on excessive losses
- **Daily Loss Limit**: Maximum daily loss protection
- **Trade Limits**: Maximum number of trades per day
- **API Testing**: Verify connection before live trading

## 📱 Benefits of Desktop vs Web

✅ **Faster Performance**: No web server overhead
✅ **Better Reliability**: No network connectivity issues
✅ **Real-time Updates**: Instant feedback and updates
✅ **Offline Capability**: Works without internet for backtesting
✅ **Better User Experience**: Native desktop interface
✅ **Resource Efficient**: Lower memory and CPU usage

## 🔍 Troubleshooting

### Common Issues:
1. **Import Errors**: Make sure all dependencies are installed
2. **API Connection**: Verify API keys and permissions
3. **GUI Issues**: Ensure tkinter is installed (usually comes with Python)
4. **Chart Display**: Install matplotlib if charts don't show

### Dependencies Check:
```bash
py -c "import tkinter, matplotlib, pandas; print('All dependencies OK')"
```

## 💡 Tips

1. **Start with Virtual Mode**: Test strategies before using real money
2. **Use Small Amounts**: Start with small trade amounts
3. **Monitor Regularly**: Check trading activity frequently
4. **Save Configurations**: Save successful parameter sets
5. **Backtest First**: Always backtest before live trading

## 🎯 Next Steps

1. Run the desktop application: `py run_desktop.py`
2. Configure your parameters in the Configuration tab
3. Run a backtest to test your strategy
4. Start with virtual trading to verify everything works
5. When ready, use live trading with your API keys

Happy Trading! 🚀 