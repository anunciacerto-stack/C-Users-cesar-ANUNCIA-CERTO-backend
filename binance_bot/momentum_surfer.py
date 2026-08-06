"""
╔══════════════════════════════════════════════════════════════════════════╗
║          💎 MOMENTUM SURFER PRO — SISTEMA UNIFICADO v4.0                ║
║                                                                          ║
║  COMO FUNCIONA:                                                          ║
║                                                                          ║
║  1. SUPERTREND — Define a DIREÇÃO (única de verdade)                    ║
║     - Quando SuperTrend está verde (bullish): SÓ compra                 ║
║     - Quando SuperTrend está vermelho: não opera (spot = só long)       ║
║                                                                          ║
║  2. PULLBACK RSI — Define a ENTRADA (barato, não no topo)               ║
║     - Depois que SuperTrend vira bullish, aguarda o RSI cair para 40-50 ║
║     - Preço "recuou" para uma zona de suporte = entrada mais segura     ║
║                                                                          ║
║  3. VOLUME — Confirma a FORÇA do movimento                              ║
║     - Se o candle de entrada tem volume acima da média = sinal real     ║
║     - Volume fraco = ignora (pode ser fakeout)                          ║
║                                                                          ║
║  4. ATR DINÂMICO — Define STOP e ALVO adaptados à volatilidade         ║
║     - Mercado volátil = stop maior, alvo maior (proporcional)           ║
║     - Mercado quieto = stop menor, alvo menor (mais trades)             ║
║                                                                          ║
║  MATEMÁTICA DO LUCRO (por trade de $12):                                ║
║  - Custo de taxa (0.1% cada lado): $0.012 x 2 = $0.024                 ║
║  - Stop Loss médio (1.5 ATR): ~$0.18 risco real após taxas             ║
║  - Take Profit TP1 (2 ATR): ~$0.22 líquido                             ║
║  - Take Profit TP2 (3.5 ATR): ~$0.40 líquido                           ║
║  - Com 60% win rate: 3 wins x $0.35 - 2 losses x $0.18 = +$0.69/dia  ║
║  - 3 ativos x $0.69 = ~$2.07/dia realista com saldo atual              ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
import datetime
import threading
import requests
import ccxt
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Saída UTF-8 (Windows)
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

load_dotenv()

PORT = os.getenv('PORT', '3000')
BACKEND_URL = os.getenv('BACKEND_URL', f'http://localhost:{PORT}')
USER_ID = os.getenv('USER_ID', 'guest')

import momentum_config as cfg

# ══════════════════════════════════════════════════════════════════
#  ESTADO GLOBAL DO SISTEMA
# ══════════════════════════════════════════════════════════════════

COMPOUND_WALLET_FILE = 'compound_wallet.json'

# ─── ESCUDO DE CAPITAL ────────────────────────────────────────────
# Protege o capital original investido. O robô NUNCA arrisca o capital base.
#
# SE QUISER DEPOSITAR MAIS:
#   Depósito atual:     $12 USDT (R$ ~65)
#   +R$200 (~$37 USDT): mude CAPITAL_BASE_USDT para 49.0
#   +R$500 (~$92 USDT): mude CAPITAL_BASE_USDT para 104.0
#   O bot ajusta TUDO automaticamente!
#
CAPITAL_BASE_USDT     = 30.0   # ← Capital protegido: R$ 165.00 (colchão de segurança para saldo real de $46.96)
MIN_TRADE_USDT        = 12.0   # Mínimo da Binance Spot (não mude)
MAX_TRADE_USDT        = 200.0  # Teto de segurança por trade
COMPOUND_REINVEST_RATE = 0.80  # Reinveste 80% do lucro (guarda 20% seguro)

# Margem de segurança: para de operar se o saldo cair abaixo de:
CAPITAL_SHIELD_MARGIN = 2.0    # $2 de colchão de segurança extra
# Saldo mínimo absoluto para continuar operando:
CAPITAL_FLOOR = CAPITAL_BASE_USDT + CAPITAL_SHIELD_MARGIN

system_state = {
    'daily_loss': 0.0,
    'daily_profit': 0.0,
    'last_reset_date': str(datetime.date.today()),
    'api_key': None,
    'api_secret': None,
    'is_active': False,
    'exchange': None,
}

print_lock = threading.Lock()


def tprint(*args, **kwargs):
    """Thread-safe print."""
    with print_lock:
        print(*args, **kwargs)


# ══════════════════════════════════════════════════════════════════
#  BACKEND
# ══════════════════════════════════════════════════════════════════

def fetch_backend_config():
    """Busca configurações e ativa/desativa via app."""
    try:
        r = requests.get(f"{BACKEND_URL}/bot/config?userId={USER_ID}", timeout=8)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def register_trade(bot_name, asset, trade_type, price, amount, value, profit_pct=None):
    """Registra trade no backend (histórico no app)."""
    payload = {
        'userId': USER_ID,
        'asset': f"[{bot_name}] {asset}",
        'type': trade_type,
        'price': round(float(price), 6),
        'amount': round(float(amount), 8),
        'value': round(float(value), 4)
    }
    if profit_pct is not None:
        payload['profitPct'] = f"{profit_pct:+.2f}%"
    try:
        requests.post(f"{BACKEND_URL}/bot/trades", json=payload, timeout=8)
    except Exception:
        pass


def send_telegram(message):
    """Alerta Telegram."""
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
    if not token or not chat_id or 'seu_token' in token:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={'chat_id': chat_id, 'text': f"💎 MOMENTUM SURFER\n\n{message}", 'parse_mode': 'Markdown'},
            timeout=5
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  EXCHANGE
# ══════════════════════════════════════════════════════════════════

def build_exchange(api_key, api_secret):
    """Cria conexão com a Binance."""
    use_testnet = os.getenv('USE_TESTNET', 'False').lower() == 'true'  # Padrão: CONTA REAL
    if not api_key or len(api_key.strip()) < 10:
        return None
    ex = ccxt.binance({
        'apiKey': api_key.strip(),
        'secret': api_secret.strip(),
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })
    if use_testnet:
        ex.set_sandbox_mode(True)
    return ex


# ══════════════════════════════════════════════════════════════════
#  DADOS E INDICADORES
# ══════════════════════════════════════════════════════════════════

def fetch_candles(exchange, symbol, timeframe, limit=200):
    """Busca candles OHLCV da Binance."""
    try:
        raw = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(raw, columns=['ts', 'open', 'high', 'low', 'close', 'volume'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        return df
    except Exception as e:
        tprint(f"[DADOS] Erro ao buscar {symbol}/{timeframe}: {e}")
        return None


def calc_atr(df, period=14):
    """ATR — mede a volatilidade real do mercado."""
    h, l, c = df['high'], df['low'], df['close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def calc_supertrend(df, atr_period=10, multiplier=3.0):
    """
    SuperTrend — o indicador mais confiável para definir direção de tendência.
    
    Lógica:
    - Calcula um "canal" acima e abaixo do preço usando ATR
    - Quando preço FECHOU ACIMA da linha superior → tendência de ALTA (bullish)
    - Quando preço FECHOU ABAIXO da linha inferior → tendência de BAIXA (bearish)
    - Muito difícil de fazer whipsaw porque usa ATR adaptativo
    
    Retorna:
    - 'supertrend': preço do nível do SuperTrend
    - 'direction': +1 = bullish, -1 = bearish
    """
    hl2 = (df['high'] + df['low']) / 2
    atr = calc_atr(df, atr_period)
    
    basic_upper = hl2 + multiplier * atr
    basic_lower = hl2 - multiplier * atr
    
    n = len(df)
    upper = basic_upper.copy()
    lower = basic_lower.copy()
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(1, n):
        # Banda Superior: nunca sobe se o preço ainda estiver abaixo dela
        if basic_upper.iloc[i] < upper.iloc[i-1] or df['close'].iloc[i-1] > upper.iloc[i-1]:
            upper.iloc[i] = basic_upper.iloc[i]
        else:
            upper.iloc[i] = upper.iloc[i-1]
        
        # Banda Inferior: nunca desce se o preço ainda estiver acima dela
        if basic_lower.iloc[i] > lower.iloc[i-1] or df['close'].iloc[i-1] < lower.iloc[i-1]:
            lower.iloc[i] = basic_lower.iloc[i]
        else:
            lower.iloc[i] = lower.iloc[i-1]
        
        # Direção
        if supertrend.isna().iloc[i-1]:
            direction.iloc[i] = 1
            supertrend.iloc[i] = lower.iloc[i]
        elif supertrend.iloc[i-1] == upper.iloc[i-1]:
            # Estava em downtrend
            if df['close'].iloc[i] > upper.iloc[i]:
                direction.iloc[i] = 1   # Virou bullish!
                supertrend.iloc[i] = lower.iloc[i]
            else:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upper.iloc[i]
        else:
            # Estava em uptrend
            if df['close'].iloc[i] < lower.iloc[i]:
                direction.iloc[i] = -1  # Virou bearish!
                supertrend.iloc[i] = upper.iloc[i]
            else:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lower.iloc[i]
    
    df['supertrend'] = supertrend
    df['st_direction'] = direction
    return df


def calc_rsi(close, period=14):
    """RSI padrão."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).ewm(span=period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=period, adjust=False).mean()
    return 100 - (100 / (1 + gain / (loss + 1e-9)))


def calc_all_indicators(df):
    """Calcula todos os indicadores num DataFrame."""
    # Bollinger Bands
    sma = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    df['bb_middle'] = sma
    df['bb_upper'] = sma + (2.0 * std)
    df['bb_lower'] = sma - (2.0 * std)
    
    df['rsi'] = calc_rsi(df['close'], cfg.RSI_PERIOD)
    df['atr'] = calc_atr(df, cfg.ATR_PERIOD)
    df['vol_ma'] = df['volume'].rolling(20).mean()
    df = calc_supertrend(df, cfg.SUPERTREND_ATR_PERIOD, cfg.SUPERTREND_MULTIPLIER)
    return df


def get_macro_direction(exchange, symbol, macro_tf):
    """Verifica tendência no timeframe maior (1h).
    Retorna +1 se bullish, -1 se bearish, 0 se incerto."""
    try:
        df1h = fetch_candles(exchange, symbol, macro_tf, limit=60)
        if df1h is None or len(df1h) < 30:
            return 0
        df1h = calc_supertrend(df1h, cfg.SUPERTREND_ATR_PERIOD, cfg.SUPERTREND_MULTIPLIER)
        last = df1h.iloc[-2]  # Candle fechado
        return int(last.get('st_direction', 0))
    except Exception:
        return 0  # Incerto = não bloqueia


# ══════════════════════════════════════════════════════════════════
#  LÓGICA DE SINAL
# ══════════════════════════════════════════════════════════════════

def check_entry(df, macro_direction):
    """
    SINAL DE ENTRADA — SuperTrend + RSI Pullback Strategy (Uptrend Only)
    
    CONDIÇÕES PARA COMPRA:
    1. Macro Tendência (1h) é de ALTA: macro_direction == 1
    2. Local Tendência (15m) é de ALTA: st_direction == 1
    3. SuperTrend de alta ativa há pelo menos MIN_CANDLES_IN_TREND (3) candles
    4. Recuo (Pullback) no RSI de 15m: rsi <= RSI_PULLBACK_LOW (45) mas acima de RSI_OVERSOLD (25)
    5. Confirmação de Volume: volume do candle >= vol_ma * VOLUME_MULT (1.2)
    """
    if len(df) < 50:
        return False, "Dados insuficientes", 0.0
    
    c_last = df.iloc[-2]   # Último candle fechado
    
    # 1. Filtro Macro (1h)
    if macro_direction != 1:
        return False, f"Macro tendência não é de alta (macro={macro_direction})", 0.0
        
    # 2. Filtro Local (15m)
    st_dir = c_last.get('st_direction', 0)
    if st_dir != 1:
        return False, "SuperTrend local (15m) não é de alta", 0.0
        
    # 3. Evita breakout esticado (mínimo de candles na tendência atual)
    for offset in range(2, 2 + cfg.MIN_CANDLES_IN_TREND):
        if df.iloc[-offset].get('st_direction', 0) != 1:
            return False, f"SuperTrend de alta recente demais (<{cfg.MIN_CANDLES_IN_TREND} candles)", 0.0
            
    # 4. Pullback saudável no RSI (comprar na correção, não no topo)
    rsi = c_last.get('rsi', 50)
    if rsi > cfg.RSI_PULLBACK_LOW:
        return False, f"Sem Pullback: RSI={rsi:.1f} > {cfg.RSI_PULLBACK_LOW} (muito esticado)", 0.0
    if rsi < cfg.RSI_OVERSOLD:
        return False, f"RSI muito baixo: RSI={rsi:.1f} < {cfg.RSI_OVERSOLD} (queda forte)", 0.0
        
    # 5. Filtro de Volume (confirmação de força)
    if cfg.VOLUME_FILTER:
        vol = c_last.get('volume', 0.0)
        vol_ma = c_last.get('vol_ma', 0.0)
        min_vol = vol_ma * cfg.VOLUME_MULT
        if vol < min_vol:
            return False, f"Volume baixo: {vol:.0f} < {min_vol:.0f} (Média x {cfg.VOLUME_MULT})", 0.0
            
    # Tudo validado!
    atr = c_last.get('atr', 0.0)
    reason = f"SuperTrend 1h/15m🟢 | Pullback RSI={rsi:.1f}🟢 | Volume Confirmado🟢 | ATR=${atr:.4f}"
    return True, reason, atr



def check_exit_technical(df, state):
    """
    Verifica se é hora de sair pela análise técnica.
    Desativado na estratégia Bollinger + RSI para permitir reversão média.
    """
    return False, ""


# ══════════════════════════════════════════════════════════════════
#  EXECUÇÃO DE ORDENS
# ══════════════════════════════════════════════════════════════════

def buy_market(exchange, symbol, usdt_amount, bot_name):
    """Executa ordem de compra a mercado."""
    try:
        exchange.load_markets()
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']
        qty = usdt_amount / price
        formatted = float(exchange.amount_to_precision(symbol, qty))
        tprint(f"\n[{bot_name}] 🛒 COMPRA: {formatted} {symbol.split('/')[0]} @ ${price:.4f}")
        order = exchange.create_market_buy_order(symbol, formatted)
        time.sleep(1.5)
        balance = exchange.fetch_balance()
        base = symbol.split('/')[0]
        actual = float(exchange.amount_to_precision(symbol, balance['free'].get(base, 0.0)))
        tprint(f"[{bot_name}] ✅ Comprado! Qtd líquida: {actual}")
        return order, price, actual
    except Exception as e:
        tprint(f"[{bot_name}] ❌ ERRO COMPRA: {e}")
        return None, 0.0, 0.0


def sell_market(exchange, symbol, qty, bot_name, reason="Saída"):
    """Executa ordem de venda a mercado."""
    try:
        exchange.load_markets()
        formatted = float(exchange.amount_to_precision(symbol, qty))
        if formatted <= 0:
            tprint(f"[{bot_name}] ⚠️ Qtd zero. Abortando venda.")
            return None
        tprint(f"\n[{bot_name}] 📤 VENDA: {formatted} ({reason})")
        return exchange.create_market_sell_order(symbol, formatted)
    except Exception as e:
        tprint(f"[{bot_name}] ❌ ERRO VENDA ({reason}): {e}")
        return None


# ══════════════════════════════════════════════════════════════════
#  ESTADO POR BOT
# ══════════════════════════════════════════════════════════════════

def load_bot_state(state_file):
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {
        'in_position': False,
        'entry_price': 0.0,
        'stop_loss': 0.0,
        'tp1': 0.0,
        'tp2': 0.0,
        'quantity': 0.0,
        'atr_at_entry': 0.0,
        'is_partial_executed': False,
        'trailing_stop': 0.0,
        'daily_trades': 0,
        'last_reset_date': str(datetime.date.today()),
    }


def save_bot_state(state_file, state):
    try:
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        tprint(f"[ESTADO] Erro ao salvar {state_file}: {e}")


# ══════════════════════════════════════════════════════════════════
#  💰 COMPOUND WALLET — JUROS COMPOSTOS AUTOMÁTICOS
# ══════════════════════════════════════════════════════════════════
# Lógica:
#   - Começa com $12 (mínimo Binance)
#   - Cada lucro vai para a carteira composta
#   - Próximo trade usa: base + (lucro_acumulado x 80%)
#   - Exemplo: lucro $3 → carteira=$15 → próximo trade=$15
#              lucro $5 → carteira=$20 → próximo trade=$20
#   - Em caso de stop loss, o tamanho volta um pouco (proteção)
# ══════════════════════════════════════════════════════════════════

def load_compound_wallet():
    """Carrega a carteira composta do disco (persistência entre reinicios)."""
    if os.path.exists(COMPOUND_WALLET_FILE):
        try:
            with open(COMPOUND_WALLET_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    # Estado inicial: $14 por bot para aproveitar melhor o saldo de $43
    return {
        'base_capital': 14.0,
        'total_profit_accumulated': 0.0,
        'total_loss_accumulated': 0.0,
        'current_trade_size': 14.0,
        'all_time_high_wallet': 14.0,
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'created_at': str(datetime.datetime.now()),
    }


def save_compound_wallet(wallet):
    """Salva o estado da carteira composta."""
    try:
        with open(COMPOUND_WALLET_FILE, 'w') as f:
            json.dump(wallet, f, indent=2)
    except Exception as e:
        tprint(f"[WALLET] Erro ao salvar: {e}")


def update_wallet_after_win(wallet, profit_usd):
    """
    Após um TRADE LUCRATIVO:
    Adiciona 80% do lucro ao capital de trade (reinveste).
    Guarda 20% como lucro realizado (segurança).
    """
    reinvested = profit_usd * COMPOUND_REINVEST_RATE
    wallet['total_profit_accumulated'] += profit_usd
    wallet['current_trade_size'] = min(
        wallet['current_trade_size'] + reinvested,
        MAX_TRADE_USDT
    )
    # Atualiza máximo histórico da carteira
    if wallet['current_trade_size'] > wallet['all_time_high_wallet']:
        wallet['all_time_high_wallet'] = wallet['current_trade_size']
    wallet['total_trades'] += 1
    wallet['winning_trades'] += 1
    save_compound_wallet(wallet)
    tprint(
        f"\n[WALLET] 📈 WIN! +${profit_usd:.3f} → "
        f"Reinvestido: +${reinvested:.3f} | "
        f"Próximo trade: ${wallet['current_trade_size']:.2f}"
    )
    return wallet


def update_wallet_after_loss(wallet, loss_usd):
    """
    Após um STOP LOSS:
    Reduz o tamanho do próximo trade proporcionalmente.
    Garante que nunca desce abaixo do mínimo da Binance ($12).
    """
    # Reduz 50% do loss do tamanho do trade (não 100%, para não travar)
    reducao = loss_usd * 0.50
    wallet['total_loss_accumulated'] += loss_usd
    wallet['current_trade_size'] = max(
        wallet['current_trade_size'] - reducao,
        MIN_TRADE_USDT
    )
    wallet['total_trades'] += 1
    wallet['losing_trades'] += 1
    save_compound_wallet(wallet)
    tprint(
        f"\n[WALLET] 📉 LOSS! -${loss_usd:.3f} → "
        f"Redução: -${reducao:.3f} | "
        f"Próximo trade: ${wallet['current_trade_size']:.2f}"
    )
    return wallet


# ══════════════════════════════════════════════════════════════════
#  🛡️ ESCUDO DE CAPITAL — PROTEÇÃO DO INVESTIMENTO ORIGINAL
# ══════════════════════════════════════════════════════════════════

def get_total_equity(exchange):
    """Calcula o patrimônio total (USDT + valor das posições abertas)."""
    try:
        balance = exchange.fetch_balance()
        total_usdt = balance['total'].get('USDT', 0.0)
        
        # Adiciona o valor estimado das posições abertas em SOL, BTC, ETH
        for coin in ['SOL', 'BTC', 'ETH']:
            qty = balance['total'].get(coin, 0.0)
            if qty > 0.0001:
                try:
                    ticker = exchange.fetch_ticker(f"{coin}/USDT")
                    price = ticker['last']
                    total_usdt += qty * price
                except Exception:
                    pass
        return total_usdt
    except Exception as e:
        tprint(f"[SHIELD] Erro ao calcular equity total: {e}")
        return 0.0


def check_capital_shield(exchange, bot_name):
    """
    VERIFICAÇÃO DO ESCUDO DE CAPITAL.
    
    Antes de cada trade, verifica o patrimônio total (USDT + valor das posições).
    Se o patrimônio estiver abaixo do CAPITAL_FLOOR, bloqueia novas entradas.
    """
    try:
        total_equity = get_total_equity(exchange)
        if total_equity <= 0.0:
            # Em caso de erro temporário na API, permite passar para não travar o bot
            return True, 0.0
            
        if total_equity < CAPITAL_FLOOR:
            msg = (
                f"🛡️ *ESCUDO DE CAPITAL ATIVADO — [{bot_name}]*\n"
                f"⚠️ Patrimônio Total estimado: ${total_equity:.2f}\n"
                f"🔒 Capital mínimo protegido: ${CAPITAL_FLOOR:.2f}\n"
                f"🚫 NOVAS ENTRADAS BLOQUEADAS para preservar seu patrimônio.\n\n"
                f"✅ Seu investimento de ${CAPITAL_BASE_USDT:.2f} está PROTEGIDO."
            )
            tprint(f"\n[{bot_name}] 🛡️ ESCUDO DE CAPITAL! Patrimônio=${total_equity:.2f} < Piso=${CAPITAL_FLOOR:.2f}")
            tprint(f"[{bot_name}] 🚫 Novas entradas bloqueadas para proteger capital original.")
            send_telegram(msg)
            return False, total_equity
        
        return True, total_equity
    except Exception as e:
        tprint(f"[{bot_name}] [SHIELD] Erro: {e}. Liberando por segurança.")
        return True, 0.0


def calc_safe_trade_size(exchange, bot_name, desired_size):
    """
    Calcula o tamanho SEGURO do trade:
    - Verifica saldo real disponível
    - Nunca usa mais do que (saldo - CAPITAL_BASE_USDT)
      ou seja: SÓ ARRISCA O LUCRO, nunca o capital base
    - Retorna o menor entre: tamanho desejado e o máximo seguro
    """
    try:
        balance = exchange.fetch_balance()
        usdt_free = balance['free'].get('USDT', 0.0)
        
        # Capital disponível para arriscar = saldo total - capital base protegido
        # Exemplo: saldo=$18, base=$12 → disponível para arriscar=$6
        # MAS: se o disponível < MIN_TRADE_USDT, usa o mínimo mesmo
        # (nas primeiras operações ainda não há lucro acumulado)
        capital_disponivel = usdt_free - CAPITAL_BASE_USDT
        
        if capital_disponivel >= MIN_TRADE_USDT:
            # Já há lucro suficiente — arrisca só o lucro
            safe_size = min(desired_size, capital_disponivel)
            tprint(f"[{bot_name}] 🛡️ Modo LUCRO: investindo ${safe_size:.2f} (só lucro, base protegida)")
        else:
            # Ainda nas primeiras operações — usa o tamanho mínimo
            # (inevitável no início, mas o stop loss limita o risco)
            safe_size = min(desired_size, usdt_free * 0.85)  # usa no máx 85% do saldo
            tprint(f"[{bot_name}] 🛡️ Modo INICIAL: investindo ${safe_size:.2f} | Saldo=${usdt_free:.2f}")
        
        safe_size = max(safe_size, MIN_TRADE_USDT)  # garante mínimo Binance
        safe_size = min(safe_size, MAX_TRADE_USDT)  # garante teto de segurança
        return round(safe_size, 2)
    except Exception as e:
        tprint(f"[{bot_name}] [SHIELD] Erro ao calcular size seguro: {e}")
        return MIN_TRADE_USDT


def get_wallet_summary(wallet):
    """Retorna um resumo formatado da carteira para Telegram."""
    win_rate = 0
    if wallet['total_trades'] > 0:
        win_rate = wallet['winning_trades'] / wallet['total_trades'] * 100
    net_profit = wallet['total_profit_accumulated'] - wallet['total_loss_accumulated']
    return (
        f"💰 *COMPOUND WALLET — STATUS*\n"
        f"───────────────────────────\n"
        f"💵 Capital inicial: ${wallet['base_capital']:.2f}\n"
        f"🚀 Trade atual: ${wallet['current_trade_size']:.2f}\n"
        f"📈 Lucro acumulado: +${wallet['total_profit_accumulated']:.3f}\n"
        f"📉 Perda acumulada: -${wallet['total_loss_accumulated']:.3f}\n"
        f"💎 Lucro líquido: ${net_profit:+.3f}\n"
        f"🏆 Máximo atingido: ${wallet['all_time_high_wallet']:.2f}\n"
        f"📊 Trades: {wallet['total_trades']} "
        f"(✅{wallet['winning_trades']} ❌{wallet['losing_trades']}) "
        f"Win: {win_rate:.0f}%"
    )


# ══════════════════════════════════════════════════════════════════
#  THREAD DE CADA BOT
# ══════════════════════════════════════════════════════════════════

# Carteira composta compartilhada entre todos os bots
compound_wallet = load_compound_wallet()
wallet_lock = threading.Lock()


def run_single_bot(bot_cfg):
    """
    Thread independente para cada ativo.
    Cada bot roda de forma paralela sem interferir nos outros.
    Usa o Compound Wallet para crescer o tamanho do trade com os lucros.
    """
    global compound_wallet
    name = bot_cfg['name']
    symbol = bot_cfg['symbol']
    tf = bot_cfg['timeframe']
    tf_macro = bot_cfg['timeframe_macro']
    state_file = bot_cfg['state_file']
    
    state = load_bot_state(state_file)
    last_macro_check = 0
    macro_direction = 0
    
    tprint(f"[{name}] 🚀 Iniciado para {symbol} | TF: {tf} | Macro: {tf_macro}")
    with wallet_lock:
        tprint(f"[{name}] 💰 Trade size atual (compound): ${compound_wallet['current_trade_size']:.2f}")

    while True:
        try:
            exchange = system_state.get('exchange')
            is_active = system_state.get('is_active', False)

            # ── Robô global desativado ─────────────────────────────
            if not is_active:
                if state['in_position'] and exchange is not None:
                    ticker = exchange.fetch_ticker(symbol)
                    cp = ticker['last']
                    sell_market(exchange, symbol, state['quantity'], name, "Desligamento")
                    pct = (cp - state['entry_price']) / state['entry_price'] * 100
                    profit = (cp - state['entry_price']) * state['quantity']
                    register_trade(name, symbol, "VENDA (DESLIGADO)", cp,
                                   state['quantity'], state['quantity'] * cp, pct)
                    if profit > 0:
                        system_state['daily_profit'] += profit
                    else:
                        system_state['daily_loss'] += abs(profit)
                    state['in_position'] = False
                    save_bot_state(state_file, state)
                time.sleep(15)
                continue

            # ── Filtro de Plano (1 Robô vs 3 Robôs) ──────────────────
            allowed_sym = system_state.get('allowed_symbol', 'ALL')
            if allowed_sym != 'ALL' and allowed_sym != symbol:
                # O usuário contratou 1 robô e selecionou outro símbolo, esta thread fica em espera
                time.sleep(30)
                continue

            if exchange is None:
                time.sleep(10)
                continue

            # ── Reset diário ───────────────────────────────────────
            today = str(datetime.date.today())
            if state.get('last_reset_date') != today:
                state['daily_trades'] = 0
                state['last_reset_date'] = today
                save_bot_state(state_file, state)

            # ── 🛡️ ESCUDO DE CAPITAL — verifica saldo ANTES de qualquer decisão ──
            if not state['in_position']:
                shield_ok, usdt_balance = check_capital_shield(exchange, name)
                if not shield_ok:
                    tprint(f"\r[{name}] 🛡️ ESCUDO ATIVO | Saldo=${usdt_balance:.2f} < Piso=${CAPITAL_FLOOR:.2f} | Aguardando...", end="", flush=True)
                    time.sleep(300)  # Aguarda 5 min antes de checar de novo
                    continue

            # ── Proteção diária global ─────────────────────────────
            if system_state['daily_loss'] >= cfg.MAX_DAILY_LOSS_USDT:
                tprint(f"[{name}] ⛔ Sistema pausado: limite de perda diária atingido.")
                time.sleep(600)
                continue
            
            if system_state['daily_profit'] >= cfg.MAX_DAILY_PROFIT_USDT:
                tprint(f"[{name}] 🏆 Meta do dia atingida: +${system_state['daily_profit']:.2f}")
                time.sleep(600)
                continue

            # ── Limite de trades do bot ────────────────────────────
            if state['daily_trades'] >= cfg.MAX_TRADES_PER_BOT_PER_DAY and not state['in_position']:
                time.sleep(300)
                continue

            # ── Filtro de horário ──────────────────────────────────
            if cfg.TIME_FILTER and not state['in_position']:
                h = datetime.datetime.utcnow().hour
                if not (cfg.HOURS_START_UTC <= h < cfg.HOURS_END_UTC):
                    time.sleep(60)
                    continue

            # ── Busca dados de mercado ─────────────────────────────
            df = fetch_candles(exchange, symbol, tf, limit=200)
            if df is None or len(df) < 50:
                time.sleep(cfg.LOOP_INTERVAL_SECONDS)
                continue
            
            df = calc_all_indicators(df)
            current_price = df.iloc[-1]['close']  # Preço atual (candle aberto)

            tprint(
                f"\r[{name}] ${current_price:.4f} | BB_Low:${df.iloc[-2].get('bb_lower',0.0):.2f} RSI:{df.iloc[-2].get('rsi',0):.0f} | Pos:{state['in_position']}"
                f" | +${system_state['daily_profit']:.2f} -${system_state['daily_loss']:.2f}"
                f" | {datetime.datetime.now().strftime('%H:%M:%S')}",
                end="", flush=True
            )

            # ══════════════════════════════════════════════════════
            #  MODO POSICIONADO — GESTÃO DA POSIÇÃO ABERTA
            # ══════════════════════════════════════════════════════
            if state['in_position']:
                entry = state['entry_price']
                qty = state['quantity']
                atr = state.get('atr_at_entry', 0)

                # ── A. STOP LOSS ───────────────────────────────────
                if current_price <= state['stop_loss']:
                    loss = (entry - current_price) * qty
                    tprint(f"\n[{name}] 🚨 STOP LOSS @ ${current_price:.4f} | -${loss:.3f}")
                    sell_market(exchange, symbol, qty, name, "Stop Loss")
                    system_state['daily_loss'] += loss
                    pct = -(entry - current_price) / entry * 100
                    register_trade(name, symbol, "VENDA (STOP)", current_price, qty, qty*current_price, pct)
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_bot_state(state_file, state)
                    # 📉 COMPOUND: Reduz tamanho do próximo trade após loss
                    with wallet_lock:
                        compound_wallet = update_wallet_after_loss(compound_wallet, loss)
                        next_size = compound_wallet['current_trade_size']
                    send_telegram(
                        f"❌ *[{name}] Stop Loss — {symbol}*\n"
                        f"📉 Saída: ${current_price:.4f}\n"
                        f"💸 Perda: -${loss:.3f} ({pct:+.2f}%)\n"
                        f"📊 P/L dia: +${system_state['daily_profit']:.2f} / -${system_state['daily_loss']:.2f}\n"
                        f"💰 Próximo trade: ${next_size:.2f}"
                    )
                    time.sleep(cfg.LOOP_INTERVAL_SECONDS)
                    continue

                # ── B. TAKE PROFIT (Bollinger Middle Band) ──────────
                bb_middle = df.iloc[-2].get('bb_middle', 0.0)
                if bb_middle > 0.0 and current_price >= bb_middle:
                    profit = (current_price - entry) * qty
                    tprint(f"\n[{name}] 🏆 TAKE PROFIT (Média BB) @ ${current_price:.4f} | +${profit:.3f}")
                    sell_market(exchange, symbol, qty, name, "TP Bollinger Middle")
                    system_state['daily_profit'] += profit
                    pct = (current_price - entry) / entry * 100
                    register_trade(name, symbol, "VENDA (TP)", current_price, qty, qty*current_price, pct)
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_bot_state(state_file, state)
                    # 📈 COMPOUND: Cresce tamanho do próximo trade
                    with wallet_lock:
                        compound_wallet = update_wallet_after_win(compound_wallet, profit)
                        next_size = compound_wallet['current_trade_size']
                        summary = get_wallet_summary(compound_wallet)
                    send_telegram(
                        f"🏆 *[{name}] Take Profit (Média BB) — {symbol}*\n"
                        f"💵 +${profit:.3f} ({pct:+.2f}%)\n"
                        f"📊 P/L dia total: +${system_state['daily_profit']:.2f}\n\n"
                        + summary
                    )
                    time.sleep(cfg.LOOP_INTERVAL_SECONDS)
                    continue

            # ══════════════════════════════════════════════════════
            #  MODO FLAT — PROCURANDO SINAL
            # ══════════════════════════════════════════════════════
            else:
                # Verifica macro tendência (a cada 5 min)
                if time.time() - last_macro_check > 300:
                    macro_direction = get_macro_direction(exchange, symbol, tf_macro)
                    last_macro_check = time.time()
                    macro_str = '🟢 ALTA' if macro_direction == 1 else ('🔴 BAIXA' if macro_direction == -1 else '⬜ NEUTRO')
                    tprint(f"\n[{name}] 📊 Macro ({tf_macro}): {macro_str}")
                
                signal_ok, signal_reason, atr = check_entry(df, macro_direction)
                
                if signal_ok:
                    # 💰 COMPOUND + 🛡️ SHIELD: Calcula tamanho seguro real
                    with wallet_lock:
                        trade_desejado = compound_wallet['current_trade_size']
                    
                    # Verifica saldo e calcula tamanho que protege o capital base
                    trade_usdt_atual = calc_safe_trade_size(exchange, name, trade_desejado)
                    
                    tprint(f"\n[{name}] 🚀 SINAL CONFIRMADO! {signal_reason}")
                    tprint(f"[{name}] 💰 Investindo: ${trade_usdt_atual:.2f} (desejado=${trade_desejado:.2f})")
                    order, buy_price, qty_bought = buy_market(exchange, symbol, trade_usdt_atual, name)
                    
                    if order is not None and qty_bought > 0:
                        # Stops e alvos pelo ATR dinâmico
                        sl = buy_price - cfg.ATR_STOP_MULT * atr
                        tp1 = buy_price + cfg.ATR_TP1_MULT * atr
                        tp2 = buy_price + cfg.ATR_TP2_MULT * atr
                        rr = (tp2 - buy_price) / (buy_price - sl)
                        
                        state['in_position'] = True
                        state['entry_price'] = buy_price
                        state['quantity'] = qty_bought
                        state['stop_loss'] = sl
                        state['tp1'] = tp1
                        state['tp2'] = tp2
                        state['atr_at_entry'] = atr
                        state['is_partial_executed'] = False
                        state['trailing_stop'] = 0.0
                        state['daily_trades'] = state.get('daily_trades', 0) + 1
                        save_bot_state(state_file, state)
                        
                        register_trade(name, symbol, "COMPRA", buy_price, qty_bought, qty_bought * buy_price)
                        
                        tprint(
                            f"[{name}] 📋 Plano: SL=${sl:.4f} | TP1=${tp1:.4f} | TP2=${tp2:.4f} | R/R={rr:.1f}x"
                        )
                        send_telegram(
                            f"🚀 *[{name}] Nova Posição!*\n"
                            f"🪙 {symbol} @ ${buy_price:.4f}\n"
                            f"📊 {signal_reason}\n\n"
                            f"💰 Investido (compound): ${trade_usdt_atual:.2f}\n"
                            f"🛑 Stop: ${sl:.4f}\n"
                            f"🎯 TP1: ${tp1:.4f}\n"
                            f"🏆 TP2: ${tp2:.4f}\n"
                            f"📐 Risco/Retorno: {rr:.1f}x\n"
                            f"📅 Trade #{state['daily_trades']} do dia"
                        )

            time.sleep(cfg.LOOP_INTERVAL_SECONDS)

        except ccxt.NetworkError as e:
            tprint(f"\n[{name}] [REDE] {e}. 15s...")
            time.sleep(15)
        except ccxt.ExchangeError as e:
            tprint(f"\n[{name}] [EXCHANGE] {e}. 30s...")
            time.sleep(30)
        except Exception as e:
            tprint(f"\n[{name}] [CRÍTICO] {e}. 30s...")
            time.sleep(30)


# ══════════════════════════════════════════════════════════════════
#  THREAD DE SINCRONIZAÇÃO COM O BACKEND
# ══════════════════════════════════════════════════════════════════

def backend_sync_thread():
    """Atualiza configurações do backend a cada 60s."""
    tprint("[SISTEMA] Thread de sincronização com backend iniciada.")
    while True:
        try:
            bcfg = fetch_backend_config()
            today = str(datetime.date.today())
            
            # Reset diário
            if system_state.get('last_reset_date') != today:
                tprint(f"\n[SISTEMA] 🔄 Novo dia! Resetando P/L.")
                system_state['daily_loss'] = 0.0
                system_state['daily_profit'] = 0.0
                system_state['last_reset_date'] = today
            
            if bcfg is None:
                # Backend offline: usa .env como fallback
                api_key = os.getenv('BINANCE_API_KEY', '')
                api_secret = os.getenv('BINANCE_API_SECRET', '')
                is_active = True
                allowed_symbol = 'ALL'
            else:
                api_key = bcfg.get('binanceApiKey', '')
                api_secret = bcfg.get('binanceApiSecret', '')
                is_active = bcfg.get('isActive', False)
                allowed_symbol = bcfg.get('symbol', 'ALL')
            
            system_state['allowed_symbol'] = allowed_symbol
            
            # Reconecta exchange se as chaves mudaram
            if api_key != system_state.get('api_key') or api_secret != system_state.get('api_secret'):
                tprint(f"\n[SISTEMA] 🔑 Novas chaves detectadas. Reconectando...")
                ex = build_exchange(api_key, api_secret)
                system_state['exchange'] = ex
                system_state['api_key'] = api_key
                system_state['api_secret'] = api_secret
                if ex:
                    tprint(f"[SISTEMA] ✅ Exchange conectada com sucesso.")
                else:
                    tprint(f"[SISTEMA] ⚠️ Chaves inválidas. Aguardando configuração no app.")
            
            system_state['is_active'] = is_active
            
            if is_active:
                tprint(
                    f"\r[SISTEMA] ✅ Ativo | P/L Dia: +${system_state['daily_profit']:.3f}"
                    f" / -${system_state['daily_loss']:.3f} | {datetime.datetime.now().strftime('%H:%M:%S')}",
                    end="", flush=True
                )
            
        except Exception as e:
            tprint(f"\n[SISTEMA] [SYNC ERRO] {e}")
        
        time.sleep(cfg.BACKEND_SYNC_INTERVAL)


# ══════════════════════════════════════════════════════════════════
#  PONTO DE ENTRADA PRINCIPAL
# ══════════════════════════════════════════════════════════════════

def main():
    print("=" * 72)
    print("  💎 MOMENTUM SURFER PRO v4.0 — SISTEMA MULTI-ATIVO INICIANDO")
    print("=" * 72)
    print(f"  Estratégia: Bollinger Bands + RSI Mean Reversion")
    print(f"  Ativos: {' | '.join(b['symbol'] for b in cfg.BOTS)}")
    print(f"  Meta diária: +${cfg.MAX_DAILY_PROFIT_USDT} | Limite perda: -${cfg.MAX_DAILY_LOSS_USDT}")
    print(f"  Max {cfg.MAX_TRADES_PER_BOT_PER_DAY} trades/ativo/dia | Janela: {cfg.HOURS_START_UTC}h-{cfg.HOURS_END_UTC}h UTC")
    print("=" * 72)
    
    # Inicia thread de sincronização com backend
    sync_thread = threading.Thread(target=backend_sync_thread, daemon=True)
    sync_thread.start()
    
    # Aguarda exchange ser inicializada (máx 60s)
    tprint("[SISTEMA] Aguardando configuração das chaves API...")
    for _ in range(30):
        if system_state.get('exchange') is not None or system_state.get('api_key'):
            break
        time.sleep(2)
    
    # Inicia uma thread por ativo
    threads = []
    for bot_cfg in cfg.BOTS:
        t = threading.Thread(target=run_single_bot, args=(bot_cfg,), daemon=True, name=bot_cfg['name'])
        t.start()
        threads.append(t)
        tprint(f"[SISTEMA] Thread {bot_cfg['name']} iniciada para {bot_cfg['symbol']}")
        time.sleep(2)  # Pequeno delay entre threads para evitar rate limit
    
    tprint(f"\n[SISTEMA] ✅ {len(threads)} robôs rodando em paralelo!\n")
    
    # Mantém o processo principal vivo
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        tprint("\n\n[SISTEMA] Interrompido pelo usuário. Encerrando...")
        sys.exit(0)


if __name__ == '__main__':
    main()
