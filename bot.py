import ccxt
import pandas as pd
import os

# Bybit API Credentials (Yeh GitHub Secrets se automatic utha lega)
exchange = ccxt.bybit({
    'apiKey': os.getenv('BYBIT_API_KEY'),
    'secret': os.getenv('BYBIT_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'} # Spot trading ke liye
})

SYMBOL = 'BTC/USDT'
TIMEFRAME = '15m'
INVESTMENT_AMOUNT_USDT = 20  # Har trade mein kitne USDT lagane hain

def check_indicators_and_trade():
    try:
        print(f"Fetching market data for {SYMBOL}...")
        # 1. Bybit se past 100 candles ka data fetch karna
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 2. Aapke indicator ka logic (EMA crossover example)
        df['ema_fast'] = df['close'].ewm(span=10, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()
        
        last_fast = df['ema_fast'].iloc[-1]
        last_slow = df['ema_slow'].iloc[-1]
        prev_fast = df['ema_fast'].iloc[-2]
        prev_slow = df['ema_slow'].iloc[-2]
        
        print(f"Fast EMA: {last_fast}, Slow EMA: {last_slow}")

        # 3. BUY Signal Logic
        if last_fast > last_slow and prev_fast <= prev_slow:
            print("🟢 BUY Signal detected!")
            usdt_balance = exchange.fetch_free_balance().get('USDT', 0)
            if usdt_balance >= INVESTMENT_AMOUNT_USDT:
                ticker = exchange.fetch_ticker(SYMBOL)
                price = ticker['ask']
                amount = INVESTMENT_AMOUNT_USDT / price
                order = exchange.create_market_buy_order(SYMBOL, amount)
                print(f"Order Executed (BUY): {order}")
            else:
                print("Insufficient USDT balance for buying.")

        # 4. SELL Signal Logic
        elif last_fast < last_slow and prev_fast >= prev_slow:
            print("🔴 SELL Signal detected!")
            base_currency = SYMBOL.split('/')[0]
            coin_balance = exchange.fetch_free_balance().get(base_currency, 0)
            if coin_balance > 0:
                order = exchange.create_market_sell_order(SYMBOL, coin_balance)
                print(f"Order Executed (SELL): {order}")
            else:
                print("No coin balance to sell.")
        else:
            print("No crossover signal. Holding position.")
                
    except Exception as e:
        print(f"Error aagaya: {e}")

if __name__ == "__main__":
    check_indicators_and_trade()
