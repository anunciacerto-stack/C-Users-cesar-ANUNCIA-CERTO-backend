"""
╔══════════════════════════════════════════════════════════════════════════╗
║           💎 SISTEMA "MOMENTUM SURFER" — ESTRATÉGIA UNIFICADA v4.0      ║
║                                                                          ║
║  FILOSOFIA: Um único robô gerencia os 3 ativos de forma inteligente.    ║
║                                                                          ║
║  ESTRATÉGIA: SuperTrend + RSI Pullback + Breakout de Consolidação       ║
║                                                                          ║
║  POR QUE ESSA ESTRATÉGIA GANHA:                                         ║
║  ✅ SuperTrend é o indicador mais confiável para tendência (usa ATR)     ║
║  ✅ Só entra em PULLBACKS (entrada barata, não no topo)                 ║
║  ✅ Aguarda confirmação de candle FECHADO (zero whipsaw)                ║
║  ✅ Ratio Risco/Retorno mínimo de 2:1 (2 wins pagam 4 losses)          ║
║  ✅ Opera os 3 ativos em paralelo = mais oportunidades por dia          ║
║  ✅ Filtra horários ruins (madrugada UTC = mercado sem liquidez)        ║
║  ✅ Para automaticamente ao atingir a meta do dia                       ║
║  ✅ BNB para pagar taxas (reduz custo de 0.10% → 0.075% por lado)      ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

# ═══════════════════════════════════════════════════════════════════
#  CARTEIRA DE ATIVOS — 3 ATIVOS DIFERENTES PARA DIVERSIFICAÇÃO
# ═══════════════════════════════════════════════════════════════════

BOTS = [
    {
        'name': 'SURF-A',
        'symbol': 'SOL/USDT',
        'timeframe': '15m',           # Timeframe principal
        'timeframe_macro': '1h',      # Filtro de tendência
        'trade_usdt': 12.0,
        'state_file': 'state_surfa.json',
    },
    {
        'name': 'SURF-B',
        'symbol': 'BTC/USDT',
        'timeframe': '15m',
        'timeframe_macro': '1h',
        'trade_usdt': 12.0,
        'state_file': 'state_surfb.json',
    },
    {
        'name': 'SURF-C',
        'symbol': 'ETH/USDT',
        'timeframe': '15m',
        'timeframe_macro': '1h',
        'trade_usdt': 12.0,
        'state_file': 'state_surfc.json',
    }
]

# ═══════════════════════════════════════════════════════════════════
#  SUPERTREND — PARÂMETROS
# ═══════════════════════════════════════════════════════════════════

SUPERTREND_ATR_PERIOD = 10     # ATR period para o SuperTrend
SUPERTREND_MULTIPLIER = 3.0    # Multiplicador do ATR (3.0 = padrão do mercado)

# ═══════════════════════════════════════════════════════════════════
#  RSI — CONFIGURAÇÃO PARA PULLBACK
# ═══════════════════════════════════════════════════════════════════

RSI_PERIOD = 14
RSI_PULLBACK_LOW = 45          # RSI < 45 em uptrend = pullback saudável (boa entrada)
RSI_PULLBACK_HIGH = 55         # RSI > 55 em downtrend = pullback de baixa (não opera)
RSI_OVERBOUGHT = 75            # Saída / bloqueio de entradas
RSI_OVERSOLD = 25              # Piso do RSI (reversão possível)

# ═══════════════════════════════════════════════════════════════════
#  GESTÃO DE RISCO — ATR DINÂMICO
# ═══════════════════════════════════════════════════════════════════

ATR_PERIOD = 14
ATR_STOP_MULT = 1.5            # Stop = entrada - 1.5 x ATR
ATR_TP1_MULT = 2.0             # TP1  = entrada + 2.0 x ATR  (ratio 1.33:1)
ATR_TP2_MULT = 3.5             # TP2  = entrada + 3.5 x ATR  (ratio 2.33:1)
MIN_RR_RATIO = 1.8             # Risco/Retorno mínimo: só entra se R/R >= 1.8:1

# ═══════════════════════════════════════════════════════════════════
#  GESTÃO DE POSIÇÃO
# ═══════════════════════════════════════════════════════════════════

PARTIAL_EXIT_PCT = 0.50        # Fecha 50% no TP1, deixa 50% correr
ACTIVATE_BREAKEVEN = True      # Move SL para entrada após TP1
TRAILING_AFTER_TP1 = True      # Ativa trailing stop após TP1
TRAILING_ATR_MULT = 1.0        # Trailing = 1.0 x ATR abaixo do preço

# ═══════════════════════════════════════════════════════════════════
#  FILTROS DE QUALIDADE
# ═══════════════════════════════════════════════════════════════════

VOLUME_FILTER = True
VOLUME_MULT = 1.2              # Volume do candle >= 1.2x a média dos últimos 20

TIME_FILTER = True
HOURS_START_UTC = 7            # Não opera antes das 07:00 UTC (04:00 BRT)
HOURS_END_UTC = 22             # Não opera após 22:00 UTC (19:00 BRT)

# Mínimo de candles de consolidação antes do sinal
# (evita entrar em movimentos já esticados)
MIN_CANDLES_IN_TREND = 3       # SuperTrend deve estar ativo há pelo menos 3 candles

# ═══════════════════════════════════════════════════════════════════
#  PROTEÇÃO DIÁRIA
# ═══════════════════════════════════════════════════════════════════

MAX_DAILY_LOSS_USDT = 18.0     # Para tudo se perder $18 no dia (1.5 stops)
MAX_DAILY_PROFIT_USDT = 30.0   # Trava de meta: +$30 no dia = encerra operações
MAX_TRADES_PER_BOT_PER_DAY = 4 # Máx 4 trades por ativo por dia (qualidade > qtd)

# ═══════════════════════════════════════════════════════════════════
#  LOOP
# ═══════════════════════════════════════════════════════════════════

LOOP_INTERVAL_SECONDS = 20     # Checagem a cada 20 segundos
BACKEND_SYNC_INTERVAL = 60     # Sincronização com backend a cada 60 segundos
