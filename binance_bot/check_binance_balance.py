import os
import ccxt
from dotenv import load_dotenv

load_dotenv()

def main():
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    use_testnet = os.getenv('USE_TESTNET', 'True').lower() == 'true'

    print(f"Connecting to Binance (Sandbox={use_testnet})...")
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    if use_testnet:
        exchange.set_sandbox_mode(True)

    try:
        balance = exchange.fetch_balance()
        print("\n--- BINANCE SPOT BALANCE ---")
        for asset, asset_bal in balance['total'].items():
            if asset_bal > 0:
                free = balance['free'].get(asset, 0)
                used = balance['used'].get(asset, 0)
                print(f"{asset}: Total={asset_bal:.6f} | Free={free:.6f} | Used={used:.6f}")
        print("----------------------------")
    except Exception as e:
        print(f"Error fetching balance: {e}")

if __name__ == '__main__':
    main()
