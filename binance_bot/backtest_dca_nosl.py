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

# Parâmetros de DCA Grid sem Stop Loss
DCA_CONFIG = {
    'max_safety_orders': 3,     # Total de 4 compras (Base + 3 Seguranças)
    'dca_step_pct': 0.02,       # Compra a cada 2% de queda
    'profit_target_pct': 0.010  # 1.0% de lucro sobre o preço médio do ciclo
}

def calc_atr(df, period=14):
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(span=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=period, adjust=False).mean()
    return 100 - (100 / (1 + gain / (loss + 1e-9)))

def prepare_data(df):
    df['rsi'] = calc_rsi(df['close'], 14)
    df['atr'] = calc_atr(df, 14)
    return df

def run_dca_no_stoploss(df, trade_amount=12.0):
    balance = 0.0
    in_cycle = False
    orders = []
    trades_log = []
    
    max_capital = 0.0
    days_stuck = 0
    cycle_start_idx = 0
    max_days_stuck = 0
    
    for i in range(50, len(df)):
        c_current = df.iloc[i]
        
        if in_cycle:
            total_qty = sum(o['qty'] for o in orders)
            total_value = sum(o['value'] for o in orders)
            avg_price = total_value / total_qty
            
            if total_value > max_capital:
                max_capital = total_value
                
            tp_price = avg_price * (1 + DCA_CONFIG['profit_target_pct'])
            
            # Check Take Profit
            if c_current['high'] >= tp_price:
                profit = (tp_price - avg_price) * total_qty
                balance += profit
                
                # Calcular quantos dias ficou "preso" nesse ciclo
                candles_stuck = i - cycle_start_idx
                days_stuck_this_cycle = (candles_stuck * 15) / (24 * 60) # Cada candle tem 15m
                if days_stuck_this_cycle > max_days_stuck:
                    max_days_stuck = days_stuck_this_cycle
                    
                trades_log.append({
                    'type': 'WIN',
                    'profit_usd': profit,
                    'days_stuck': days_stuck_this_cycle
                })
                in_cycle = False
                orders = []
                continue
                
            # Check se precisa de safety order
            if len(orders) <= DCA_CONFIG['max_safety_orders']:
                last_order_price = orders[-1]['price']
                trigger_price = last_order_price * (1 - DCA_CONFIG['dca_step_pct'])
                
                if c_current['low'] <= trigger_price:
                    orders.append({
                        'price': trigger_price,
                        'qty': trade_amount / trigger_price,
                        'value': trade_amount
                    })
                    continue
        else:
            # Inicia ciclo
            entry_price = c_current['open']
            orders.append({
                'price': entry_price,
                'qty': trade_amount / entry_price,
                'value': trade_amount
            })
            in_cycle = True
            cycle_start_idx = i
            
    # Se terminou o período no meio de um ciclo
    if in_cycle:
        total_qty = sum(o['qty'] for o in orders)
        total_value = sum(o['value'] for o in orders)
        avg_price = total_value / total_qty
        current_price = df.iloc[-1]['close']
        unrealized_profit = (current_price - avg_price) * total_qty
        balance += unrealized_profit # Lucro flutuante (positivo ou negativo)
        
    total = len(trades_log)
    wins = sum(1 for t in trades_log if t['profit_usd'] > 0)
    
    return {
        'profit': balance,
        'win_rate': 100.0 if total > 0 else 0,
        'total': total,
        'wins': wins,
        'losses': 0,
        'max_capital': max_capital,
        'max_days_stuck': max_days_stuck,
        'still_open': in_cycle
    }

def main():
    print("Iniciando simulação DCA sem Stop Loss (30 dias)...")
    exchange = ccxt.binance()
    limit = 3000
    
    try:
        print("Buscando dados de SOL, BTC e ETH...")
        raw_sol = exchange.fetch_ohlcv('SOL/USDT', '15m', limit=limit)
        df_sol = prepare_data(pd.DataFrame(raw_sol, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        raw_btc = exchange.fetch_ohlcv('BTC/USDT', '15m', limit=limit)
        df_btc = prepare_data(pd.DataFrame(raw_btc, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        raw_eth = exchange.fetch_ohlcv('ETH/USDT', '15m', limit=limit)
        df_eth = prepare_data(pd.DataFrame(raw_eth, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        print("\n==================================================")
        print("    DCA GRID SEM STOP LOSS - SPOT (30 DIAS)")
        print("      SOL/USDT | BTC/USDT | ETH/USDT (15m)")
        print("==================================================")
        
        # SOL
        res_sol = run_dca_no_stoploss(df_sol, trade_amount=12.0)
        print(f"\n🪙 SOL/USDT (Entrada $12.00):")
        print(f"   - Lucro Liquido Final: ${res_sol['profit']:+.2f} USDT")
        print(f"   - Ciclos de Lucro Finalizados: {res_sol['total']} (Taxa de acerto: {res_sol['win_rate']:.1f}%)")
        print(f"   - Capital Maximo Exposto: ${res_sol['max_capital']:.1f} USDT")
        print(f"   - Tempo Maximo Preso em um ciclo: {res_sol['max_days_stuck']:.1f} dias")
        print(f"   - Ficou com ciclo aberto no final? {'Sim' if res_sol['still_open'] else 'Nao'}")
        
        # BTC
        res_btc = run_dca_no_stoploss(df_btc, trade_amount=12.0)
        print(f"\n🪙 BTC/USDT (Entrada $12.00):")
        print(f"   - Lucro Liquido Final: ${res_btc['profit']:+.2f} USDT")
        print(f"   - Ciclos de Lucro Finalizados: {res_btc['total']} (Taxa de acerto: {res_btc['win_rate']:.1f}%)")
        print(f"   - Capital Maximo Exposto: ${res_btc['max_capital']:.1f} USDT")
        print(f"   - Tempo Maximo Preso em um ciclo: {res_btc['max_days_stuck']:.1f} dias")
        print(f"   - Ficou com ciclo aberto no final? {'Sim' if res_btc['still_open'] else 'Nao'}")
        
        # ETH
        res_eth = run_dca_no_stoploss(df_eth, trade_amount=12.0)
        print(f"\n🪙 ETH/USDT (Entrada $12.00):")
        print(f"   - Lucro Liquido Final: ${res_eth['profit']:+.2f} USDT")
        print(f"   - Ciclos de Lucro Finalizados: {res_eth['total']} (Taxa de acerto: {res_eth['win_rate']:.1f}%)")
        print(f"   - Capital Maximo Exposto: ${res_eth['max_capital']:.1f} USDT")
        print(f"   - Tempo Maximo Preso em um ciclo: {res_eth['max_days_stuck']:.1f} dias")
        print(f"   - Ficou com ciclo aberto no final? {'Sim' if res_eth['still_open'] else 'Nao'}")
        
        print("\n==================================================")
        print("🔥 SOMA TOTAL DOS 3 ROBÔS SEM STOP LOSS:")
        total_profit = res_sol['profit'] + res_btc['profit'] + res_eth['profit']
        print(f"   Lucro Liquido Total: ${total_profit:+.2f} USDT")
        print("==================================================")
        
    except Exception as e:
        print(f"Erro ao executar simulacao: {e}")

if __name__ == '__main__':
    main()
