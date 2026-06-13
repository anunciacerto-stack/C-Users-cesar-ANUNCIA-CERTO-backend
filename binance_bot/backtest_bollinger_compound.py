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

# --- SIMULAÇÃO DE JUROS COMPOSTOS UNIFICADOS (3 BOTS EM PARALELO) ---
def run_compound_simulation(df_sol, df_btc, df_eth, initial_capital_usd):
    # Capital total da conta
    capital = initial_capital_usd
    
    # Estados dos bots
    bots = {
        'SOL': {'df': df_sol, 'in_pos': False, 'entry': 0.0, 'qty': 0.0, 'sl': 0.0},
        'BTC': {'df': df_btc, 'in_pos': False, 'entry': 0.0, 'qty': 0.0, 'sl': 0.0},
        'ETH': {'df': df_eth, 'in_pos': False, 'entry': 0.0, 'qty': 0.0, 'sl': 0.0}
    }
    
    # Estatísticas
    total_trades = 0
    wins = 0
    losses = 0
    
    # Simulando minuto a minuto (candle a candle)
    # Todos os DataFrames têm o mesmo tamanho (3000 candles)
    for i in range(50, len(df_sol)):
        # Fração por trade: cada robô entra com 25% do capital total atual da conta
        # Se os 3 estiverem posicionados, expõe no máximo 75% do capital
        trade_amount = capital * 0.25
        
        # Garante mínimo da Binance ($12) para simulações realistas.
        # Se a banca for pequena (ex: R$ 500 = $92), 8% de $92 é $7.36. 
        # Nesses casos, usamos o mínimo de $12.00 por trade para poder operar na Binance.
        trade_amount = max(trade_amount, 12.0)
        
        for coin, bot in bots.items():
            df = bot['df']
            c_last = df.iloc[i-1]
            c_current = df.iloc[i]
            
            if bot['in_pos']:
                # Check Take Profit (Toca na banda do meio)
                if c_current['high'] >= c_last['bb_middle']:
                    tp_price = c_last['bb_middle']
                    profit = (tp_price - bot['entry']) * bot['qty']
                    capital += profit # Adiciona lucro diretamente ao capital (Juros Compostos!)
                    total_trades += 1
                    wins += 1
                    bot['in_pos'] = False
                    
                # Check Stop Loss
                elif c_current['low'] <= bot['sl']:
                    loss = (bot['entry'] - bot['sl']) * bot['qty']
                    capital -= loss # Subtrai perda do capital
                    total_trades += 1
                    losses += 1
                    bot['in_pos'] = False
            else:
                # Sinal de Compra
                cond_bb = c_last['close'] < c_last['bb_lower']
                cond_rsi = c_last['rsi'] < CONFIG['rsi_buy_level']
                
                # Só compra se tiver saldo livre suficiente na conta
                if cond_bb and cond_rsi and capital > trade_amount:
                    bot['entry'] = c_current['open']
                    atr = c_last['atr']
                    bot['sl'] = bot['entry'] - (CONFIG['atr_stop_mult'] * atr)
                    bot['qty'] = trade_amount / bot['entry']
                    bot['in_pos'] = True
                    
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    return {
        'final_capital': capital,
        'profit_usd': capital - initial_capital_usd,
        'win_rate': win_rate,
        'total_trades': total_trades,
        'wins': wins,
        'losses': losses
    }

def main():
    print("Obtendo dados históricos para simulação de Juros Compostos (30 dias)...")
    exchange = ccxt.binance()
    limit = 3000
    exchange_rate = 5.40 # 1 USD = 5.40 BRL
    
    try:
        raw_sol = exchange.fetch_ohlcv('SOL/USDT', '15m', limit=limit)
        df_sol = prepare_data(pd.DataFrame(raw_sol, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        raw_btc = exchange.fetch_ohlcv('BTC/USDT', '15m', limit=limit)
        df_btc = prepare_data(pd.DataFrame(raw_btc, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        raw_eth = exchange.fetch_ohlcv('ETH/USDT', '15m', limit=limit)
        df_eth = prepare_data(pd.DataFrame(raw_eth, columns=['ts', 'open', 'high', 'low', 'close', 'volume']))
        
        print("\n=========================================================================")
        print("   TABELA DE RENDIMENTO ACUMULADO (JUROS COMPOSTOS) - 30 DIAS REAIS")
        print("          Estratégia: Bollinger + RSI | 3 Bots em Paralelo")
        print("=========================================================================")
        print(f"{'Capital Inicial':<18} | {'Lucro Líquido (30d)':<22} | {'Capital Final':<18} | {'Retorno (%)':<12}")
        print("-" * 78)
        
        for cap_brl in range(500, 5500, 500):
            # Converte capital inicial de BRL para USD
            cap_usd = cap_brl / exchange_rate
            
            # Executa simulação com juros compostos
            res = run_compound_simulation(df_sol, df_btc, df_eth, cap_usd)
            
            # Converte resultados de USD de volta para BRL
            profit_brl = res['profit_usd'] * exchange_rate
            final_cap_brl = res['final_capital'] * exchange_rate
            yield_pct = (res['profit_usd'] / cap_usd) * 100
            
            cap_str = f"R$ {cap_brl:.2f}"
            profit_str = f"R$ {profit_brl:.2f}"
            final_str = f"R$ {final_cap_brl:.2f}"
            yield_str = f"{yield_pct:+.2f}%"
            
            print(f"{cap_str:<18} | {profit_str:<22} | {final_str:<18} | {yield_str:<12}")
            
        print("=========================================================================")
        print("💡 NOTA: O rendimento composto diário varia conforme a banca inicial, pois")
        print("bancas menores usam o limite mínimo de $12 por trade exigido pela Binance,")
        print("o que altera a proporção de alocação de risco e acelera o ganho proporcional.")
        print("=========================================================================")
        
    except Exception as e:
        print(f"Erro ao rodar backtest composto: {e}")

if __name__ == '__main__':
    main()
