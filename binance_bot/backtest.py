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

# Carrega configurações
load_dotenv()

# Parâmetros das duas estratégias para comparar
CONFIG_ORIGINAL = {
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

CONFIG_MODIFICADA = {
    'supertrend_period': 10,
    'supertrend_mult': 3.0,
    'rsi_period': 14,
    'rsi_low': 50,       # Mais agressivo (entra mais fácil)
    'rsi_high': 55,
    'atr_period': 14,
    'atr_stop_mult': 1.0, # Stop mais curto
    'atr_tp1_mult': 1.5,  # Parcial mais rápida
    'atr_tp2_mult': 3.0,  # TP2 mais curto
    'partial_exit_pct': 0.5,
    'volume_filter': False, # Desativa filtro de volume (opera mais)
    'volume_mult': 1.2
}

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

def prepare_data(df, config):
    df = calc_supertrend(df, config['supertrend_period'], config['supertrend_mult'])
    df['rsi'] = calc_rsi(df['close'], config['rsi_period'])
    df['atr'] = calc_atr(df, config['atr_period'])
    df['vol_ma'] = df['volume'].rolling(20).mean()
    return df

# --- MOTOR DE BACKTEST ---
def run_backtest(df_raw, config, symbol, initial_balance=100.0, trade_amount=12.0):
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
        c_last = df.iloc[i-1] # Candle fechado
        c_current = df.iloc[i] # Candle atual (em andamento)
        
        # 1. GESTÃO DA POSIÇÃO ABERTA
        if in_position:
            # Check Stop Loss
            if c_current['low'] <= stop_loss:
                loss = (entry_price - stop_loss) * qty
                balance -= loss
                trades_log.append({
                    'type': 'LOSS',
                    'entry': entry_price,
                    'exit': stop_loss,
                    'profit_usd': -loss,
                    'profit_pct': -((entry_price - stop_loss) / entry_price * 100)
                })
                in_position = False
                is_partial_executed = False
                continue
                
            # Check TP1 (Parcial)
            if not is_partial_executed and c_current['high'] >= tp1:
                p_qty = qty * config['partial_exit_pct']
                partial_profit = (tp1 - entry_price) * p_qty
                balance += partial_profit
                
                # Regras de defesa do TP1
                stop_loss = entry_price # Breakeven
                is_partial_executed = True
                qty -= p_qty # Reduz tamanho restante
                
            # Check TP2 (Alvo Final)
            if c_current['high'] >= tp2:
                profit = (tp2 - entry_price) * qty
                balance += profit
                trades_log.append({
                    'type': 'WIN (TP2)',
                    'entry': entry_price,
                    'exit': tp2,
                    'profit_usd': profit if not is_partial_executed else (profit + (tp1 - entry_price)*(qty/config['partial_exit_pct'] * config['partial_exit_pct'])),
                    'profit_pct': ((tp2 - entry_price) / entry_price * 100)
                })
                in_position = False
                is_partial_executed = False
                continue
                
            # Check Saída Técnica (SuperTrend inverteu para vermelho)
            if c_last['st_direction'] == -1:
                exit_price = c_current['open'] # Sai na abertura do próximo
                profit = (exit_price - entry_price) * qty
                balance += profit
                trades_log.append({
                    'type': 'TECH_EXIT',
                    'entry': entry_price,
                    'exit': exit_price,
                    'profit_usd': profit,
                    'profit_pct': ((exit_price - entry_price) / entry_price * 100)
                })
                in_position = False
                is_partial_executed = False
                continue

        # 2. PROCURAR SINAL DE ENTRADA
        else:
            # Condições de Compra
            cond_st = c_last['st_direction'] == 1
            cond_rsi = 25 < c_last['rsi'] < config['rsi_low']
            
            # Filtro de Volume
            cond_vol = True
            if config['volume_filter']:
                cond_vol = c_last['volume'] >= c_last['vol_ma'] * config['volume_mult']
                
            if cond_st and cond_rsi and cond_vol:
                entry_price = c_current['open'] # Compra na abertura do candle atual
                atr = c_last['atr']
                
                stop_loss = entry_price - (config['atr_stop_mult'] * atr)
                tp1 = entry_price + (config['atr_tp1_mult'] * atr)
                tp2 = entry_price + (config['atr_tp2_mult'] * atr)
                
                qty = trade_amount / entry_price
                in_position = True
                is_partial_executed = False
                
    # Calcular Estatísticas
    total_trades = len(trades_log)
    if total_trades == 0:
        return {'profit': 0.0, 'win_rate': 0.0, 'total': 0, 'wins': 0, 'losses': 0}
        
    wins = sum(1 for t in trades_log if t['profit_usd'] > 0)
    losses = sum(1 for t in trades_log if t['profit_usd'] <= 0)
    win_rate = (wins / total_trades) * 100
    net_profit = balance - initial_balance
    
    return {
        'profit': net_profit,
        'win_rate': win_rate,
        'total': total_trades,
        'wins': wins,
        'losses': losses
    }

# --- BUSCAR DADOS DO MERCADO E EXECUTAR ---
def main():
    print("Obtendo dados historicos da Binance Spot (1000 candles de 15m)...")
    exchange = ccxt.binance()
    
    try:
        raw_candles = exchange.fetch_ohlcv('SOL/USDT', '15m', limit=1000)
        df_raw = pd.DataFrame(raw_candles, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df_raw['ts'] = pd.to_datetime(df_raw['ts'], unit='ms')
        
        print("\n==================================================")
        print("          RESULTADO DO BACKTEST (SOL/USDT)")
        print("         Periodo Testado: ultimos ~10 dias")
        print("==================================================")
        
        # Teste 1: Configuração Original (Defensiva)
        res_orig = run_backtest(df_raw, CONFIG_ORIGINAL, 'SOL/USDT', initial_balance=100.0, trade_amount=14.0)
        print("\n[ESTRATEGIA ORIGINAL (DEFENSIVA)]:")
        print(f"   - Lucro Liquido: ${res_orig['profit']:.2f} USDT")
        print(f"   - Taxa de Acerto (Win Rate): {res_orig['win_rate']:.1f}%")
        print(f"   - Total de Trades executados: {res_orig['total']}")
        print(f"     (Wins: {res_orig['wins']} | Losses: {res_orig['losses']})")
        
        # Teste 2: Configuração Modificada (Mais Agressiva, Stop Curto)
        res_mod = run_backtest(df_raw, CONFIG_MODIFICADA, 'SOL/USDT', initial_balance=100.0, trade_amount=14.0)
        print("\n[ESTRATEGIA MODIFICADA (AGRESSIVA + STOP CURTO)]:")
        print(f"   - Lucro Liquido: ${res_mod['profit']:.2f} USDT")
        print(f"   - Taxa de Acerto (Win Rate): {res_mod['win_rate']:.1f}%")
        print(f"   - Total de Trades executados: {res_mod['total']}")
        print(f"     (Wins: {res_mod['wins']} | Losses: {res_mod['losses']})")
        
        print("\n==================================================")
        print("💡 CONCLUSAO:")
        if res_orig['profit'] > res_mod['profit']:
            print("A ESTRATEGIA ORIGINAL (DEFENSIVA) foi MAIS LUCRATIVA no periodo de teste.")
        elif res_orig['profit'] < res_mod['profit']:
            print("A ESTRATEGIA MODIFICADA (AGRESSIVA) foi MAIS LUCRATIVA no periodo de teste.")
        else:
            print("Ambas as estrategias tiveram o mesmo resultado financeiro.")
        print("==================================================")
        
    except Exception as e:
        print(f"Erro ao rodar backtest: {e}")

if __name__ == '__main__':
    main()
