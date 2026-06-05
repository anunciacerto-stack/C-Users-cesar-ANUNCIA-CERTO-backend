import os
import time
import ccxt
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot'
    }
})

def clean_dust():
    print("=== INICIANDO LIMPEZA DE SALDO RESIDUAL (POEIRA) ===")
    
    # 1. Verificar saldos atuais
    balance = exchange.fetch_balance()
    btc_free = balance['free'].get('BTC', 0.0)
    usdt_free = balance['free'].get('USDT', 0.0)
    
    print(f"Saldo atual em BTC: {btc_free:.8f}")
    print(f"Saldo atual em USDT: {usdt_free:.8f}")
    
    if btc_free < 0.00001:
        print("Nenhum saldo residual significativo de BTC para limpar.")
        return
        
    if usdt_free < 11.0:
        print(f"Saldo em USDT insuficiente ({usdt_free:.2f}) para realizar a compra de ajuste.")
        return
        
    try:
        # 2. Comprar $11.0 USDT de BTC para passar do limite mínimo de $10
        print("\nPasso 1: Comprando $11.0 USDT de BTC para ultrapassar o limite mínimo da Binance...")
        ticker = exchange.fetch_ticker('BTC/USDT')
        price = ticker['last']
        qty_to_buy = 11.0 / price
        formatted_qty_buy = float(exchange.amount_to_precision('BTC/USDT', qty_to_buy))
        
        print(f"Enviando ordem de compra de {formatted_qty_buy:.8f} BTC...")
        buy_order = exchange.create_market_buy_order('BTC/USDT', formatted_qty_buy)
        print("Compra realizada com sucesso!")
        
        time.sleep(2)
        
        # 3. Consultar novo saldo total de BTC
        balance = exchange.fetch_balance()
        total_btc = balance['free'].get('BTC', 0.0)
        formatted_qty_sell = float(exchange.amount_to_precision('BTC/USDT', total_btc))
        
        print(f"\nPasso 2: Vendendo o saldo total acumulado de {formatted_qty_sell:.8f} BTC para USDT...")
        sell_order = exchange.create_market_sell_order('BTC/USDT', formatted_qty_sell)
        print("Venda realizada com sucesso!")
        
        time.sleep(2)
        
        # 4. Verificar saldos finais
        balance = exchange.fetch_balance()
        final_btc = balance['free'].get('BTC', 0.0)
        final_usdt = balance['free'].get('USDT', 0.0)
        
        print("\n=== LIMPEZA CONCLUÍDA ===")
        print(f"Saldo final em BTC: {final_btc:.8f}")
        print(f"Saldo final em USDT: {final_usdt:.8f}")
        
    except Exception as e:
        print(f"\n[ERRO] Ocorreu um problema durante a limpeza: {e}")

if __name__ == '__main__':
    clean_dust()
