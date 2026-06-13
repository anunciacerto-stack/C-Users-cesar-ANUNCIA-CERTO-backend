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

# Configuração Original Defensiva
CONFIG = {
    'supertrend_period': 10,
    'supertrend_mult': 3.0,
    'rsi_period': 14,
    'rsi_low': 45,
    'rsi_high': 55,
    'atr_period': 14,
    'atr_stop_mult': 1.5,
    'atr_tp1_mult': 2.0,
    'atr_tp2_mult': 3.5,
    'partial_exit_pct': 0.5,
    'volume_filter': True,
    'volume_mult': 1.2
}

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

def prepare_data(df, config):
    df = calc_supertrend(df, config['supertrend_period'], config['supertrend_mult'])
    df['rsi'] = calc_rsi(df['close'], config['rsi_period'])
    df['atr'] = calc_atr(df, config['atr_period'])
    df['vol_ma'] = df['volume'].rolling(20).mean()
    return df

def run_backtest(df_raw, config, initial_balance=100.0, trade_amount=12.0):
    df = prepare_data(df_raw.copy(), config)
    
    balance = initial_balance
    in_position = False
    entry_price = 0.0
    qty = 0.0
    stop_loss = 0.0
    tp1 = 0.0
    tp2 = 0.0
    is_partial_executed = False
    
    trades_log = []
    
    for i in range(50, len(df)):
        c_last = df.iloc[i-1]
        c_current = df.iloc[i]
        
        if in_position:
            # SL
            if c_current['low'] <= stop_loss:
                loss = (entry_price - stop_loss) * qty
                balance -= loss
                trades_log.append({'type': 'LOSS', 'profit_usd': -loss})
                in_position = False
                is_partial_executed = False
                continue
                
            # TP1 (Parcial)
            if not is_partial_executed and c_current['high'] >= tp1:
                p_qty = qty * config['partial_exit_pct']
                partial_profit = (tp1 - entry_price) * p_qty
                balance += partial_profit
                stop_loss = entry_price # Breakeven
                is_partial_executed = True
                qty -= p_qty
                
            # TP2 (Final)
            if c_current['high'] >= tp2:
                profit = (tp2 - entry_price) * qty
                balance += profit
                trades_log.append({'type': 'WIN_TP2', 'profit_usd': profit})
                in_position = False
                is_partial_executed = False
                continue
                
            # Saída Técnica
            if c_last['st_direction'] == -1:
                exit_price = c_current['open']
                profit = (exit_price - entry_price) * qty
                balance += profit
                trades_log.append({'type': 'TECH_EXIT', 'profit_usd': profit})
                in_position = False
                is_partial_executed = False
                continue
        else:
            # Sinais de entrada
            cond_st = c_last['st_direction'] == 1
            cond_rsi = 25 < c_last['rsi'] < config['rsi_low']
            cond_vol = c_last['volume'] >= c_last['vol_ma'] * config['volume_mult']
            
            if cond_st and cond_rsi and cond_vol:
                entry_price = c_current['open']
                atr = c_last['atr']
                
                stop_loss = entry_price - (config['atr_stop_mult'] * atr)
                tp1 = entry_price + (config['atr_tp1_mult'] * atr)
                tp2 = entry_price + (config['atr_tp2_mult'] * atr)
                
                qty = trade_amount / entry_price
                in_position = True
                is_partial_executed = False
                
    total_trades = len(trades_log)
    if total_trades == 0:
        return {'profit': 0.0, 'win_rate': 0.0, 'total': 0, 'wins': 0, 'losses': 0}
        
    wins = sum(1 for t in trades_log if t['profit_usd'] > 0)
    losses = sum(1 for t in trades_log if t['profit_usd'] <= 0)
    win_rate = (wins / total_trades) * 100
    
    return {
        'profit': balance - initial_balance,
        'win_rate': win_rate,
        'total': total_trades,
        'wins': wins,
        'losses': losses
    }

def main():
    print("Iniciando comparativo de timeframes no backtest...")
    exchange = ccxt.binance()
    
    # 1. Obter 1000 candles de 15m (~10 dias)
    print("Buscando dados de 15m (1000 candles)...")
    candles_15m = exchange.fetch_ohlcv('SOL/USDT', '15m', limit=1000)
    df_15m = pd.DataFrame(candles_15m, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
    
    # 2. Obter 3000 candles de 5m (mesmo período de ~10 dias)
    print("Buscando dados de 5m (3000 candles)...")
    candles_5m = exchange.fetch_ohlcv('SOL/USDT', '5m', limit=3000)
    df_5m = pd.DataFrame(candles_5m, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
    
    print("\n==================================================")
    print("      TESTE DE TIMEFRAME: 15 MINUTOS vs 5 MINUTOS")
    print("        Par: SOL/USDT | Periodo: ~10 dias")
    print("==================================================")
    
    # Executa backtest de 15m
    res_15m = run_backtest(df_15m, CONFIG, initial_balance=100.0, trade_amount=12.0)
    print("\n[TIMEFRAME DE 15 MINUTOS (PADRAO)]:")
    print(f"   - Lucro Liquido: ${res_15m['profit']:.2f} USDT")
    print(f"   - Taxa de Acerto (Win Rate): {res_15m['win_rate']:.1f}%")
    print(f"   - Total de Trades: {res_15m['total']}")
    print(f"     (Wins: {res_15m['wins']} | Losses: {res_15m['losses']})")
    
    # Executa backtest de 5m
    res_5m = run_backtest(df_5m, CONFIG, initial_balance=100.0, trade_amount=12.0)
    print("\n[TIMEFRAME DE 5 MINUTOS (RAPIDO)]:")
    print(f"   - Lucro Liquido: ${res_5m['profit']:.2f} USDT")
    print(f"   - Taxa de Acerto (Win Rate): {res_5m['win_rate']:.1f}%")
    print(f"   - Total de Trades: {res_5m['total']}")
    print(f"     (Wins: {res_5m['wins']} | Losses: {res_5m['losses']})")
    
    print("\n==================================================")
    print("💡 ANALISE:")
    print(f"O gráfico de 5m gerou {res_5m['total']} trades, enquanto o de 15m gerou {res_15m['total']} trades.")
    if res_5m['profit'] < res_15m['profit']:
        print("Sua intuição de que '5m arrisca demais' esta correta. O de 15m deu melhor resultado financeiro.")
    else:
        print("No curto prazo testado, o grafico de 5m teve melhor desempenho, mas operou mais vezes.")
    print("==================================================")

if __name__ == '__main__':
    main()
