# CONFIGURAÇÕES DO BOT A - SEGUIDOR DE TENDÊNCIA (TREND FOLLOWING)

# Ativo de negociação e tempo gráfico
SYMBOL = 'BTC/USDT'
TIMEFRAME = '15m'

# Valor simulado a ser investido por operação: ~$1.700 (ou $300 USD)
# Ajustado para o mínimo real da Binance Spot
TRADE_AMOUNT_USDT = 12.0

# ----------------- MOTOR DE DEFESA E RISCO MÍNIMO -----------------
# Stop Loss Inicial: 1.5% (Perda máxima por trade: ~$4.50)
STOP_LOSS_PCT = 0.015

# Alvo Parcial (Take Profit 1 - TP1): 1.0% (Lucro parcial: ~$1.80)
TAKE_PROFIT_1_PCT = 0.010

# Fração a fechar no TP1: 60% da posição
PARTIAL_EXIT_PCT = 0.60

# Ativar Breakeven (Risco Zero após TP1)?
ACTIVATE_BREAKEVEN = True

# Alvo Final (Take Profit 2 - TP2): 3.0%
TAKE_PROFIT_2_PCT = 0.030

# Trava diária de prejuízo máximo
MAX_DAILY_LOSS_USDT = 50.0

# Meta diária de lucro máximo
MAX_DAILY_PROFIT_USDT = 150.0

# ----------------- INDICADORES TÉCNICOS (MÉDIAS + RSI) -----------------
EMA_FAST_PERIOD = 9      # Média rápida
EMA_SLOW_PERIOD = 21     # Média lenta
RSI_PERIOD = 14          # Período do RSI
RSI_OVERBOUGHT = 70      # Zona de sobrecompra

# Nome do arquivo de estado
STATE_FILE = 'bot_state_a.json'

# Tempo de espera entre verificações (30 segundos)
LOOP_INTERVAL_SECONDS = 30
