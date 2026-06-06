import os
import time
import json
import datetime
import requests
import ccxt
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import sys
import io

# Garante que a saída padrão no console suporte UTF-8 e trate caracteres especiais/emojis sem quebrar
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

# Carrega as configurações de variáveis de ambiente (.env)
load_dotenv()

# Importa as configurações operacionais
import config

# Caminho do arquivo de persistência de estado local
STATE_FILE = 'bot_state.json'

# --- FUNÇÕES DE CONEXÃO COM O BACKEND API ---

def fetch_backend_config():
    """Busca as configurações do robô no backend NestJS."""
    backend_url = os.getenv('BACKEND_URL', 'http://localhost:3000')
    user_id = os.getenv('USER_ID', 'guest')
    try:
        response = requests.get(f"{backend_url}/bot/config?userId={user_id}", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"\n[ERRO] Falha ao buscar config do backend: Status {response.status_code}")
    except Exception as e:
        print(f"\n[ERRO] Falha ao conectar ao backend: {e}")
    return None

def register_trade_backend(asset, trade_type, price, amount, value, profit_pct=None):
    """Registra uma transação no backend para aparecer no histórico do app."""
    backend_url = os.getenv('BACKEND_URL', 'http://localhost:3000')
    user_id = os.getenv('USER_ID', 'guest')
    payload = {
        'userId': user_id,
        'asset': asset,
        'type': trade_type,
        'price': float(price),
        'amount': float(amount),
        'value': float(value)
    }
    if profit_pct is not None:
        payload['profitPct'] = f"{profit_pct:+.2f}%" if isinstance(profit_pct, (int, float)) else str(profit_pct)

    try:
        response = requests.post(f"{backend_url}/bot/trades", json=payload, timeout=10)
        if response.status_code == 201:
            print(f"\n[BACKEND] Trade registrado com sucesso: {trade_type} {asset}")
        else:
            print(f"\n[ERRO] Falha ao registrar trade no backend: Status {response.status_code}")
    except Exception as e:
        print(f"\n[ERRO] Falha ao conectar ao backend para registrar trade: {e}")

# --- FUNÇÕES DE INICIALIZAÇÃO E UTILITÁRIAS ---

def get_exchange_connection(api_key, api_secret):
    """Inicializa a conexão com a API da Binance usando CCXT."""
    use_testnet = os.getenv('USE_TESTNET', 'True').lower() == 'true'

    if not api_key or not api_secret or api_key == 'sua_chave_api_aqui' or len(api_key.strip()) < 10:
        print("[AVISO] Chaves de API não configuradas ou inválidas!")
        return None, use_testnet

    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
        'options': {
            'defaultType': 'spot'  # Operando no mercado à vista (Spot)
        }
    })

    if use_testnet:
        exchange.set_sandbox_mode(True)
        print("[INFO] Conectado à TESTNET (Ambiente de Simulação) da Binance.")
    else:
        print("[PERIGO] CONECTADO À CONTA REAL DA BINANCE! Operações usarão saldo real.")

    return exchange, use_testnet

def send_telegram_message(message):
    """Envia um alerta formatado para o Telegram do usuário se configurado."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id or token == 'seu_token_do_telegram_aqui':
        # Telegram não configurado, exibe apenas no console
        print(f"[TELEGRAM LOG] {message}")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': f"🤖 *Motor de Defesa Binance*\n\n{message}",
        'parse_mode': 'Markdown'
    }
    
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"[ERRO] Falha ao enviar mensagem para o Telegram: {e}")

# --- GERENCIAMENTO DE ESTADO (À PROVA DE QUEDAS) ---

def load_state():
    """Carrega o estado atual do bot do arquivo JSON local de segurança."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                print(f"[ESTADO] Estado anterior carregado com sucesso.")
                return state
        except Exception as e:
            print(f"[ERRO] Falha ao carregar estado: {e}")
    
    # Estado inicial padrão (Flat)
    return {
        'in_position': False,
        'entry_price': 0.0,
        'stop_loss_price': 0.0,
        'take_profit_1': 0.0,
        'take_profit_2': 0.0,
        'quantity_bought': 0.0,
        'is_partial_executed': False,
        'daily_loss_accumulated': 0.0,
        'daily_profit_accumulated': 0.0,
        'last_reset_date': str(datetime.date.today())
    }

def save_state(state):
    """Salva o estado atual do bot no arquivo JSON local de segurança."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        print(f"[ERRO] Falha ao salvar estado: {e}")

# --- ANÁLISE TÉCNICA E INDICADORES ---

def fetch_candles(exchange, symbol, timeframe, limit=100):
    """Busca candles recentes da Binance e retorna em formato DataFrame."""
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"[ERRO] Falha ao buscar candles de {symbol}: {e}")
        return None

def calculate_indicators(df):
    """Calcula as Médias Móveis Exponenciais (EMA) e o RSI."""
    # Cálculo das EMAs
    df['ema_fast'] = df['close'].ewm(span=config.EMA_FAST_PERIOD, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=config.EMA_SLOW_PERIOD, adjust=False).mean()
    
    # Cálculo do RSI (Índice de Força Relativa)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=config.RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=config.RSI_PERIOD).mean()
    
    rs = gain / (loss + 1e-9) # evita divisão por zero
    df['rsi'] = 100 - (100 / (1 + rs))
    
    return df

# --- MOTOR DE EXECUÇÃO DE ORDENS E DEFESA ---

def buy_entry(exchange, symbol, amount_usdt):
    """Executa a compra do ativo no mercado Spot calculando precisões corretas."""
    try:
        # Carrega dados do mercado para pegar precisões decimais exigidas pela Binance
        exchange.load_markets()
        market = exchange.market(symbol)
        
        # Obtém o preço atual (ticker)
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # Calcula a quantidade necessária de moedas baseado no valor em USDT
        qty = amount_usdt / current_price
        
        # Ajusta precisões exigidas pela Binance
        formatted_qty = float(exchange.amount_to_precision(symbol, qty))
        
        print(f"[EXECUÇÃO] Enviando ordem de COMPRA a Mercado de {formatted_qty} {market['base']} a aprox. ${current_price}")
        
        # Executa a ordem de compra a mercado
        order = exchange.create_market_buy_order(symbol, formatted_qty)
        
        # Aguarda 1 segundo e busca o saldo real da moeda livre na carteira para evitar problemas de arredondamento de taxas
        time.sleep(1)
        balance = exchange.fetch_balance()
        base_asset = symbol.split('/')[0]
        actual_qty = balance['free'].get(base_asset, 0.0)
        
        # Ajusta a quantidade com a precisão permitida para venda
        actual_qty_formatted = float(exchange.amount_to_precision(symbol, actual_qty))
        
        print(f"[SUCESSO] Ordem executada. Quantidade líquida na carteira: {actual_qty_formatted}")
        return order, current_price, actual_qty_formatted
        
    except Exception as e:
        print(f"[ERRO] Falha ao executar compra a mercado: {e}")
        return None, 0.0, 0.0

def sell_exit(exchange, symbol, qty, reason="Saída"):
    """Executa a venda de uma quantidade do ativo no mercado Spot."""
    try:
        exchange.load_markets()
        formatted_qty = float(exchange.amount_to_precision(symbol, qty))
        
        if formatted_qty <= 0:
            print("[AVISO] Quantidade de venda calculada como zero. Abortando venda.")
            return None
            
        print(f"[EXECUÇÃO] Enviando ordem de VENDA a Mercado de {formatted_qty} ({reason})")
        order = exchange.create_market_sell_order(symbol, formatted_qty)
        return order
    except Exception as e:
        print(f"[ERRO] Falha ao executar venda ({reason}): {e}")
        return None

# --- LOOP PRINCIPAL DO MOTOR DE TRADING ---

def run_trading_bot():
    print("====================================================")
    print("      INICIALIZANDO MOTOR DE TRADING AUTOMATIZADO    ")
    print("      (INTEGRADO AO BACKEND DO ANUNCIA CERTO)        ")
    print("====================================================")
    
    # Carrega estado anterior
    state = load_state()
    
    # Valida reinicialização do limite diário
    today_str = str(datetime.date.today())
    if state.get('last_reset_date') != today_str:
        print("[DIÁRIO] Novo dia detectado. Resetando limites acumulados de lucro/perda.")
        state['daily_loss_accumulated'] = 0.0
        state['daily_profit_accumulated'] = 0.0
        state['last_reset_date'] = today_str
        save_state(state)

    exchange = None
    use_testnet = False
    current_api_key = None
    current_api_secret = None

    while True:
        try:
            # 1. Busca configurações no backend
            backend_config = fetch_backend_config()
            
            if backend_config is None:
                print("\n[AVISO] Backend inacessível. O robô usará as chaves locais do arquivo .env.")
                api_key = os.getenv('BINANCE_API_KEY')
                api_secret = os.getenv('BINANCE_API_SECRET')
                is_active = True  # Assume ativo em caso de queda do backend para monitoramento local
                symbol = config.SYMBOL
                trade_amount = config.TRADE_AMOUNT_USDT
            else:
                api_key = backend_config.get('binanceApiKey')
                api_secret = backend_config.get('binanceApiSecret')
                is_active = backend_config.get('isActive', False)
                symbol = backend_config.get('symbol', 'SOL/USDT')
                trade_amount = float(backend_config.get('tradeAmount', 12.0))

            # 2. Se o usuário desativou o robô
            if not is_active:
                # Se estiver posicionado, fecha a posição imediatamente para segurança do saldo
                if state['in_position'] and exchange is not None:
                    qty = state['quantity_bought']
                    print(f"\n🚨 [DESLIGAMENTO] Robô desativado pelo usuário. Fechando posição de {qty} {symbol} a mercado por segurança.")
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        current_price = ticker['last']
                        sell_exit(exchange, symbol, qty, reason="Desligamento Forçado")
                        
                        # Calcula lucro/prejuízo
                        profit_pct = ((current_price - state['entry_price']) / state['entry_price']) * 100
                        register_trade_backend(
                            asset=symbol,
                            trade_type="VENDA (DESLIGAMENTO)",
                            price=current_price,
                            amount=qty,
                            value=qty * current_price,
                            profit_pct=profit_pct
                        )
                    except Exception as ex:
                        print(f"[ERRO] Falha ao liquidar posição no desligamento: {ex}")
                    
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                
                print(f"\r[STATUS] Robô desativado na nuvem. Aguardando ativação via App... | Horário: {datetime.datetime.now().strftime('%H:%M:%S')}", end="", flush=True)
                time.sleep(15)
                continue

            # 3. Inicializa ou reconecta a Exchange se as chaves mudaram
            if exchange is None or api_key != current_api_key or api_secret != current_api_secret:
                print(f"\n[INFO] Inicializando conexão com a Binance usando chaves configuradas...")
                exchange, use_testnet = get_exchange_connection(api_key, api_secret)
                if exchange is None:
                    print("[ERRO] Chaves de API inválidas ou vazias no backend. Aguardando configuração...")
                    time.sleep(15)
                    continue
                current_api_key = api_key
                current_api_secret = api_secret

            # 4. Verifica limites de segurança diários
            if state['daily_loss_accumulated'] >= config.MAX_DAILY_LOSS_USDT:
                print(f"[SEGURANÇA] Limite diário de perda atingido (-${state['daily_loss_accumulated']:.2f}). Robô pausado até amanhã.")
                time.sleep(600)
                continue
                
            if state['daily_profit_accumulated'] >= config.MAX_DAILY_PROFIT_USDT:
                print(f"[PARADA] Meta diária de lucro atingida (+${state['daily_profit_accumulated']:.2f}). Robô finalizou o dia com sucesso!")
                time.sleep(600)
                continue

            # 5. Obtém dados atuais de mercado
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            print(f"\r[STATUS] Ativo: {symbol} | Preço Atual: ${current_price:.2f} | Posicionado: {state['in_position']} | Horário: {datetime.datetime.now().strftime('%H:%M:%S')}", end="", flush=True)

            # --- CASO 1: ROBÔ POSICIONADO (MONITORAMENTO DO MOTOR DE DEFESA) ---
            if state['in_position']:
                qty = state['quantity_bought']
                entry_price = state['entry_price']
                
                # A. DEFESA 1: STOP LOSS ATINGIDO
                if current_price <= state['stop_loss_price']:
                    loss_usd = (entry_price - current_price) * qty
                    print(f"\n🚨 [DEFESA] STOP LOSS acionado no preço de ${current_price:.2f}!")
                    
                    sell_exit(exchange, symbol, qty, reason="Stop Loss")
                    
                    # Atualiza acumulado de perda diária
                    state['daily_loss_accumulated'] += loss_usd
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                    
                    # Registra trade no backend
                    profit_pct = -((entry_price - current_price) / entry_price) * 100
                    register_trade_backend(
                        asset=symbol,
                        trade_type="VENDA (STOP LOSS)",
                        price=current_price,
                        amount=qty,
                        value=qty * current_price,
                        profit_pct=profit_pct
                    )
                    
                    send_telegram_message(
                        f"❌ *Operação encerrada no Stop Loss*\n"
                        f"📉 Preço de Saída: ${current_price:.2f}\n"
                        f"💸 Perda estimada: -${loss_usd:.2f}\n"
                        f"🛡️ Defesa acionada para proteger o capital restante."
                    )
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # B. DEFESA 2: TAKE PROFIT 1 (REALIZAÇÃO PARCIAL E ACIONAR RISCO ZERO)
                if not state['is_partial_executed'] and current_price >= state['take_profit_1']:
                    print(f"\n🎯 [DEFESA] Alvo Parcial 1 (TP1) atingido a ${current_price:.2f}!")
                    
                    # Calcula quantidade parcial a vender
                    partial_qty = qty * config.PARTIAL_EXIT_PCT
                    
                    order = sell_exit(exchange, symbol, partial_qty, reason="Realização Parcial (TP1)")
                    if order is None:
                        print("\n🚨 [ERRO] Venda parcial falhou! O valor pode ser menor que o limite mínimo de $10 da Binance Spot.")
                        time.sleep(config.LOOP_INTERVAL_SECONDS)
                        continue
                    
                    # Atualiza quantidade restante da posição na carteira real
                    time.sleep(1)
                    balance = exchange.fetch_balance()
                    base_asset = symbol.split('/')[0]
                    remaining_qty = balance['free'].get(base_asset, 0.0)
                    formatted_remaining = float(exchange.amount_to_precision(symbol, remaining_qty))
                    
                    # Aciona o Breakeven (Risco Zero): Move o Stop Loss para o preço de entrada
                    if config.ACTIVATE_BREAKEVEN:
                        state['stop_loss_price'] = entry_price
                        print(f"🛡️ [BREAKEVEN] Stop Loss movido para o preço de entrada: ${entry_price:.2f} (Operação com RISCO ZERO).")
                    
                    # Lucro parcial
                    partial_profit = (current_price - entry_price) * partial_qty
                    state['daily_profit_accumulated'] += partial_profit
                    
                    # Registra a venda parcial no backend
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    register_trade_backend(
                        asset=symbol,
                        trade_type="VENDA PARCIAL (TP1)",
                        price=current_price,
                        amount=partial_qty,
                        value=partial_qty * current_price,
                        profit_pct=profit_pct
                    )

                    # Verifica se o que restou na carteira é apenas poeira/dust (menor que $2)
                    remaining_value_usdt = formatted_remaining * current_price
                    if remaining_value_usdt < 2.0:
                        state['in_position'] = False
                        state['is_partial_executed'] = False
                        state['quantity_bought'] = 0.0
                        print(f"\n📌 [INFO] Posição totalmente encerrada (restante de ${remaining_value_usdt:.2f} é poeira/dust).")
                    else:
                        state['quantity_bought'] = formatted_remaining
                        state['is_partial_executed'] = True
                    
                    save_state(state)
                    
                    send_telegram_message(
                        f"🎯 *Realização Parcial (TP1) Concluída!*\n"
                        f"💰 Preço de Saída Parcial: ${current_price:.2f}\n"
                        f"📈 Lucro parcial no bolso: +${partial_profit:.2f}\n"
                        f"🛡️ *Breakeven Ativado:* Stop Loss movido para a entrada (${entry_price:.2f}). Risco agora é ZERO!"
                    )
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # C. DEFESA 3: TAKE PROFIT 2 (ALVO FINAL)
                if current_price >= state['take_profit_2']:
                    profit_usd = (current_price - entry_price) * qty
                    print(f"\n🏆 [SUCESSO] Alvo Final (TP2) atingido a ${current_price:.2f}!")
                    
                    sell_exit(exchange, symbol, qty, reason="Alvo Final (TP2)")
                    
                    state['daily_profit_accumulated'] += profit_usd
                    state['in_position'] = False
                    state['is_partial_executed'] = False
                    save_state(state)
                    
                    # Registra no backend
                    profit_pct = ((current_price - entry_price) / entry_price) * 100
                    register_trade_backend(
                        asset=symbol,
                        trade_type="VENDA (TP2)",
                        price=current_price,
                        amount=qty,
                        value=qty * current_price,
                        profit_pct=profit_pct
                    )
                    
                    send_telegram_message(
                        f"🏆 *Alvo Final (TP2) Atingido!*\n"
                        f"📈 Preço de Saída Final: ${current_price:.2f}\n"
                        f"💵 Lucro nesta perna final: +${profit_usd:.2f}\n"
                        f"🚀 Operação finalizada com sucesso máximo!"
                    )
                    time.sleep(config.LOOP_INTERVAL_SECONDS)
                    continue

                # D. DEFESA 4: SAÍDA TÉCNICA (SINAL REVERSO DE TENDÊNCIA)
                df = fetch_candles(exchange, symbol, config.TIMEFRAME)
                if df is not None:
                    df = calculate_indicators(df)
                    last_closed_row = df.iloc[-2]
                    
                    if last_closed_row['ema_fast'] < last_closed_row['ema_slow']:
                        profit_usd = (current_price - entry_price) * qty
                        print(f"\n⚠️ [SAÍDA TÉCNICA] Média rápida cruzou abaixo da média lenta. Fechando posição preventivamente.")
                        
                        sell_exit(exchange, symbol, qty, reason="Saída Técnica (Reversão)")
                        
                        if profit_usd > 0:
                            state['daily_profit_accumulated'] += profit_usd
                        else:
                            state['daily_loss_accumulated'] += abs(profit_usd)
                            
                        state['in_position'] = False
                        state['is_partial_executed'] = False
                        save_state(state)
                        
                        # Registra no backend
                        profit_pct = ((current_price - entry_price) / entry_price) * 100
                        register_trade_backend(
                            asset=symbol,
                            trade_type="VENDA (TÉCNICA)",
                            price=current_price,
                            amount=qty,
                            value=qty * current_price,
                            profit_pct=profit_pct
                        )
                        
                        send_telegram_message(
                            f"⚠️ *Saída Técnica Acionada (Reversão)*\n"
                            f"📉 Preço de Saída: ${current_price:.2f}\n"
                            f"📊 Motivo: Cruzamento reverso de médias móveis.\n"
                            f"💵 Resultado estimado: {'+$' if profit_usd >= 0 else '-$'}{abs(profit_usd):.2f}"
                        )

            # --- CASO 2: ROBÔ FLAT (PROCURANDO OPORTUNIDADE DE ATAQUE) ---
            else:
                df = fetch_candles(exchange, symbol, config.TIMEFRAME)
                if df is not None:
                    df = calculate_indicators(df)
                    
                    # Pega as duas últimas linhas FECHADAS para detectar o cruzamento real confirmado
                    prev_row = df.iloc[-3]
                    last_row = df.iloc[-2]
                    
                    # Condição de Cruzamento de Alta (Fast EMA cruza acima da Slow EMA)
                    cruzamento_alta = (prev_row['ema_fast'] <= prev_row['ema_slow']) and (last_row['ema_fast'] > last_row['ema_slow'])
                    
                    # Filtro de RSI: Garante que não estamos comprando topo esticado (sobrecomprado)
                    rsi_aceitavel = last_row['rsi'] < config.RSI_OVERBOUGHT
                    
                    if cruzamento_alta and rsi_aceitavel:
                        print(f"\n🚀 [SINAL] Cruzamento de Alta detectado no tempo gráfico {config.TIMEFRAME}!")
                        print(f"📊 Indicadores: Fast EMA: {last_row['ema_fast']:.2f} | Slow EMA: {last_row['ema_slow']:.2f} | RSI: {last_row['rsi']:.1f}")
                        
                        # Executa compra
                        order, buy_price, qty_bought = buy_entry(exchange, symbol, trade_amount)
                        
                        if order is not None and qty_bought > 0:
                            # Configura parâmetros de defesa
                            state['in_position'] = True
                            state['entry_price'] = buy_price
                            state['quantity_bought'] = qty_bought
                            state['stop_loss_price'] = buy_price * (1.0 - config.STOP_LOSS_PCT)
                            state['take_profit_1'] = buy_price * (1.0 + config.TAKE_PROFIT_1_PCT)
                            state['take_profit_2'] = buy_price * (1.0 + config.TAKE_PROFIT_2_PCT)
                            state['is_partial_executed'] = False
                            save_state(state)
                            
                            # Registra compra no backend
                            register_trade_backend(
                                asset=symbol,
                                trade_type="COMPRA",
                                price=buy_price,
                                amount=qty_bought,
                                value=qty_bought * buy_price
                            )
                            
                            send_telegram_message(
                                f"🚀 *Nova Posição Aberta (COMPRA)*\n"
                                f"🪙 Ativo: {symbol}\n"
                                f"💵 Preço de Entrada: ${buy_price:.2f}\n"
                                f"📦 Qtd comprada: {qty_bought}\n\n"
                                f"🛡️ *Parâmetros de Defesa Inicial:*\n"
                                f"🛑 Stop Loss: ${state['stop_loss_price']:.2f} (-{config.STOP_LOSS_PCT*100:.1f}%)\n"
                                f"🎯 Alvo Parcial (TP1): ${state['take_profit_1']:.2f} (+{config.TAKE_PROFIT_1_PCT*100:.1f}%)\n"
                                f"🏆 Alvo Final (TP2): ${state['take_profit_2']:.2f} (+{config.TAKE_PROFIT_2_PCT*100:.1f}%)"
                            )

            # Espera o intervalo antes da próxima análise
            time.sleep(config.LOOP_INTERVAL_SECONDS)
            
        except ccxt.NetworkError as ne:
            print(f"\n[ERRO DE CONEXÃO] Problema de rede com a Binance: {ne}. Tentando novamente em 15s...")
            time.sleep(15)
        except ccxt.AuthenticationError as ae:
            print(f"\n[ERRO DE AUTENTICAÇÃO] Credenciais inválidas na Binance: {ae}. Desativando robô para segurança...")
            if backend_config is not None:
                try:
                    requests.post(f"{os.getenv('BACKEND_URL', 'http://localhost:3000')}/bot/config", json={
                        'userId': os.getenv('USER_ID', 'guest'),
                        'isActive': False
                    }, timeout=10)
                except Exception as ex:
                    print(f"[ERRO] Falha ao desativar robô no backend: {ex}")
            time.sleep(30)
        except ccxt.ExchangeError as ee:
            print(f"\n[ERRO DE EXCHANGE] Erro na API da Binance: {ee}. Verifique se seu saldo é suficiente ou suas credenciais.")
            time.sleep(30)
        except Exception as e:
            print(f"\n[ERRO CRÍTICO] Loop principal falhou: {e}. Reiniciando loop em 30s...")
            time.sleep(30)

if __name__ == '__main__':
    run_trading_bot()
