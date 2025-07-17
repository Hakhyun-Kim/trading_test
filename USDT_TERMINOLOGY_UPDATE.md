# USDT Terminology Update Summary

## Overview
Updated the codebase to correctly use USDT (Tether) terminology instead of USD, since Upbit trades USDT/KRW pairs, not USD/KRW.

## Key Changes

### 1. User Interface Updates

#### Input Labels
- **Before**: "Initial USD Balance"
- **After**: "Initial USDT Balance"

- **Before**: "Max Trade Amount (USD)"
- **After**: "Max Trade Amount (USDT)"

#### Table Headers
- **Before**: "Amount (USD)"
- **After**: "Amount (USDT)"

#### Chart Labels
- **Before**: "Value (USD)"
- **After**: "Value (USDT equivalent)"

### 2. Backend Updates

#### Comments and Documentation
- Added clarifying comments that fields named `usd` actually represent USDT
- Kept internal variable names for backward compatibility
- Updated error messages to reference USDT

#### Error Messages
- **Before**: "Insufficient USD balance"
- **After**: "Insufficient USDT balance"

### 3. Trade Logic Clarification

The arbitrage trading logic now correctly represents:
- **BUY**: Purchase USDT using KRW when USDT is cheap in Korea
- **SELL**: Sell USDT for KRW when USDT is expensive in Korea

### 4. Important Notes

- **Variable Names**: Internal variable names like `initial_balance_usd` and `amount_usd` remain unchanged for backward compatibility
- **Kimchi Premium**: Still calculated as the difference between USDT/KRW price on Upbit vs USD/KRW forex rate
- **Value Display**: All dollar amounts shown represent USDT value, not USD

## Trading Flow

```
1. User holds USDT and KRW on Upbit
2. Bot monitors USDT/KRW price vs USD/KRW forex rate
3. When kimchi premium is negative → BUY USDT (cheap)
4. When kimchi premium is positive → SELL USDT (expensive)
```

## Default Values

- Initial USDT Balance: 5,000 USDT
- Initial KRW Balance: 6,500,000 KRW
- Total Portfolio Value: ~10,000 USDT equivalent

This provides a balanced 50/50 portfolio for effective arbitrage trading. 