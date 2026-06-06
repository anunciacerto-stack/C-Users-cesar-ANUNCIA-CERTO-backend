# CONFIGURAÇÕES DO BOT B - REVERSÃO À MÉDIA (MEAN REVERSION - BANDAS DE BOLLINGER)

# Ativo de negociação e tempo gráfico
SYMBOL = 'BTC/USDT'
TIMEFRAME = '15m'

# Valor simulado a ser investido por operação: ~$1.700 (ou $300 USD)
# Ajustado para $12.0 que é o mínimo real para ordens da Binance Spot
TRADE_AMOUNT_USDT = 12.0

# ----------------- MOTOR DE DEFESA E RISCO MÍNIMO -----------------
# Stop Loss Inicial: 1.2% (Perda máxima por trade: ~$3.60)
# Mais curto porque se perder a média, devemos estancar a perda rápido
STOP_LOSS_PCT = 0.012

# Alvo Parcial (Take Profit 1 - TP1): 0.8% (Lucro parcial: ~$1.44)
TAKE_PROFIT_1_PCT = 0.008

# Fração a fechar no TP1: 60% da posição
PARTIAL_EXIT_PCT = 0.60

# Ativar Breakeven (Risco Zero após TP1)?
ACTIVATE_BREAKEVEN = True

# Alvo Final (Take Profit 2 - TP2): 2.0%
TAKE_PROFIT_2_PCT = 0.020

# Trava diária de prejuízo máximo
MAX_DAILY_LOSS_USDT = 50.0

# Meta diária de lucro máximo
MAX_DAILY_PROFIT_USDT = 150.0

# ----------------- INDICADORES TÉCNICOS (BANDAS DE BOLLINGER) -----------------
BOLLINGER_PERIOD = 20    # Período da Média Simples das bandas
BOLLINGER_DEV = 2        # Desvios Padrão para abrir as bandas superiores e inferiores
RSI_PERIOD = 14          # RSI para filtro de força do movimento
RSI_OVERSOLD = 30        # Indica se está sobrevendido (segurança extra para comprar)

# Nome do arquivo de estado
STATE_FILE = 'bot_state_b.json'

# Tempo de espera entre verificações (30 segundos)
LOOP_INTERVAL_SECONDS = 30
