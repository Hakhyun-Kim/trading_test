# Upbit Trading Bot - Desktop Application

## Overview
The Upbit Trading Bot Desktop Application provides a comprehensive GUI for cryptocurrency trading, backtesting, and analysis with enhanced charting capabilities.

## Features

### 1. Backtest Configuration
- Set trading parameters (initial balance, trade amounts, thresholds)
- Configure kimchi premium strategy thresholds
- Advanced parameters for profit/risk boundaries
- Debug mode for detailed trade analysis

### 2. Automated Chart Display
After running a backtest, the application automatically displays comprehensive charts:

#### Equity Curve
- Shows portfolio value over time
- Highlights initial balance line
- Filled area chart for visual impact

#### Trade Distribution
- Pie chart showing winning vs losing trades
- Clear percentage breakdown

#### Monthly Returns
- Bar chart of returns grouped by month
- Green bars for profits, red for losses

#### Drawdown History
- Shows maximum portfolio drawdown over time
- Critical for risk assessment

#### Profit/Loss Distribution
- Histogram of trade returns
- Helps identify trading pattern effectiveness

#### Performance Summary
- Key metrics displayed in a clean format
- Total return, Sharpe ratio, win rate, etc.

### 3. Parameter Optimization
- **Find Profitable Boundaries** button to automatically optimize parameters
- Tests multiple parameter combinations
- Auto-applies best performing parameters

### 4. Scenario Testing
- Predefined trading scenarios (Conservative, Moderate, Aggressive, etc.)
- Quick comparison of different strategies
- Results ranked by performance

## Running the Application

### Desktop Mode
```bash
py run_desktop.py
```

### Command Line Mode
```bash
py cli_runner.py --start-date 2024-01-01 --end-date 2024-12-31 --initial-balance 10000
```

## Usage Tips

1. **First Time Setup**
   - Run a backtest to see sample data
   - Charts automatically appear after backtest completion
   - Review all 6 chart panels for comprehensive analysis

2. **Optimizing Strategy**
   - Click "Find Profitable Boundaries" to test parameter ranges
   - Review suggested parameters before applying
   - Test with different date ranges

3. **Interpreting Charts**
   - **Equity Curve**: Should trend upward for profitable strategy
   - **Win Rate**: Aim for >50% but consider profit factor too
   - **Drawdown**: Lower is better, indicates less risk
   - **Monthly Returns**: Look for consistency

4. **Debug Mode**
   - Enable for detailed trade-by-trade analysis
   - Shows exact entry/exit points
   - Useful for strategy refinement

## Requirements
- Python 3.8+
- Required packages: pandas, numpy, matplotlib, tkinter, ccxt, requests
- Install with: `pip install -r requirements.txt`

## Chart Navigation
- Charts update automatically after each backtest
- Click the "Charts & Analysis" tab to view results
- All charts are interactive - hover for details
- Performance summary provides quick metrics overview

## Troubleshooting
- If charts don't appear, check the "Charts & Analysis" tab
- Ensure backtest completes successfully (check progress bar)
- For "No trades executed" - adjust thresholds or date range
- Use debug mode to identify why trades aren't triggering

## Future Enhancements
- Real-time chart updates during live trading
- Export charts as images
- Custom chart indicators
- Multi-timeframe analysis 