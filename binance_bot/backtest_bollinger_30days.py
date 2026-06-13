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

# Configuração Bollinger
CONFIG = {
    'bb_period': 20,
    'bb_std': 2.0,
    'rsi_period': 14,
    'rsi_buy_level': 30,
    'atr_period': 14,
    'atr_stop_mult': 1.5
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

def calc_bollinger_bands(df, period=20, num_std=2):
    sma = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std()
    df['bb_middle'] = sma
    df['bb_upper'] = sma + (num_std * std)
    df['bb_lower'] = sma - (num_std * std)
    return df

def prepare_data(df):
    df['rsi'] = calc_rsi(df['close'], CONFIG['rsi_period'])
    df['atr'] = calc_atr(df, CONFIG['atr_period'])
    df = calc_bollinger_bands(df, CONFIG['bb_period'], CONFIG['bb_std'])
    return df

def run_bollinger_rsi(df, trade_amount=12.0):
    balance = 100.0
    initial_balance = 100.0
    in_position = False
    entry_price = 0.0
    qty = 0.0
    stop_loss = 0.0
    trades_log = []
    
    for i in range(50, len(df)):
        c_last = df.iloc[i-1]
        c_current = df.iloc[i]
        
        if in_position:
            # TP: Toca na linha do meio das Bandas de Bollinger
            if c_current['high'] >= c_last['bb_middle']:
                tp_price = c_last['bb_middle']
                profit = (tp_price - entry_price) * qty
                balance += profit
                trades_log.append({'type': 'WIN', 'profit_usd': profit})
                in_position = False
                continue
            # SL: Preço cai abaixo do Stop Loss
            elif c_current['low'] <= stop_loss:
                loss = (entry_price - stop_loss) * qty
                balance -= loss
                trades_log.append({'type': 'LOSS', 'profit_usd': -loss})
                in_position = False
                continue
        else:
            # Compra: Fechamento abaixo da Banda Inferior e RSI < 30
            if c_last['close'] < c_last['bb_lower'] and c_last['rsi'] < CONFIG['rsi_buy_level']:
                entry_price = c_current['open']
                atr = c_last['atr']
                stop_loss = entry_price - (CONFIG['atr_stop_mult'] * atr)
                qty = trade_amount / entry_price
                in_position = True
                
    total = len(trades_log)
    wins = sum(1 for t in trades_log if t['profit_usd'] > 0)
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0
    return {
        'profit': balance - initial_balance,
        'win_rate': win_rate,
        'total': total,
        'wins': wins,
        'losses': losses
    }

def main():
    print("Iniciando simulação Bollinger + RSI (30 dias)...")
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
        print("    BOLLINGER BANDS + RSI (REVERSÃO À MÉDIA) - 30 DIAS")
        print("      SOL/USDT | BTC/USDT | ETH/USDT (15m)")
        print("==================================================")
        
        res_sol = run_bollinger_rsi(df_sol, trade_amount=12.0)
        print(f"\n🪙 SOL/USDT (Entrada $12.00):")
        print(f"   - Lucro Liquido Final: {res_sol['profit']:+.2f} USDT")
        print(f"   - Taxa de Acerto: {res_sol['win_rate']:.1f}% ({res_sol['wins']}W / {res_sol['losses']}L)")
        
        res_btc = run_bollinger_rsi(df_btc, trade_amount=12.0)
        print(f"\n🪙 BTC/USDT (Entrada $12.00):")
        print(f"   - Lucro Liquido Final: {res_btc['profit']:+.2f} USDT")
        print(f"   - Taxa de Acerto: {res_btc['win_rate']:.1f}% ({res_btc['wins']}W / {res_btc['losses']}L)")
        
        res_eth = run_bollinger_rsi(df_eth, trade_amount=12.0)
        print(f"\n🪙 ETH/USDT (Entrada $12.00):")
        print(f"   - Lucro Liquido Final: {res_eth['profit']:+.2f} USDT")
        print(f"   - Taxa de Acerto: {res_eth['win_rate']:.1f}% ({res_eth['wins']}W / {res_eth['losses']}L)")
        
        print("\n==================================================")
        print("🔥 SOMA TOTAL DOS 3 ROBÔS BOLLINGER+RSI:")
        total_profit = res_sol['profit'] + res_btc['profit'] + res_eth['profit']
        print(f"   Lucro Liquido Total: {total_profit:+.2f} USDT")
        print("==================================================")
        
    except Exception as e:
        print(f"Erro ao executar simulacao: {e}")

if __name__ == '__main__':
    main()
