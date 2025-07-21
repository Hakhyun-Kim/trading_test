# 2x Short Strategy Update - 5000 USDT Configuration

## Overview

Updated the Bitcoin arbitrage trading strategy to use **5000 USDT** as the initial balance on Binance for the **2x short strategy**. This configuration provides a more conservative approach while maintaining the leverage benefits.

## Key Changes Made

### 1. Initial Balance Configuration

**Before:**
- Initial USDT Balance: 10,000 USDT
- Initial KRW Balance: 13,500,000 KRW (~10,000 USD equivalent)

**After:**
- Initial USDT Balance: 5,000 USDT
- Initial KRW Balance: 13,500,000 KRW (~10,000 USD equivalent, 1x leverage for Upbit)

### 2. Files Updated

#### Core Configuration Files
- `upbit_bot/bitcoin_backtest.py` - Updated `BitcoinBacktestConfig` default values
- `run_bitcoin_backtest.py` - Updated main backtest script configuration
- `run_bitcoin_backtest_ma.py` - Updated MA strategy backtest configuration
- `optimize_bitcoin_thresholds.py` - Updated optimization script configuration

#### Web Interface
- `web_app.py` - Updated API request model defaults
- `templates/index.html` - Updated web form default values
- `krw_ui_preview.html` - Updated UI preview values

#### Documentation
- `BITCOIN_ARBITRAGE_README.md` - Updated configuration examples

## Strategy Details

### Mixed Leverage Strategy

The strategy uses different leverage on each exchange:

```python
config = BitcoinBacktestConfig(
    initial_balance_usdt=5_000,      # 5,000 USDT for Binance
    initial_balance_krw=13_500_000,  # 13,500,000 KRW for Upbit
    leverage_multiplier=2.0,         # 2x leverage for Binance futures only
    max_position_size_btc=0.1,       # Max 0.1 BTC per position
    entry_premium_threshold=-2.0,    # Enter when premium < -2%
    exit_profit_threshold=2.0,       # Exit when profit > 2%
)
```

### How Mixed Leverage Works

**Upbit (1x Leverage - Normal Trading):**
- **Position Size**: Up to 13,500,000 KRW worth of Bitcoin positions
- **Capital Required**: Full 13,500,000 KRW needed for 13,500,000 KRW exposure
- **Trading Type**: Normal buying and selling of Bitcoin

**Binance (2x Leverage - Shorting):**
- **Effective Position Size**: Up to 10,000 USDT worth of Bitcoin positions
- **Margin Required**: Only 5,000 USDT needed for 10,000 USDT exposure
- **Trading Type**: Short selling with leverage

**Risk Management**: Leverage amplifies gains and losses on Binance only

### Trading Logic

1. **Entry Signal** (Kimchi Premium < -2%):
   - Buy Bitcoin on Upbit with KRW (1x leverage - normal trading)
   - Short Bitcoin on Binance with 2x leverage using USDT

2. **Exit Signal** (Total Profit > 2%):
   - Sell Bitcoin on Upbit (1x leverage - normal trading)
   - Close short position on Binance (2x leverage)

## Benefits of 5000 USDT Configuration

### 1. Optimized Capital Allocation
- Reduced USDT requirement (5,000 instead of 10,000)
- Maintained KRW balance for Upbit normal trading
- More efficient use of available capital

### 2. Strategic Leverage Usage
- 2x leverage only on Binance for shorting (higher risk/reward)
- 1x leverage on Upbit for normal trading (lower risk)
- Balanced risk management approach

### 3. Better Risk Management
- Smaller position sizes reduce individual trade risk
- More positions can be opened with the same capital
- Easier to manage multiple concurrent positions

## Usage

### Running the Updated Strategy

```bash
# Run standard Bitcoin backtest
python run_bitcoin_backtest.py

# Run with Moving Average strategy
python run_bitcoin_backtest_ma.py

# Optimize thresholds
python optimize_bitcoin_thresholds.py
```

### Web Interface

The web interface now defaults to:
- Initial USDT Balance: 5,000 USDT (2x leverage on Binance)
- Initial KRW Balance: 13,500,000 KRW (1x leverage on Upbit)
- All other parameters remain the same

### API Usage

```python
from upbit_bot.bitcoin_backtest import BitcoinBacktestConfig, BitcoinBacktester

config = BitcoinBacktestConfig(
    initial_balance_usdt=5_000,      # 5,000 USDT (2x leverage on Binance)
    initial_balance_krw=13_500_000,  # 13,500,000 KRW (1x leverage on Upbit)
    leverage_multiplier=2.0          # 2x leverage for Binance only
)

backtester = BitcoinBacktester(config)
results = backtester.run_backtest('2024-01-01', '2024-12-31')
```

## Risk Considerations

### Leverage Risks
- 2x leverage means 2x potential losses
- Market volatility can quickly erode capital
- Requires careful position sizing

### Position Management
- Monitor open positions regularly
- Set appropriate stop-loss levels
- Don't over-leverage available capital

### Market Conditions
- Strategy works best in trending markets
- High volatility can lead to frequent entries/exits
- Consider market conditions before deploying

## Performance Expectations

With the reduced capital base:
- **Lower Absolute Returns**: Smaller capital means smaller absolute profits
- **Similar Percentage Returns**: Strategy should maintain similar percentage performance
- **Better Capital Efficiency**: More efficient use of available funds
- **Reduced Risk**: Smaller exposure per trade

## Monitoring and Maintenance

### Key Metrics to Track
- Total return percentage
- Maximum drawdown
- Win rate
- Average trade duration
- Leverage utilization

### Regular Reviews
- Monthly performance analysis
- Strategy parameter optimization
- Risk management assessment
- Capital allocation review

---

**Note**: This configuration is suitable for traders with 5,000 USDT available for the strategy. Always test with virtual trading before using real funds, and ensure you understand the risks associated with leveraged trading. 