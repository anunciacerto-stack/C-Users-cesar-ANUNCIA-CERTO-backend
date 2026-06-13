import os
import sys
import ccxt
import pandas as pd
import numpy as np
import urllib.request
import json
import datetime
from dotenv import load_dotenv

# UTF-8 for Windows output console
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

load_dotenv()

# Strategy Configuration (Bollinger + RSI Mean Reversion)
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

# Fetch USD/BRL Rates from AwesomeAPI
def fetch_usd_brl_rates():
    url = "https://economia.awesomeapi.com.br/json/daily/USD-BRL/50"
    try:
        res = urllib.request.urlopen(url).read()
        data = json.loads(res)
        rates = {}
        for item in data:
            ts = int(item['timestamp'])
            dt = datetime.datetime.fromtimestamp(ts)
            date_str = dt.strftime('%Y-%m-%d')
            rates[date_str] = float(item['bid'])
        return rates
    except Exception as e:
        print(f"Erro ao buscar taxas de câmbio via API: {e}. Usando fallback histórico.")
        # Fallback rates matching the last 40 days
        return {
            "2026-06-12": 5.0852,
            "2026-06-11": 5.1137,
            "2026-06-10": 5.1922,
            "2026-06-09": 5.1845,
            "2026-06-08": 5.1826,
            "2026-06-07": 5.1769,
            "2026-06-05": 5.1671,
            "2026-06-04": 5.0607,
            "2026-06-03": 5.0774,
            "2026-06-02": 5.0207,
            "2026-06-01": 5.0384,
            "2026-05-31": 5.0393,
            "2026-05-29": 5.0321,
            "2026-05-28": 5.0517,
            "2026-05-27": 5.0729,
            "2026-05-26": 5.0445,
            "2026-05-25": 5.0100,
            "2026-05-24": 5.0275,
            "2026-05-22": 5.0294,
            "2026-05-21": 5.0174,
            "2026-05-20": 5.0119,
            "2026-05-19": 5.0581,
            "2026-05-18": 5.0079,
            "2026-05-17": 5.0606,
            "2026-05-15": 5.0518,
            "2026-05-14": 5.0040,
            "2026-05-13": 5.0052,
            "2026-05-12": 4.9095,
            "2026-05-11": 4.9064,
            "2026-05-10": 4.9133,
            "2026-05-08": 4.9094,
            "2026-05-07": 4.9419,
            "2026-05-06": 4.9323,
            "2026-05-05": 4.9273,
            "2026-05-04": 4.9849,
            "2026-05-03": 4.9565,
            "2026-05-02": 4.9489,
            "2026-05-01": 4.9913,
            "2026-04-30": 4.9694,
            "2026-04-29": 5.0175,
        }

def get_rate_for_timestamp(ts_ms, rates):
    dt = datetime.datetime.fromtimestamp(ts_ms / 1000)
    date_str = dt.strftime('%Y-%m-%d')
    if date_str in rates:
        return rates[date_str]
    
    # Nearest previous available rate
    available_dates = sorted(rates.keys())
    selected_rate = 5.08
    for d in available_dates:
        if d <= date_str:
            selected_rate = rates[d]
        else:
            break
    return selected_rate

def run_real_exchange_simulation(df_sol, df_btc, df_eth, initial_capital_brl, rates):
    # Determine initial exchange rate based on the first candle timestamp
    start_ts = int(df_sol.iloc[50]['ts'])
    start_rate = get_rate_for_timestamp(start_ts, rates)
    
    # Convert initial BRL capital to USD
    capital_usd = initial_capital_brl / start_rate
    initial_capital_usd = capital_usd
    
    bots = {
        'SOL': {'df': df_sol, 'in_pos': False, 'entry': 0.0, 'qty': 0.0, 'sl': 0.0},
        'BTC': {'df': df_btc, 'in_pos': False, 'entry': 0.0, 'qty': 0.0, 'sl': 0.0},
        'ETH': {'df': df_eth, 'in_pos': False, 'entry': 0.0, 'qty': 0.0, 'sl': 0.0}
    }
    
    total_trades = 0
    wins = 0
    losses = 0
    
    # Main simulation loop
    for i in range(50, len(df_sol)):
        # Size per trade is 25% of current USD balance
        trade_amount = capital_usd * 0.25
        
        # Ensure Binance minimum size of $12
        trade_amount = max(trade_amount, 12.0)
        
        for coin, bot in bots.items():
            df = bot['df']
            c_last = df.iloc[i-1]
            c_current = df.iloc[i]
            
            if bot['in_pos']:
                # Take Profit (touched Middle Bollinger Band)
                if c_current['high'] >= c_last['bb_middle']:
                    tp_price = c_last['bb_middle']
                    profit = (tp_price - bot['entry']) * bot['qty']
                    capital_usd += profit
                    total_trades += 1
                    wins += 1
                    bot['in_pos'] = False
                # Stop Loss
                elif c_current['low'] <= bot['sl']:
                    loss = (bot['entry'] - bot['sl']) * bot['qty']
                    capital_usd -= loss
                    total_trades += 1
                    losses += 1
                    bot['in_pos'] = False
            else:
                # Buy Entry Signal
                cond_bb = c_last['close'] < c_last['bb_lower']
                cond_rsi = c_last['rsi'] < CONFIG['rsi_buy_level']
                
                if cond_bb and cond_rsi and capital_usd > trade_amount:
                    bot['entry'] = c_current['open']
                    atr = c_last['atr']
                    bot['sl'] = bot['entry'] - (CONFIG['atr_stop_mult'] * atr)
                    bot['qty'] = trade_amount / bot['entry']
                    bot['in_pos'] = True
                    
    # End rate
    end_ts = int(df_sol.iloc[-1]['ts'])
    end_rate = get_rate_for_timestamp(end_ts, rates)
    
    # Final BRL capital based on final USD capital * ending exchange rate
    final_capital_brl = capital_usd * end_rate
    profit_brl = final_capital_brl - initial_capital_brl
    yield_brl_pct = (profit_brl / initial_capital_brl) * 100
    
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    return {
        'initial_rate': start_rate,
        'end_rate': end_rate,
        'final_capital_brl': final_capital_brl,
        'profit_brl': profit_brl,
        'yield_brl_pct': yield_brl_pct,
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses,
        'win_rate': win_rate
    }

def main():
    print("Obtendo taxas reais diárias de USD/BRL...")
    rates = fetch_usd_brl_rates()
    
    print("Obtendo dados de mercado da Binance (SOL, BTC, ETH)...")
    exchange = ccxt.binance()
    limit = 3000
    
    try:
        raw_sol = exchange.fetch_ohlcv('SOL/USDT', '15m', limit=limit)
        df_sol = prepare_data(pd.DataFrame(raw_sol, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        raw_btc = exchange.fetch_ohlcv('BTC/USDT', '15m', limit=limit)
        df_btc = prepare_data(pd.DataFrame(raw_btc, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        raw_eth = exchange.fetch_ohlcv('ETH/USDT', '15m', limit=limit)
        df_eth = prepare_data(pd.DataFrame(raw_eth, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        print("\n==========================================================================================")
        print("          TABELA DE SIMULACAO DE RENDIMENTO REAL EM REAIS (COM CAMBIO DIARIO)")
        print("          Estratégia: Bollinger + RSI | 3 Bots (SOL, BTC, ETH) | 30 Dias Reais")
        print("==========================================================================================")
        print(f"{'Cap. Inicial BRL':<17} | {'Cambio Inicio':<13} | {'Cambio Fim':<11} | {'Lucro Liquido BRL':<20} | {'Cap. Final BRL':<17} | {'Retorno BRL %':<13}")
        print("-" * 106)
        
        # Markdown table container for printing
        md_rows = []
        
        for cap_brl in range(500, 5500, 500):
            res = run_real_exchange_simulation(df_sol, df_btc, df_eth, cap_brl, rates)
            
            cap_str = f"R$ {cap_brl:.2f}"
            start_rate_str = f"{res['initial_rate']:.4f}"
            end_rate_str = f"{res['end_rate']:.4f}"
            profit_str = f"R$ {res['profit_brl']:+.2f}"
            final_str = f"R$ {res['final_capital_brl']:.2f}"
            yield_str = f"{res['yield_brl_pct']:+.2f}%"
            
            print(f"{cap_str:<17} | {start_rate_str:<13} | {end_rate_str:<11} | {profit_str:<20} | {final_str:<17} | {yield_str:<13}")
            
            # Save for markdown formatting
            md_rows.append(f"| {cap_str} | {start_rate_str} | {end_rate_str} | **{profit_str}** | **{final_str}** | **{yield_str}** |")
            
        print("==========================================================================================")
        print(f"Estatísticas dos trades: {res['total_trades']} trades | {res['wins']} Vitórias | {res['losses']} Derrotas | Win Rate: {res['win_rate']:.1f}%")
        print("==========================================================================================")
        
        # Also print raw markdown format for copy-pasting to mural
        print("\n--- FORMATO TABELA MARKDOWN PARA O MURAL ---")
        print("| Capital Inicial | Câmbio Entrada | Câmbio Saída | Lucro Líquido Real | Capital Final Real | Retorno (%) |")
        print("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for row in md_rows:
            print(row)
        print("--------------------------------------------")
        
    except Exception as e:
        print(f"Erro ao executar simulação: {e}")

if __name__ == '__main__':
    main()
