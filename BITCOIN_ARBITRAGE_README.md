# Bitcoin Kimchi Premium Arbitrage Strategy

## Overview

This module implements an advanced Bitcoin arbitrage strategy that profits from price differences between Korean exchanges (Upbit) and international exchanges (Binance). The strategy involves:

1. **Shorting Bitcoin on Binance** when the kimchi premium is low (< 0.3%)
2. **Buying Bitcoin on Upbit** with limit orders (one tick below current price)
3. **Closing positions** when the kimchi premium is high (> 1.3%)
4. **Selling Bitcoin on Upbit** with limit orders (one tick above current price)

## Key Features

- **Dual Exchange Arbitrage**: Simultaneously operates on Binance (international) and Upbit (Korean)
- **Smart Order Execution**: Uses limit orders on Upbit for better fills, market orders on Binance for speed
- **Risk Management**: Maximum position sizes, multiple position tracking
- **Real-time Premium Monitoring**: Continuously tracks Bitcoin price differences
- **Historical Backtesting**: Test strategies with real historical data

## How It Works

### 1. Kimchi Premium Calculation

The kimchi premium is calculated as:
```
Premium = ((Upbit_BTC_KRW - Binance_BTC_KRW) / Binance_BTC_KRW) * 100
```

Where:
- `Upbit_BTC_KRW`: Bitcoin price on Upbit in Korean Won
- `Binance_BTC_KRW`: Bitcoin price on Binance converted to KRW using USD/KRW rate

### 2. Entry Signal (Premium < 0.3%)

When Bitcoin is cheaper in Korea:
1. Buy Bitcoin on Upbit (limit order, 1 tick below best bid)
2. Short Bitcoin on Binance (market order for immediate execution)

### 3. Exit Signal (Premium > 1.3%)

When Bitcoin is expensive in Korea:
1. Sell Bitcoin on Upbit (limit order, 1 tick above best ask)
2. Close short position on Binance (market order)

## Configuration

### Strategy Parameters

```python
config = BitcoinArbitrageConfig(
    entry_premium_threshold=0.3,    # Enter when premium < 0.3%
    exit_premium_threshold=1.3,     # Exit when premium > 1.3%
    max_position_size_btc=0.1,      # Maximum 0.1 BTC per position
    tick_offset=1,                  # Place orders 1 tick away from best price
    max_open_positions=3,           # Maximum 3 simultaneous positions
    use_market_orders_binance=True  # Use market orders on Binance
)
```

### Backtest Configuration

```python
backtest_config = BitcoinBacktestConfig(
    initial_balance_krw=13_500_000,  # ~$10,000 in KRW
    initial_balance_usdt=10_000,     # $10,000 USDT for Binance
    entry_premium_threshold=0.3,
    exit_premium_threshold=1.3,
    max_position_size_btc=0.1,
    upbit_commission=0.0025,         # 0.25% Upbit fee
    binance_commission=0.001,        # 0.1% Binance fee
    slippage_rate=0.001             # 0.1% slippage
)
```

## Usage

### 1. Test Current Premium

```python
from upbit_bot.bitcoin_kimchi_strategy import BitcoinKimchiPremiumCalculator

calculator = BitcoinKimchiPremiumCalculator()
result = calculator.calculate_bitcoin_kimchi_premium()
print(f"Current Bitcoin Kimchi Premium: {result['kimchi_premium_percentage']:.2f}%")
```

### 2. Run Backtest

```python
from upbit_bot.bitcoin_backtest import BitcoinBacktester, BitcoinBacktestConfig

config = BitcoinBacktestConfig()
backtester = BitcoinBacktester(config)
results = backtester.run_backtest('2024-01-01', '2024-01-31')
```

### 3. Live Trading (Example)

```python
from upbit_bot.bitcoin_kimchi_strategy import BitcoinArbitrageStrategy

strategy = BitcoinArbitrageStrategy(config)
status = strategy.get_strategy_status()

# Check for entry signals
if strategy.should_enter_position(premium_data):
    position = strategy.execute_entry(premium_data, available_krw, available_usdt)
```

## API Endpoints

The web interface provides these endpoints for Bitcoin arbitrage:

- `GET /api/bitcoin-kimchi-premium` - Get current Bitcoin kimchi premium
- `POST /api/bitcoin-backtest` - Run historical backtest
- `POST /api/bitcoin-arbitrage/start` - Start live arbitrage strategy
- `GET /api/bitcoin-arbitrage/status` - Get strategy status

## Risk Considerations

1. **Exchange Risk**: Funds are split between two exchanges
2. **Execution Risk**: Limit orders may not fill immediately
3. **Premium Volatility**: Kimchi premium can change rapidly
4. **Regulatory Risk**: Cross-border arbitrage regulations
5. **Technical Risk**: API failures, network issues

## Performance Metrics

Typical backtest results (example):
- Average Premium Capture: 0.8-1.2% per trade
- Win Rate: 65-75%
- Maximum Drawdown: 3-5%
- Trades per Month: 20-40

## Testing

Run the test script to see the strategy in action:

```bash
python test_bitcoin_arbitrage.py
```

This will:
1. Calculate current Bitcoin kimchi premium
2. Show entry/exit signals based on current market
3. Run a 30-day backtest with historical data

## Future Enhancements

1. **Multi-Currency Support**: Add ETH, XRP arbitrage
2. **Advanced Order Types**: Iceberg orders, TWAP
3. **Machine Learning**: Premium prediction models
4. **Risk Analytics**: Real-time VAR calculation
5. **Automated Rebalancing**: Maintain optimal fund distribution 