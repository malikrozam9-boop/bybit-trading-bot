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

SYMBOL = 'BTC/USDT'     # Aap yahan apna coin badal sakte hain (jaise 'SOL/USDT')
TIMEFRAME = '15m'       
INVESTMENT_USDT = 20    # Yahan aap apna investment amount set kar rahe hain (e.g., 20 USDT)
ATR_LEN = 10
TRAINING_PERIOD = 100

def calculate_supertrend_with_ml(df):
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

    # 2. Simplified Volatility Centroids (K-Means Simulation in Python)
    rolling_high = df['atr'].rolling(window=TRAINING_PERIOD).max()
    rolling_low = df['atr'].rolling(window=TRAINING_PERIOD).min()
    
    # Percentile guesses matching your Pine Script logic
    hv_guess = rolling_low + (rolling_high - rolling_low) * 0.75
    mv_guess = rolling_low + (rolling_high - rolling_low) * 0.50
    lv_guess = rolling_low + (rolling_high - rolling_low) * 0.25
    
    # Assigning cluster based on closest distance to volatility
    df['vdist_a'] = abs(df['atr'] - hv_guess)
    df['vdist_b'] = abs(df['atr'] - mv_guess)
    df['vdist_c'] = abs(df['atr'] - lv_guess)
    
    # Find minimum distance cluster (0: High, 1: Medium, 2: Low)
    distances = pd.concat([df['vdist_a'], df['vdist_b'], df['vdist_c']], axis=1)
    cluster = distances.idxmin(axis=1)
    
    # Adaptive Factor based on Volatility cluster
    # High volatility = tighter factor, Low volatility = wider factor
    df['factor'] = np.where(cluster == 'vdist_a', 2.0, np.where(cluster == 'vdist_b', 3.0, 4.0))

    # 3. SuperTrend Calculation
    hl2 = (high + low) / 2
    df['upperBand'] = hl2 + (df['factor'] * df['atr'])
    df['lowerBand'] = hl2 - (df['factor'] * df['atr'])
    
    df['st'] = 0.0
    df['dir'] = 1
    
    for i in range(1, len(df)):
        prev_lb = df['lowerBand'].iloc[i-1]
        curr_lb = df['lowerBand'].iloc[i]
        if curr_lb > prev_lb or close.iloc[i-1] < prev_lb:
            df.loc[df.index[i], 'lowerBand'] = curr_lb
        else:
            df.loc[df.index[i], 'lowerBand'] = prev_lb
            
        prev_ub = df['upperBand'].iloc[i-1]
        curr_ub = df['upperBand'].iloc[i]
        if curr_ub < prev_ub or close.iloc[i-1] > prev_ub:
            df.loc[df.index[i], 'upperBand'] = curr_ub
        else:
            df.loc[df.index[i], 'upperBand'] = prev_ub

        if pd.isna(df['atr'].iloc[i-1]):
            df.loc[df.index[i], 'dir'] = 1
        elif df['st'].iloc[i-1] == df['upperBand'].iloc[i-1]:
            df.loc[df.index[i], 'dir'] = -1 if close.iloc[i] > df['upperBand'].iloc[i] else 1
        else:
            df.loc[df.index[i], 'dir'] = 1 if close.iloc[i] < df['lowerBand'].iloc[i] else -1
            
        df.loc[df.index[i], 'st'] = df['lowerBand'].iloc[i] if df['dir'].iloc[i] == -1 else df['upperBand'].iloc[i]

    return df

def run_trading_bot():
    try:
        print(f"Fetching market data for {SYMBOL}...")
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=150)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Apply Machine Learning Adaptive SuperTrend Strategy
        df = calculate_supertrend_with_ml(df)
        
        current_dir = df['dir'].iloc[-1]
        prev_dir = df['dir'].iloc[-2]
        
        print(f"Current Direction Signal: {current_dir} (Previous: {prev_dir})")

        # BUY Signal: Direction flips from 1 to -1 (Bullish Trend Shift)
        if prev_dir == 1 and current_dir == -1:
            print("🟢 Bullish Trend Shift detected! Executing BUY...")
            usdt_balance = exchange.fetch_free_balance().get('USDT', 0)
            
            if usdt_balance >= INVESTMENT_USDT:
                ticker = exchange.fetch_ticker(SYMBOL)
                price = ticker['ask']
                amount = INVESTMENT_USDT / price
                order = exchange.create_market_buy_order(SYMBOL, amount)
                print(f"Successfully Bought: {order}")
            else:
                print(f"Not enough USDT balance. Available: {usdt_balance}")

        # SELL Signal: Direction flips from -1 to 1 (Bearish Trend Shift)
        elif prev_dir == -1 and current_dir == 1:
            print("🔴 Bearish Trend Shift detected! Executing SELL...")
            base_currency = SYMBOL.split('/')[0]
            coin_balance = exchange.fetch_free_balance().get(base_currency, 0)
            
            if coin_balance > 0:
                order = exchange.create_market_sell_order(SYMBOL, coin_balance)
                print(f"Successfully Sold: {order}")
            else:
                print(f"No {base_currency} balance available to sell.")
        else:
            print("No trend shift signal. Holding position.")
                
    except Exception as e:
        print(f"Error in trading bot: {e}")

if __name__ == "__main__":
    run_trading_bot()
