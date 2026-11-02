import ccxt
import pandas as pd
import numpy as np
import os

# Bybit API Credentials (GitHub Secrets se uthayega)
exchange = ccxt.bybit({
    'apiKey': os.getenv('BYBIT_API_KEY'),
    'secret': os.getenv('BYBIT_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'} # Spot trading
})

SYMBOL = 'BTC/USDT'      # Aap yahan apna coin badal sakte hain
TIMEFRAME = '15m'
INVESTMENT_USDT = 5    # Yahan aap apna investment change kar sakte hain
ATR_LEN = 10
TRAINING_PERIOD = 100

def calculate_supertrend_with_ml(df):
    # Safe cleaning for initial NaN values
    df = df.dropna().reset_index(drop=True)
    if len(df) < ATR_LEN:
        return df

    # 1. ATR Calculation
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_LEN, adjust=False).mean()
    df['atr'] = atr

    # 2. Simplified Volatility Centroids (K-Means / Rolling)
    rolling_high = df['atr'].rolling(window=TRAINING_PERIOD, min_periods=1).max()
    rolling_low = df['atr'].rolling(window=TRAINING_PERIOD, min_periods=1).min()

    # Percentile guesses matching your Pine Script
    hv_guess = rolling_low + (rolling_high - rolling_low) * 0.75
    mv_guess = rolling_low + (rolling_high - rolling_low) * 0.50
    lv_guess = rolling_low + (rolling_high - rolling_low) * 0.25

    # Assigning cluster based on closest distance
    df['vdist_a'] = abs(df['atr'] - hv_guess)
    df['vdist_b'] = abs(df['atr'] - mv_guess)
    df['vdist_c'] = abs(df['atr'] - lv_guess)
    
    # Drop any leftover NaNs to prevent calculation failure
    df = df.dropna().reset_index(drop=True)
    return df
