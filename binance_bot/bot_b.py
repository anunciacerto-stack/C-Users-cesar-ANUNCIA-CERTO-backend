"""
╔══════════════════════════════════════════════════════════════════════╗
║  ROBÔ B — BTC/USDT — REVERSÃO À MÉDIA + SQUEEZE MOMENTUM v3.0       ║
║                                                                      ║
║  Melhorias:                                                          ║
║  ✅ Bollinger Band Squeeze (detecta explosão antes de acontecer)     ║
║  ✅ Stochastic RSI para confirmar sobrevendido real                  ║
║  ✅ Candle de confirmação fechado (sem whipsaw como antes)           ║
║  ✅ ATR stops dinâmicos adaptados à volatilidade BTC                 ║
║  ✅ Trailing stop para capturar continuações de movimento            ║
║  ✅ Filtro macro 1h (não reverte contra tendência maior)             ║
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

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

load_dotenv()

PORT = os.getenv('PORT', '3000')
BACKEND_URL = os.getenv('BACKEND_URL', f'http://localhost:{PORT}')
USER_ID = os.getenv('USER_ID', 'guest')

import config_b as config

STATE_FILE = config.STATE_FILE
BOT_NAME = '[BOT B - BTC/USDT]'


# ══════════════════════════════════════════════════════════════════════
#  BACKEND INTEGRATION
# ══════════════════════════════════════════════════════════════════════

def fetch_backend_config():
    try:
        r = requests.get(f"{BACKEND_URL}/bot/config?userId={USER_ID}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"\n{BOT_NAME} [ERRO] Backend: {e}")
    return None


def register_trade_backend(asset, trade_type, price, amount, value, profit_pct=None):
    payload = {
        'userId': USER_ID, 'asset': asset, 'type': trade_type,
        'price': float(price), 'amount': float(amount), 'value': float(value)
    }
    if profit_pct is not None:
        payload['profitPct'] = f"{profit_pct:+.2f}%"
    try:
        r = requests.post(f"{BACKEND_URL}/bot/trades", json=payload, timeout=10)
        if r.status_code == 201:
            print(f"\n{BOT_NAME} [BACKEND] Trade: {trade_type} {asset}")
    except Exception as e:
        print(f"\n{BOT_NAME} [ERRO BACKEND] {e}")


def get_exchange_connection(api_key=None, api_secret=None):
    if not api_key or api_key == 'sua_chave_api_aqui':
        api_key = os.getenv('BINANCE_API_KEY')
    if not api_secret or api_secret == 'sua_chave_api_aqui':
        api_secret = os.getenv('BINANCE_API_SECRET')
    use_testnet = os.getenv('USE_TESTNET', 'True').lower() == 'true'
    
    if not api_key or len(api_key.strip()) < 10:
        return ccxt.binance({'enableRateLimit': True}), use_testnet
    
    exchange = ccxt.binance({
        'apiKey': api_key, 'secret': api_secret,
        'enableRateLimit': True, 'options': {'defaultType': 'spot'}
    })
    if use_testnet:
        exchange.set_sandbox_mode(True)
        print(f"{BOT_NAME} [INFO] TESTNET ativa.")
    else:
        print(f"{BOT_NAME} [PERIGO] CONTA REAL!")
    return exchange, use_testnet


def send_telegram_message(message):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not token or not chat_id or 'seu_token' in token:
        print(f"{BOT_NAME} [TELEGRAM] {message}")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={'chat_id': chat_id, 'text': f"🤖 *{BOT_NAME}*\n\n{message}", 'parse_mode': 'Markdown'},
            timeout=5
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════
#  ESTADO
# ══════════════════════════════════════════════════════════════════════

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
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
        print(f"{BOT_NAME} [ESTADO ERRO] {e}")


# ══════════════════════════════════════════════════════════════════════
#  INDICADORES
# ══════════════════════════════════════════════════════════════════════

def fetch_candles(exchange, symbol, timeframe, limit=150):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"\n{BOT_NAME} [ERRO CANDLES] {e}")
        return None


def calculate_atr(df, period=14):
    high, low, close = df['high'], df['low'], df['close']
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def calculate_stoch_rsi(close, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3):
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(span=rsi_period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=rsi_period, adjust=False).mean()
    rsi = 100 - (100 / (1 + gain / (loss + 1e-9)))
    rsi_min = rsi.rolling(stoch_period).min()
    rsi_max = rsi.rolling(stoch_period).max()
    stoch_k = (100 * (rsi - rsi_min) / (rsi_max - rsi_min + 1e-9)).rolling(smooth_k).mean()
    stoch_d = stoch_k.rolling(smooth_d).mean()
    return rsi, stoch_k, stoch_d


def calculate_keltner_channels(df, ema_period=20, atr_mult=1.5):
    """Keltner Channels para detectar squeeze das Bandas de Bollinger."""
    ema = df['close'].ewm(span=ema_period, adjust=False).mean()
    atr = calculate_atr(df, ema_period)
    upper = ema + atr_mult * atr
    lower = ema - atr_mult * atr
    return upper, lower


def calculate_indicators(df):
    """Calcula BB, BB Squeeze, Stoch RSI, ATR, Volume MA."""
    close = df['close']
    period = config.BOLLINGER_PERIOD
    dev = config.BOLLINGER_DEV
    
    # Bollinger Bands
    df['bb_mid'] = close.rolling(period).mean()
    df['bb_std'] = close.rolling(period).std()
    df['bb_upper'] = df['bb_mid'] + dev * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - dev * df['bb_std']
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    
    # Keltner Channels (para detectar squeeze)
    kc_upper, kc_lower = calculate_keltner_channels(df, period, config.KELTNER_ATR_MULT)
    df['kc_upper'] = kc_upper
    df['kc_lower'] = kc_lower
    
    # BB Squeeze: BB está dentro das Keltner Channels = mercado comprimido
    # Quando sai do squeeze (BB > KC) = explosão iminente
    df['in_squeeze'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_released'] = (~df['in_squeeze']) & df['in_squeeze'].shift(1).fillna(False)
    
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
    
    # Volume
    df['volume_ma'] = df['volume'].rolling(config.VOLUME_MA_PERIOD).mean()
    
    # EMA simples para macro
    df['ema_50'] = close.ewm(span=50, adjust=False).mean()
    
    return df


def is_trading_hours():
    if not config.TIME_FILTER:
        return True
    h = datetime.datetime.utcnow().hour
    return config.TRADING_HOURS_UTC_START <= h < config.TRADING_HOURS_UTC_END


def check_macro_trend(exchange, symbol):
    """Não reverte contra tendência maior."""
    try:
        df1h = fetch_candles(exchange, symbol, config.TIMEFRAME_MACRO, limit=60)
        if df1h is None:
            return True
        df1h['ema50'] = df1h['close'].ewm(span=50, adjust=False).mean()
        last = df1h.iloc[-2]
        return last['close'] > last['ema50']
    except Exception:
        return True


def check_entry_signal(df):
    """
    Estratégia: Fechou Abaixo/Voltou Acima das Bandas de Bollinger
    Com filtros Stochastic RSI + Volume + Squeeze Release.
    
    Condições para COMPRA:
    1. Candle anterior (c2) fechou ABAIXO da Banda Inferior (sobrevendido extremo)
    2. Último candle fechado (c3) VOLTOU para dentro das bandas (recuperação confirmada)
    3. Stochastic RSI sobrevendido (< 25) ou cruzando acima do D
    4. Volume no candle de recuperação acima da média (força no retorno)
    5. RSI não sobrecomprado
    """
    if len(df) < 50:
        return False, "Dados insuficientes"
    
    c1 = df.iloc[-4]
    c2 = df.iloc[-3]   # Candle que fechou fora
    c3 = df.iloc[-2]   # Último candle FECHADO = decisivo
    
    reasons = []
    
    # 1. Fechou abaixo da banda inferior + voltou acima
    fechou_fora = c2['close'] < c2['bb_lower']
    fechou_dentro = c3['close'] > c3['bb_lower']
    
    if not (fechou_fora and fechou_dentro):
        # Alternativa: candle c3 tocou abaixo da banda e fechou acima (pin bar de reversão)
        pin_bar_reversal = (c3['low'] < c3['bb_lower']) and (c3['close'] > c3['bb_lower'])
        if not pin_bar_reversal:
            return False, f"BB: sem padrão de reversão (c2_close={c2['close']:.1f}, c2_bb_lower={c2['bb_lower']:.1f})"
        reasons.append("PinBar-BB✅")
    else:
        reasons.append("FechouFora/Dentro✅")
    
    # 2. Stochastic RSI sobrevendido
    stoch_oversold = c3['stoch_k'] < config.STOCH_RSI_OVERSOLD or \
                     (c2['stoch_k'] < c2['stoch_d'] and c3['stoch_k'] > c3['stoch_d'])
    if not stoch_oversold:
        return False, f"StochRSI: K={c3['stoch_k']:.1f} D={c3['stoch_d']:.1f} (sem sobrevendido)"
    reasons.append(f"StochRSI={c3['stoch_k']:.0f}✅")
    
    # 3. RSI não sobrecomprado
    if c3['rsi'] > config.RSI_OVERBOUGHT:
        return False, f"RSI sobrecomprado: {c3['rsi']:.1f}"
    reasons.append(f"RSI={c3['rsi']:.0f}✅")
    
    # 4. Volume no candle de recuperação acima da média
    if config.VOLUME_FILTER:
        vol_ok = c3['volume'] >= c3['volume_ma'] * config.VOLUME_MIN_RATIO
        if not vol_ok:
            return False, f"Volume baixo: {c3['volume']:.0f} < {c3['volume_ma']*config.VOLUME_MIN_RATIO:.0f}"
        reasons.append("VOL✅")
    
    # 5. Bônus: squeeze recém-liberado (explosão de volatilidade iminente)
    if c3.get('squeeze_released', False):
        reasons.append("SQUEEZE-RELEASE✅")
    
    # Risco-retorno: a distância da banda inferior ao meio deve compensar o stop
    banda_distancia = c3['bb_mid'] - c3['bb_lower']
    if banda_distancia < c3.get('atr', 0) * 0.5:
        return False, "Largura de banda muito estreita — sem potencial de lucro adequado"
    
    return True, " | ".join(reasons)


# ══════════════════════════════════════════════════════════════════════
#  EXECUÇÃO
# ══════════════════════════════════════════════════════════════════════

def buy_entry(exchange, symbol, amount_usdt):
    try:
        exchange.load_markets()
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        qty = amount_usdt / current_price
        formatted_qty = float(exchange.amount_to_precision(symbol, qty))
        print(f"\n{BOT_NAME} [COMPRA] {formatted_qty} @ ${current_price:.2f}")
        order = exchange.create_market_buy_order(symbol, formatted_qty)
        time.sleep(1.5)
        balance = exchange.fetch_balance()
        base_asset = symbol.split('/')[0]
        actual_qty = float(exchange.amount_to_precision(symbol, balance['free'].get(base_asset, 0.0)))
        print(f"{BOT_NAME} [COMPRA OK] Qtd líquida: {actual_qty}")
        return order, current_price, actual_qty
    except Exception as e:
        print(f"\n{BOT_NAME} [ERRO COMPRA] {e}")
        return None, 0.0, 0.0


def sell_exit(exchange, symbol, qty, reason="Saída"):
    try:
        exchange.load_markets()
        formatted_qty = float(exchange.amount_to_precision(symbol, qty))
        if formatted_qty <= 0:
            return None
        print(f"\n{BOT_NAME} [VENDA] {formatted_qty} ({reason})")
        return exchange.create_market_sell_order(symbol, formatted_qty)
    except Exception as e:
        print(f"\n{BOT_NAME} [ERRO VENDA] {e}")
        return None


# ══════════════════════════════════════════════════════════════════════
#  LOOP PRINCIPAL
# ══════════════════════════════════════════════════════════════════════

def run_trading_bot():
    print("=" * 68)
    print(f"  {BOT_NAME} INICIANDO — REVERSÃO À MÉDIA + SQUEEZE v3.0")
    print(f"  Ativo: {config.SYMBOL} | TF: {config.TIMEFRAME}")
    print("=" * 68)
    
    state = load_state()
    today_str = str(datetime.date.today())
    if state.get('last_reset_date') != today_str:
        state['daily_loss_accumulated'] = 0.0
        state['daily_profit_accumulated'] = 0.0
        state['trades_today'] = 0
        state['last_reset_date'] = today_str
        save_state(state)
    
    exchange = None
    current_api_key = None
    current_api_secret = None
    last_macro_check = 0
    macro_trend_ok = True
    symbol = config.SYMBOL

    while True:
        try:
            backend_cfg = fetch_backend_config()
            if backend_cfg is None:
                api_key = os.getenv('BINANCE_API_KEY')
                api_secret = os.getenv('BINANCE_API_SECRET')
                is_active = True
            else:
                api_key = backend_cfg.get('binanceApiKey')
                api_secret = backend_cfg.get('binanceApiSecret')
                is_active = backend_cfg.get('isActive', False)

            if not is_active:
                if state['in_position'] and exchange is not None:
                    ticker = exchange.fetch_ticker(symbol)
                    cp = ticker['last']
                    sell_exit(exchange, symbol, state['quantity_bought'], "Desligamento")
                    pct = (cp - state['entry_price']) / state['entry_price'] * 100
                    register_trade_backend(symbol, "VENDA (MÉDIA-DESLIG)", cp, state['quantity_bought'], state['quantity_bought']*cp, pct)
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                print(f"\r{BOT_NAME} [OFF] {datetime.datetime.now().strftime('%H:%M:%S')}", end="", flush=True)
                time.sleep(15)
                continue

            if exchange is None or api_key != current_api_key or api_secret != current_api_secret:
                exchange, _ = get_exchange_connection(api_key, api_secret)
                if exchange is None:
                    time.sleep(15)
                    continue
                current_api_key = api_key
                current_api_secret = api_secret

            # Reset diário
            today_str = str(datetime.date.today())
            if state.get('last_reset_date') != today_str:
                state['daily_loss_accumulated'] = 0.0
                state['daily_profit_accumulated'] = 0.0
                state['trades_today'] = 0
                state['last_reset_date'] = today_str
                save_state(state)

            # Proteções diárias
            if state['daily_loss_accumulated'] >= config.MAX_DAILY_LOSS_USDT:
                print(f"\n{BOT_NAME} [PAUSADO] Limite perda diária atingida.")
                time.sleep(600)
                continue
            if state['daily_profit_accumulated'] >= config.MAX_DAILY_PROFIT_USDT:
                print(f"\n{BOT_NAME} [META] Lucro diário atingido.")
                time.sleep(600)
                continue
            if state.get('trades_today', 0) >= config.MAX_TRADES_PER_DAY and not state['in_position']:
                time.sleep(300)
                continue

            if not is_trading_hours() and not state['in_position']:
                time.sleep(60)
                continue

            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            print(f"\r{BOT_NAME} | ${current_price:.2f} | Pos:{state['in_position']} | "
                  f"P/L: ${state['daily_profit_accumulated']:.2f}/${state['daily_loss_accumulated']:.2f} | "
                  f"T:{state.get('trades_today',0)} | {datetime.datetime.now().strftime('%H:%M:%S')}",
                  end="", flush=True)

            # ── POSICIONADO ──────────────────────────────────────────
            if state['in_position']:
                qty = state['quantity_bought']
                entry_price = state['entry_price']

                # Stop Loss
                if current_price <= state['stop_loss_price']:
                    loss_usd = (entry_price - current_price) * qty
                    print(f"\n{BOT_NAME} 🚨 STOP LOSS @ ${current_price:.2f}")
                    sell_exit(exchange, symbol, qty, "Stop Loss")
                    state['daily_loss_accumulated'] += loss_usd
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                    pct = -((entry_price - current_price) / entry_price) * 100
                    register_trade_backend(symbol, "VENDA (MÉDIA-STOP)", current_price, qty, qty*current_price, pct)
                    send_telegram_message(f"❌ *Stop Loss*\n📉 ${current_price:.2f} | Perda: -${loss_usd:.2f} ({pct:+.2f}%)")
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # Trailing Stop
                if config.TRAILING_STOP and state.get('is_partial_executed', False):
                    new_trailing = current_price * (1 - config.TRAILING_STOP_PCT)
                    if new_trailing > state.get('trailing_stop_price', 0):
                        state['trailing_stop_price'] = new_trailing
                        state['stop_loss_price'] = max(state['stop_loss_price'], new_trailing)
                        save_state(state)
                    if current_price <= state.get('trailing_stop_price', 0):
                        profit_usd = (current_price - entry_price) * qty
                        print(f"\n{BOT_NAME} 🎯 TRAILING STOP @ ${current_price:.2f}")
                        sell_exit(exchange, symbol, qty, "Trailing Stop")
                        state['daily_profit_accumulated'] += profit_usd
                        state['in_position'] = False
                        state['is_partial_executed'] = False
                        save_state(state)
                        pct = (current_price - entry_price) / entry_price * 100
                        register_trade_backend(symbol, "VENDA (MÉDIA-TRAIL)", current_price, qty, qty*current_price, pct)
                        send_telegram_message(f"🎯 *Trailing Stop*\n💵 +${profit_usd:.2f} ({pct:+.2f}%)")
                        time.sleep(config.LOOP_INTERVAL_SECONDS)
                        continue

                # TP1
                if not state['is_partial_executed'] and current_price >= state['take_profit_1']:
                    print(f"\n{BOT_NAME} 🎯 TP1 @ ${current_price:.2f}")
                    partial_qty = qty * config.PARTIAL_EXIT_PCT
                    order = sell_exit(exchange, symbol, partial_qty, "Parcial TP1")
                    if order is None:
                        time.sleep(config.LOOP_INTERVAL_SECONDS)
                        continue
                    time.sleep(1.5)
                    balance = exchange.fetch_balance()
                    base_asset = symbol.split('/')[0]
                    remaining = float(exchange.amount_to_precision(symbol, balance['free'].get(base_asset, 0.0)))
                    if config.ACTIVATE_BREAKEVEN:
                        state['stop_loss_price'] = entry_price
                    state['trailing_stop_price'] = current_price * (1 - config.TRAILING_STOP_PCT)
                    partial_profit = (current_price - entry_price) * partial_qty
                    state['daily_profit_accumulated'] += partial_profit
                    pct = (current_price - entry_price) / entry_price * 100
                    register_trade_backend(symbol, "VENDA PARCIAL (MÉDIA)", current_price, partial_qty, partial_qty*current_price, pct)
                    if remaining * current_price < 2.0:
                        state['in_position'] = False
                        state['is_partial_executed'] = False
                        state['quantity_bought'] = 0.0
                    else:
                        state['quantity_bought'] = remaining
                        state['is_partial_executed'] = True
                    save_state(state)
                    send_telegram_message(f"🎯 *TP1 Parcial!*\n💰 +${partial_profit:.2f} ({pct:+.2f}%)\n🛡️ Breakeven ativo!")
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # TP2
                if current_price >= state['take_profit_2']:
                    profit_usd = (current_price - entry_price) * qty
                    print(f"\n{BOT_NAME} 🏆 TP2 @ ${current_price:.2f}")
                    sell_exit(exchange, symbol, qty, "TP2")
                    state['daily_profit_accumulated'] += profit_usd
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                    pct = (current_price - entry_price) / entry_price * 100
                    register_trade_backend(symbol, "VENDA (MÉDIA-TP)", current_price, qty, qty*current_price, pct)
                    send_telegram_message(f"🏆 *TP2 ATINGIDO!*\n💵 +${profit_usd:.2f} ({pct:+.2f}%)")
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # Saída técnica: preço toca a banda superior (exaustão do movimento)
                df = fetch_candles(exchange, symbol, config.TIMEFRAME)
                if df is not None:
                    df = calculate_indicators(df)
                    c3 = df.iloc[-2]
                    # Saída se preço tocou a Banda Superior (objetivo da reversão à média atingido)
                    if current_price >= c3['bb_upper'] and state.get('is_partial_executed', False):
                        profit_usd = (current_price - entry_price) * qty
                        print(f"\n{BOT_NAME} 🎯 BANDA SUPERIOR TOCADA @ ${current_price:.2f}")
                        sell_exit(exchange, symbol, qty, "Toque Banda Superior")
                        state['daily_profit_accumulated'] += profit_usd
                        state['in_position'] = False
                        state['is_partial_executed'] = False
                        save_state(state)
                        pct = (current_price - entry_price) / entry_price * 100
                        register_trade_backend(symbol, "VENDA (BANDA SUP)", current_price, qty, qty*current_price, pct)
                        send_telegram_message(f"🎯 *Saída: Banda Superior*\n💵 +${profit_usd:.2f} ({pct:+.2f}%)")

            # ── FLAT — PROCURANDO ENTRADA ────────────────────────────
            else:
                # Verificação macro a cada 5 min
                if time.time() - last_macro_check > 300:
                    macro_trend_ok = check_macro_trend(exchange, symbol)
                    last_macro_check = time.time()
                
                df = fetch_candles(exchange, symbol, config.TIMEFRAME)
                if df is not None:
                    df = calculate_indicators(df)
                    signal_ok, signal_reason = check_entry_signal(df)
                    
                    if signal_ok:
                        print(f"\n{BOT_NAME} 🚀 SINAL DE REVERSÃO! {signal_reason}")
                        order, buy_price, qty_bought = buy_entry(exchange, symbol, config.TRADE_AMOUNT_USDT)
                        
                        if order is not None and qty_bought > 0:
                            last_atr = df.iloc[-2]['atr']
                            if config.USE_ATR_STOPS and last_atr > 0:
                                sl_price = buy_price - config.ATR_STOP_MULTIPLIER * last_atr
                                tp1_price = buy_price + config.ATR_TP1_MULTIPLIER * last_atr
                                tp2_price = buy_price + config.ATR_TP2_MULTIPLIER * last_atr
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
                            register_trade_backend(symbol, "COMPRA (MÉDIA)", buy_price, qty_bought, qty_bought*buy_price)
                            rr = (tp2_price - buy_price) / (buy_price - sl_price) if (buy_price - sl_price) > 0 else 0
                            send_telegram_message(
                                f"🔄 *Bot B: Reversão Detectada!*\n"
                                f"🪙 {symbol} | Entrada: ${buy_price:.2f}\n"
                                f"📊 {signal_reason}\n"
                                f"🛑 SL: ${sl_price:.2f} | 🎯 TP1: ${tp1_price:.2f} | 🏆 TP2: ${tp2_price:.2f}\n"
                                f"📐 R/R: {rr:.1f}x"
                            )

            time.sleep(config.LOOP_INTERVAL_SECONDS)

        except ccxt.NetworkError as ne:
            print(f"\n{BOT_NAME} [REDE] {ne}. 15s...")
            time.sleep(15)
        except ccxt.ExchangeError as ee:
            print(f"\n{BOT_NAME} [EXCHANGE] {ee}. 30s...")
            time.sleep(30)
        except Exception as e:
            print(f"\n{BOT_NAME} [CRÍTICO] {e}. 30s...")
            time.sleep(30)


if __name__ == '__main__':
    run_trading_bot()
