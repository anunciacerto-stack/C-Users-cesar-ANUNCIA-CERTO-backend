import os
import ccxt
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
use_testnet = os.getenv('USE_TESTNET', 'True').lower() == 'true'

print("Iniciando script de venda de emergência...")
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
    exchange.load_markets()
    
    # Buscar saldo de SOL
    balance = exchange.fetch_balance()
    sol_qty = balance['free'].get('SOL', 0)
    print(f"Saldo livre de SOL na conta: {sol_qty:.8f}")
    
    if sol_qty > 0.05:
        # Formatar quantidade para a precisão da Binance
        formatted_qty = float(exchange.amount_to_precision('SOL/USDT', sol_qty))
        print(f"Vendendo {formatted_qty} SOL a mercado para converter em USDT...")
        
        order = exchange.create_market_sell_order('SOL/USDT', formatted_qty)
        print("✅ Venda realizada com sucesso! Seu saldo foi convertido para USDT.")
        
        # Buscar saldo final
        new_balance = exchange.fetch_balance()
        print(f"Saldo atualizado de USDT: ${new_balance['free'].get('USDT', 0):.2f}")
    else:
        print("⚠️ Você não tem saldo de SOL suficiente para realizar uma venda (mínimo de ~0.08 SOL na Binance).")
        
except Exception as e:
    print(f"❌ Erro ao executar a venda: {e}")
