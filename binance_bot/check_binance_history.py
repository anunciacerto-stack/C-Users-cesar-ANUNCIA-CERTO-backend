import os
import ccxt
from dotenv import load_dotenv

load_dotenv()

def main():
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    use_testnet = os.getenv('USE_TESTNET', 'True').lower() == 'true'

    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    if use_testnet:
        exchange.set_sandbox_mode(True)

    try:
        trades = exchange.fetch_my_trades('SOL/USDT', limit=20)
        print("\n--- RECENT BINANCE TRADES (SOL/USDT) ---")
        for trade in trades:
            print(f"ID: {trade['id']} | {trade['datetime']} | {trade['side'].upper()} | Price: {trade['price']} | Qty: {trade['amount']} | Value: {trade['cost']} USDT")
        print("----------------------------------------")
    except Exception as e:
        print(f"Error fetching trades: {e}")

if __name__ == '__main__':
    main()
