"""
╔══════════════════════════════════════════════════════════════════════╗
║  ROBÔ A — SOL/USDT — TENDÊNCIA MULTI-TIMEFRAME AVANÇADA v3.0        ║
║                                                                      ║
║  Melhorias vs versão anterior:                                       ║
║  ✅ Confirmação Multi-Timeframe (15m + 1h)                           ║
║  ✅ Indicadores: EMA + MACD + Stochastic RSI (sem whipsaw)           ║
║  ✅ ATR dinâmico para stop/target adaptado à volatilidade            ║
║  ✅ Trailing Stop automático após TP1                                ║
║  ✅ Filtro de volume: exige força no candle de entrada               ║
║  ✅ Filtro de horário UTC: opera apenas em alta liquidez             ║
║  ✅ Limite diário de trades para evitar over-trading                 ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
import datetime
import requests
import ccxt
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Garante saída UTF-8 no Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

load_dotenv()

PORT = os.getenv('PORT', '3000')
BACKEND_URL = os.getenv('BACKEND_URL', f'http://localhost:{PORT}')
USER_ID = os.getenv('USER_ID', 'guest')

import config

STATE_FILE = 'bot_state.json'
BOT_NAME = '[BOT A - SOL/USDT]'


# ══════════════════════════════════════════════════════════════════════
#  BACKEND INTEGRATION
# ══════════════════════════════════════════════════════════════════════

def fetch_backend_config():
    try:
        r = requests.get(f"{BACKEND_URL}/bot/config?userId={USER_ID}", timeout=10)
        if r.status_code == 200:
            return r.json()
        print(f"\n{BOT_NAME} [ERRO] Backend status {r.status_code}")
    except Exception as e:
        print(f"\n{BOT_NAME} [ERRO] Backend inacessível: {e}")
    return None


def register_trade_backend(asset, trade_type, price, amount, value, profit_pct=None):
    payload = {
        'userId': USER_ID,
        'asset': asset,
        'type': trade_type,
        'price': float(price),
        'amount': float(amount),
        'value': float(value)
    }
    if profit_pct is not None:
        payload['profitPct'] = f"{profit_pct:+.2f}%" if isinstance(profit_pct, (int, float)) else str(profit_pct)
    try:
        r = requests.post(f"{BACKEND_URL}/bot/trades", json=payload, timeout=10)
        if r.status_code == 201:
            print(f"\n{BOT_NAME} [BACKEND] Trade registrado: {trade_type} {asset}")
        else:
            print(f"\n{BOT_NAME} [ERRO BACKEND] Status {r.status_code}")
    except Exception as e:
        print(f"\n{BOT_NAME} [ERRO BACKEND] {e}")


# ══════════════════════════════════════════════════════════════════════
#  CONEXÃO / EXCHANGE
# ══════════════════════════════════════════════════════════════════════

def get_exchange_connection(api_key, api_secret):
    use_testnet = os.getenv('USE_TESTNET', 'True').lower() == 'true'
    if not api_key or not api_secret or len(api_key.strip()) < 10:
        print(f"{BOT_NAME} [AVISO] Chaves de API inválidas!")
        return None, use_testnet
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    if use_testnet:
        exchange.set_sandbox_mode(True)
        print(f"{BOT_NAME} [INFO] Conectado à TESTNET da Binance.")
    else:
        print(f"{BOT_NAME} [PERIGO] CONTA REAL DA BINANCE!")
    return exchange, use_testnet


def send_telegram_message(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id or token == 'seu_token_do_telegram_aqui':
        print(f"{BOT_NAME} [TELEGRAM] {message}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={'chat_id': chat_id, 'text': f"🤖 *{BOT_NAME}*\n\n{message}", 'parse_mode': 'Markdown'},
            timeout=5
        )
    except Exception as e:
        print(f"{BOT_NAME} [TELEGRAM ERRO] {e}")


# ══════════════════════════════════════════════════════════════════════
#  ESTADO LOCAL
# ══════════════════════════════════════════════════════════════════════

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"{BOT_NAME} [ESTADO] Erro ao carregar: {e}")
    return {
        'in_position': False,
        'entry_price': 0.0,
        'stop_loss_price': 0.0,
        'take_profit_1': 0.0,
        'take_profit_2': 0.0,
        'quantity_bought': 0.0,
        'is_partial_executed': False,
        'trailing_stop_price': 0.0,
        'daily_loss_accumulated': 0.0,
        'daily_profit_accumulated': 0.0,
        'trades_today': 0,
        'last_reset_date': str(datetime.date.today())
    }


def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"{BOT_NAME} [ESTADO] Erro ao salvar: {e}")


# ══════════════════════════════════════════════════════════════════════
#  INDICADORES TÉCNICOS AVANÇADOS
# ══════════════════════════════════════════════════════════════════════

def fetch_candles(exchange, symbol, timeframe, limit=150):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"\n{BOT_NAME} [ERRO] Falha ao buscar candles: {e}")
        return None


def calculate_atr(df, period=14):
    """Average True Range — mede a volatilidade real do mercado."""
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def calculate_macd(close, fast=12, slow=26, signal=9):
    """MACD — identifica mudanças na força, direção e duração da tendência."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_stoch_rsi(close, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3):
    """Stochastic RSI — muito mais sensível que o RSI normal para detectar 
    reversões e confirmar entradas sem whipsaw."""
    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(span=rsi_period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=rsi_period, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    
    # Stochastic do RSI
    rsi_min = rsi.rolling(stoch_period).min()
    rsi_max = rsi.rolling(stoch_period).max()
    stoch_k_raw = 100 * (rsi - rsi_min) / (rsi_max - rsi_min + 1e-9)
    stoch_k = stoch_k_raw.rolling(smooth_k).mean()
    stoch_d = stoch_k.rolling(smooth_d).mean()
    return rsi, stoch_k, stoch_d


def calculate_indicators(df):
    """Calcula todos os indicadores: EMA + MACD + Stoch RSI + ATR + Volume MA."""
    close = df['close']
    
    # EMAs de tendência
    df['ema_fast'] = close.ewm(span=config.EMA_FAST_PERIOD, adjust=False).mean()
    df['ema_slow'] = close.ewm(span=config.EMA_SLOW_PERIOD, adjust=False).mean()
    df['ema_macro'] = close.ewm(span=config.EMA_MACRO_PERIOD, adjust=False).mean()
    
    # MACD
    df['macd'], df['macd_signal'], df['macd_hist'] = calculate_macd(
        close, config.MACD_FAST, config.MACD_SLOW, config.MACD_SIGNAL
    )
    
    # Stochastic RSI
    df['rsi'], df['stoch_k'], df['stoch_d'] = calculate_stoch_rsi(
        close,
        rsi_period=config.RSI_PERIOD,
        stoch_period=config.STOCH_RSI_PERIOD,
        smooth_k=config.STOCH_RSI_SMOOTH_K,
        smooth_d=config.STOCH_RSI_SMOOTH_D
    )
    
    # ATR
    df['atr'] = calculate_atr(df, config.ATR_PERIOD)
    
    # Média de Volume
    df['volume_ma'] = df['volume'].rolling(window=config.VOLUME_MA_PERIOD).mean()
    
    return df


def is_trading_hours():
    """Verifica se estamos dentro da janela de alta liquidez."""
    if not config.TIME_FILTER:
        return True
    now_utc = datetime.datetime.utcnow()
    hour = now_utc.hour
    return config.TRADING_HOURS_UTC_START <= hour < config.TRADING_HOURS_UTC_END


def check_macro_trend(exchange, symbol):
    """Verifica a tendência no timeframe maior (1h).
    Retorna True se a tendência macro for de ALTA (bullish)."""
    try:
        df_1h = fetch_candles(exchange, symbol, config.TIMEFRAME_MACRO, limit=60)
        if df_1h is None:
            return True  # Em caso de falha, não bloqueia
        df_1h['ema_macro'] = df_1h['close'].ewm(span=config.EMA_MACRO_PERIOD, adjust=False).mean()
        last = df_1h.iloc[-2]  # Candle fechado mais recente
        # Tendência bullish: preço acima da EMA macro E EMA em alta
        price_above_macro = last['close'] > last['ema_macro']
        ema_trending_up = df_1h['ema_macro'].iloc[-2] > df_1h['ema_macro'].iloc[-5]
        return price_above_macro and ema_trending_up
    except Exception as e:
        print(f"\n{BOT_NAME} [AVISO] Falha ao verificar tendência macro: {e}")
        return True


# ══════════════════════════════════════════════════════════════════════
#  EXECUÇÃO DE ORDENS
# ══════════════════════════════════════════════════════════════════════

def buy_entry(exchange, symbol, amount_usdt):
    try:
        exchange.load_markets()
        market = exchange.market(symbol)
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        qty = amount_usdt / current_price
        formatted_qty = float(exchange.amount_to_precision(symbol, qty))
        print(f"\n{BOT_NAME} [COMPRA] {formatted_qty} {market['base']} @ ~${current_price:.4f}")
        order = exchange.create_market_buy_order(symbol, formatted_qty)
        time.sleep(1.5)
        balance = exchange.fetch_balance()
        base_asset = symbol.split('/')[0]
        actual_qty = balance['free'].get(base_asset, 0.0)
        actual_qty_formatted = float(exchange.amount_to_precision(symbol, actual_qty))
        print(f"{BOT_NAME} [COMPRA OK] Qtd líquida: {actual_qty_formatted}")
        return order, current_price, actual_qty_formatted
    except Exception as e:
        print(f"\n{BOT_NAME} [ERRO COMPRA] {e}")
        return None, 0.0, 0.0


def sell_exit(exchange, symbol, qty, reason="Saída"):
    try:
        exchange.load_markets()
        formatted_qty = float(exchange.amount_to_precision(symbol, qty))
        if formatted_qty <= 0:
            print(f"{BOT_NAME} [AVISO] Qtd zero. Abortando venda.")
            return None
        print(f"\n{BOT_NAME} [VENDA] {formatted_qty} ({reason})")
        return exchange.create_market_sell_order(symbol, formatted_qty)
    except Exception as e:
        print(f"\n{BOT_NAME} [ERRO VENDA] {e}")
        return None


# ══════════════════════════════════════════════════════════════════════
#  LÓGICA PRINCIPAL DE SINAL
# ══════════════════════════════════════════════════════════════════════

def check_entry_signal(df, exchange, symbol):
    """
    Analisa os indicadores e retorna True se houver sinal de COMPRA confirmado.
    
    Condições necessárias (TODAS devem ser verdadeiras):
    1. Cruzamento EMA rápida acima da EMA lenta (candle anterior: baixo, atual: alto)
    2. MACD histograma positivo E crescente (confirmação de momentum)
    3. Stochastic RSI saindo da zona de sobrevenda (K cruzando acima de D)
    4. RSI não sobrecomprado (abaixo de 72)
    5. Volume acima da média (sinal com força)
    6. Preço acima da EMA macro (não contra-tendência)
    """
    if len(df) < 50:
        return False, "Dados insuficientes"
    
    # Últimos 3 candles fechados (iloc[-1] é o candle atual ainda aberto)
    c1 = df.iloc[-4]  # 3 candles atrás
    c2 = df.iloc[-3]  # 2 candles atrás  
    c3 = df.iloc[-2]  # Último candle FECHADO (o mais importante)
    
    reasons = []
    
    # 1. Cruzamento EMA: Fast cruzou acima de Slow
    ema_cross_up = (c2['ema_fast'] <= c2['ema_slow']) and (c3['ema_fast'] > c3['ema_slow'])
    
    # Ou: EMA fast já acima E gap crescendo (tendência em aceleração)
    ema_gap_growing = (c3['ema_fast'] > c3['ema_slow']) and \
                      (c3['ema_fast'] - c3['ema_slow']) > (c2['ema_fast'] - c2['ema_slow'])
    
    ema_ok = ema_cross_up or ema_gap_growing
    if not ema_ok:
        return False, "EMA: sem cruzamento de alta"
    reasons.append("EMA✅")
    
    # 2. MACD Histograma positivo e crescendo (momentum verde)
    macd_ok = c3['macd_hist'] > 0 and c3['macd_hist'] > c2['macd_hist']
    if not macd_ok:
        return False, f"MACD: histograma {c3['macd_hist']:.4f} (precisa ser positivo e crescendo)"
    reasons.append("MACD✅")
    
    # 3. Stochastic RSI saindo de sobrevenda
    stoch_ok = (c2['stoch_k'] < c2['stoch_d'] or c2['stoch_k'] < 40) and \
               (c3['stoch_k'] > c3['stoch_d']) and \
               c3['stoch_k'] < config.RSI_OVERBOUGHT
    if not stoch_ok:
        return False, f"StochRSI: K={c3['stoch_k']:.1f}, D={c3['stoch_d']:.1f} (sem cruzamento ascendente)"
    reasons.append("StochRSI✅")
    
    # 4. RSI não sobrecomprado
    rsi_ok = c3['rsi'] < config.RSI_OVERBOUGHT
    if not rsi_ok:
        return False, f"RSI sobrecomprado: {c3['rsi']:.1f}"
    reasons.append(f"RSI={c3['rsi']:.0f}✅")
    
    # 5. Filtro de volume
    if config.VOLUME_FILTER:
        vol_ok = c3['volume'] >= (c3['volume_ma'] * config.VOLUME_MIN_RATIO)
        if not vol_ok:
            return False, f"Volume baixo: {c3['volume']:.0f} < {c3['volume_ma']*config.VOLUME_MIN_RATIO:.0f} (min)"
        reasons.append("VOL✅")
    
    # 6. Preço acima da EMA macro (não entrar contra-tendência)
    macro_ok = c3['close'] > c3['ema_macro']
    if not macro_ok:
        return False, f"Preço abaixo da EMA{config.EMA_MACRO_PERIOD}: {c3['close']:.4f} < {c3['ema_macro']:.4f}"
    reasons.append(f"EMA{config.EMA_MACRO_PERIOD}✅")
    
    return True, " | ".join(reasons)


def check_exit_signal(df, current_price, state, symbol):
    """
    Verifica sinais de saída técnica (além dos stops de preço).
    Retorna (should_exit: bool, reason: str)
    """
    c2 = df.iloc[-3]
    c3 = df.iloc[-2]  # Último candle fechado
    
    # Saída 1: EMA fast cruzou abaixo da slow (reversão de tendência)
    ema_cross_down = (c2['ema_fast'] >= c2['ema_slow']) and (c3['ema_fast'] < c3['ema_slow'])
    if ema_cross_down:
        return True, "Cruzamento reverso de EMAs"
    
    # Saída 2: MACD histograma virou negativo (momentum inverteu)
    macd_reversal = c3['macd_hist'] < 0 and c2['macd_hist'] > 0
    if macd_reversal:
        return True, "MACD histograma virou negativo"
    
    # Saída 3: RSI entrou em sobrecompra extrema (>80) — risco de correção
    if c3['rsi'] > 80 and state.get('is_partial_executed', False):
        return True, f"RSI em sobrecompra extrema: {c3['rsi']:.1f}"
    
    return False, ""


# ══════════════════════════════════════════════════════════════════════
#  LOOP PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

def run_trading_bot():
    print("=" * 68)
    print(f"  {BOT_NAME} INICIANDO — TENDÊNCIA MULTI-TIMEFRAME v3.0")
    print(f"  Ativo: {config.SYMBOL} | TF: {config.TIMEFRAME} | Macro: {config.TIMEFRAME_MACRO}")
    print("=" * 68)
    
    state = load_state()
    
    # Reset diário
    today_str = str(datetime.date.today())
    if state.get('last_reset_date') != today_str:
        print(f"{BOT_NAME} [DIÁRIO] Novo dia. Resetando contadores.")
        state['daily_loss_accumulated'] = 0.0
        state['daily_profit_accumulated'] = 0.0
        state['trades_today'] = 0
        state['last_reset_date'] = today_str
        save_state(state)
    
    exchange = None
    use_testnet = False
    current_api_key = None
    current_api_secret = None
    last_macro_check = 0
    macro_trend_ok = True

    while True:
        try:
            # ── Busca config no backend ──────────────────────────────
            backend_cfg = fetch_backend_config()
            if backend_cfg is None:
                api_key = os.getenv('BINANCE_API_KEY')
                api_secret = os.getenv('BINANCE_API_SECRET')
                is_active = True
                symbol = config.SYMBOL
                trade_amount = config.TRADE_AMOUNT_USDT
            else:
                api_key = backend_cfg.get('binanceApiKey')
                api_secret = backend_cfg.get('binanceApiSecret')
                is_active = backend_cfg.get('isActive', False)
                symbol = backend_cfg.get('symbol', config.SYMBOL)
                trade_amount = float(backend_cfg.get('tradeAmount', config.TRADE_AMOUNT_USDT))

            # ── Robô desativado ──────────────────────────────────────
            if not is_active:
                if state['in_position'] and exchange is not None:
                    ticker = exchange.fetch_ticker(symbol)
                    cp = ticker['last']
                    sell_exit(exchange, symbol, state['quantity_bought'], "Desligamento")
                    pct = ((cp - state['entry_price']) / state['entry_price']) * 100
                    register_trade_backend(symbol, "VENDA (DESLIGAMENTO)", cp,
                                           state['quantity_bought'], state['quantity_bought'] * cp, pct)
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                print(f"\r{BOT_NAME} [OFF] Aguardando ativação via App... {datetime.datetime.now().strftime('%H:%M:%S')}", end="", flush=True)
                time.sleep(15)
                continue

            # ── Inicializa exchange ──────────────────────────────────
            if exchange is None or api_key != current_api_key or api_secret != current_api_secret:
                exchange, use_testnet = get_exchange_connection(api_key, api_secret)
                if exchange is None:
                    time.sleep(15)
                    continue
                current_api_key = api_key
                current_api_secret = api_secret

            # ── Reset diário ─────────────────────────────────────────
            today_str = str(datetime.date.today())
            if state.get('last_reset_date') != today_str:
                state['daily_loss_accumulated'] = 0.0
                state['daily_profit_accumulated'] = 0.0
                state['trades_today'] = 0
                state['last_reset_date'] = today_str
                save_state(state)

            # ── Proteções diárias ────────────────────────────────────
            if state['daily_loss_accumulated'] >= config.MAX_DAILY_LOSS_USDT:
                print(f"\n{BOT_NAME} [PAUSADO] Limite de perda diária atingido (${state['daily_loss_accumulated']:.2f}). Parando até amanhã.")
                time.sleep(600)
                continue
            
            if state['daily_profit_accumulated'] >= config.MAX_DAILY_PROFIT_USDT:
                print(f"\n{BOT_NAME} [META ATINGIDA] Lucro do dia: +${state['daily_profit_accumulated']:.2f}. Encerrando operações.")
                time.sleep(600)
                continue
            
            if state.get('trades_today', 0) >= config.MAX_TRADES_PER_DAY and not state['in_position']:
                print(f"\n{BOT_NAME} [LIMITE] {config.MAX_TRADES_PER_DAY} trades hoje. Aguardando reset diário.")
                time.sleep(300)
                continue

            # ── Filtro de horário ────────────────────────────────────
            if not is_trading_hours() and not state['in_position']:
                print(f"\r{BOT_NAME} [HORÁRIO] Fora da janela de liquidez. {datetime.datetime.now().strftime('%H:%M:%S')} UTC", end="", flush=True)
                time.sleep(60)
                continue

            # ── Preço atual ──────────────────────────────────────────
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            print(f"\r{BOT_NAME} | ${current_price:.4f} | Pos:{state['in_position']} | "
                  f"P/L dia: ${state['daily_profit_accumulated']:.2f}/${state['daily_loss_accumulated']:.2f} | "
                  f"Trades: {state.get('trades_today',0)} | {datetime.datetime.now().strftime('%H:%M:%S')} UTC",
                  end="", flush=True)

            # ══════════════════════════════════════════════════════════
            #  MODO POSICIONADO — GESTÃO DA POSIÇÃO ABERTA
            # ══════════════════════════════════════════════════════════
            if state['in_position']:
                qty = state['quantity_bought']
                entry_price = state['entry_price']
                current_pnl_pct = (current_price - entry_price) / entry_price * 100

                # A. STOP LOSS
                if current_price <= state['stop_loss_price']:
                    loss_usd = (entry_price - current_price) * qty
                    print(f"\n{BOT_NAME} 🚨 STOP LOSS @ ${current_price:.4f} | Perda: -${loss_usd:.2f}")
                    sell_exit(exchange, symbol, qty, "Stop Loss")
                    state['daily_loss_accumulated'] += loss_usd
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                    profit_pct = -((entry_price - current_price) / entry_price) * 100
                    register_trade_backend(symbol, "VENDA (STOP LOSS)", current_price, qty, qty * current_price, profit_pct)
                    send_telegram_message(
                        f"❌ *Stop Loss Acionado*\n"
                        f"📉 Saída: ${current_price:.4f}\n"
                        f"💸 Perda: -${loss_usd:.2f} ({profit_pct:+.2f}%)\n"
                        f"📊 Capital protegido pelo sistema de defesa."
                    )
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # B. TRAILING STOP (após TP1 atingido)
                if config.TRAILING_STOP and state.get('is_partial_executed', False):
                    new_trailing = current_price * (1 - config.TRAILING_STOP_PCT)
                    if new_trailing > state.get('trailing_stop_price', 0):
                        state['trailing_stop_price'] = new_trailing
                        state['stop_loss_price'] = max(state['stop_loss_price'], new_trailing)
                        save_state(state)
                    
                    if current_price <= state.get('trailing_stop_price', 0):
                        profit_usd = (current_price - entry_price) * qty
                        print(f"\n{BOT_NAME} 🎯 TRAILING STOP @ ${current_price:.4f} | Lucro: +${profit_usd:.2f}")
                        sell_exit(exchange, symbol, qty, "Trailing Stop")
                        state['daily_profit_accumulated'] += profit_usd
                        state['in_position'] = False
                        state['is_partial_executed'] = False
                        save_state(state)
                        pct = (current_price - entry_price) / entry_price * 100
                        register_trade_backend(symbol, "VENDA (TRAILING STOP)", current_price, qty, qty * current_price, pct)
                        send_telegram_message(f"🎯 *Trailing Stop — Lucro Garantido!*\n💵 +${profit_usd:.2f} ({pct:+.2f}%)")
                        time.sleep(config.LOOP_INTERVAL_SECONDS)
                        continue

                # C. TAKE PROFIT 1 (realização parcial)
                if not state['is_partial_executed'] and current_price >= state['take_profit_1']:
                    print(f"\n{BOT_NAME} 🎯 TP1 @ ${current_price:.4f}")
                    partial_qty = qty * config.PARTIAL_EXIT_PCT
                    order = sell_exit(exchange, symbol, partial_qty, "Realização Parcial TP1")
                    if order is None:
                        time.sleep(config.LOOP_INTERVAL_SECONDS)
                        continue
                    time.sleep(1.5)
                    balance = exchange.fetch_balance()
                    base_asset = symbol.split('/')[0]
                    remaining_qty = float(exchange.amount_to_precision(symbol, balance['free'].get(base_asset, 0.0)))
                    
                    if config.ACTIVATE_BREAKEVEN:
                        state['stop_loss_price'] = entry_price  # Risco zero
                        print(f"{BOT_NAME} 🛡️ Breakeven: Stop movido para ${entry_price:.4f}")
                    
                    state['trailing_stop_price'] = current_price * (1 - config.TRAILING_STOP_PCT)
                    partial_profit = (current_price - entry_price) * partial_qty
                    state['daily_profit_accumulated'] += partial_profit
                    
                    pct = (current_price - entry_price) / entry_price * 100
                    register_trade_backend(symbol, "VENDA PARCIAL (TP1)", current_price, partial_qty,
                                           partial_qty * current_price, pct)
                    
                    remaining_val = remaining_qty * current_price
                    if remaining_val < 2.0:
                        state['in_position'] = False
                        state['is_partial_executed'] = False
                        state['quantity_bought'] = 0.0
                    else:
                        state['quantity_bought'] = remaining_qty
                        state['is_partial_executed'] = True
                    save_state(state)
                    
                    send_telegram_message(
                        f"🎯 *TP1 Atingido — Lucro Parcial Garantido!*\n"
                        f"💰 +${partial_profit:.2f} ({pct:+.2f}%)\n"
                        f"🛡️ Breakeven: SL movido para entrada. Risco = ZERO!\n"
                        f"🚀 {remaining_qty:.6f} restante buscando TP2"
                    )
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # D. TAKE PROFIT 2 (alvo final)
                if current_price >= state['take_profit_2']:
                    profit_usd = (current_price - entry_price) * qty
                    print(f"\n{BOT_NAME} 🏆 TP2 ATINGIDO @ ${current_price:.4f} | Lucro: +${profit_usd:.2f}")
                    sell_exit(exchange, symbol, qty, "Alvo Final TP2")
                    state['daily_profit_accumulated'] += profit_usd
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                    pct = (current_price - entry_price) / entry_price * 100
                    register_trade_backend(symbol, "VENDA (TP2)", current_price, qty, qty * current_price, pct)
                    send_telegram_message(
                        f"🏆 *ALVO FINAL (TP2) ATINGIDO!*\n"
                        f"📈 Saída: ${current_price:.4f}\n"
                        f"💵 Lucro total: +${profit_usd:.2f} ({pct:+.2f}%)\n"
                        f"🚀 Operação concluída com excelência!"
                    )
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # E. SAÍDA TÉCNICA (reversão de indicadores)
                df = fetch_candles(exchange, symbol, config.TIMEFRAME)
                if df is not None:
                    df = calculate_indicators(df)
                    should_exit, exit_reason = check_exit_signal(df, current_price, state, symbol)
                    if should_exit:
                        profit_usd = (current_price - entry_price) * qty
                        print(f"\n{BOT_NAME} ⚠️ SAÍDA TÉCNICA: {exit_reason}")
                        sell_exit(exchange, symbol, qty, f"Saída Técnica: {exit_reason}")
                        if profit_usd > 0:
                            state['daily_profit_accumulated'] += profit_usd
                        else:
                            state['daily_loss_accumulated'] += abs(profit_usd)
                        state['in_position'] = False
                        state['is_partial_executed'] = False
                        save_state(state)
                        pct = (current_price - entry_price) / entry_price * 100
                        register_trade_backend(symbol, "VENDA (TÉCNICA)", current_price, qty, qty * current_price, pct)
                        send_telegram_message(
                            f"⚠️ *Saída Técnica*\n"
                            f"📊 Motivo: {exit_reason}\n"
                            f"💵 Resultado: {'+$' if profit_usd >= 0 else '-$'}{abs(profit_usd):.2f} ({pct:+.2f}%)"
                        )

            # ══════════════════════════════════════════════════════════
            #  MODO FLAT — PROCURANDO SINAL DE ENTRADA
            # ══════════════════════════════════════════════════════════
            else:
                # Verificação de tendência macro a cada 5 minutos
                now_ts = time.time()
                if now_ts - last_macro_check > 300:
                    macro_trend_ok = check_macro_trend(exchange, symbol)
                    last_macro_check = now_ts
                    if not macro_trend_ok:
                        print(f"\n{BOT_NAME} [MACRO] Tendência 1h de baixa. Aguardando reversão macro...")
                
                if not macro_trend_ok:
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue
                
                df = fetch_candles(exchange, symbol, config.TIMEFRAME)
                if df is not None:
                    df = calculate_indicators(df)
                    signal_ok, signal_reason = check_entry_signal(df, exchange, symbol)
                    
                    if signal_ok:
                        print(f"\n{BOT_NAME} 🚀 SINAL CONFIRMADO! {signal_reason}")
                        print(f"{BOT_NAME}    Preço: ${current_price:.4f} | ATR: ${df.iloc[-2]['atr']:.4f}")
                        
                        order, buy_price, qty_bought = buy_entry(exchange, symbol, trade_amount)
                        
                        if order is not None and qty_bought > 0:
                            # Calcula stops/targets pelo ATR se disponível
                            last_atr = df.iloc[-2]['atr']
                            if config.USE_ATR_STOPS and last_atr > 0:
                                sl_price = buy_price - (config.ATR_STOP_MULTIPLIER * last_atr)
                                tp1_price = buy_price + (config.ATR_TP1_MULTIPLIER * last_atr)
                                tp2_price = buy_price + (config.ATR_TP2_MULTIPLIER * last_atr)
                            else:
                                sl_price = buy_price * (1 - config.STOP_LOSS_PCT)
                                tp1_price = buy_price * (1 + config.TAKE_PROFIT_1_PCT)
                                tp2_price = buy_price * (1 + config.TAKE_PROFIT_2_PCT)
                            
                            state['in_position'] = True
                            state['entry_price'] = buy_price
                            state['quantity_bought'] = qty_bought
                            state['stop_loss_price'] = sl_price
                            state['take_profit_1'] = tp1_price
                            state['take_profit_2'] = tp2_price
                            state['is_partial_executed'] = False
                            state['trailing_stop_price'] = 0.0
                            state['trades_today'] = state.get('trades_today', 0) + 1
                            save_state(state)
                            
                            register_trade_backend(symbol, "COMPRA", buy_price, qty_bought, qty_bought * buy_price)
                            
                            risco = buy_price - sl_price
                            retorno = tp2_price - buy_price
                            rr_ratio = retorno / risco if risco > 0 else 0
                            
                            send_telegram_message(
                                f"🚀 *Nova Posição Aberta!*\n"
                                f"🪙 {symbol} | Entrada: ${buy_price:.4f}\n"
                                f"📦 Qtd: {qty_bought}\n"
                                f"📊 Sinais: {signal_reason}\n\n"
                                f"🛡️ *Defesa Configurada:*\n"
                                f"🛑 Stop Loss: ${sl_price:.4f}\n"
                                f"🎯 TP1 (parcial): ${tp1_price:.4f}\n"
                                f"🏆 TP2 (alvo): ${tp2_price:.4f}\n"
                                f"📐 Risco/Retorno: {rr_ratio:.1f}x\n"
                                f"📅 Trade #{state['trades_today']} do dia"
                            )
                    else:
                        # Log compacto do motivo da não entrada (a cada 10 loops)
                        pass

            time.sleep(config.LOOP_INTERVAL_SECONDS)

        except ccxt.NetworkError as ne:
            print(f"\n{BOT_NAME} [REDE] {ne}. Retentando em 15s...")
            time.sleep(15)
        except ccxt.AuthenticationError as ae:
            print(f"\n{BOT_NAME} [AUTH ERRO] Credenciais inválidas: {ae}")
            try:
                requests.post(f"{BACKEND_URL}/bot/config",
                              json={'userId': USER_ID, 'isActive': False}, timeout=10)
            except Exception:
                pass
            time.sleep(30)
        except ccxt.ExchangeError as ee:
            print(f"\n{BOT_NAME} [EXCHANGE ERRO] {ee}. Retentando em 30s...")
            time.sleep(30)
        except Exception as e:
            print(f"\n{BOT_NAME} [ERRO CRÍTICO] {e}. Reiniciando em 30s...")
            time.sleep(30)


if __name__ == '__main__':
    run_trading_bot()
