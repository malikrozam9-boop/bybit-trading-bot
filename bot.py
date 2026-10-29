import ccxt
import pandas as pd
import time

# Bybit API Credentials (Apni Bybit account ki API Key aur Secret yahan dalen)
exchange = ccxt.bybit({
    'apiKey': 'YAHAN_APNI_API_KEY_DALEN',
    'secret': 'YAHAN_APNA_SECRET_KEY_DALEN',
    'enableRateLimit': True,
    'options': {'defaultType': 'spot'} # Spot trading ke liye
})

SYMBOL = 'BTC/USDT'
TIMEFRAME = '15m'
INVESTMENT_AMOUNT_USDT = 20  # Har trade mein kitne USDT lagane hain

def check_indicators_and_trade():
    try:
        # 1. Bybit se past 100 candles ka data fetch karna
        ohlcv = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 2. Aapke indicator ka logic (Yahan hum EMA crossover use kar rahe hain as an example)
        df['ema_fast'] = df['close'].ewm(span=10, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()
        
        last_fast = df['ema_fast'].iloc[-1]
        last_slow = df['ema_slow'].iloc[-1]
        prev_fast = df['ema_fast'].iloc[-2]
        prev_slow = df['ema_slow'].iloc[-2]
        
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

        # 4. SELL Signal Logic
        elif last_fast < last_slow and prev_fast >= prev_slow:
            print("🔴 SELL Signal detected!")
            base_currency = SYMBOL.split('/')[0]
            coin_balance = exchange.fetch_free_balance().get(base_currency, 0)
            if coin_balance > 0:
                order = exchange.create_market_sell_order(SYMBOL, coin_balance)
                print(f"Order Executed (SELL): {order}")
                
    except Exception as e:
        print(f"Error aagaya: {e}")

if __name__ == "__main__":
    print("Bot 24/7 background mein start ho gaya hai...")
    while True:
        check_indicators_and_trade()
        # Har 15 minute (900 seconds) baad dobara check karega
        time.sleep(900)
