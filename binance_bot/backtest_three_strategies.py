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
    df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
    return df

def calc_macd(df, fast=12, slow=26, signal=9):
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    df['macd_line'] = ema_fast - ema_slow
    df['macd_signal'] = df['macd_line'].ewm(span=signal, adjust=False).mean()
    return df

# --- ESTRATÉGIA 1: Bollinger Bands + RSI (Reversão à Média) ---
def run_strategy_1(df, initial_balance=100.0, trade_amount=12.0):
    balance = initial_balance
    in_position = False
    entry_price = 0.0
    qty = 0.0
    stop_loss = 0.0
    trades_log = []
    
    for i in range(25, len(df)):
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
            # SL: Preço cai abaixo do Stop Loss (1.5x ATR)
            elif c_current['low'] <= stop_loss:
                loss = (entry_price - stop_loss) * qty
                balance -= loss
                trades_log.append({'type': 'LOSS', 'profit_usd': -loss})
                in_position = False
                continue
        else:
            # Compra: Preço fecha abaixo da Banda Inferior e RSI < 30
            if c_last['close'] < c_last['bb_lower'] and c_last['rsi'] < 30:
                entry_price = c_current['open']
                atr = c_last['atr']
                stop_loss = entry_price - (1.5 * atr)
                qty = trade_amount / entry_price
                in_position = True
                
    total = len(trades_log)
    wins = sum(1 for t in trades_log if t['profit_usd'] > 0)
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0
    return {'profit': balance - initial_balance, 'win_rate': win_rate, 'total': total, 'wins': wins, 'losses': losses}

# --- ESTRATÉGIA 2: Cruzamento EMA + MACD (Scalper) ---
def run_strategy_2(df, initial_balance=100.0, trade_amount=12.0):
    balance = initial_balance
    in_position = False
    entry_price = 0.0
    qty = 0.0
    stop_loss = 0.0
    tp = 0.0
    trades_log = []
    
    for i in range(200, len(df)):
        c_prev = df.iloc[i-2]
        c_last = df.iloc[i-1]
        c_current = df.iloc[i]
        
        if in_position:
            if c_current['low'] <= stop_loss:
                loss = (entry_price - stop_loss) * qty
                balance -= loss
                trades_log.append({'type': 'LOSS', 'profit_usd': -loss})
                in_position = False
            elif c_current['high'] >= tp:
                profit = (tp - entry_price) * qty
                balance += profit
                trades_log.append({'type': 'WIN', 'profit_usd': profit})
                in_position = False
        else:
            # Golden Cross de EMA 9/21, tendência acima de EMA 200, MACD favorável
            cross_up = c_prev['ema_9'] <= c_prev['ema_21'] and c_last['ema_9'] > c_last['ema_21']
            above_200 = c_last['close'] > c_last['ema_200']
            macd_bullish = c_last['macd_line'] > c_last['macd_signal']
            
            if cross_up and above_200 and macd_bullish:
                entry_price = c_current['open']
                atr = c_last['atr']
                stop_loss = entry_price - (1.2 * atr)
                tp = entry_price + (2.4 * atr) # R/R 2:1
                qty = trade_amount / entry_price
                in_position = True
                
    total = len(trades_log)
    wins = sum(1 for t in trades_log if t['profit_usd'] > 0)
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0
    return {'profit': balance - initial_balance, 'win_rate': win_rate, 'total': total, 'wins': wins, 'losses': losses}

# --- ESTRATÉGIA 3: DCA Grid (Martingale Limitada) ---
def run_strategy_3(df, initial_balance=100.0, trade_amount=12.0):
    balance = initial_balance
    
    # Parâmetros de DCA
    max_safety_orders = 3 # Total de 4 compras no ciclo
    dca_step_pct = 0.02   # Compra a cada 2% de queda
    profit_target_pct = 0.010 # 1.0% de lucro sobre o preço médio
    stop_loss_pct = 0.03 # Stop se cair 3% abaixo do último nível de segurança
    
    in_cycle = False
    orders = [] # [{price, qty, value}]
    
    trades_log = []
    
    for i in range(50, len(df)):
        c_current = df.iloc[i]
        
        if in_cycle:
            avg_price = sum(o['price'] * o['qty'] for o in orders) / sum(o['qty'] for o in orders)
            total_qty = sum(o['qty'] for o in orders)
            total_value = sum(o['value'] for o in orders)
            
            # Alvo de Take Profit (1.0% acima do preço médio)
            tp_price = avg_price * (1 + profit_target_pct)
            
            # Check Take Profit
            if c_current['high'] >= tp_price:
                profit = (tp_price - avg_price) * total_qty
                balance += profit
                trades_log.append({'type': 'WIN_DCA', 'profit_usd': profit})
                in_cycle = False
                orders = []
                continue
            
            # Check se precisa executar Ordem de Segurança (Safety Order)
            current_price = c_current['low']
            last_order_price = orders[-1]['price']
            
            if len(orders) <= max_safety_orders:
                trigger_price = last_order_price * (1 - dca_step_pct)
                if current_price <= trigger_price:
                    # Executa nova compra
                    buy_qty = trade_amount / trigger_price
                    orders.append({
                        'price': trigger_price,
                        'qty': buy_qty,
                        'value': trade_amount
                    })
                    continue
            
            # Check Stop Loss (3% abaixo da última ordem possível)
            if len(orders) == (max_safety_orders + 1):
                sl_price = orders[-1]['price'] * (1 - stop_loss_pct)
                if current_price <= sl_price:
                    # Encerra ciclo no prejuízo para proteger capital
                    loss = (avg_price - sl_price) * total_qty
                    balance -= loss
                    trades_log.append({'type': 'LOSS_DCA', 'profit_usd': -loss})
                    in_cycle = False
                    orders = []
                    continue
        else:
            # Inicia ciclo imediatamente (DCA Grid sempre rodando)
            entry_price = c_current['open']
            qty = trade_amount / entry_price
            orders.append({
                'price': entry_price,
                'qty': qty,
                'value': trade_amount
            })
            in_cycle = True
            
    total = len(trades_log)
    wins = sum(1 for t in trades_log if t['profit_usd'] > 0)
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0
    return {'profit': balance - initial_balance, 'win_rate': win_rate, 'total': total, 'wins': wins, 'losses': losses}

# --- PRINCIPAL ---
def main():
    print("Obtendo dados de SOL/USDT da Binance Spot...")
    exchange = ccxt.binance()
    
    # 5 dias úteis de 15m = 5 * 24 * 4 = 480 candles
    limit_candles = 500
    
    try:
        raw_candles = exchange.fetch_ohlcv('SOL/USDT', '15m', limit=limit_candles)
        df = pd.DataFrame(raw_candles, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        
        # Calcula indicadores comuns
        df['rsi'] = calc_rsi(df['close'], 14)
        df['atr'] = calc_atr(df, 14)
        df = calc_bollinger_bands(df, 20, 2)
        df = calc_emas(df)
        df = calc_macd(df)
        
        print("\n==================================================")
        print("    COMPARATIVO DE ESTRATÉGIAS (5 DIAS ÚTEIS)")
        print("          SOL/USDT | Gráfico: 15 minutos")
        print("==================================================")
        
        # 1. Bollinger + RSI
        res_s1 = run_strategy_1(df, initial_balance=100.0, trade_amount=12.0)
        print("\n📊 ESTRATÉGIA 1: REVERSÃO À MÉDIA (Bollinger + RSI)")
        print(f"   - Lucro Líquido: ${res_s1['profit']:.2f} USDT")
        print(f"   - Taxa de Acerto: {res_s1['win_rate']:.1f}%")
        print(f"   - Total de Trades: {res_s1['total']} (Wins: {res_s1['wins']} | Losses: {res_s1['losses']})")
        
        # 2. EMA + MACD Scalper
        res_s2 = run_strategy_2(df, initial_balance=100.0, trade_amount=12.0)
        print("\n⚡ ESTRATÉGIA 2: SCALPER DE MOMENTO (Cruzamento EMA + MACD)")
        print(f"   - Lucro Líquido: ${res_s2['profit']:.2f} USDT")
        print(f"   - Taxa de Acerto: {res_s2['win_rate']:.1f}%")
        print(f"   - Total de Trades: {res_s2['total']} (Wins: {res_s2['wins']} | Losses: {res_s2['losses']})")
        
        # 3. DCA Grid
        res_s3 = run_strategy_3(df, initial_balance=100.0, trade_amount=12.0)
        print("\n🛡️ ESTRATÉGIA 3: DCA GRID (Martingale Limitada)")
        print(f"   - Lucro Líquido: ${res_s3['profit']:.2f} USDT")
        print(f"   - Taxa de Acerto: {res_s3['win_rate']:.1f}%")
        print(f"   - Total de Ciclos Finalizados: {res_s3['total']} (Wins: {res_s3['wins']} | Losses: {res_s3['losses']})")
        
        print("\n==================================================")
        print("💡 VERDICTO:")
        profits = {'Reversão à Média': res_s1['profit'], 'Scalper EMA+MACD': res_s2['profit'], 'DCA Grid': res_s3['profit']}
        best = max(profits, key=profits.get)
        print(f"A melhor estratégia para o período foi **{best}** com lucro de ${profits[best]:.2f} USDT.")
        print("==================================================")
        
    except Exception as e:
        print(f"Erro ao rodar backtest: {e}")

if __name__ == '__main__':
    main()
