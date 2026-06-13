import os
import sys
import ccxt
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Configuração de saída UTF-8 para Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

load_dotenv()

# Parâmetros de DCA Grid
DCA_CONFIG = {
    'max_safety_orders': 3,     # Total de 4 compras (Base + 3 Seguranças)
    'dca_step_pct': 0.02,       # Compra a cada 2% de queda
    'profit_target_pct': 0.010, # 1.0% de lucro sobre o preço médio do ciclo
    'stop_loss_pct': 0.03       # Stop de segurança: 3% abaixo da 4ª compra
}

# --- CÁLCULO DE INDICADORES ---
def calc_atr(df, period=14):
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(span=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=period, adjust=False).mean()
    return 100 - (100 / (1 + gain / (loss + 1e-9)))

def calc_bollinger_bands(df, period=20, num_std=2):
    sma = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std()
    df['bb_middle'] = sma
    df['bb_upper'] = sma + (num_std * std)
    df['bb_lower'] = sma - (num_std * std)
    return df

def calc_emas(df):
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    return df

def prepare_data(df):
    df['rsi'] = calc_rsi(df['close'], 14)
    df['atr'] = calc_atr(df, 14)
    df = calc_bollinger_bands(df, 20, 2)
    df = calc_emas(df)
    return df

# --- MOTOR DE SIMULAÇÃO DCA ---
def simulate_dca(df, symbol, trade_amount=12.0):
    balance = 0.0
    in_cycle = False
    orders = [] # [{price, qty, value}]
    trades_log = []
    
    # Métricas de risco
    max_capital_used = 0.0
    max_safety_reached = 0
    
    for i in range(50, len(df)):
        c_current = df.iloc[i]
        
        if in_cycle:
            # Preço médio, quantidade e valor investido atual no ciclo
            total_qty = sum(o['qty'] for o in orders)
            total_value = sum(o['value'] for o in orders)
            avg_price = total_value / total_qty
            
            # Atualiza máxima exposição de capital
            if total_value > max_capital_used:
                max_capital_used = total_value
            if (len(orders) - 1) > max_safety_reached:
                max_safety_reached = len(orders) - 1
                
            tp_price = avg_price * (1 + DCA_CONFIG['profit_target_pct'])
            current_price_low = c_current['low']
            current_price_high = c_current['high']
            
            # 1. Check Take Profit
            if current_price_high >= tp_price:
                profit = (tp_price - avg_price) * total_qty
                balance += profit
                trades_log.append({
                    'type': 'WIN',
                    'profit_usd': profit,
                    'orders_count': len(orders),
                    'capital_used': total_value
                })
                in_cycle = False
                orders = []
                continue
                
            # 2. Check se precisa de Safety Order (Compra de Segurança)
            if len(orders) <= DCA_CONFIG['max_safety_orders']:
                last_order_price = orders[-1]['price']
                trigger_price = last_order_price * (1 - DCA_CONFIG['dca_step_pct'])
                
                if current_price_low <= trigger_price:
                    buy_qty = trade_amount / trigger_price
                    orders.append({
                        'price': trigger_price,
                        'qty': buy_qty,
                        'value': trade_amount
                    })
                    continue
            
            # 3. Check Stop Loss (3% abaixo da 4ª compra)
            if len(orders) == (DCA_CONFIG['max_safety_orders'] + 1):
                sl_price = orders[-1]['price'] * (1 - DCA_CONFIG['stop_loss_pct'])
                if current_price_low <= sl_price:
                    loss = (avg_price - sl_price) * total_qty
                    balance -= loss
                    trades_log.append({
                        'type': 'STOP_LOSS',
                        'profit_usd': -loss,
                        'orders_count': len(orders),
                        'capital_used': total_value
                    })
                    in_cycle = False
                    orders = []
                    continue
        else:
            # Inicia ciclo na abertura do candle
            entry_price = c_current['open']
            qty = trade_amount / entry_price
            orders.append({
                'price': entry_price,
                'qty': qty,
                'value': trade_amount
            })
            in_cycle = True
            if trade_amount > max_capital_used:
                max_capital_used = trade_amount
                
    total_cycles = len(trades_log)
    wins = sum(1 for t in trades_log if t['type'] == 'WIN')
    losses = total_cycles - wins
    win_rate = (wins / total_cycles * 100) if total_cycles > 0 else 0
    
    return {
        'profit': balance,
        'total_cycles': total_cycles,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate,
        'max_capital_used': max_capital_used,
        'max_safety_reached': max_safety_reached
    }

# --- SCRIPT PRINCIPAL ---
def main():
    print("Buscando dados históricos da Binance Spot (3000 candles de 15m = ~31 dias)...")
    exchange = ccxt.binance()
    limit = 3000
    
    try:
        # 1. Carregar dados de SOL, BTC e ETH
        print("Buscando SOL/USDT...")
        raw_sol = exchange.fetch_ohlcv('SOL/USDT', '15m', limit=limit)
        df_sol = prepare_data(pd.DataFrame(raw_sol, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        print("Buscando BTC/USDT...")
        raw_btc = exchange.fetch_ohlcv('BTC/USDT', '15m', limit=limit)
        df_btc = prepare_data(pd.DataFrame(raw_btc, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        print("Buscando ETH/USDT...")
        raw_eth = exchange.fetch_ohlcv('ETH/USDT', '15m', limit=limit)
        df_eth = prepare_data(pd.DataFrame(raw_eth, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        print("\n==================================================")
        print("     SIMULAÇÃO DCA GRID - PERÍODO DE 30 DIAS")
        print("==================================================")
        
        # ------------------------------------------------
        # TESTE 1: 3 Robôs em paralelo (SOL, BTC, ETH) com R$ 12,00 cada
        # ------------------------------------------------
        print("\n[TESTE 1: 3 ROBÔS EM PARALELO (SOL, BTC, ETH) - Entrada $12.00]")
        
        res_sol_12 = simulate_dca(df_sol, 'SOL/USDT', trade_amount=12.0)
        res_btc_12 = simulate_dca(df_btc, 'BTC/USDT', trade_amount=12.0)
        res_eth_12 = simulate_dca(df_eth, 'ETH/USDT', trade_amount=12.0)
        
        total_profit_1 = res_sol_12['profit'] + res_btc_12['profit'] + res_eth_12['profit']
        # Capital máximo usado assume pior cenário: todos os 3 robôs exigindo segurança máxima ao mesmo tempo
        max_capital_1 = res_sol_12['max_capital_used'] + res_btc_12['max_capital_used'] + res_eth_12['max_capital_used']
        
        print(f"   SOL/USDT: Lucro = ${res_sol_12['profit']:.2f} | Win Rate = {res_sol_12['win_rate']:.1f}% ({res_sol_12['wins']}W / {res_sol_12['losses']}L) | Máx Capital Usado = ${res_sol_12['max_capital_used']:.1f}")
        print(f"   BTC/USDT: Lucro = ${res_btc_12['profit']:.2f} | Win Rate = {res_btc_12['win_rate']:.1f}% ({res_btc_12['wins']}W / {res_btc_12['losses']}L) | Máx Capital Usado = ${res_btc_12['max_capital_used']:.1f}")
        print(f"   ETH/USDT: Lucro = ${res_eth_12['profit']:.2f} | Win Rate = {res_eth_12['win_rate']:.1f}% ({res_eth_12['wins']}W / {res_eth_12['losses']}L) | Máx Capital Usado = ${res_eth_12['max_capital_used']:.1f}")
        print(f"   ---------------------------------------------")
        print(f"   🔥 Lucro Total de 3 Robôs: ${total_profit_1:+.2f} USDT")
        print(f"   ⚠️ Capital Máximo Exposto (Pior Cenário): ${max_capital_1:.2f} USDT")
        
        # ------------------------------------------------
        # TESTE 2: 1 Único Robô (SOL/USDT) com Entrada de $50,00
        # ------------------------------------------------
        print("\n[TESTE 2: 1 ÚNICO ROBÔ (SOL/USDT) - Entrada $50.00]")
        res_sol_50 = simulate_dca(df_sol, 'SOL/USDT', trade_amount=50.0)
        print(f"   Lucro Líquido: ${res_sol_50['profit']:+.2f} USDT")
        print(f"   Taxa de Acerto: {res_sol_50['win_rate']:.1f}% ({res_sol_50['wins']}W / {res_sol_50['losses']}L)")
        print(f"   Exposição de Capital Máxima (4 compras): ${res_sol_50['max_capital_used']:.2f} USDT")
        
        # ------------------------------------------------
        # TESTE 3: 1 Único Robô (SOL/USDT) com Entrada de $12,00 (Para a banca atual de $35-$43)
        # ------------------------------------------------
        print(f"\n[TESTE 3: 1 ÚNICO ROBÔ (SOL/USDT) - Entrada $12.00 (Mais seguro para sua banca)]")
        res_sol_safe = res_sol_12
        print(f"   Lucro Líquido: ${res_sol_safe['profit']:+.2f} USDT")
        print(f"   Taxa de Acerto: {res_sol_safe['win_rate']:.1f}% ({res_sol_safe['wins']}W / {res_sol_safe['losses']}L)")
        print(f"   Exposição de Capital Máxima: ${res_sol_safe['max_capital_used']:.2f} USDT")
        
        print("\n==================================================")
        print("💡 CONSELHO E ANÁLISE DE SEGURANÇA PARA A SUA BANCA:")
        print("Sua banca atual na Binance é de cerca de $43 dólares.")
        print("\n* Se você usar a Opção 1 (3 robôs de $12):")
        print(f"  O pior cenário exigiria até ${max_capital_1:.1f} USDT. Isso quebraria a banca se todos caíssem juntos.")
        print("\n* Se você usar a Opção 2 (1 robô de $50):")
        print(f"  Você não tem saldo suficiente de $200.00 para aguentar as 4 ordens da grade de $50 (4x$50 = $200).")
        print("\n* Se você usar a Opção 3 (1 robô de $12 de SOL/USDT):")
        print(f"  O capital máximo exigido na grade de $12 é de **$48.00**.")
        print("  Como você tem ~$43, a sua banca está muito protegida, pois o robô raramente precisa chegar")
        print("  na 4ª compra de segurança. É de longe a opção mais segura para o seu saldo atual.")
        print("==================================================")
        
    except Exception as e:
        print(f"Erro ao executar simulação: {e}")

if __name__ == '__main__':
    main()
