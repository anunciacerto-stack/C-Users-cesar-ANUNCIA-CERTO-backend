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

# --- CÁLCULO DE INDICADORES ---
def calc_atr(df, period=14):
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

def calc_supertrend(df, period=10, multiplier=3.0):
    hl2 = (df['high'] + df['low']) / 2
    atr = calc_atr(df, period)
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr
    
    n = len(df)
    upper = basic_upper.copy()
    lower = basic_lower.copy()
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(1, n):
        if basic_upper.iloc[i] < upper.iloc[i-1] or df['close'].iloc[i-1] > upper.iloc[i-1]:
            upper.iloc[i] = basic_upper.iloc[i]
        else:
            upper.iloc[i] = upper.iloc[i-1]
            
        if basic_lower.iloc[i] > lower.iloc[i-1] or df['close'].iloc[i-1] < lower.iloc[i-1]:
            lower.iloc[i] = basic_lower.iloc[i]
        else:
            lower.iloc[i] = lower.iloc[i-1]
            
        if supertrend.isna().iloc[i-1]:
            direction.iloc[i] = 1
            supertrend.iloc[i] = lower.iloc[i]
        elif supertrend.iloc[i-1] == upper.iloc[i-1]:
            if df['close'].iloc[i] > upper.iloc[i]:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lower.iloc[i]
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upper.iloc[i]
        else:
            if df['close'].iloc[i] < lower.iloc[i]:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upper.iloc[i]
            else:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lower.iloc[i]
                
    df['supertrend'] = supertrend
    df['st_direction'] = direction
    return df

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(span=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=period, adjust=False).mean()
    return 100 - (100 / (1 + gain / (loss + 1e-9)))

def prepare_data(df):
    df['rsi'] = calc_rsi(df['close'], 14)
    df['atr'] = calc_atr(df, 14)
    df = calc_supertrend(df, 10, 3.0)
    return df

# --- ESTRATÉGIA A: DCA Padrão (Sem filtro, grade 2%) ---
def run_dca_standard(df, trade_amount=12.0):
    balance = 0.0
    in_cycle = False
    orders = []
    trades_log = []
    
    max_capital = 0.0
    
    for i in range(50, len(df)):
        c_current = df.iloc[i]
        
        if in_cycle:
            total_qty = sum(o['qty'] for o in orders)
            total_value = sum(o['value'] for o in orders)
            avg_price = total_value / total_qty
            
            if total_value > max_capital:
                max_capital = total_value
                
            tp_price = avg_price * 1.010 # 1.0% lucro
            
            if c_current['high'] >= tp_price:
                profit = (tp_price - avg_price) * total_qty
                balance += profit
                trades_log.append({'type': 'WIN', 'profit_usd': profit})
                in_cycle = False
                orders = []
                continue
                
            if len(orders) <= 3:
                last_order_price = orders[-1]['price']
                trigger_price = last_order_price * 0.98 # Queda de 2%
                if c_current['low'] <= trigger_price:
                    orders.append({'price': trigger_price, 'qty': trade_amount / trigger_price, 'value': trade_amount})
                    continue
                    
            if len(orders) == 4:
                sl_price = orders[-1]['price'] * 0.97 # Stop 3% abaixo da 4ª
                if c_current['low'] <= sl_price:
                    loss = (avg_price - sl_price) * total_qty
                    balance -= loss
                    trades_log.append({'type': 'LOSS', 'profit_usd': -loss})
                    in_cycle = False
                    orders = []
                    continue
        else:
            entry_price = c_current['open']
            orders.append({'price': entry_price, 'qty': trade_amount / entry_price, 'value': trade_amount})
            in_cycle = True
            
    total = len(trades_log)
    wins = sum(1 for t in trades_log if t['profit_usd'] > 0)
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0
    return {'profit': balance, 'win_rate': win_rate, 'total': total, 'wins': wins, 'losses': losses, 'max_capital': max_capital}

# --- ESTRATÉGIA B: DCA com Filtro Trend (Só entra se SuperTrend = 1) ---
def run_dca_trend_filtered(df, trade_amount=12.0):
    balance = 0.0
    in_cycle = False
    orders = []
    trades_log = []
    
    max_capital = 0.0
    
    for i in range(50, len(df)):
        c_last = df.iloc[i-1]
        c_current = df.iloc[i]
        
        if in_cycle:
            total_qty = sum(o['qty'] for o in orders)
            total_value = sum(o['value'] for o in orders)
            avg_price = total_value / total_qty
            
            if total_value > max_capital:
                max_capital = total_value
                
            tp_price = avg_price * 1.010
            
            if c_current['high'] >= tp_price:
                profit = (tp_price - avg_price) * total_qty
                balance += profit
                trades_log.append({'type': 'WIN', 'profit_usd': profit})
                in_cycle = False
                orders = []
                continue
                
            if len(orders) <= 3:
                last_order_price = orders[-1]['price']
                trigger_price = last_order_price * 0.98
                if c_current['low'] <= trigger_price:
                    orders.append({'price': trigger_price, 'qty': trade_amount / trigger_price, 'value': trade_amount})
                    continue
                    
            if len(orders) == 4:
                sl_price = orders[-1]['price'] * 0.97
                if c_current['low'] <= sl_price:
                    loss = (avg_price - sl_price) * total_qty
                    balance -= loss
                    trades_log.append({'type': 'LOSS', 'profit_usd': -loss})
                    in_cycle = False
                    orders = []
                    continue
        else:
            # Só inicia ciclo se SuperTrend estiver verde (alta)
            if c_last['st_direction'] == 1:
                entry_price = c_current['open']
                orders.append({'price': entry_price, 'qty': trade_amount / entry_price, 'value': trade_amount})
                in_cycle = True
            
    total = len(trades_log)
    wins = sum(1 for t in trades_log if t['profit_usd'] > 0)
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0
    return {'profit': balance, 'win_rate': win_rate, 'total': total, 'wins': wins, 'losses': losses, 'max_capital': max_capital}

# --- ESTRATÉGIA C: DCA Larga (Sem filtro, grade de 3.5%) ---
def run_dca_wide_grid(df, trade_amount=12.0):
    balance = 0.0
    in_cycle = False
    orders = []
    trades_log = []
    
    max_capital = 0.0
    
    for i in range(50, len(df)):
        c_current = df.iloc[i]
        
        if in_cycle:
            total_qty = sum(o['qty'] for o in orders)
            total_value = sum(o['value'] for o in orders)
            avg_price = total_value / total_qty
            
            if total_value > max_capital:
                max_capital = total_value
                
            tp_price = avg_price * 1.010
            
            if c_current['high'] >= tp_price:
                profit = (tp_price - avg_price) * total_qty
                balance += profit
                trades_log.append({'type': 'WIN', 'profit_usd': profit})
                in_cycle = False
                orders = []
                continue
                
            if len(orders) <= 3:
                last_order_price = orders[-1]['price']
                trigger_price = last_order_price * 0.965 # Queda de 3.5%
                if c_current['low'] <= trigger_price:
                    orders.append({'price': trigger_price, 'qty': trade_amount / trigger_price, 'value': trade_amount})
                    continue
                    
            if len(orders) == 4:
                sl_price = orders[-1]['price'] * 0.97
                if c_current['low'] <= sl_price:
                    loss = (avg_price - sl_price) * total_qty
                    balance -= loss
                    trades_log.append({'type': 'LOSS', 'profit_usd': -loss})
                    in_cycle = False
                    orders = []
                    continue
        else:
            entry_price = c_current['open']
            orders.append({'price': entry_price, 'qty': trade_amount / entry_price, 'value': trade_amount})
            in_cycle = True
            
    total = len(trades_log)
    wins = sum(1 for t in trades_log if t['profit_usd'] > 0)
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0
    return {'profit': balance, 'win_rate': win_rate, 'total': total, 'wins': wins, 'losses': losses, 'max_capital': max_capital}

def main():
    print("Iniciando comparativo das 3 variantes do DCA (30 dias)...")
    exchange = ccxt.binance()
    limit = 3000
    
    try:
        print("Buscando dados históricos de SOL/USDT...")
        raw_sol = exchange.fetch_ohlcv('SOL/USDT', '15m', limit=limit)
        df_sol = prepare_data(pd.DataFrame(raw_sol, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        print("\n==================================================")
        print("      COMPARATIVO DE VARIANTES DCA (30 DIAS)")
        print("          SOL/USDT | Gráfico: 15 minutos")
        print("==================================================")
        
        # 1. Padrão
        res_std = run_dca_standard(df_sol, trade_amount=12.0)
        print("\n📊 VARIANTE 1: DCA PADRÃO (Grade 2%, Sem Filtro)")
        print(f"   - Lucro Líquido: ${res_std['profit']:+.2f} USDT")
        print(f"   - Taxa de Acerto: {res_std['win_rate']:.1f}%")
        print(f"   - Total de Trades: {res_std['total']} (Wins: {res_std['wins']} | Losses: {res_std['losses']})")
        print(f"   - Capital Máximo Exposto: ${res_std['max_capital']:.1f} USDT")
        
        # 2. Filtrada por tendência
        res_filt = run_dca_trend_filtered(df_sol, trade_amount=12.0)
        print("\n🛡️ VARIANTE 2: DCA COM FILTRO DE TENDÊNCIA (Só opera em alta)")
        print(f"   - Lucro Líquido: ${res_filt['profit']:+.2f} USDT")
        print(f"   - Taxa de Acerto: {res_filt['win_rate']:.1f}%")
        print(f"   - Total de Trades: {res_filt['total']} (Wins: {res_filt['wins']} | Losses: {res_filt['losses']})")
        print(f"   - Capital Máximo Exposto: ${res_filt['max_capital']:.1f} USDT")
        
        # 3. Grade larga
        res_wide = run_dca_wide_grid(df_sol, trade_amount=12.0)
        print("\n⚡ VARIANTE 3: DCA GRADE LARGA (Grade 3.5%, Sem Filtro)")
        print(f"   - Lucro Líquido: ${res_wide['profit']:+.2f} USDT")
        print(f"   - Taxa de Acerto: {res_wide['win_rate']:.1f}%")
        print(f"   - Total de Trades: {res_wide['total']} (Wins: {res_wide['wins']} | Losses: {res_wide['losses']})")
        print(f"   - Capital Máximo Exposto: ${res_wide['max_capital']:.1f} USDT")
        
        print("\n==================================================")
        print("💡 CONCLUSAO:")
        profits = {'DCA Padrao': res_std['profit'], 'DCA Filtrado': res_filt['profit'], 'DCA Grade Larga': res_wide['profit']}
        best = max(profits, key=profits.get)
        print(f"A melhor variante para SOL/USDT foi **{best}** com lucro de ${profits[best]:.2f} USDT.")
        print("==================================================")
        
    except Exception as e:
        print(f"Erro ao executar comparativo: {e}")

if __name__ == '__main__':
    main()
