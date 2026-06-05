# CONFIGURAÇÕES OPERACIONAIS E PARAMETRIZAÇÃO DO ROBÔ

# Ativo de negociação (ex: BTC/USDT, ETH/USDT, SOL/USDT)
SYMBOL = 'SOL/USDT'

# Tempo gráfico dos candles (ex: '1m', '5m', '15m', '1h', '1d')
TIMEFRAME = '15m'

# Valor em USDT a ser investido por operação
# IMPORTANTE: Garanta que este valor seja superior ao mínimo exigido pela Binance (geralmente $5 ou $10)
TRADE_AMOUNT_USDT = 12.0

# ----------------- MOTOR DE DEFESA E GERENCIAMENTO DE RISCO -----------------

# Porcentagem de Stop Loss (inicial) - Defesa se a operação der errado
# 0.020 = 2.0% abaixo/acima do preço de entrada
STOP_LOSS_PCT = 0.020

# Porcentagem para Realização Parcial (Take Profit 1 - TP1)
# 0.020 = 2.0% de ganho
TAKE_PROFIT_1_PCT = 0.020

# Fração a fechar no Take Profit 1 (Parcial)
# 1.0 = Fechará 100% da posição no TP1, já que frações menores seriam bloqueadas pelo limite mínimo de $10 da Binance Spot
PARTIAL_EXIT_PCT = 1.0

# Ativar Breakeven Automático?
# Se True: Assim que o TP1 (parcial) for atingido, o Stop Loss do restante da posição
# é movido automaticamente para o preço de entrada (custo/risco zero).
ACTIVATE_BREAKEVEN = True

# Porcentagem para Alvo Final (Take Profit 2 - TP2)
# 0.03 = 3.0% de ganho
TAKE_PROFIT_2_PCT = 0.030

# Trava de Segurança Diária (Controle de Danos)
# Se o robô atingir este limite de perda acumulada no dia, ele para de operar
MAX_DAILY_LOSS_USDT = 15.0

# Meta de Lucro Diária (Saber a hora de parar)
# Se o robô atingir este lucro acumulado no dia, ele encerra as operações do dia
MAX_DAILY_PROFIT_USDT = 45.0

# ----------------- PARÂMETROS DA ESTRATÉGIA TÉCNICA -----------------
# Estratégia padrão: Cruzamento de Médias Móveis com Filtro de RSI (Índice de Força Relativa)

EMA_FAST_PERIOD = 9      # Média móvel exponencial rápida
EMA_SLOW_PERIOD = 21     # Média móvel exponencial lenta
RSI_PERIOD = 14          # Período do RSI
RSI_OVERBOUGHT = 70      # Zona de sobrecompra (evitar comprar acima disso)
RSI_OVERSOLD = 30        # Zona de sobrevenda (evitar vender abaixo disso)

# Tempo de espera entre verificações do robô (em segundos)
LOOP_INTERVAL_SECONDS = 30
