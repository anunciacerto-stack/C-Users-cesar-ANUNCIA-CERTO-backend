# ╔══════════════════════════════════════════════════════════════════╗
# ║  BOT A — SOL/USDT — TENDÊNCIA MULTI-TIMEFRAME (EMA + MACD + RSI) ║
# ║  Estratégia: Entrada em cruzamento EMA confirmado no 1h com     ║
# ║  filtro MACD e Stochastic RSI para evitar whipsaw e falsos sinais║
# ╚══════════════════════════════════════════════════════════════════╝

# Ativo e timeframe principal de entrada
SYMBOL = 'SOL/USDT'
TIMEFRAME = '1h'          # Timeframe de análise de entrada (alterado de 15m para evitar whipsaws)
TIMEFRAME_MACRO = '1h'    # Timeframe macro para filtro de tendência

# Valor por operação. Com $12, o objetivo é ~$0.30-0.50/trade líquido
# Ajuste para o saldo disponível conforme possível
TRADE_AMOUNT_USDT = 12.0

# ─── MOTOR DE DEFESA: STOP/TARGET DINÂMICO (VIA ATR) ────────────────
# O ATR define o tamanho do stop dinamicamente pela volatilidade real
# Stop = entrada - (ATR_MULTIPLIER * ATR); TP1 = entrada + (TP1_MULTIPLIER * ATR)

USE_ATR_STOPS = True       # Ativa stops/targets baseados no ATR
ATR_PERIOD = 14            # Período do ATR
ATR_STOP_MULTIPLIER = 1.5  # Distância do stop em múltiplos de ATR (ex: 1.5x ATR)
ATR_TP1_MULTIPLIER = 2.0   # Distância do TP1 em múltiplos de ATR
ATR_TP2_MULTIPLIER = 4.0   # Distância do TP2 em múltiplos de ATR (alvo grande)

# Stops percentuais (fallback se ATR não disponível)
STOP_LOSS_PCT = 0.018      # 1.8% stop (fallback)
TAKE_PROFIT_1_PCT = 0.025  # 2.5% TP1 (fallback)
TAKE_PROFIT_2_PCT = 0.050  # 5.0% TP2 (fallback — tendência forte)

# ─── GESTÃO DE POSIÇÃO ────────────────────────────────────────────────
PARTIAL_EXIT_PCT = 0.50     # Fecha 50% no TP1, deixa 50% correr para TP2
ACTIVATE_BREAKEVEN = True   # Move SL para entrada após TP1
TRAILING_STOP = True        # Ativa trailing stop após breakeven
TRAILING_STOP_PCT = 0.015   # Segue o preço com 1.5% de distância (trailing)

# ─── FILTROS DE QUALIDADE DO SINAL ────────────────────────────────────
# Filtro de volume: exige que o volume do candle atual seja maior que a
# média dos últimos N candles (sem isso, entradas em lateralização geram whipsaw)
VOLUME_FILTER = True
VOLUME_MA_PERIOD = 20       # Média de volume para comparação
VOLUME_MIN_RATIO = 1.3      # Volume deve ser ≥ 130% da média (sinal com força)

# Filtro de horário (UTC): opera apenas em janelas de alta liquidez
TIME_FILTER = True
TRADING_HOURS_UTC_START = 8   # 08:00 UTC = 05:00 BRT
TRADING_HOURS_UTC_END = 22    # 22:00 UTC = 19:00 BRT

# ─── INDICADORES TÉCNICOS ─────────────────────────────────────────────
EMA_FAST_PERIOD = 9         # EMA rápida (entrada)
EMA_SLOW_PERIOD = 21        # EMA lenta (tendência)
EMA_MACRO_PERIOD = 50       # EMA macro (filtro direcional no 1h)
RSI_PERIOD = 14
RSI_OVERBOUGHT = 72         # Evita comprar sobrecomprado
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
STOCH_RSI_PERIOD = 14       # Período do Stochastic RSI
STOCH_RSI_SMOOTH_K = 3
STOCH_RSI_SMOOTH_D = 3
STOCH_RSI_OVERSOLD = 25     # Stoch RSI abaixo de 25 = sobrevendido (bom pra comprar)

# ─── PROTEÇÃO DIÁRIA ─────────────────────────────────────────────────
MAX_DAILY_LOSS_USDT = 15.0   # Para se perder $15 no dia
MAX_DAILY_PROFIT_USDT = 25.0 # Para se lucrar $25 no dia (proteção de meta)
MAX_TRADES_PER_DAY = 6       # Máximo de entradas por dia

# Loop principal
LOOP_INTERVAL_SECONDS = 20  # Checagem a cada 20s (mais rápido = melhor execução)
