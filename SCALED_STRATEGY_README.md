# Scaled Entry/Exit Strategy for Bitcoin Arbitrage

## Overview

The scaled entry/exit strategy implements a **dollar-cost averaging** approach for Bitcoin arbitrage trading. Instead of using all capital at once, the strategy:

- **Enters positions gradually** as the kimchi premium becomes more negative
- **Exits positions gradually** as profits accumulate
- **Uses 25% of capital** for each position
- **Maximizes profit capture** while minimizing risk

## Strategy Details

### Entry Strategy (Scaled In)

The strategy enters positions at multiple premium levels:

```
Entry Levels:
- 0%     (Premium < 0%)     → Use 25% of capital
- -0.5%  (Premium < -0.5%)  → Use 25% of capital  
- -1.0%  (Premium < -1.0%)  → Use 25% of capital
- -1.5%  (Premium < -1.5%)  → Use 25% of capital
- -2.0%  (Premium < -2.0%)  → Use 25% of capital
- -2.5%  (Premium < -2.5%)  → Use 25% of capital
- -3.0%  (Premium < -3.0%)  → Use 25% of capital
- -3.5%  (Premium < -3.5%)  → Use 25% of capital
- -4.0%  (Premium < -4.0%)  → Use 25% of capital
```

**Logic**: As the kimchi premium becomes more negative (Bitcoin cheaper in Korea), we gradually build positions.

### Exit Strategy (Scaled Out)

The strategy exits positions at multiple profit levels:

```
Exit Levels:
- 0.5%   (Profit > 0.5%)    → Exit 25% of positions
- 1.0%   (Profit > 1.0%)    → Exit 25% of positions
- 1.5%   (Profit > 1.5%)    → Exit 25% of positions
- 2.0%   (Profit > 2.0%)    → Exit 25% of positions
- 2.5%   (Profit > 2.5%)    → Exit 25% of positions
- 3.0%   (Profit > 3.0%)    → Exit 25% of positions
- 3.5%   (Profit > 3.5%)    → Exit 25% of positions
- 4.0%   (Profit > 4.0%)    → Exit 25% of positions
```

**Logic**: As profits accumulate, we gradually take profits to lock in gains.

## Configuration

### Default Settings

```python
config = BitcoinBacktestConfig(
    initial_balance_krw=13_500_000,  # 13.5M KRW (1x leverage for Upbit)
    initial_balance_usdt=5_000,      # 5K USDT (2x leverage for Binance)
    use_scaled_strategy=True,        # Enable scaled strategy
    position_portion=0.25,           # 25% of capital per position
    leverage_multiplier=2.0,         # 2x leverage on Binance only
    max_position_size_btc=0.1        # Max 0.1 BTC per position
)
```

### Strategy Parameters

- **`use_scaled_strategy`**: Enable/disable scaled entry/exit
- **`position_portion`**: Percentage of capital per position (0.25 = 25%)
- **`entry_premium_threshold`**: Fallback entry threshold (if scaled strategy disabled)
- **`exit_profit_threshold`**: Fallback exit threshold (if scaled strategy disabled)

## How It Works

### 1. Entry Process

1. **Monitor Premium**: Continuously track kimchi premium
2. **Check Entry Levels**: When premium crosses below an unused entry level
3. **Calculate Position Size**: Use 25% of available capital
4. **Execute Trade**: 
   - Buy Bitcoin on Upbit (1x leverage)
   - Short Bitcoin on Binance (2x leverage)
5. **Mark Level Used**: Prevent duplicate entries at same level

### 2. Exit Process

1. **Monitor Profits**: Calculate total arbitrage profit for each position
2. **Check Exit Levels**: When profit crosses above an unused exit level
3. **Close Position**: 
   - Sell Bitcoin on Upbit
   - Close short on Binance
4. **Mark Level Used**: Prevent duplicate exits at same level

### 3. Position Management

- **Maximum Positions**: Up to 8 positions (one per entry level)
- **Position Sizing**: Each position uses 25% of available capital
- **Risk Distribution**: Spreads risk across multiple entry points
- **Profit Capture**: Locks in profits at multiple levels

## Example Scenario

### Market Conditions
- Bitcoin price on Upbit: 50,000,000 KRW
- Bitcoin price on Binance: 38,000 USDT
- USD/KRW rate: 1,350 KRW/USD
- Kimchi Premium: -2.5%

### Entry Execution
1. **Premium crosses -2.0%**: Enter first position (25% of capital)
2. **Premium crosses -2.5%**: Enter second position (25% of capital)
3. **Premium crosses -3.0%**: Enter third position (25% of capital)

### Exit Execution
1. **Profit reaches 0.5%**: Exit first position
2. **Profit reaches 1.0%**: Exit second position
3. **Profit reaches 1.5%**: Exit third position

## Benefits

### 1. Risk Management
- **Diversified Entry**: Spreads risk across multiple price levels
- **Gradual Exposure**: Builds positions over time, not all at once
- **Controlled Risk**: Each position represents only 25% of capital

### 2. Profit Optimization
- **Multiple Profit Targets**: Captures profits at various levels
- **Reduced Slippage**: Smaller positions cause less market impact
- **Better Fill Rates**: Smaller orders get better execution

### 3. Market Adaptation
- **Trend Following**: Enters more positions as premium worsens
- **Profit Taking**: Exits positions as profits materialize
- **Flexible Strategy**: Adapts to market conditions automatically

## Usage

### Running the Strategy

```bash
# Run scaled strategy backtest
python run_bitcoin_backtest.py

# The strategy is enabled by default with:
# - 25% position sizing
# - 9 entry levels (0% to -4%)
# - 8 exit levels (0.5% to 4%)
```

### Expected Output

```
====================================================================
BITCOIN ARBITRAGE BACKTEST - SCALED STRATEGY
====================================================================
Period: 2024-01-01 to 2024-12-31
Initial KRW Balance: ₩13,500,000
Initial USDT Balance: $5,000
Strategy: Scaled Entry/Exit (25% per position)
Entry Levels: 0%, -0.5%, -1.0%, -1.5%, -2.0%, -2.5%, -3.0%, -3.5%, -4.0%
Exit Levels: 0.5%, 1.0%, 1.5%, 2.0%, 2.5%, 3.0%, 3.5%, 4.0%
Leverage: 2x on Binance
====================================================================

Recent Trades (last 10):
[ENTRY] 2024-01-15 - Premium: -2.1% (Level: -2.0%), Size: 0.025000 BTC, 2x
[ENTRY] 2024-01-16 - Premium: -2.6% (Level: -2.5%), Size: 0.025000 BTC, 2x
[EXIT] 2024-01-20 - Premium: 0.8% (Level: 0.5%), P&L: 🟢 ₩125,000
[EXIT] 2024-01-22 - Premium: 1.2% (Level: 1.0%), P&L: 🟢 ₩180,000
```

## Risk Considerations

### 1. Capital Allocation
- **Maximum Exposure**: Up to 200% of capital (8 positions × 25%)
- **Leverage Risk**: 2x leverage on Binance amplifies gains/losses
- **Position Correlation**: All positions are correlated to Bitcoin price

### 2. Market Conditions
- **Low Volatility**: May not trigger all entry/exit levels
- **High Volatility**: May trigger multiple levels quickly
- **Trend Changes**: Rapid premium changes can affect strategy

### 3. Execution Risk
- **Slippage**: Multiple small trades may have higher total slippage
- **Timing**: Entry/exit timing depends on market conditions
- **Liquidity**: Smaller exchanges may have liquidity constraints

## Performance Expectations

### Typical Results
- **More Trades**: Scaled strategy generates more frequent trades
- **Lower Per-Trade Profit**: Individual trades have smaller profits
- **Higher Total Return**: Better profit capture over time
- **Reduced Drawdown**: More stable performance due to diversification

### Monitoring Metrics
- **Entry Level Utilization**: How many entry levels were used
- **Exit Level Utilization**: How many exit levels were used
- **Average Position Size**: Average size of positions taken
- **Profit Distribution**: Distribution of profits across exit levels

---

**Note**: This scaled strategy is designed for markets with frequent kimchi premium fluctuations. In stable markets, fewer entry/exit levels may be triggered, reducing the strategy's effectiveness. 