import os
import ccxt
from dotenv import load_dotenv

# Carrega as configurações de variáveis de ambiente (.env)
load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
use_testnet = os.getenv('USE_TESTNET', 'True').lower() == 'true'

print(f"Chave carregada: {api_key[:6]}...{api_key[-6:]}")
print(f"Modo simulador (TESTNET): {use_testnet}")

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot'
    }
})

if use_testnet:
    exchange.set_sandbox_mode(True)

try:
    # 1. Obter saldo spot
    balance = exchange.fetch_balance()
    print("\n--- SALDOS SPOT ---")
    for asset, data in balance['total'].items():
        if data > 0:
            free = balance['free'].get(asset, 0)
            used = balance['used'].get(asset, 0)
            print(f"{asset}: Total={data:.8f} | Livre={free:.8f} | Bloqueado={used:.8f}")
            
    # 2. Obter últimas ordens/trades de BTC/USDT
    print("\n--- ÚLTIMOS TRADES DE BTC/USDT ---")
    trades = exchange.fetch_my_trades('BTC/USDT', limit=5)
    if not trades:
        print("Nenhum trade recente encontrado no histórico de BTC/USDT.")
    for t in trades:
        print(f"Data: {t['datetime']} | {t['side'].upper()} | Preço: {t['price']} | Qtd: {t['amount']} | Total: {t['cost']} USDT")
        
except Exception as e:
    print(f"Erro ao consultar Binance: {e}")
