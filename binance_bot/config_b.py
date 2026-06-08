# ╔══════════════════════════════════════════════════════════════════╗
# ║  BOT B — BTC/USDT — REVERSÃO BANDAS BOLLINGER + STOCH RSI       ║
# ║  Estratégia: Mean Reversion com Squeeze Momentum                 ║
# ║  Filtros: BB squeeze → explosão + RSI divergência                ║
# ╚══════════════════════════════════════════════════════════════════╝

SYMBOL = 'BTC/USDT'
TIMEFRAME = '5m'           # 5m para capturas mais frequentes em reversão
TIMEFRAME_MACRO = '1h'     # Filtro de tendência macro

TRADE_AMOUNT_USDT = 12.0

# ─── STOPS DINÂMICOS POR ATR ──────────────────────────────────────────
USE_ATR_STOPS = True
ATR_PERIOD = 14
ATR_STOP_MULTIPLIER = 1.2   # Stop mais apertado (reversão tem targets menores)
ATR_TP1_MULTIPLIER = 1.5
ATR_TP2_MULTIPLIER = 3.0

# Fallback percentual
STOP_LOSS_PCT = 0.012
TAKE_PROFIT_1_PCT = 0.015
TAKE_PROFIT_2_PCT = 0.030

# ─── GESTÃO DE POSIÇÃO ────────────────────────────────────────────────
PARTIAL_EXIT_PCT = 0.60     # Fecha 60% no TP1
ACTIVATE_BREAKEVEN = True
TRAILING_STOP = True
TRAILING_STOP_PCT = 0.010   # 1.0% trailing (BTC mais previsível)

# ─── FILTROS ─────────────────────────────────────────────────────────
VOLUME_FILTER = True
VOLUME_MA_PERIOD = 20
VOLUME_MIN_RATIO = 1.5      # Exige 150% de volume no candle de reversão

TIME_FILTER = True
TRADING_HOURS_UTC_START = 7
TRADING_HOURS_UTC_END = 23

# ─── BOLLINGER BANDS + SQUEEZE ────────────────────────────────────────
BOLLINGER_PERIOD = 20
BOLLINGER_DEV = 2.0
# Squeeze: BB dentro das Keltner Channels indica compressão antes da explosão
KELTNER_ATR_MULT = 1.5      # Multiplicador ATR para Keltner Channels

# ─── RSI E STOCHASTIC RSI ─────────────────────────────────────────────
RSI_PERIOD = 14
RSI_OVERSOLD = 35           # Mais permissivo pois BB confirma a reversão
RSI_OVERBOUGHT = 70
STOCH_RSI_PERIOD = 14
STOCH_RSI_SMOOTH_K = 3
STOCH_RSI_SMOOTH_D = 3
STOCH_RSI_OVERSOLD = 20     # Stoch RSI muito sobrevendido = sinal forte

# ─── PROTEÇÃO DIÁRIA ─────────────────────────────────────────────────
MAX_DAILY_LOSS_USDT = 15.0
MAX_DAILY_PROFIT_USDT = 25.0
MAX_TRADES_PER_DAY = 8      # Estratégia de reversão gera mais sinais

STATE_FILE = 'bot_state_b.json'
LOOP_INTERVAL_SECONDS = 15  # Checagem frequente para 5m
