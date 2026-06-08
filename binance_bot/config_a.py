# ╔══════════════════════════════════════════════════════════════════╗
# ║  BOT C — ETH/USDT — SCALPING COM VWAP + EMA RIBBON             ║
# ║  Estratégia: Preço cruza acima do VWAP + EMA ribbon alinhada   ║
# ║  + volume confirmado = entrada de alta probabilidade            ║
# ╚══════════════════════════════════════════════════════════════════╝

# ETH tem excelente volatilidade intraday e taxas menores que BTC
SYMBOL = 'ETH/USDT'
TIMEFRAME = '5m'
TIMEFRAME_MACRO = '1h'

TRADE_AMOUNT_USDT = 12.0

# ─── STOPS DINÂMICOS POR ATR ──────────────────────────────────────────
USE_ATR_STOPS = True
ATR_PERIOD = 14
ATR_STOP_MULTIPLIER = 1.3
ATR_TP1_MULTIPLIER = 1.8
ATR_TP2_MULTIPLIER = 3.5

STOP_LOSS_PCT = 0.015
TAKE_PROFIT_1_PCT = 0.020
TAKE_PROFIT_2_PCT = 0.045

# ─── GESTÃO DE POSIÇÃO ────────────────────────────────────────────────
PARTIAL_EXIT_PCT = 0.55
ACTIVATE_BREAKEVEN = True
TRAILING_STOP = True
TRAILING_STOP_PCT = 0.012

# ─── FILTROS ─────────────────────────────────────────────────────────
VOLUME_FILTER = True
VOLUME_MA_PERIOD = 20
VOLUME_MIN_RATIO = 1.4

TIME_FILTER = True
TRADING_HOURS_UTC_START = 8
TRADING_HOURS_UTC_END = 22

# ─── VWAP + EMA RIBBON ────────────────────────────────────────────────
# O VWAP é o indicador institucional mais confiável do dia
# Quando o preço está acima do VWAP = bulls no controle
VWAP_ENABLED = True

# EMA Ribbon: 5 EMAs para confirmar alinhamento (todas crescentes = tendência forte)
EMA_RIBBON = [8, 13, 21, 34, 55]

# ─── RSI ──────────────────────────────────────────────────────────────
RSI_PERIOD = 14
RSI_OVERSOLD = 40           # Mais permissivo pois VWAP e ribbon confirmam
RSI_OVERBOUGHT = 75

# ─── PROTEÇÃO DIÁRIA ─────────────────────────────────────────────────
MAX_DAILY_LOSS_USDT = 15.0
MAX_DAILY_PROFIT_USDT = 25.0
MAX_TRADES_PER_DAY = 8

STATE_FILE = 'bot_state_a.json'
LOOP_INTERVAL_SECONDS = 15
