# Web Interface USDT Terminology Update Summary

## Overview
Updated all user-facing terminology in the web interface from "USD" to "USDT" to accurately reflect that Upbit uses USDT (Tether) for trading, not USD.

## Files Updated

### 1. templates/index.html
- ✅ **Initial USDT Balance** - Updated label for initial balance input
- ✅ **Initial KRW Balance** - Added new input field for KRW balance
- ✅ **Max Trade Amount (USDT)** - Updated label for max trade amount
- ✅ **Trade Amount (USDT)** - Updated label in quick actions

### 2. templates/virtual.html
- ✅ **USDT Balance** - Updated balance display label
- ✅ **Amount (USDT)** - Updated trade amount input label
- ✅ **Amount (USDT)** - Updated trade history table header

### 3. templates/live.html
- ✅ **Max Trade Amount (USDT)** - Updated configuration label
- ✅ **Max Daily Loss (USDT)** - Updated risk management label
- ✅ **Total Value (USDT)** - Updated portfolio value display
- ✅ **Amount (USDT)** - Updated manual trade input label
- ✅ **Amount (USDT)** - Updated trade history table header

### 4. templates/results.html
- ✅ **Amount (USDT)** - Updated trade history table headers
- ✅ **USD/KRW Rate** - Kept as is (this is the actual exchange rate)
- ✅ **USDT/KRW Price** - Kept as is (this is the actual trading price)

## Backend Integration

### web_app.py
- ✅ **Initial KRW Balance** - Added support for KRW balance input
- ✅ **USDT Terminology** - Updated comments and error messages
- ✅ **Form Processing** - Updated to handle KRW balance parameter

### Backtest Configuration
- ✅ **BacktestConfig** - Added `initial_balance_krw` parameter
- ✅ **EnhancedUpbitBacktest** - Updated to use KRW balance in portfolio initialization

## Key Features

### 1. Initial KRW Balance Input
- Users can now specify an initial KRW balance for backtesting
- If KRW balance is provided, it's used; otherwise defaults to 50/50 USDT/KRW split
- Allows more realistic portfolio simulation

### 2. USDT Terminology
- All user-facing labels now correctly show "USDT" instead of "USD"
- Maintains internal variable names for backward compatibility
- Clear distinction between USD/KRW exchange rate and USDT/KRW trading price

### 3. Enhanced Portfolio Management
- Better initial portfolio balance options
- More accurate representation of Upbit trading environment
- Improved backtest realism

## Testing

### Test Scripts Created
1. `test_usdt_terminology.py` - Tests backend terminology updates
2. `test_web_terminology.py` - Tests web interface terminology updates

### Verification Steps
1. ✅ Web server starts successfully
2. ✅ Backtest form shows USDT terminology
3. ✅ KRW balance input field is available
4. ✅ Form submission works with new parameters
5. ✅ Results display with correct terminology

## Usage Instructions

### Running the Web Interface
```bash
python run_web.py
# or
py run_web.py
```

### Testing the Changes
```bash
python test_web_terminology.py
```

### Accessing the Interface
1. Open http://127.0.0.1:8000 in your browser
2. Click "Backtest Strategy"
3. Fill in the form with:
   - Initial USDT Balance: $10,000
   - Initial KRW Balance: ₩6,500,000
   - Other parameters as desired
4. Click "Run Backtest"
5. View results with USDT terminology

## Notes

- Internal variable names (like `profit_loss_usd`) remain unchanged for backward compatibility
- USD/KRW rate references are kept as they represent the actual exchange rate
- USDT/KRW price references are kept as they represent the actual trading price
- All user-facing labels now accurately reflect USDT usage

## Status: ✅ COMPLETE

All USDT terminology updates have been successfully applied to the web interface. The system now accurately represents Upbit's USDT-based trading environment while maintaining full functionality and backward compatibility. 